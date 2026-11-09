"""
Convert heterogeneous vector + graph results into a unified evidence list
with per-source ranks, so the ranker can apply Weighted RRF.
"""


def _vector_item_to_evidence(item: dict):
    meta = item.get("metadata", {}) or {}
    return {
        "evidence_id": f"vec::{item.get('chunk_id')}",
        "kind": "chunk",
        "chunk_id": item.get("chunk_id"),
        "document_id": meta.get("document_id"),
        "text": item.get("text", ""),
        "source_filename": meta.get("source"),
        "page_number": meta.get("page_number"),
        "vector_similarity": item.get("similarity", 0.0),
        "retrieval_sources": ["vector"],
        "graph_evidence": None,
    }


def _relationship_to_evidence(rel: dict):
    text = (
        f"{rel.get('source_name')} --{rel.get('relation_type')}--> "
        f"{rel.get('target_name')}"
    )
    evidence_quote = rel.get("evidence") or ""
    if evidence_quote:
        text += f' (evidence: "{evidence_quote}")'

    return {
        "evidence_id": (
            f"rel::{rel.get('source_id')}::{rel.get('target_id')}::"
            f"{rel.get('relation_type')}::{rel.get('chunk_id') or ''}"
        ),
        "kind": "relationship",
        "chunk_id": rel.get("chunk_id"),
        "document_id": rel.get("document_id"),
        "text": text,
        "source_filename": None,
        "page_number": None,
        "vector_similarity": 0.0,
        "retrieval_sources": ["graph"],
        "graph_evidence": {
            "source_name": rel.get("source_name"),
            "source_type": rel.get("source_type"),
            "target_name": rel.get("target_name"),
            "target_type": rel.get("target_type"),
            "relation_type": rel.get("relation_type"),
            "evidence": evidence_quote,
            "depth": rel.get("depth", 1),
        },
    }


def _entity_to_evidence(entity: dict):
    text = (
        f"Entity: {entity.get('name')} "
        f"(type: {entity.get('type')})"
    )
    if entity.get("description"):
        text += f" — {entity['description']}"

    return {
        "evidence_id": f"ent::{entity.get('id')}",
        "kind": "entity",
        "chunk_id": None,
        "document_id": None,
        "text": text,
        "source_filename": None,
        "page_number": None,
        "vector_similarity": 0.0,
        "retrieval_sources": ["graph"],
        "graph_evidence": {
            "entity_id": entity.get("id"),
            "entity_name": entity.get("name"),
            "entity_type": entity.get("type"),
            "description": entity.get("description"),
        },
    }


def fuse_results(vector_results: list, graph_results: dict):
    """
    Returns:
        vector_ranked: [(evidence_dict, rank)]
        graph_ranked:  [(evidence_dict, rank)]
    Rank starts at 1 (highest relevance).
    """
    # --- Vector side (already ordered by similarity) ---
    vector_ranked = []
    for rank, item in enumerate(vector_results, start=1):
        vector_ranked.append((_vector_item_to_evidence(item), rank))

    # --- Graph side: rank by type priority then depth ---
    # Priority: relationship > entity (relationships carry more signal)
    # Within relationships: shallower depth = more relevant.
    relationships = graph_results.get("relationships", []) or []
    entities = graph_results.get("matched_entities", []) or []

    sorted_rels = sorted(
        relationships, key=lambda r: (r.get("depth", 1),)
    )

    graph_ranked = []
    for rank, rel in enumerate(sorted_rels, start=1):
        graph_ranked.append((_relationship_to_evidence(rel), rank))

    # Entities go after relationships; carry separate rank stream
    offset = len(sorted_rels)
    for idx, ent in enumerate(entities, start=1):
        graph_ranked.append((_entity_to_evidence(ent), offset + idx))

    return vector_ranked, graph_ranked