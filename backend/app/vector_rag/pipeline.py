import json
from pathlib import Path

from app.vector_rag.embeddings import (
    generate_embeddings,
    get_embedding_model,
)
from app.vector_rag.vector_store import add_chunks

BASE_DIR = Path(__file__).resolve().parents[3]
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def index_document(document_id: str):
    file_path = PROCESSED_DIR / f"{document_id}.json"
    if not file_path.exists():
        raise ValueError("Processed document not found.")

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    chunks = data["chunks"]
    if not chunks:
        raise ValueError("Document has no chunks to index.")

    # Attach source filename into each chunk's metadata
    for chunk in chunks:
        chunk["metadata"]["source"] = data["filename"]

    texts = [chunk["text"] for chunk in chunks]
    embeddings = generate_embeddings(texts)

    if not embeddings:
        raise ValueError("Failed to generate embeddings.")

    indexed_count = add_chunks(chunks, embeddings)

    # Determine embedding dimension from the model
    model = get_embedding_model()
    dimension = model.get_sentence_embedding_dimension()

    return {
        "document_id": document_id,
        "filename": data["filename"],
        "indexed_chunks": indexed_count,
        "embedding_dimensions": dimension,
    }