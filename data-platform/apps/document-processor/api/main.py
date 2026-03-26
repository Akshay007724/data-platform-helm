import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.config import settings
from api.middleware import MaxBodySizeMiddleware
from api.routes import documents, search
from api.routes import ask
from models.schemas import HealthResponse
from services.chunk_store import ChunkStore
from services.document_store import DocumentStore
from services.embedder import Embedder
from services.hybrid_search import HybridSearch
from services.image_store import ImageStore
from services.llm import LLMService
from services.processor import DocumentProcessor
from services.reranker import Reranker
from services.vector_store import VectorStore

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

UI_PATH = Path(__file__).parent.parent / "ui" / "index.html"
UI_ASSETS_PATH = Path(__file__).parent.parent / "ui" / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — loading models and initialising services")

    embedder = Embedder()
    reranker = Reranker()
    doc_store = DocumentStore()
    vec_store = VectorStore(embedder)
    chunk_store = ChunkStore()
    image_store = ImageStore()
    hybrid_search = HybridSearch()
    llm_service = LLMService()

    await chunk_store.init()
    await image_store.init()
    await doc_store.init()
    await vec_store.ensure_collection()

    chunks = await chunk_store.get_all()
    hybrid_search.build(chunks)
    hybrid_search.set_chunk_store(chunk_store)

    processor = DocumentProcessor(
        doc_store, vec_store, embedder, chunk_store, hybrid_search, image_store
    )

    await llm_service.ensure_model()

    app.state.embedder = embedder
    app.state.reranker = reranker
    app.state.doc_store = doc_store
    app.state.vec_store = vec_store
    app.state.chunk_store = chunk_store
    app.state.image_store = image_store
    app.state.hybrid_search = hybrid_search
    app.state.llm_service = llm_service
    app.state.processor = processor

    logger.info("All services ready")
    yield

    await vec_store.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Document Processor",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    MaxBodySizeMiddleware,
    max_bytes=settings.max_upload_size_mb * 1024 * 1024,
)

app.include_router(documents.router)
app.include_router(search.router)
app.include_router(ask.router)

app.mount("/assets", StaticFiles(directory=UI_ASSETS_PATH), name="assets")


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(UI_PATH)
