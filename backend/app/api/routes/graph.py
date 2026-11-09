from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph_rag.pipeline import process_graph_document
from app.graph_rag.neo4j_store import (
    verify_connection,
    get_graph_statistics,
)
from app.graph_rag.retriever import (
    retrieve_graph_evidence,
    get_entity_details,
)
from app.graph_rag.answer import generate_graph_answer

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])


class GraphSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=20)


class GraphRetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    depth: int = Field(default=2, ge=1, le=2)


class GraphQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    depth: int = Field(default=2, ge=1, le=2)


@router.get("/health")
def graph_health():
    try:
        verify_connection()
        return {"success": True, "neo4j": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Neo4j connection failed: {exc}",
        )


@router.post("/index/{document_id}")
def index_document_graph(document_id: str):
    try:
        result = process_graph_document(document_id)
        return {
            "success": True,
            "message": "Knowledge graph construction completed",
            "result": result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Graph construction failed: {exc}",
        )


@router.get("/statistics")
def graph_statistics():
    try:
        stats = get_graph_statistics()
        return {"success": True, "statistics": stats}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch statistics: {exc}",
        )


@router.post("/search")
def graph_search(request: GraphSearchRequest):
    """Match entities for a query — no traversal."""
    try:
        from app.graph_rag.query_processor import (
            extract_candidate_phrases,
            extract_keywords,
        )
        from app.graph_rag.entity_matcher import match_entities_by_keywords

        phrases = extract_candidate_phrases(request.query)
        keywords = extract_keywords(request.query)
        matched = match_entities_by_keywords(
            phrases + keywords, max_results=request.top_k
        )
        return {
            "success": True,
            "query": request.query,
            "total_matches": len(matched),
            "matches": matched,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Graph search failed: {exc}"
        )


@router.post("/retrieve")
def graph_retrieve(request: GraphRetrieveRequest):
    """Retrieve graph evidence (entities + relationships + mentions)."""
    try:
        result = retrieve_graph_evidence(
            query=request.query, depth=request.depth
        )
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Graph retrieval failed: {exc}"
        )


@router.post("/query")
def graph_query(request: GraphQueryRequest):
    """Complete Graph RAG: retrieve + LLM answer."""
    try:
        result = generate_graph_answer(
            query=request.query, depth=request.depth
        )
        return {"success": True, "query": request.query, **result}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=500, detail="Graph RAG answering failed."
        )


@router.get("/entity/{entity_id}")
def entity_details(entity_id: str):
    try:
        details = get_entity_details(entity_id)
        if not details:
            raise HTTPException(status_code=404, detail="Entity not found.")
        return {"success": True, **details}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch entity: {exc}",
        )