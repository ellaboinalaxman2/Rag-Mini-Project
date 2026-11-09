import hashlib
from pathlib import Path

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def validate_file(filename: str, content: bytes) -> bool:
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF and DOCX files are supported.")

    if not content:
        raise ValueError("Uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("File size exceeds the 10 MB limit.")

    # File signature checks
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF file.")

    if extension == ".docx":
        if not content.startswith(b"PK"):
            raise ValueError("Invalid DOCX file.")

    return True


def calculate_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()