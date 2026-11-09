"""
Centralized routing policy — all thresholds and keyword lists live here.
Tune here during Phase 10 evaluation, not scattered across modules.
"""

# --- Relationship-indicating keywords (higher → graph bias) ---
RELATIONSHIP_KEYWORDS = {
    "relationship", "relate", "related", "connect", "connection",
    "connected", "link", "linked", "between", "depends", "depend",
    "depend", "uses", "use", "using", "develop", "developed",
    "develops", "own", "owns", "owned", "produce", "produces",
    "produced", "works", "work", "work together", "together",
    "associate", "associated", "part of", "belongs", "belong",
    "through", "via", "chain", "path", "how does", "how do",
    "who developed", "who owns", "who created",
}

# --- Semantic / definitional keywords (higher → vector bias) ---
SEMANTIC_KEYWORDS = {
    "what is", "what are", "define", "definition", "meaning",
    "explain", "explanation", "describe", "summary", "summarize",
    "overview", "detail", "details", "information about",
    "tell me about", "how does", "how can", "why is", "why does",
    "example", "examples", "concept", "concept of",
}

# --- Multi-hop / reasoning indicators ---
MULTIHOP_KEYWORDS = {
    "through", "via", "chain", "path", "indirectly",
    "ultimately", "eventually", "leads to", "result", "results",
    "consequence", "because of", "due to", "which leads",
}

# --- Comparison / analysis keywords ---
COMPARISON_KEYWORDS = {
    "compare", "comparison", "difference", "differences",
    "vs", "versus", "better", "worse", "best", "worst",
    "contrast", "unlike", "similar", "similarity",
}

# --- Summary intent keywords ---
SUMMARY_KEYWORDS = {
    "summarize", "summary", "overview", "brief", "recap",
    "summarise", "key points", "main points",
}

# --- Thresholds (tunable via .env, but defaults here for safety) ---
ENTITY_DENSITY_THRESHOLD = 2
RELATIONSHIP_KEYWORD_WEIGHT = 0.35
SEMANTIC_KEYWORD_WEIGHT = 0.35
HYBRID_CONFIDENCE_THRESHOLD = 0.55
GRAPH_CONFIDENCE_THRESHOLD = 0.55
VECTOR_CONFIDENCE_THRESHOLD = 0.45
VECTOR_TOP_K = 8
GRAPH_DEPTH = 2


def get_policy() -> dict:
    """Read .env overrides with defaults from this module."""
    import os

    def _float(name, default):
        try:
            return float(os.getenv(name, default))
        except (TypeError, ValueError):
            return default

    def _int(name, default):
        try:
            return int(os.getenv(name, default))
        except (TypeError, ValueError):
            return default

    return {
        "entity_density_threshold": _int(
            "ROUTER_ENTITY_DENSITY_THRESHOLD", ENTITY_DENSITY_THRESHOLD
        ),
        "relationship_keyword_weight": _float(
            "ROUTER_RELATIONSHIP_KEYWORD_WEIGHT", RELATIONSHIP_KEYWORD_WEIGHT
        ),
        "semantic_keyword_weight": _float(
            "ROUTER_SEMANTIC_KEYWORD_WEIGHT", SEMANTIC_KEYWORD_WEIGHT
        ),
        "hybrid_confidence_threshold": _float(
            "ROUTER_HYBRID_CONFIDENCE_THRESHOLD", HYBRID_CONFIDENCE_THRESHOLD
        ),
        "graph_confidence_threshold": _float(
            "ROUTER_GRAPH_CONFIDENCE_THRESHOLD", GRAPH_CONFIDENCE_THRESHOLD
        ),
        "vector_confidence_threshold": _float(
            "ROUTER_VECTOR_CONFIDENCE_THRESHOLD", VECTOR_CONFIDENCE_THRESHOLD
        ),
        "vector_top_k": _int("ROUTER_VECTOR_TOP_K", VECTOR_TOP_K),
        "graph_depth": _int("ROUTER_GRAPH_DEPTH", GRAPH_DEPTH),
    }