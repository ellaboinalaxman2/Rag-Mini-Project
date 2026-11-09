"""
Parallel retrieval from Vector RAG and Graph RAG.
Runs both engines, captures per-source errors so one failure doesn't
kill the whole hybrid request.
"""
import time

from app.vector_rag.retriever import retrieve_chunks
from app.graph_rag.retriever import retrieve_graph_evidence


def _run_vector(query: str, top_k: int, document_id: str | None):
    start = time.perf_counter()
    try:
        results = retrieve_chunks(
            query=query, top_k=top_k, document_id=document_id
        )
        return results, None, round((time.perf_counter() - start) * 1000, 1)
    except Exception as exc:
        return [], str(exc), round((time.perf_counter() - start) * 1000, 1)


def _run_graph(query: str, depth: int):
    start = time.perf_counter()
    try:
        results = retrieve_graph_evidence(query=query, depth=depth)
        return results, None, round((time.perf_counter() - start) * 1000, 1)
    except Exception as exc:
        return {
            "query": query,
            "keywords": [],
            "matched_entities": [],
            "relationships": [],
            "mentions": [],
            "traversal_depth": depth,
        }, str(exc), round((time.perf_counter() - start) * 1000, 1)


def hybrid_retrieve(
    query: str,
    vector_top_k: int = 10,
    graph_depth: int = 2,
    document_id: str | None = None,
):
    """
    Run both retrievals sequentially (Python 3.10+ still serial; we can
    parallelize later with ThreadPoolExecutor if needed — the LLM/embedding
    call is the bottleneck, so serial is fine at this stage).
    """
    vector_results, vector_error, vector_ms = _run_vector(
        query, vector_top_k, document_id
    )
    graph_results, graph_error, graph_ms = _run_graph(query, graph_depth)

    return {
        "vector_results": vector_results,
        "vector_error": vector_error,
        "vector_latency_ms": vector_ms,
        "graph_results": graph_results,
        "graph_error": graph_error,
        "graph_latency_ms": graph_ms,
    }