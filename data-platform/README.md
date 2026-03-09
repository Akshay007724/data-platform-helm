# Document Processor

A self-hosted document intelligence service. Upload PDFs, Word documents, Excel spreadsheets, and images — the service extracts, chunks, and indexes their content so you can search semantically and ask questions answered by an on-device LLM.

---

## Features

- **Multi-format ingestion** — PDF, DOCX/DOC, XLSX/XLS, JPG, PNG, TIFF, BMP, WebP
- **Smart OCR routing** — Digital PDFs use the fast text-layer extractor; scanned PDFs and images are automatically routed to GLM-OCR (0.9B)
- **Hybrid search** — BM25 keyword retrieval fused with HNSW vector search via Reciprocal Rank Fusion (RRF), reranked by a cross-encoder
- **RAG Q&A** — Ask natural-language questions; answers are streamed token-by-token from Qwen2.5 running locally via Ollama
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
│  ┌──────────────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │      Processor       │  │  Embedder   │  │ HybridSearch  │  │
│  │                      │  │ nomic-embed │  │ BM25 + RRF    │  │
│  │  ┌────────────────┐  │  │ clip-ViT    │  │ cross-encoder │  │
│  │  │ Smart routing  │  │  └─────────────┘  └───────────────┘  │
│  │  │ Digital PDF    │  │                                       │
│  │  │  → PyMuPDF     │  │  ┌─────────────┐  ┌───────────────┐  │
│  │  │ Scanned PDF    │  │  │  LLMService │  │   Reranker    │  │
│  │  │  → GLM-OCR     │  │  │  Qwen2.5   │  │  ms-marco     │  │
│  │  │ Images         │  │  │  via Ollama │  │  MiniLM       │  │
│  │  │  → GLM-OCR     │  │  └─────────────┘  └───────────────┘  │
│  │  └────────────────┘  │                                       │
│  └──────────────────────┘                                       │
└──────┬──────────────────────┬──────────────────────────────────┘
       │                      │
┌──────▼──────┐   ┌───────────▼──────────┐   ┌──────────────────┐
│   SQLite    │   │       ChromaDB       │   │     Ollama       │
│  documents  │   │    HNSW vectors      │   │  qwen2.5:0.5b    │
│  chunks     │   │  cosine similarity   │   │  (:11434)        │
│  (:file)    │   │     (:8001)          │   └──────────────────┘
└─────────────┘   └──────────────────────┘
```

### Components

| Component | Technology | Role |
|---|---|---|
| **API** | FastAPI + Uvicorn | Async HTTP server; background task processing |
| **Extractor (digital)** | PyMuPDF | Fast text-layer + table extraction for digital PDFs |
| **Extractor (OCR)** | `zai-org/GLM-OCR` (0.9B) | Reads scanned PDFs and image uploads; loaded lazily on first use |
| **Embedder** | `nomic-ai/nomic-embed-text-v1.5` (768-dim) + `clip-ViT-B-32` | Dense embeddings for text and images |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Re-scores top candidates for final ranking accuracy |
| **HybridSearch** | `rank-bm25` (BM25Okapi) + RRF | Fuses sparse keyword and dense vector results |
| **LLMService** | Qwen2.5 0.5B via Ollama | Streams RAG answers over SSE |
| **ChromaDB** | HNSW vector index | Persists and queries dense embeddings (768-dim cosine space) |
| **SQLite** | Two tables: `documents`, `chunks` | Tracks document metadata and raw chunk text for BM25 |
| **Ollama** | Container sidecar | Serves the local LLM; downloads model on first boot |

---

## OCR Routing

When a document is uploaded, the processor automatically chooses the best extractor:

| Input | Condition | Extractor |
|---|---|---|
| PDF | Average extracted chars/page ≥ 100 | PyMuPDF (text layer) — fast |
| PDF | Average extracted chars/page < 100 | GLM-OCR — scanned document |
| JPG / PNG / TIFF / BMP / WebP | — | GLM-OCR |
| DOCX / XLSX | — | Dedicated office extractor |

GLM-OCR is loaded lazily — the 0.9B model is only downloaded and loaded into memory the first time a scanned PDF or image is uploaded.

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
   Qwen2.5 0.5B (Ollama) ──► SSE token stream

SSE events:
  {"type":"sources","data":[{doc_id, filename, page, score, snippet}]}
  {"type":"token",  "data":"Hello"}   ← repeated per token
  {"type":"done"}
```

---

## Deployment

### Option A — Docker Compose (local / single-machine)

**Prerequisites:** Docker Desktop with at least 4 GB RAM allocated.

