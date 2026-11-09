import json
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.ingestion.pipeline import process_document
from app.ingestion.validators import MAX_FILE_SIZE
from app.core.database import get_all_documents, get_document

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read(MAX_FILE_SIZE + 1)

        result = process_document(
            filename=file.filename or "unknown",
            content=content,
        )

        return {
            "success": True,
            "message": "Document uploaded and processed successfully",
            "document": result["document"],
            "chunk_preview": result["chunks"][:2],
        }

    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


@router.get("")
def list_documents():
    documents = get_all_documents()
    return {
        "success": True,
        "total_documents": len(documents),
        "documents": documents,
    }


@router.get("/{document_id}")
def get_document_details(document_id: str):
    document = get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    processed_path = Path(document["processed_path"])
    if not processed_path.exists():
        raise HTTPException(
            status_code=404, detail="Processed chunks file not found."
        )

    chunks = json.loads(processed_path.read_text(encoding="utf-8"))

    return {
        "success": True,
        "document": document,
        "chunks": chunks.get("chunks", []),
    }