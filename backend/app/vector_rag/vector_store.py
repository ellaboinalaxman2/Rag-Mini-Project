from pathlib import Path
import json
import sqlite3

import numpy as np

try:
    import chromadb
    CHROMA_AVAILABLE = True
except Exception as exc:
    # Some managed Windows environments block Chroma's bundled gRPC DLL.
    # Keep local development usable with a persistent SQLite cosine index.
    print(f"[vector-store] ChromaDB unavailable ({exc}); using SQLite fallback")
    CHROMA_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parents[3]
CHROMA_DIR = BASE_DIR / "data" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

if CHROMA_AVAILABLE:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name="knowledge_chunks",
        metadata={"hnsw:space": "cosine"},
    )
else:
    client = None
    collection = None
    FALLBACK_DB = BASE_DIR / "data" / "vectors.sqlite3"
    with sqlite3.connect(FALLBACK_DB) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS vectors (
            id TEXT PRIMARY KEY, document TEXT NOT NULL, metadata TEXT NOT NULL,
            embedding TEXT NOT NULL)""")


def _fallback_upsert(ids, documents, metadatas, embeddings):
    with sqlite3.connect(FALLBACK_DB) as connection:
        connection.executemany(
            "INSERT INTO vectors(id,document,metadata,embedding) VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET document=excluded.document, "
            "metadata=excluded.metadata, embedding=excluded.embedding",
            [(i, d, json.dumps(m), json.dumps(e)) for i, d, m, e in zip(ids, documents, metadatas, embeddings)],
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

    if collection is not None:
        collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    else:
        _fallback_upsert(ids, documents, metadatas, embeddings)
    return len(ids)


def search_vectors(query_embedding, top_k: int = 5, document_id: str | None = None):
    if not query_embedding:
        raise ValueError("Query embedding is required.")

    if collection is None:
        with sqlite3.connect(FALLBACK_DB) as connection:
            rows = connection.execute(
                "SELECT id,document,metadata,embedding FROM vectors"
            ).fetchall()
        if document_id:
            rows = [row for row in rows if json.loads(row[2]).get("document_id") == document_id]
        query = np.asarray(query_embedding, dtype=float)
        scored = []
        for row in rows:
            vector = np.asarray(json.loads(row[3]), dtype=float)
            denom = np.linalg.norm(query) * np.linalg.norm(vector)
            similarity = float(np.dot(query, vector) / denom) if denom else 0.0
            scored.append((similarity, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:top_k]
        return {
            "ids": [[row[0] for _, row in top]],
            "documents": [[row[1] for _, row in top]],
            "metadatas": [[json.loads(row[2]) for _, row in top]],
            "distances": [[1.0 - score for score, _ in top]],
        }
    where = {"document_id": document_id} if document_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    return results


def get_collection_count():
    if collection is not None:
        return collection.count()
    with sqlite3.connect(FALLBACK_DB) as connection:
        return connection.execute("SELECT count(*) FROM vectors").fetchone()[0]


def document_indexed(document_id: str) -> bool:
    if collection is None:
        with sqlite3.connect(FALLBACK_DB) as connection:
            return connection.execute(
                "SELECT 1 FROM vectors WHERE json_extract(metadata, '$.document_id') = ? LIMIT 1",
                (document_id,),
            ).fetchone() is not None
    result = collection.get(where={"document_id": document_id}, limit=1)
    return len(result.get("ids", [])) > 0
