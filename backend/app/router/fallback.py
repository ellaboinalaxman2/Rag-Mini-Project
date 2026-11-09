"""
Execute the selected engine, with graceful fallback if that engine fails.
"""


def execute_with_fallback(
    engine: str,
    query: str,
    document_id: str | None,
    vector_top_k: int,
    graph_depth: int,
) -> dict:
    """
    Returns:
        {
            "engine_used": <str>,
            "fallback_applied": bool,
            "fallback_reason": str | None,
            "result": <engine response>
        }
    """
    from app.vector_rag.answer import generate_answer
    from app.graph_rag.answer import generate_graph_answer
    from app.hybrid_rag.pipeline import run_hybrid

    def _run_vector():
        return generate_answer(query=query, top_k=vector_top_k)

    def _run_graph():
        return generate_graph_answer(query=query, depth=graph_depth)

    def _run_hybrid():
        return run_hybrid(
            query=query,
            document_id=document_id,
            generate_answer=True,
        )

    runners = {
        "vector": _run_vector,
        "graph": _run_graph,
        "hybrid": _run_hybrid,
    }

    order = [engine]
    # Fallback order: hybrid → vector → graph, graph → vector, vector → hybrid
    fallbacks = {
        "hybrid": ["vector", "graph"],
        "graph": ["vector"],
        "vector": ["hybrid"],
    }
    order.extend(fallbacks.get(engine, []))

    last_error = None
    for attempt_engine in order:
        try:
            result = runners[attempt_engine]()
            return {
                "engine_used": attempt_engine,
                "fallback_applied": attempt_engine != engine,
                "fallback_reason": (
                    f"Primary engine '{engine}' failed; "
                    f"used '{attempt_engine}' instead"
                    if attempt_engine != engine
                    else None
                ),
                "result": result,
            }
        except Exception as exc:
            last_error = str(exc)
            continue

    raise RuntimeError(
        f"All retrieval engines failed. Last error: {last_error}"
    )