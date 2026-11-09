import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from app.ingestion.validators import (
    validate_file,
    calculate_file_hash,
)
from app.ingestion.extractors import extract_document
from app.ingestion.cleaner import clean_text
from app.ingestion.chunker import create_chunks
from app.core.database import (
    save_document,
    get_document_by_hash,
)

BASE_DIR = Path(__file__).resolve().parents[3]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def process_document(filename: str, content: bytes):
    # 1. Validate
    validate_file(filename, content)

    # 2. Duplicate check
    file_hash = calculate_file_hash(content)
    existing = get_document_by_hash(file_hash)
    if existing:
        raise FileExistsError(
            f"Document already exists with ID: {existing['id']}"
        )

    # 3. IDs and paths
    document_id = str(uuid.uuid4())
    extension = filename.lower().rsplit(".", 1)[-1]
    original_path = UPLOAD_DIR / f"{document_id}.{extension}"
    processed_path = PROCESSED_DIR / f"{document_id}.json"

    # 4. Save original file
    original_path.write_bytes(content)

    # 5. Extract
    source_units = extract_document(filename, content)

    # 6. Clean
    cleaned_units = [
        {
            "page_number": unit["page_number"],
            "paragraph_number": unit["paragraph_number"],
            "text": clean_text(unit["text"]),
        }
        for unit in source_units
        if clean_text(unit["text"])
    ]

    if not cleaned_units:
        raise ValueError("Document contains no usable text after cleaning.")

    # 7. Chunk
    chunks = create_chunks(
        cleaned_units,
        document_id=document_id,
        chunk_size=500,
        overlap=75,
    )

    if not chunks:
        raise ValueError("No chunks could be generated from the document.")

    # 8. Save processed JSON
    payload = {
        "document_id": document_id,
        "filename": filename,
        "file_type": extension,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    processed_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # 9. Metadata
    document = {
        "id": document_id,
        "filename": filename,
        "file_type": extension,
        "file_hash": file_hash,
        "status": "processed",
        "page_count": len(cleaned_units),
        "chunk_count": len(chunks),
        "original_path": str(original_path),
        "processed_path": str(processed_path),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    save_document(document)

    return {
        "document": document,
        "chunks": chunks,
    }