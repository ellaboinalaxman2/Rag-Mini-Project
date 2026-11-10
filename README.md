# Intelligent RAG Routing

A local document question-answering platform that combines vector retrieval, a Neo4j knowledge graph, adaptive routing, and LLMOps monitoring.

## What it does

- **Document RAG:** Upload PDF or DOCX files. Text is extracted, chunked, embedded, and automatically added to the vector index. Answers cite the retrieved document sources.
- **Adaptive model routing:** Questions with no relevant document evidence are answered from general AI knowledge. The model is selected by estimated question burden using `GROQ_LIGHT_MODEL`, `GROQ_MEDIUM_MODEL`, and `GROQ_HEAVY_MODEL`.
- **Knowledge graph:** Build a document's entities and relationships in Neo4j from the Documents page. The Graph Explorer visualizes the stored graph.
- **Hybrid retrieval:** Combines vector and graph evidence, ranks it, and generates a cited answer.
- **Routing analytics:** Inspect routing decisions and see engine usage and fallback counts.
- **LLMOps Monitor Center:** View query health, model/provider usage, estimated cost, latency, cache activity, and Prometheus-format metrics.
- **Evaluation Center:** Run up to 10 benchmark questions against optional reference answers and expected documents, inspect per-case answers and retrieval, and reopen saved runs.
- **Animated dashboard:** The React interface includes animated navigation, graph exploration, and analytics visualizations.

## Requirements

- Windows 10/11
- Python 3.12
- Node.js compatible with Vite 8
- Docker Desktop with Docker Compose (needed for Neo4j and Redis)
- A Groq API key for answer generation and graph extraction

## Setup on Windows

Run commands from the project directory.

1. Copy `.env.example` to `.env`. Set `GROQ_API_KEY` and, if needed, adjust the model IDs. The default Neo4j credentials used by Compose are `neo4j` and `password123`; configure matching `NEO4J_USERNAME` and `NEO4J_PASSWORD` values in `.env` if you change them.

2. Start the supporting services:

   ```powershell
   docker compose up -d
   ```

3. Install and start the backend:

   ```powershell
   py -3.12 -m venv backend\venv
   .\backend\venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
   .\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend
   ```

   The API is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

4. In a second terminal, install and start the frontend:

   ```powershell
   Set-Location .\frontend
   npm install
   npm run dev
   ```

   Open `http://localhost:5173`. Set `VITE_API_URL` before starting Vite if the backend is not at `http://localhost:8000`.

## First use

1. Open **Documents** and upload a PDF or DOCX. New uploads are automatically processed and vector-indexed. If indexing fails, the UI reports the error and the document remains available for retry with the **Vector** action.
2. Ask questions in **AI Assistant**. Choose **All indexed documents** or a specific document. Vector, graph, and hybrid retrieval honor the selected document scope. If evidence is insufficient, the router uses the general-model fallback and identifies that the answer is not from the uploaded documents.
3. Use the **Graph** action on a document to extract and store its entities and relationships. This requires Neo4j and a configured Groq key; graph extraction is intentionally separate because it can take longer and make additional model calls.
4. Explore graph data in **Graph Explorer**, inspect decisions in **Routing Analytics**, and monitor runtime usage in **LLMOps Monitoring**.
5. In **Evaluation Center**, create a small repeatable set of questions. Add reference answers to measure token-overlap F1 and select an expected document to measure document retrieval hits. Evaluation run history is stored in the local SQLite database.

Documents uploaded before automatic vector indexing was added may need the **Vector** action once before they can answer document questions. Graph indexing is a separate action.

## Configuration

Important `.env` settings:

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Required for generated answers and graph extraction |
| `GROQ_MODEL` | Model used for evidence-grounded answers |
| `GROQ_LIGHT_MODEL` | Model for low-burden general questions |
| `GROQ_MEDIUM_MODEL` | Model for medium-burden general questions |
| `GROQ_HEAVY_MODEL` | Model for high-burden general questions |
| `VECTOR_RELEVANCE_THRESHOLD` | Minimum vector similarity to use document evidence |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | Neo4j connection |
| `REDIS_URL`, `CACHE_ENABLED`, `CACHE_TTL_SECONDS` | Query cache settings |
| `VITE_API_URL` | Frontend API base URL |

Use model identifiers available to your configured Groq account. The application returns provider/indexing errors to the UI rather than treating an empty model response as a successful answer.

After changing `.env`, restart the backend so its process reloads the updated model configuration. A model that has been retired or is not enabled for your Groq account will fail even while the backend health indicator says it is connected.

## Validation

Backend unit tests:

```powershell
Set-Location .\backend
.\venv\Scripts\python.exe -m unittest discover -s ..\tests -v
```

Frontend lint and production build:

```powershell
Set-Location .\frontend
npm run lint
npm run build
```

## Notes

- Neo4j and Redis are optional for vector-only Q&A; graph and cache capabilities require their respective services.
- Query counters, latency samples, token counts, and cost estimates are maintained by the running backend process and reset when it restarts.
- Estimated costs use the configured per-model pricing values and are for operational guidance, not billing.
- Evaluation answer F1 is a lexical token-overlap metric, not a semantic or LLM-judge score. Evaluation requests run the router directly and are not added to live LLMOps query counters.
