import hashlib
import re
import unicodedata


def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = unicodedata.normalize("NFKC", name)
    name = name.strip().lower()
    name = re.sub(r"\s+", " ", name)
    return name


def generate_entity_id(name: str, entity_type: str) -> str:
    normalized_name = normalize_name(name)
    normalized_type = normalize_name(entity_type)
    identity = f"{normalized_type}:{normalized_name}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def generate_relation_id(
    source_id: str,
    target_id: str,
    relation_type: str,
    document_id: str,
    chunk_id: str,
) -> str:
    identity = (
        f"{source_id}|{target_id}|"
        f"{normalize_name(relation_type)}|"
        f"{document_id}|{chunk_id}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()