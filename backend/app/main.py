from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.documents import router as document_router
from app.api.routes.vector import router as vector_router
from app.api.routes.graph import router as graph_router
from app.api.routes.hybrid import router as hybrid_router
from app.api.routes.router import router as router_router
from app.api.routes.monitoring import router as monitoring_router  # NEW
from app.api.routes.evaluation import router as evaluation_router
from app.core.database import initialize_database
from app.graph_rag.neo4j_store import initialize_graph

app = FastAPI(
    title="Intelligent RAG Routing API",
    description="Adaptive Vector RAG, Graph RAG and Hybrid RAG platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    initialize_database()
    try:
        initialize_graph()
        print("[startup] Neo4j graph initialized")
    except Exception as exc:
        print(f"[startup] Neo4j initialization failed: {exc}")


@app.get("/")
def root():
    return {
        "message": "Intelligent RAG Routing API is running",
        "status": "success",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "backend",
    }


app.include_router(document_router)
app.include_router(vector_router)
app.include_router(graph_router)
app.include_router(hybrid_router)
app.include_router(router_router)
app.include_router(monitoring_router)  # NEW
app.include_router(evaluation_router)