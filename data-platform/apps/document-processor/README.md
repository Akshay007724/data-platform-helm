# Document Processor

A self-hosted document intelligence service. Upload PDFs, Word documents, and Excel spreadsheets — the service extracts, chunks, and indexes their content so you can search semantically and ask questions answered by an on-device LLM.

---

## Features

- **Multi-format ingestion** — PDF, DOCX/DOC, XLSX/XLS
- **Hybrid search** — BM25 keyword retrieval fused with HNSW vector search via Reciprocal Rank Fusion (RRF), reranked by a cross-encoder
- **RAG Q&A** — Ask natural-language questions; answers are streamed token-by-token from DeepSeek-R1 running locally via Ollama
- **Image understanding** — Embedded images are indexed using CLIP and returned in search results
- **Fully local** — No external API calls; all models run on your machine

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser UI                               │
│         Upload · Documents · Search · Ask                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI app (:8000)                        │
│                                                                 │
│  POST /upload   GET /documents   POST /search   POST /ask       │
│                                                                 │
│  ┌────────────┐  ┌─────────────┐  ┌────────────────────────┐   │
│  │ Processor  │  │  Embedder   │  │     HybridSearch       │   │
│  │            │  │ nomic-embed │  │  BM25Okapi + RRF       │   │
│  │ Extract    │  │ clip-ViT    │  │  + cross-encoder       │   │
│  │ Chunk      │  └─────────────┘  └────────────────────────┘   │
│  │ Embed      │                                                 │
│  │ Index      │  ┌─────────────┐  ┌────────────────────────┐   │
│  └────────────┘  │  LLMService │  │      Reranker          │   │
│                  │  DeepSeek   │  │  ms-marco-MiniLM       │   │
│                  │  via Ollama │  └────────────────────────┘   │
│                  └─────────────┘                                │
└──────┬──────────────────────┬──────────────────────────────────┘
       │                      │
┌──────▼──────┐   ┌───────────▼──────────┐   ┌──────────────────┐
│   SQLite    │   │       ChromaDB       │   │     Ollama       │
│  documents  │   │    HNSW vectors      │   │  deepseek-r1:1.5b│
│  chunks     │   │  cosine similarity   │   │  (:11434)        │
│  (:file)    │   │     (:8001)          │   └──────────────────┘
└─────────────┘   └──────────────────────┘
```

### Components

| Component | Technology | Role |
|---|---|---|
| **API** | FastAPI + Uvicorn | Async HTTP server; background task processing |
| **Embedder** | `nomic-ai/nomic-embed-text-v1.5` + `clip-ViT-B-32` | Dense embeddings for text and images |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Re-scores top candidates for final ranking accuracy |
| **HybridSearch** | `rank-bm25` (BM25Okapi) + RRF | Fuses sparse keyword and dense vector results |
| **LLMService** | DeepSeek-R1 1.5B via Ollama | Streams RAG answers over SSE |
| **ChromaDB** | HNSW vector index | Persists and queries dense embeddings |
| **SQLite** | Two tables: `documents`, `chunks` | Tracks document metadata and raw chunk text for BM25 |
| **Ollama** | Container sidecar | Serves the local LLM; downloads model on first boot |

---

## Search Pipeline

```
Query
 ├─► embed_query() ──────────► ChromaDB HNSW ──► top-N vector hits
 └─► BM25Okapi.get_scores() ──────────────────► top-N BM25 hits
                   │
                   ▼
             RRF fusion (k=60)    1/(k+rank) per retriever
                   │
                   ▼
          cross-encoder rerank ──► top-limit results
```

**Why hybrid?** Dense vectors capture semantic meaning but miss exact keyword matches. BM25 excels at keyword recall. RRF merges both ranked lists without needing score normalisation.

---

## Q&A Pipeline

```
Question
 └─► HybridSearch (above) ──► top-k chunks
         │
         ▼
   cross-encoder rerank ──► top-5 context passages
         │
         ▼
   DeepSeek-R1 (Ollama) ──► SSE token stream

SSE events:
  {"type":"sources","data":[{doc_id, filename, page, score, snippet}]}
  {"type":"token",  "data":"Hello"}   ← repeated per token
  {"type":"done"}
```

---

## Deployment

### Prerequisites

- Docker and Docker Compose
- ~5 GB disk space (models + data)
- 8 GB RAM recommended (4 GB minimum with swap)

### Quick start

```bash
# 1. Clone and enter the service directory
cd apps/document-processor

# 2. Copy and review environment config
cp .env.example .env

# 3. Build and start all services
docker compose up --build
```

On first boot the app container downloads ~650 MB of HuggingFace models at build time. Ollama pulls `deepseek-r1:1.5b` (~1.1 GB) on first startup — this is cached in the `ollama_data` volume and skipped on subsequent restarts.

Open `http://localhost:8000` once you see `All services ready` in the logs.

