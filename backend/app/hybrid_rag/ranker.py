"""
Weighted Reciprocal Rank Fusion.

    RRF(d) = Σ_s  w_s / (k + rank_s(d))
"""
from app.hybrid_rag.fusion import fuse_results


def _rrf_score(rank: int, weight: float, k: int) -> float:
    return weight / (k + rank)


def rank_evidence(
    vector_results: list,
    graph_results: dict,
    vector_weight: float = 0.5,
    graph_weight: float = 0.5,
    rrf_k: int = 60,
):
    """
    Returns a list of merged evidence dicts, sorted by descending RRF score.
    Each item includes:
        - all original fields
        - 'fusion_score'
        - 'retrieval_sources' (accumulated across sources)
    """
    vector_ranked, graph_ranked = fuse_results(
        vector_results, graph_results
    )

    merged: dict[str, dict] = {}

    # Seed from vector stream
    for evidence, rank in vector_ranked:
        eid = evidence["evidence_id"]
        entry = merged.get(eid)
        if not entry:
            entry = {**evidence, "fusion_score": 0.0}
            merged[eid] = entry
        entry["fusion_score"] += _rrf_score(rank, vector_weight, rrf_k)

    # Merge graph stream
    for evidence, rank in graph_ranked:
        eid = evidence["evidence_id"]
        entry = merged.get(eid)
        if not entry:
            entry = {**evidence, "fusion_score": 0.0}
            merged[eid] = entry
        else:
            # Accumulate retrieval sources
            for src in evidence["retrieval_sources"]:
                if src not in entry["retrieval_sources"]:
                    entry["retrieval_sources"].append(src)
        entry["fusion_score"] += _rrf_score(rank, graph_weight, rrf_k)

    ranked = sorted(
        merged.values(),
        key=lambda e: e["fusion_score"],
        reverse=True,
    )
    return ranked