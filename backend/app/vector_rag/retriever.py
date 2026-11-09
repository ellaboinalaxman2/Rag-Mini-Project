from app.vector_rag.embeddings import generate_query_embedding
from app.vector_rag.vector_store import (
    search_vectors,
    get_collection_count,
)


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
):
    query = query.strip()
    if not query:
        raise ValueError("Search query cannot be empty.")

    if top_k < 1 or top_k > 20:
        raise ValueError("top_k must be between 1 and 20.")

    total = get_collection_count()
    if total == 0:
        return []

    query_embedding = generate_query_embedding(query)

    results = search_vectors(
        query_embedding=query_embedding,
        top_k=top_k,
        document_id=document_id,
    )

    retrieved = []

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i in range(len(ids)):
        distance = distances[i] if i < len(distances) else 1.0
        similarity = 1.0 - distance  # cosine distance → similarity

        metadata = metadatas[i] if i < len(metadatas) else {}

        # Clean sentinel -1 values back to None
        page_number = metadata.get("page_number")
        paragraph_number = metadata.get("paragraph_number")
        if page_number == -1:
            page_number = None
        if paragraph_number == -1:
            paragraph_number = None

        retrieved.append(
            {
                "chunk_id": ids[i],
                "text": documents[i] if i < len(documents) else "",
                "metadata": {
                    "document_id": metadata.get("document_id"),
                    "source": metadata.get("source"),
                    "page_number": page_number,
                    "paragraph_number": paragraph_number,
                    "chunk_index": metadata.get("chunk_index"),
                    "word_count": metadata.get("word_count"),
                },
                "similarity": round(similarity, 4),
            }
        )

    return retrieved