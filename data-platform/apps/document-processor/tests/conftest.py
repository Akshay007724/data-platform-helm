import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def make_mock_embedder():
    emb = MagicMock()
    emb.text_dim = 768
    emb.image_dim = 512
    emb.embed_texts.return_value = [[0.1] * 768]
    emb.embed_query.return_value = [0.1] * 768
    emb.embed_image.return_value = [0.2] * 512
    emb.embed_image_caption.return_value = [0.1] * 512
    return emb


def make_mock_doc_store():
    import uuid
    from datetime import datetime, timezone

    store = MagicMock()
    _docs: dict[str, dict] = {}

    async def create(doc_id, filename, file_type):
        now = datetime.now(timezone.utc).isoformat()
        _docs[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "status": "pending",
            "chunk_count": 0,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        return _docs[doc_id]

    async def get(doc_id):
        return _docs.get(doc_id)

    async def list_all():
        return list(_docs.values())

    async def update_status(doc_id, status, chunk_count=None, error_message=None):
        if doc_id in _docs:
            _docs[doc_id]["status"] = status
            if chunk_count is not None:
                _docs[doc_id]["chunk_count"] = chunk_count
            _docs[doc_id]["error_message"] = error_message

    async def delete(doc_id):
        return _docs.pop(doc_id, None) is not None

    async def init():
        pass

    store.create = AsyncMock(side_effect=create)
    store.get = AsyncMock(side_effect=get)
    store.list_all = AsyncMock(side_effect=list_all)
    store.update_status = AsyncMock(side_effect=update_status)
    store.delete = AsyncMock(side_effect=delete)
    store.init = AsyncMock(side_effect=init)
    return store, _docs


def make_mock_vec_store():
    store = MagicMock()
    store.ensure_collection = AsyncMock()
    store.upsert_text_point = AsyncMock()
    store.upsert_image_point = AsyncMock()
    store.delete_by_doc_id = AsyncMock()
    store.close = AsyncMock()
    store.search = AsyncMock(return_value=[])
    return store


def make_mock_reranker():
    reranker = MagicMock()
    # Pass results through unchanged — scores already set by vec_store mock
    reranker.rerank = MagicMock(side_effect=lambda query, results, top_k: results[:top_k])
    return reranker


@pytest.fixture
def mock_embedder():
    return make_mock_embedder()


@pytest.fixture
def mock_reranker():
    return make_mock_reranker()


@pytest.fixture
def mock_doc_store():
    store, docs = make_mock_doc_store()
    return store, docs


@pytest.fixture
def mock_vec_store():
    return make_mock_vec_store()


@pytest.fixture
def client(mock_embedder, mock_doc_store, mock_vec_store, mock_reranker):
    doc_store, _ = mock_doc_store
    vec_store = mock_vec_store

    mock_processor = MagicMock()
    mock_processor.process = AsyncMock()

    with patch("api.main.Embedder", return_value=mock_embedder), \
         patch("api.main.Reranker", return_value=mock_reranker), \
         patch("api.main.DocumentStore", return_value=doc_store), \
         patch("api.main.VectorStore", return_value=vec_store), \
         patch("api.main.DocumentProcessor", return_value=mock_processor):
        from api.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
