from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    status: Literal["pending", "processing", "ready", "error"]
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class UploadResponse(BaseModel):
    uploaded: list[str]
    message: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    doc_ids: list[str] | None = None


class SearchResult(BaseModel):
    doc_id: str
    filename: str
    score: float
    content: str
    page: int | None
    result_type: Literal["text", "image"]


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str


class HealthResponse(BaseModel):
    status: str
    version: str


class AskRequest(BaseModel):
    question: str
    limit: int = 5
    doc_ids: list[str] | None = None


class SourceReference(BaseModel):
    doc_id: str
    filename: str
    page: int | None
    score: float
    snippet: str