### Services and ports

| Service | Host port | Purpose |
|---|---|---|
| `app` | `8000` | FastAPI application + UI |
| `chromadb` | `8001` | ChromaDB HTTP API (internal use) |
| `ollama` | `11434` | Ollama LLM runtime |

### Environment variables

All variables have defaults; only override what you need.

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Uvicorn log level |
| `CHROMA_HOST` | `chromadb` | ChromaDB hostname |
| `CHROMA_PORT` | `8000` | ChromaDB port |
| `CHROMA_COLLECTION` | `documents` | Collection name |
| `SQLITE_PATH` | `/app/data/documents.db` | SQLite database path |
| `TEXT_MODEL` | `nomic-ai/nomic-embed-text-v1.5` | Text embedding model |
| `IMAGE_MODEL` | `clip-ViT-B-32` | Image embedding model |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder reranker |
| `CHUNK_SIZE` | `512` | Max tokens per chunk |
| `CHUNK_OVERLAP` | `64` | Token overlap between chunks |
| `MAX_WORKERS` | `50` | Thread pool size for CPU-bound work |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama base URL |
| `LLM_MODEL` | `deepseek-r1:1.5b` | Model to pull and serve |
| `RAG_CONTEXT_CHUNKS` | `5` | Top-k chunks passed to the LLM |

### Volumes

| Volume | Mounted at | Contains |
|---|---|---|
| `app_data` | `/app/data` | SQLite database (`documents.db`) |
| `hf_cache` | `/app/hf_cache` | HuggingFace model weights |
| `chroma_data` | `/chroma/chroma` | ChromaDB vector index |
| `ollama_data` | `/root/.ollama` | Pulled Ollama models |

### Stopping and resetting

```bash
# Stop services (data preserved)
docker compose down

# Stop and delete all data volumes (full reset)
docker compose down -v
```

---

## API Reference

### Documents

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload one or more files (multipart) |
| `GET` | `/api/v1/documents` | List all documents |
| `GET` | `/api/v1/documents/{doc_id}` | Get document status and metadata |
| `DELETE` | `/api/v1/documents/{doc_id}` | Delete document and all indexed data |

### Search

```
POST /api/v1/search
{
  "query": "what is the refund policy?",
  "limit": 10,
  "doc_ids": ["abc123"]   // optional — filter to specific documents
}
```

### Ask

```
POST /api/v1/ask
{
  "question": "Summarise the key risks mentioned",
  "limit": 5,
  "doc_ids": ["abc123"]   // optional
}
```

Returns a `text/event-stream` SSE response:

```
data: {"type":"sources","data":[{"doc_id":"...","filename":"report.pdf","page":3,"score":0.91,"snippet":"..."}]}

data: {"type":"token","data":"The "}
data: {"type":"token","data":"key "}
...
data: {"type":"done"}
```

### Health

```
GET /api/v1/health
→ {"status":"ok","version":"0.1.0"}
```

---

## Development

### Running locally (without Docker)

```bash
# Start ChromaDB and Ollama only
docker compose up chromadb ollama -d

# Install Python dependencies
pip install -r requirements.txt

# Point the app at local services
export CHROMA_HOST=localhost
export CHROMA_PORT=8001
export OLLAMA_URL=http://localhost:11434
export SQLITE_PATH=./data/documents.db

# Run the app
uvicorn api.main:app --reload --port 8000
```

### Running tests

```bash
pytest
```

### Linting

```bash
ruff check .
```

---

## Project structure

```
apps/document-processor/
├── api/
│   ├── config.py          # Pydantic settings (env-driven)
│   ├── main.py            # FastAPI app, lifespan startup
│   └── routes/
│       ├── documents.py   # Upload / list / delete endpoints
│       ├── search.py      # Hybrid search endpoint
│       └── ask.py         # SSE Q&A endpoint
├── models/
│   └── schemas.py         # Request/response Pydantic models
├── services/
│   ├── chunk_store.py     # SQLite chunks table (BM25 corpus)
│   ├── hybrid_search.py   # BM25 + RRF fusion
│   ├── llm.py             # Ollama / DeepSeek streaming
│   ├── embedder.py        # Text + image embeddings
│   ├── reranker.py        # Cross-encoder reranker
│   ├── vector_store.py    # ChromaDB wrapper
│   ├── document_store.py  # SQLite documents table
│   ├── processor.py       # End-to-end doc processing pipeline
│   ├── chunker.py         # Text + table chunking
│   └── extractors/        # PDF, Word, Excel extraction
│       ├── pdf_extractor.py
│       ├── word_extractor.py
│       └── excel_extractor.py
├── ui/
│   └── index.html         # Single-page UI
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
