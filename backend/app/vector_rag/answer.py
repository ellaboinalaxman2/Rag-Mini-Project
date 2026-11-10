import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.vector_rag.retriever import retrieve_chunks
from app.router.model_selector import assess_question_burden

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")

RELEVANCE_THRESHOLD = float(os.getenv("VECTOR_RELEVANCE_THRESHOLD", "0.45"))


SYSTEM_PROMPT = (
    "You are a helpful AI assistant that answers questions strictly "
    "based on the provided document context. Cite sources using [S1], "
    "[S2], etc., matching the provided source list. If the context does "
    "not contain enough information, say so clearly. Do not invent facts."
)


def _build_context(results):
    context_blocks = []
    for idx, item in enumerate(results, start=1):
        source = item["metadata"].get("source") or "unknown"
        page = item["metadata"].get("page_number")
        page_str = f", page {page}" if page else ""
        context_blocks.append(
            f"[S{idx}] (source: {source}{page_str})\n{item['text']}"
        )
    return "\n\n".join(context_blocks)


def _general_fallback(query: str, reason: str, complexity_info: dict | None = None):
    """Answer using LLM's general knowledge when documents don't help, selecting model by question burden."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    burden_info = assess_question_burden(query, complexity_info)
    model = burden_info["model"]

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant. The user asked a question that "
                    "is not covered by the uploaded documents. Answer using your "
                    "general knowledge. Be clear that this is NOT from their documents."
                ),
            },
            {"role": "user", "content": query},
        ],
        temperature=0.3,
    )

    answer_text = response.choices[0].message.content
    if not answer_text or not answer_text.strip():
        raise RuntimeError("The LLM provider returned an empty answer.")

    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "answer": answer_text,
        "sources": [],
        "retrieval_method": "general_fallback",
        "fallback_reason": reason,
        "burden": burden_info["burden"],
        "burden_reason": burden_info["reason"],
        "model": model,
        "usage": usage,
    }


def generate_answer(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
    complexity_info: dict | None = None,
):
    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    results = retrieve_chunks(
        query=query,
        top_k=top_k,
        document_id=document_id,
    )

    # Filter by relevance
    relevant = [
        r for r in results if r.get("similarity", 0) >= RELEVANCE_THRESHOLD
    ]

    if not relevant:
        return _general_fallback(
            query,
            reason="no_relevant_chunks",
            complexity_info=complexity_info,
        )

    context = _build_context(relevant)

    user_message = (
        f"Question: {query}\n\n"
        f"Document Context:\n{context}\n\n"
        "Answer the question using only the context above. "
        "Cite sources like [S1], [S2] next to relevant statements."
    )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )

    answer_text = response.choices[0].message.content
    if not answer_text or not answer_text.strip():
        raise RuntimeError("The LLM provider returned an empty answer.")

    sources = []
    for idx, item in enumerate(relevant, start=1):
        sources.append(
            {
                "source_id": f"S{idx}",
                "chunk_id": item["chunk_id"],
                "document_id": item["metadata"].get("document_id"),
                "filename": item["metadata"].get("source"),
                "page_number": item["metadata"].get("page_number"),
                "similarity": item["similarity"],
            }
        )

    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "answer": answer_text,
        "sources": sources,
        "retrieval_method": "vector",
        "model": model_name,
        "usage": usage,
    }