```bash
# 1. Enter the service directory
cd apps/document-processor

# 2. Build and start all services
docker compose up --build
```

**What happens on first boot:**
- App container downloads ~650 MB of HuggingFace models (nomic-embed, CLIP, cross-encoder) into the `hf_cache` volume — skipped on subsequent restarts.
- Ollama pulls `qwen2.5:0.5b` (~400 MB) into the `ollama_data` volume — skipped on subsequent restarts.
- GLM-OCR (~900 MB) is downloaded the first time a scanned PDF or image is uploaded.

Open `http://localhost:8000` once you see `All services ready` in the logs.

#### Services and ports

| Service | Host port | Purpose |
|---|---|---|
| `app` | `8000` | FastAPI application + UI |
| `chromadb` | `8001` | ChromaDB HTTP API (internal use only) |
| `ollama` | `11434` | Ollama LLM runtime |

#### Stopping and resetting

```bash
# Stop services (data preserved in volumes)
docker compose down

# Stop and delete all data volumes (full reset)
docker compose down -v
```

---

### Option B — GHCR + Flux GitOps (Kubernetes)

For a production deployment on Kubernetes with automated image updates, see **[deploy.md](../../deploy.md)** at the repository root.

The flow is:
```
git push to master
      ↓
GitHub Actions — lint → test → build → push to GHCR
      ↓
Flux detects new sha-* tag via ImageRepository
      ↓
ImageUpdateAutomation commits new tag to master
      ↓
Kustomization applies updated manifests → Kubernetes rolling update
```

---

## Environment Variables

All variables have defaults; only override what you need.

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Uvicorn log level |
| `CHROMA_HOST` | `chromadb` | ChromaDB hostname (use `localhost` for local dev) |
| `CHROMA_PORT` | `8000` | ChromaDB port inside Docker network (`8001` for local dev) |
| `CHROMA_COLLECTION` | `documents` | Collection name |
| `SQLITE_PATH` | `/app/data/documents.db` | SQLite database path |
| `TEXT_MODEL` | `nomic-ai/nomic-embed-text-v1.5` | Text embedding model (768-dim) |
| `IMAGE_MODEL` | `clip-ViT-B-32` | Image embedding model |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder reranker |
| `CHUNK_SIZE` | `512` | Max tokens per chunk |
| `CHUNK_OVERLAP` | `64` | Token overlap between chunks |
| `MAX_WORKERS` | `50` | Thread pool size for CPU-bound work |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama base URL |
| `LLM_MODEL` | `qwen2.5:0.5b` | Model to pull and serve |
| `RAG_CONTEXT_CHUNKS` | `5` | Top-k chunks passed to the LLM |
| `OCR_SCANNED_THRESHOLD` | `100` | Avg chars/page below which a PDF is treated as scanned |

---

## Volumes

| Volume | Mounted at | Contains |
|---|---|---|
| `app_data` | `/app/data` | SQLite database (`documents.db`) |
| `hf_cache` | `/app/hf_cache` | HuggingFace model weights (nomic-embed, CLIP, cross-encoder, GLM-OCR) |
| `chroma_data` | `/chroma/chroma` | ChromaDB vector index |
| `ollama_data` | `/root/.ollama` | Pulled Ollama models |

---

## API Reference

### Documents

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload one or more files (multipart) |
| `GET` | `/api/v1/documents` | List all documents |
| `GET` | `/api/v1/documents/{doc_id}` | Get document status and metadata |
| `DELETE` | `/api/v1/documents/{doc_id}` | Delete document and all indexed data |

Supported upload formats: `pdf`, `docx`, `doc`, `xlsx`, `xls`, `jpg`, `jpeg`, `png`, `tiff`, `tif`, `bmp`, `webp`

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
# Note: ChromaDB is mapped to host port 8001 by docker-compose
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

## Project Structure

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
│   ├── llm.py             # Ollama / Qwen2.5 streaming
│   ├── embedder.py        # Text + image embeddings
│   ├── reranker.py        # Cross-encoder reranker
│   ├── vector_store.py    # ChromaDB wrapper
│   ├── document_store.py  # SQLite documents table
│   ├── processor.py       # End-to-end doc processing pipeline (smart OCR routing)
│   ├── chunker.py         # Text + table chunking
│   └── extractors/
│       ├── base.py              # BaseExtractor, PageContent, ExtractedContent
│       ├── pdf_extractor.py     # PyMuPDF — digital PDFs
│       ├── glm_ocr_extractor.py # GLM-OCR — scanned PDFs and images
│       ├── word_extractor.py    # DOCX/DOC
│       └── excel_extractor.py  # XLSX/XLS
├── ui/
│   └── index.html         # Single-page UI
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
