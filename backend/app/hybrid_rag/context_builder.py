"""
Build a token-bounded, citation-friendly context string from deduped
evidence.
"""
from app.config.settings import settings

DEFAULT_MAX_CHARS = getattr(settings, "HYBRID_MAX_CONTEXT_CHARS", 8000)


def _label_for(item: dict, index: int):
    kind = item["kind"]
    if kind == "chunk":
        return f"[C{index}]"
    if kind == "relationship":
        return f"[G{index}]"
    return f"[E{index}]"


def build_context(evidence_list: list, max_chars: int = DEFAULT_MAX_CHARS):
    if not evidence_list:
        return {
            "text": "(no evidence retrieved)",
            "sources": [],
            "total_chars": 0,
            "truncated": False,
        }

    blocks = []
    sources = []
    total = 0
    truncated = False

    for idx, item in enumerate(evidence_list, start=1):
        label = _label_for(item, idx)

        source_line = (
            item.get("source_filename")
            or item.get("document_id")
            or "graph"
        )
        page = item.get("page_number")
        if page:
            source_line += f", page {page}"

        header = (
            f"{label} ({item['kind']}; "
            f"sources={','.join(item['retrieval_sources'])}; "
            f"score={item['fusion_score']:.4f}; "
            f"origin={source_line})"
        )

        block = f"{header}\n{item['text']}"

        if total + len(block) > max_chars:
            truncated = True
            break

        blocks.append(block)
        total += len(block)

        sources.append(
            {
                "label": label,
                "evidence_id": item["evidence_id"],
                "kind": item["kind"],
                "chunk_id": item.get("chunk_id"),
                "document_id": item.get("document_id"),
                "source_filename": item.get("source_filename"),
                "page_number": item.get("page_number"),
                "retrieval_sources": item["retrieval_sources"],
                "fusion_score": round(item["fusion_score"], 6),
            }
        )

    return {
        "text": "\n\n".join(blocks),
        "sources": sources,
        "total_chars": total,
        "truncated": truncated,
    }