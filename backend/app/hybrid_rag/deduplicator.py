"""
Deduplicate merged evidence while preserving retrieval provenance.

Two rules:
  1. Exact evidence_id collapse — keeps the highest fusion_score.
  2. Chunk-level collapse — when a relationship's chunk_id matches a
     vector chunk's chunk_id, keep the vector chunk (richer text) but
     attach the relationship as graph_evidence on that entry.
"""


def deduplicate(ranked_evidence: list):
    by_id: dict[str, dict] = {}
    by_chunk: dict[str, dict] = {}

    for item in ranked_evidence:
        eid = item["evidence_id"]

        # Rule 1: exact duplicate → keep higher score
        existing = by_id.get(eid)
        if existing:
            if item["fusion_score"] > existing["fusion_score"]:
                by_id[eid] = item
            continue
        by_id[eid] = item

    # Rule 2: chunk-level merge
    final = []
    for item in by_id.values():
        chunk_id = item.get("chunk_id")
        if item["kind"] == "chunk" and chunk_id:
            by_chunk[chunk_id] = item

    # Attach relationship evidence to matching chunk entries
    for item in by_id.values():
        if item["kind"] == "relationship" and item.get("chunk_id"):
            chunk_entry = by_chunk.get(item["chunk_id"])
            if chunk_entry:
                # Enrich chunk text with the relationship fact
                chunk_entry["text"] = (
                    chunk_entry["text"]
                    + "\n\n[Graph fact] "
                    + item["text"]
                )
                chunk_entry.setdefault("attached_relationships", []).append(
                    item["graph_evidence"]
                )
                # Accumulate graph as a retrieval source on the chunk
                if "graph" not in chunk_entry["retrieval_sources"]:
                    chunk_entry["retrieval_sources"].append("graph")

    # Any relationship whose chunk wasn't retrieved stays as standalone
    for item in by_id.values():
        if item["kind"] == "relationship" and item.get("chunk_id"):
            if item["chunk_id"] in by_chunk:
                continue
        final.append(item)

    # Also append chunk entries that weren't already added
    for chunk_entry in by_chunk.values():
        if chunk_entry not in final:
            final.append(chunk_entry)

    # Re-rank after dedup so enrichment doesn't break ordering
    final.sort(key=lambda e: e["fusion_score"], reverse=True)
    return final