import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest


def _make_doc(doc_id: str | None = None, **kwargs):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": doc_id or str(uuid.uuid4()),
        "filename": "test.pdf",
        "file_type": "pdf",
        "status": "ready",
        "chunk_count": 10,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
        **kwargs,
    }


class TestHealth:
    def test_health_ok(self, client):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestDocuments:
    def test_list_empty(self, client):
        res = client.get("/api/v1/documents")
        assert res.status_code == 200
        data = res.json()
        assert data["documents"] == []
        assert data["total"] == 0

    def test_upload_pdf(self, client):
        content = b"%PDF-1.4 fake pdf content"
        res = client.post(
            "/api/v1/documents/upload",
            files=[("files", ("test.pdf", io.BytesIO(content), "application/pdf"))],
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["uploaded"]) == 1

    def test_upload_unsupported_type(self, client):
        res = client.post(
            "/api/v1/documents/upload",
            files=[("files", ("test.txt", io.BytesIO(b"text"), "text/plain"))],
        )
        assert res.status_code == 422

    def test_get_document_not_found(self, client):
        res = client.get("/api/v1/documents/nonexistent-id")
        assert res.status_code == 404

    def test_delete_not_found(self, client):
        res = client.delete("/api/v1/documents/nonexistent-id")
        assert res.status_code == 404

    def test_upload_then_list(self, client):
        content = b"fake xlsx content"
        client.post(
            "/api/v1/documents/upload",
            files=[("files", ("data.xlsx", io.BytesIO(content), "application/vnd.ms-excel"))],
        )
        res = client.get("/api/v1/documents")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1

    def test_upload_then_get(self, client):
        content = b"fake docx content"
        upload_res = client.post(
            "/api/v1/documents/upload",
            files=[("files", ("report.docx", io.BytesIO(content), "application/vnd.openxmlformats"))],
        )
        doc_id = upload_res.json()["uploaded"][0]
        res = client.get(f"/api/v1/documents/{doc_id}")
        assert res.status_code == 200
        assert res.json()["id"] == doc_id


class TestSearch:
    def test_search_empty_query(self, client):
        res = client.post("/api/v1/search", json={"query": "  "})
        assert res.status_code == 422

    def test_search_no_results(self, client):
        res = client.post("/api/v1/search", json={"query": "test query"})
        assert res.status_code == 200
        data = res.json()
        assert data["results"] == []
        assert data["query"] == "test query"

    def test_search_with_results(self, client, mock_vec_store, mock_doc_store):
        doc_store, docs = mock_doc_store
        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        docs[doc_id] = {
            "id": doc_id,
            "filename": "sample.pdf",
            "file_type": "pdf",
            "status": "ready",
            "chunk_count": 5,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        mock_vec_store.search = AsyncMock(
            return_value=[
                {
                    "score": 0.92,
                    "payload": {
                        "type": "text",
                        "content": "Sample content here",
                        "doc_id": doc_id,
                        "page": 1,
                    },
                }
            ]
        )
        res = client.post("/api/v1/search", json={"query": "sample"})
        assert res.status_code == 200
        data = res.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["score"] == pytest.approx(0.92)
        assert data["results"][0]["filename"] == "sample.pdf"
