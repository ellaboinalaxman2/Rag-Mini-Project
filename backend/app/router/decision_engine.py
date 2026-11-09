"""
Select retrieval strategy based on intent + complexity + policy thresholds.
"""
from app.router.routing_policy import get_policy


def decide_engine(features: dict, intent_info: dict, complexity: dict) -> dict:
    policy = get_policy()

    intent = intent_info["intent"]
    requires_vector = intent_info["requires_vector"]
    requires_graph = intent_info["requires_graph"]
    requires_multihop = intent_info["requires_multihop"]
    entity_count = features.get("entity_count", 0)

    # --- Compute per-engine scores [0, 1] ---
    vector_score = 0.0
    graph_score = 0.0

    if requires_vector:
        vector_score += 0.50
    if features.get("semantic_hits"):
        vector_score += policy["semantic_keyword_weight"]
    if intent in ("definition", "summary"):
        vector_score += 0.25
    if complexity["entity_density"] == "low":
        vector_score += 0.10
    vector_score = min(vector_score, 1.0)

    if requires_graph:
        graph_score += 0.50
    if features.get("relationship_hits"):
        graph_score += policy["relationship_keyword_weight"]
    if requires_multihop:
        graph_score += 0.20
    if entity_count >= policy["entity_density_threshold"]:
        graph_score += 0.10
    graph_score = min(graph_score, 1.0)

    # --- Decide ---
    reason = ""
    confidence = 0.0

    if requires_vector and requires_graph:
        selected = "hybrid"
        confidence = round(min(1.0, (vector_score + graph_score) / 2 + 0.15), 3)
        reason = (
            "Query requires both semantic document evidence and "
            "relationship/graph reasoning"
        )
    elif requires_graph and not requires_vector:
        if graph_score >= policy["graph_confidence_threshold"]:
            selected = "graph"
            confidence = round(graph_score, 3)
            reason = (
                "Query targets entity relationships or multi-hop facts "
                "without needing broad document context"
            )
        else:
            # weak graph signal → fall back to vector
            selected = "vector"
            confidence = round(policy["vector_confidence_threshold"] + 0.05, 3)
            reason = (
                "Graph intent detected but graph score below threshold; "
                "falling back to vector retrieval"
            )
    elif requires_vector and not requires_graph:
        selected = "vector"
        confidence = round(
            max(vector_score, policy["vector_confidence_threshold"]), 3
        )
        reason = (
            "Query asks for definitions, summaries, or general document "
            "information — semantic retrieval is sufficient"
        )
    else:
        selected = "vector"
        confidence = 0.40
        reason = "Default fallback to vector retrieval"

    return {
        "selected_engine": selected,
        "confidence": confidence,
        "reason": reason,
        "scores": {
            "vector": round(vector_score, 3),
            "graph": round(graph_score, 3),
        },
    }