"""
Complete Phase 7 routing pipeline.
"""
import re

from app.router.query_analyzer import analyze_query
from app.router.intent_classifier import classify_intent
from app.router.complexity_analyzer import analyze_complexity
from app.router.decision_engine import decide_engine
from app.router.fallback import execute_with_fallback
from app.router.routing_policy import get_policy


def _normalize_response(query, engine_used, routing_meta, engine_result):
    """
    Normalize across Vector / Graph / Hybrid response shapes so the API
    consumer gets a consistent contract.
    """
    answer = engine_result.get("answer")
    sources = engine_result.get("sources", []) or []
    retrieval_method = engine_result.get("retrieval_method", engine_used)
    fallback_reason = (
        engine_result.get("fallback_reason")
        or routing_meta.get("fallback_reason")
    )
    burden = engine_result.get("burden") or routing_meta.get("burden")
    burden_reason = engine_result.get("burden_reason") or routing_meta.get("burden_reason")
    model = engine_result.get("model")
    usage = engine_result.get("usage", {})

    return {
        "query": query,
        "routing": routing_meta,
        "retrieval_method": retrieval_method,
        "fallback_reason": fallback_reason,
        "burden": burden,
        "burden_reason": burden_reason,
        "engine_used": engine_used,
        "answer": answer,
        "sources": sources,
        "model": model,
        "usage": usage,
        "raw_engine_result": {
            k: v
            for k, v in engine_result.items()
            if k
            in (
                "vector_results",
                "graph_results",
                "merged_results",
                "deduplicated_results",
                "matched_entities",
                "relationships",
                "traversal_depth",
                "context",
            )
        },
    }


def route_query(
    query: str,
    document_id: str | None = None,
    force_engine: str | None = None,
) -> dict:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if force_engine and force_engine not in ("vector", "graph", "hybrid"):
        raise ValueError(
            "force_engine must be one of: vector, graph, hybrid"
        )

    policy = get_policy()

    # --- 1. Analyze ---
    features = analyze_query(query)
    intent_info = classify_intent(features)
    complexity = analyze_complexity(features, intent_info)

    # --- 2. Decide (unless forced) ---
    if force_engine:
        decision = {
            "selected_engine": force_engine,
            "confidence": 1.0,
            "reason": f"Engine forced to '{force_engine}' by caller",
            "scores": {},
        }
    else:
        decision = decide_engine(features, intent_info, complexity)

    # --- 3. Execute with fallback ---
    exec_result = execute_with_fallback(
        engine=decision["selected_engine"],
        query=query,
        document_id=document_id,
        vector_top_k=policy["vector_top_k"],
        graph_depth=policy["graph_depth"],
        complexity_info=complexity,
    )

    # --- 4. Build routing metadata ---
    engine_result = exec_result["result"]
    is_general_fallback = (
        engine_result.get("retrieval_method") == "general_fallback"
    )
    fallback_applied = (
        exec_result["fallback_applied"] or is_general_fallback
    )
    fallback_reason = (
        engine_result.get("fallback_reason")
        or exec_result["fallback_reason"]
    )
    burden = engine_result.get("burden")
    burden_reason = engine_result.get("burden_reason")

    routing_meta = {
        "selected_engine": decision["selected_engine"],
        "engine_used": exec_result["engine_used"],
        "intent": intent_info["intent"],
        "entity_count": features["entity_count"],
        "entity_candidates": features["entity_candidates"],
        "requires_graph": intent_info["requires_graph"],
        "requires_vector": intent_info["requires_vector"],
        "requires_multihop": intent_info["requires_multihop"],
        "entity_density": complexity["entity_density"],
        "relationship_complexity": complexity["relationship_complexity"],
        "estimated_hops": complexity["estimated_hops"],
        "overall_complexity": complexity["overall_complexity"],
        "burden": burden,
        "burden_reason": burden_reason,
        "routing_confidence": decision["confidence"],
        "scores": decision["scores"],
        "reason": decision["reason"],
        "fallback_applied": fallback_applied,
        "fallback_reason": fallback_reason,
        "features": {
            "relationship_hits": features["relationship_hits"],
            "semantic_hits": features["semantic_hits"],
            "multihop_hits": features["multihop_hits"],
            "comparison_hits": features["comparison_hits"],
            "summary_hits": features["summary_hits"],
        },
    }

    return _normalize_response(
        query=query,
        engine_used=exec_result["engine_used"],
        routing_meta=routing_meta,
        engine_result=engine_result,
    )


def analyze_only(query: str) -> dict:
    """Analyze + decide without executing retrieval."""
    features = analyze_query(query)
    intent_info = classify_intent(features)
    complexity = analyze_complexity(features, intent_info)
    decision = decide_engine(features, intent_info, complexity)

    return {
        "query": query,
        "features": features,
        "intent": intent_info,
        "complexity": complexity,
        "decision": decision,
    }