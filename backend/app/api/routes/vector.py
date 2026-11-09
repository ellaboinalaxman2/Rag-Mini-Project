from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.vector_rag.pipeline import index_document
from app.vector_rag.retriever import retrieve_chunks
from app.vector_rag.answer import generate_answer
from app.core.database import get_all_documents

router = APIRouter(prefix="/api/vector", tags=["Vector RAG"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: str | None = None


class QuestionRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/index/{document_id}")
def index_single_document(document_id: str):
    try:
        result = index_document(document_id)
        return {
            "success": True,
            "message": "Document indexed successfully",
            "result": result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Indexing failed: {exc}"
        )


@router.post("/index-all")
def index_all_documents():
    documents = get_all_documents()
    if not documents:
        return {
            "success": True,
            "message": "No documents to index",
            "indexed": [],
        }

    indexed = []
    failed = []

    for doc in documents:
        try:
            result = index_document(doc["id"])
            indexed.append(result)
        except Exception as exc:
            failed.append({"document_id": doc["id"], "error": str(exc)})

    return {
        "success": True,
        "total_documents": len(documents),
        "indexed_count": len(indexed),
        "failed_count": len(failed),
        "indexed": indexed,
        "failed": failed,
    }


@router.post("/search")
def vector_search(request: SearchRequest):
    try:
        results = retrieve_chunks(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
        )
        return {
            "success": True,
            "query": request.query,
            "total_results": len(results),
            "results": results,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Search failed: {exc}"
        )


@router.post("/query")
def vector_question(request: QuestionRequest):
    try:
        result = generate_answer(
            query=request.query,
            top_k=request.top_k,
        )
        return {
            "success": True,
            "query": request.query,
            **result,
        }
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(
            status_code=500, detail="Question answering failed."
        )