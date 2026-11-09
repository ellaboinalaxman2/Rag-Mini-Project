"""
Estimate query complexity and relationship-reasoning depth requirement.
"""


def analyze_complexity(features: dict, intent_info: dict) -> dict:
    entity_count = features.get("entity_count", 0)
    rel_hits = len(features.get("relationship_hits", []))
    multi_hits = len(features.get("multihop_hits", []))
    comp_hits = len(features.get("comparison_hits", []))
    word_count = features.get("word_count", 0)

    # --- Entity density ---
    if entity_count >= 3:
        entity_density = "high"
    elif entity_count == 2:
        entity_density = "medium"
    else:
        entity_density = "low"

    # --- Relationship complexity ---
    if multi_hits > 0 or rel_hits >= 2:
        relationship_complexity = "high"
    elif rel_hits == 1 or (entity_count >= 2 and intent_info["requires_graph"]):
        relationship_complexity = "medium"
    else:
        relationship_complexity = "low"

    # --- Multi-hop estimate (capped at 2 to match Neo4j hard-limit) ---
    if multi_hits > 0 or entity_count >= 4:
        estimated_hops = 2
    elif intent_info.get("requires_multihop"):
        estimated_hops = 2
    elif intent_info.get("requires_graph") or entity_count >= 2:
        estimated_hops = 1
    else:
        estimated_hops = 0

    # --- Overall complexity band ---
    if entity_density == "high" and relationship_complexity == "high":
        overall = "high"
    elif comp_hits > 0 or relationship_complexity == "medium":
        overall = "medium"
    elif word_count > 20:
        overall = "medium"
    else:
        overall = "low"

    return {
        "entity_density": entity_density,
        "relationship_complexity": relationship_complexity,
        "estimated_hops": estimated_hops,
        "overall_complexity": overall,
    }