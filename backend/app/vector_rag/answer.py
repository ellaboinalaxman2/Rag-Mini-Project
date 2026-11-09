import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.vector_rag.retriever import retrieve_chunks

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


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


def generate_answer(query: str, top_k: int = 5):
    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_MODEL")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    if not model_name:
        raise RuntimeError("GROQ_MODEL is not configured.")

    results = retrieve_chunks(query=query, top_k=top_k)

    if not results:
        return {
            "answer": "I could not find relevant information in the uploaded documents.",
            "sources": [],
            "retrieval_method": "vector",
            "model": model_name,
            "usage": {},
        }

    context = _build_context(results)

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

    sources = []
    for idx, item in enumerate(results, start=1):
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