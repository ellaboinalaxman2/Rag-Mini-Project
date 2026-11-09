from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def generate_embeddings(texts: list[str]):
    if not texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


def generate_query_embedding(query: str):
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    model = get_embedding_model()
    embedding = model.encode(
        [query.strip()],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return embedding[0].tolist()