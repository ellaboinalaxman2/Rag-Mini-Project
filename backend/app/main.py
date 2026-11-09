from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Intelligent RAG Routing API",
    description="Adaptive Vector RAG, Graph RAG and Hybrid RAG platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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