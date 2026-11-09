"""
Coordinates Phase 6: retrieve → fuse → rank → dedup → context.
Optionally generates an LLM answer.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.config.settings import settings
from app.hybrid_rag.retriever import hybrid_retrieve
from app.hybrid_rag.ranker import rank_evidence
from app.hybrid_rag.deduplicator import deduplicate
from app.hybrid_rag.context_builder import build_context

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


HYBRID_SYSTEM_PROMPT = (
    "You are a hybrid RAG assistant. You receive evidence extracted from "
    "BOTH a vector database (document chunks, labeled [C*]) AND a "
    "knowledge graph (facts and entities, labeled [G*] and [E*]). "
    "Answer using ONLY this evidence. Cite chunks as [C1], [C2] etc. and "
    "graph facts as [G1], [G2] etc. Prefer graph facts when they directly "
    "answer relational questions. If evidence is insufficient, say so."
)


def _cfg(name: str, default):
    return getattr(settings, name, default)


def run_hybrid(
    query: str,
    document_id: str | None = None,
    generate_answer: bool = True,
):
    vector_top_k = int(_cfg("HYBRID_VECTOR_TOP_K", 10))
    graph_depth = int(_cfg("HYBRID_GRAPH_DEPTH", 2))
    vector_weight = float(_cfg("HYBRID_VECTOR_WEIGHT", 0.5))
    graph_weight = float(_cfg("HYBRID_GRAPH_WEIGHT", 0.5))
    rrf_k = int(_cfg("HYBRID_RRF_K", 60))
    top_k = int(_cfg("HYBRID_TOP_K", 10))
    max_chars = int(_cfg("HYBRID_MAX_CONTEXT_CHARS", 8000))

    # --- 1. Parallel-safe retrieval ---
    retrieval = hybrid_retrieve(
        query=query,
        vector_top_k=vector_top_k,
        graph_depth=graph_depth,
        document_id=document_id,
    )

    vector_results = retrieval["vector_results"]
    graph_results = retrieval["graph_results"]

    # --- 2. Weighted RRF ---
    ranked = rank_evidence(
        vector_results=vector_results,
        graph_results=graph_results,
        vector_weight=vector_weight,
        graph_weight=graph_weight,
        rrf_k=rrf_k,
    )

    # --- 3. Deduplicate ---
    deduped = deduplicate(ranked)

    # --- 4. Trim to top_k ---
    deduped = deduped[:top_k]

    # --- 5. Build context ---
    context = build_context(deduped, max_chars=max_chars)

    response = {
        "query": query,
        "retrieval_method": "hybrid",
        "vector_results": len(vector_results),
        "graph_results": (
            len(graph_results.get("relationships", []) or [])
            + len(graph_results.get("matched_entities", []) or [])
        ),
        "merged_results": len(ranked),
        "deduplicated_results": len(deduped),
        "context": context,
        "weights": {
            "vector": vector_weight,
            "graph": graph_weight,
            "rrf_k": rrf_k,
        },
        "latency_ms": {
            "vector": retrieval["vector_latency_ms"],
            "graph": retrieval["graph_latency_ms"],
        },
        "errors": {
            "vector": retrieval["vector_error"],
            "graph": retrieval["graph_error"],
        },
    }

    # --- 6. Optional LLM answer ---
    if not generate_answer:
        response["answer"] = None
        return response

    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_MODEL")

    if not api_key or not model_name:
        response["answer"] = None
        response["answer_error"] = (
            "GROQ_API_KEY or GROQ_MODEL not configured."
        )
        return response

    if not deduped:
        response["answer"] = (
            "I could not find relevant evidence in either the vector "
            "store or the knowledge graph."
        )
        return response

    user_message = (
        f"Question: {query}\n\n"
        f"Unified Evidence:\n{context['text']}\n\n"
        "Answer the question using only the evidence above. "
        "Cite with [C*], [G*], [E*] labels."
    )

    try:
        client = Groq(api_key=api_key)
        llm_response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": HYBRID_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
        response["answer"] = llm_response.choices[0].message.content
        response["model"] = model_name
        if llm_response.usage:
            response["usage"] = {
                "prompt_tokens": llm_response.usage.prompt_tokens,
                "completion_tokens": llm_response.usage.completion_tokens,
                "total_tokens": llm_response.usage.total_tokens,
            }
    except Exception as exc:
        response["answer"] = None
        response["answer_error"] = f"LLM call failed: {exc}"

    return response