import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "documents.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                chunk_count INTEGER NOT NULL,
                original_path TEXT NOT NULL,
                processed_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_document_by_hash(file_hash: str):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        return dict(row) if row else None


def save_document(document: dict):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO documents (
                id, filename, file_type, file_hash, status,
                page_count, chunk_count, original_path,
                processed_path, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document["id"],
                document["filename"],
                document["file_type"],
                document["file_hash"],
                document["status"],
                document["page_count"],
                document["chunk_count"],
                document["original_path"],
                document["processed_path"],
                document["uploaded_at"],
            ),
        )
        connection.commit()


def get_all_documents():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_document(document_id: str):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        return dict(row) if row else None