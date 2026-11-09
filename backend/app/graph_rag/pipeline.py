import json
from pathlib import Path

from app.graph_rag.extractor import extract_graph_data
from app.graph_rag.normalizer import (
    normalize_name,
    generate_entity_id,
    generate_relation_id,
)
from app.graph_rag.neo4j_store import (
    clear_document_graph,
    create_document_node,
    create_entity_nodes,
    create_mentions,
    create_relationships,
)
from app.core.database import get_document

BASE_DIR = Path(__file__).resolve().parents[3]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

ALLOWED_ENTITY_TYPES = {
    "PERSON",
    "ORGANIZATION",
    "TECHNOLOGY",
    "PRODUCT",
    "LOCATION",
    "CONCEPT",
    "EVENT",
}


def _validate_entity(entity: dict) -> dict | None:
    name = (entity.get("name") or "").strip()
    etype = (entity.get("type") or "").strip().upper()
    description = (entity.get("description") or "").strip()

    if not name or etype not in ALLOWED_ENTITY_TYPES:
        return None

    return {
        "name": name,
        "type": etype,
        "description": description,
        "normalized_name": normalize_name(name),
        "id": generate_entity_id(name, etype),
    }


def _evidence_present(evidence: str, source_text: str) -> bool:
    if not evidence:
        return False
    # Case-insensitive, whitespace-normalized substring check
    evidence_norm = " ".join(evidence.lower().split())
    text_norm = " ".join(source_text.lower().split())
    return evidence_norm in text_norm


def _validate_relationship(rel: dict, chunk_text: str) -> bool:
    if not rel.get("source") or not rel.get("target"):
        return False
    if not rel.get("relation_type"):
        return False
    evidence = (rel.get("evidence") or "").strip()
    return _evidence_present(evidence, chunk_text)


def process_graph_document(document_id: str):
    document = get_document(document_id)
    if not document:
        raise ValueError("Document not found in metadata store.")

    processed_path = Path(document["processed_path"])
    if not processed_path.exists():
        raise ValueError("Processed chunks file not found.")

    with processed_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    chunks = data.get("chunks", [])
    if not chunks:
        raise ValueError("Document has no chunks to process.")

    filename = data.get("filename", document["filename"])
    file_type = data.get("file_type", document["file_type"])

    # Reset any previous graph for this document (idempotent re-index)
    try:
        clear_document_graph(document_id)
    except Exception:
        # Non-fatal: proceed if cleanup failed (e.g., first time indexing)
        pass

    create_document_node(document_id, filename, file_type)

    all_entities_by_id: dict[str, dict] = {}
    all_mentions: list[dict] = []
    all_relationships: list[dict] = []

    total_chunks = len(chunks)
    successful_chunks = 0
    failed_chunks = 0
    errors = []

    for chunk in chunks:
        chunk_text = chunk.get("text", "")
        chunk_id = chunk.get("chunk_id")

        try:
            extracted = extract_graph_data(chunk_text)
        except Exception as exc:
            failed_chunks += 1
            errors.append(f"{chunk_id}: {exc}")
            continue

        chunk_entities = extracted.get("entities", [])
        chunk_relationships = extracted.get("relationships", [])

        # 1. Validate entities for this chunk
        local_entity_by_name: dict[str, dict] = {}

        for raw in chunk_entities:
            entity = _validate_entity(raw)
            if not entity:
                continue

            all_entities_by_id[entity["id"]] = entity

            local_entity_by_name[entity["normalized_name"]] = entity

            all_mentions.append(
                {
                    "entity_id": entity["id"],
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "evidence": chunk_text[:500],
                }
            )

        # 2. Validate relationships for this chunk
        for rel in chunk_relationships:
            if not _validate_relationship(rel, chunk_text):
                continue

            source_name = normalize_name(rel.get("source", ""))
            target_name = normalize_name(rel.get("target", ""))

            source_entity = local_entity_by_name.get(source_name)
            target_entity = local_entity_by_name.get(target_name)

            if not source_entity or not target_entity:
                continue
            if source_entity["id"] == target_entity["id"]:
                continue

            relation_type = (rel.get("relation_type") or "").strip().upper()
            rel_id = generate_relation_id(
                source_id=source_entity["id"],
                target_id=target_entity["id"],
                relation_type=relation_type,
                document_id=document_id,
                chunk_id=chunk_id,
            )

            all_relationships.append(
                {
                    "id": rel_id,
                    "source_id": source_entity["id"],
                    "target_id": target_entity["id"],
                    "relation_type": relation_type,
                    "evidence": (rel.get("evidence") or "").strip(),
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "extraction_method": "groq-llm",
                }
            )

        successful_chunks += 1

    # 3. Persist to Neo4j
    entity_list = list(all_entities_by_id.values())
    create_entity_nodes(entity_list)
    create_mentions(all_mentions)
    create_relationships(all_relationships)

    return {
        "document_id": document_id,
        "filename": filename,
        "total_chunks": total_chunks,
        "successfully_extracted_chunks": successful_chunks,
        "failed_chunks": failed_chunks,
        "total_entities": len(entity_list),
        "total_mentions": len(all_mentions),
        "total_relationships": len(all_relationships),
        "errors": errors,
    }