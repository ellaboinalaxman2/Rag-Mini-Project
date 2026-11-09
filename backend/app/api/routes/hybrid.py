from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.hybrid_rag.pipeline import run_hybrid

router = APIRouter(prefix="/api/hybrid", tags=["Hybrid RAG"])


class HybridRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    document_id: str | None = None
    generate_answer: bool = True


@router.post("/retrieve")
def hybrid_retrieve_endpoint(request: HybridRequest):
    """Retrieval + fusion + context (no LLM by default? see below)."""
    try:
        result = run_hybrid(
            query=request.query,
            document_id=request.document_id,
            generate_answer=request.generate_answer,
        )
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Hybrid retrieval failed: {exc}"
        )


@router.post("/query")
def hybrid_query_endpoint(request: HybridRequest):
    """Full hybrid RAG: retrieve + fuse + LLM answer (answer forced on)."""
    try:
        result = run_hybrid(
            query=request.query,
            document_id=request.document_id,
            generate_answer=True,
        )
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Hybrid query failed: {exc}"
        )