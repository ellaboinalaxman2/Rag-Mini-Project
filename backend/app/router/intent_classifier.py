"""
Classify query intent and identify which retrieval capability it needs.
"""

INTENTS = {
    "definition": "Semantic explanation of a concept",
    "summary": "Summarization of content",
    "entity_lookup": "Find information about a named entity",
    "relationship": "Discover relationship between entities",
    "comparison": "Compare two or more things",
    "multihop_reasoning": "Reason over chained relationships",
    "general": "General question",
}


def classify_intent(features: dict) -> dict:
    """
    Input: output of query_analyzer.analyze_query
    Output: {intent, requires_vector, requires_graph, requires_multihop}
    """
    rel_hits = features.get("relationship_hits", [])
    sem_hits = features.get("semantic_hits", [])
    multi_hits = features.get("multihop_hits", [])
    comp_hits = features.get("comparison_hits", [])
    sum_hits = features.get("summary_hits", [])
    entity_count = features.get("entity_count", 0)

    # Priority order matters — multi-hop trumps plain relationship
    if multi_hits and (rel_hits or entity_count >= 2):
        intent = "multihop_reasoning"
        requires_graph = True
        requires_vector = True
        requires_multihop = True
    elif comp_hits:
        intent = "comparison"
        requires_graph = entity_count >= 2
        requires_vector = True
        requires_multihop = False
    elif rel_hits and entity_count >= 1:
        intent = "relationship"
        requires_graph = True
        requires_vector = bool(sem_hits)
        requires_multihop = False
    elif sum_hits:
        intent = "summary"
        requires_graph = False
        requires_vector = True
        requires_multihop = False
    elif sem_hits and entity_count == 0:
        intent = "definition"
        requires_graph = False
        requires_vector = True
        requires_multihop = False
    elif entity_count >= 1 and not sem_hits:
        intent = "entity_lookup"
        requires_graph = True
        requires_vector = False
        requires_multihop = False
    elif entity_count >= 1 and sem_hits:
        # Query names an entity AND asks for explanation
        intent = "relationship"
        requires_graph = True
        requires_vector = True
        requires_multihop = False
    else:
        intent = "general"
        requires_graph = False
        requires_vector = True
        requires_multihop = False

    return {
        "intent": intent,
        "intent_description": INTENTS[intent],
        "requires_vector": requires_vector,
        "requires_graph": requires_graph,
        "requires_multihop": requires_multihop,
    }