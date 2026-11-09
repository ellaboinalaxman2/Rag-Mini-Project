from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_ENV: str = "development"

    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    DB_PATH: Path = BASE_DIR / "data" / "documents.db"

    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: set = {".pdf", ".docx"}

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 75

    # Hybrid RAG (Phase 6)
    HYBRID_VECTOR_WEIGHT: float = 0.5
    HYBRID_GRAPH_WEIGHT: float = 0.5
    HYBRID_RRF_K: int = 60
    HYBRID_TOP_K: int = 10
    HYBRID_VECTOR_TOP_K: int = 10
    HYBRID_GRAPH_TOP_K: int = 10
    HYBRID_GRAPH_DEPTH: int = 2
    HYBRID_MAX_CONTEXT_CHARS: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)