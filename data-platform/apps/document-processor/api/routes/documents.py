import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.requests import Request

from models.schemas import DocumentListResponse, DocumentResponse, UploadResponse

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

ALLOWED_TYPES = {"pdf", "xlsx", "xls", "docx", "doc", "jpg", "jpeg", "png", "tiff", "tif", "bmp", "webp"}


def _get_services(request: Request):
    return request.app.state.doc_store, request.app.state.processor


def _doc_response(row: dict) -> DocumentResponse:
    return DocumentResponse(**row)


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
) -> UploadResponse:
    doc_store, processor = _get_services(request)
    uploaded_ids: list[str] = []

    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
        if ext not in ALLOWED_TYPES:
            raise HTTPException(status_code=422, detail=f"Unsupported file type: {ext}")

        doc_id = str(uuid.uuid4())
        file_bytes = await file.read()
        await doc_store.create(doc_id, file.filename, ext)
        background_tasks.add_task(processor.process, doc_id, file.filename, file_bytes)
        uploaded_ids.append(doc_id)

    return UploadResponse(uploaded=uploaded_ids, message=f"Processing {len(uploaded_ids)} file(s)")


@router.get("", response_model=DocumentListResponse)
async def list_documents(request: Request) -> DocumentListResponse:
    doc_store, _ = _get_services(request)
    docs = await doc_store.list_all()
    return DocumentListResponse(
        documents=[_doc_response(d) for d in docs],
        total=len(docs),
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, request: Request) -> DocumentResponse:
    doc_store, _ = _get_services(request)
    doc = await doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_response(doc)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, request: Request) -> None:
    doc_store, _ = _get_services(request)
    vec_store = request.app.state.vec_store

    doc = await doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_store = request.app.state.chunk_store
    image_store = request.app.state.image_store
    hybrid_search = request.app.state.hybrid_search
    await asyncio.gather(
        doc_store.delete(doc_id),
        vec_store.delete_by_doc_id(doc_id),
        chunk_store.delete_by_doc_id(doc_id),
        image_store.delete_by_doc_id(doc_id),
    )
    hybrid_search.mark_dirty()
