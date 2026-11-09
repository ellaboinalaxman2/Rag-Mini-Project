from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.router.pipeline import route_query, analyze_only
from app.router.routing_policy import get_policy

router = APIRouter(prefix="/api/router", tags=["Intelligent Router"])


class RouterQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    document_id: str | None = None
    force_engine: str | None = Field(
        default=None,
        description="Optional override: vector | graph | hybrid",
    )


class RouterAnalyzeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


@router.get("/health")
def router_health():
    return {
        "success": True,
        "router": "ready",
        "strategies": ["vector", "graph", "hybrid"],
    }


@router.get("/strategies")
def router_strategies():
    policy = get_policy()
    return {
        "success": True,
        "strategies": [
            {
                "name": "vector",
                "description": "Semantic document retrieval via ChromaDB",
                "best_for": [
                    "definitions",
                    "summaries",
                    "general questions",
                    "concept explanations",
                ],
            },
            {
                "name": "graph",
                "description": "Entity relationship traversal via Neo4j",
                "best_for": [
                    "entity lookups",
                    "relationship discovery",
                    "who/what/which entity questions",
                ],
            },
            {
                "name": "hybrid",
                "description": "Combined vector + graph retrieval with RRF",
                "best_for": [
                    "multi-hop reasoning",
                    "comparison questions",
                    "queries needing both context and relationships",
                ],
            },
        ],
        "policy": policy,
    }


@router.post("/analyze")
def router_analyze(request: RouterAnalyzeRequest):
    try:
        result = analyze_only(request.query)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Analysis failed: {exc}"
        )


@router.post("/query")
def router_query(request: RouterQueryRequest):
    try:
        result = route_query(
            query=request.query,
            document_id=request.document_id,
            force_engine=request.force_engine,
        )
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Routing failed: {exc}"
        )