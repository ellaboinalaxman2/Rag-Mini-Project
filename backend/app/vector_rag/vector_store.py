from pathlib import Path

import chromadb

BASE_DIR = Path(__file__).resolve().parents[3]
CHROMA_DIR = BASE_DIR / "data" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

client = chromadb.PersistentClient(path=str(CHROMA_DIR))

collection = client.get_or_create_collection(
    name="knowledge_chunks",
    metadata={"hnsw:space": "cosine"},
)


def add_chunks(chunks, embeddings):
    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings count mismatch.")

    if not chunks:
        return 0

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk["chunk_id"])
        documents.append(chunk["text"])
        metadatas.append(
            {
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "page_number": (
                    chunk["metadata"].get("page_number")
                    if chunk["metadata"].get("page_number") is not None
                    else -1
                ),
                "paragraph_number": (
                    chunk["metadata"].get("paragraph_number")
                    if chunk["metadata"].get("paragraph_number") is not None
                    else -1
                ),
                "word_count": chunk["metadata"].get("word_count", 0),
                "source": chunk["metadata"].get("source", "unknown"),
            }
        )

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return len(ids)


def search_vectors(query_embedding, top_k: int = 5, document_id: str | None = None):
    if not query_embedding:
        raise ValueError("Query embedding is required.")

    where = {"document_id": document_id} if document_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    return results


def get_collection_count():
    return collection.count()


def document_indexed(document_id: str) -> bool:
    result = collection.get(where={"document_id": document_id}, limit=1)
    return len(result.get("ids", [])) > 0