import json
import logging

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import StreamingResponse

from api.config import settings
from models.schemas import AskRequest, SourceReference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ask"])


@router.post("/ask")
async def ask(body: AskRequest, request: Request) -> StreamingResponse:
    embedder = request.app.state.embedder
    doc_store = request.app.state.doc_store
    vec_store = request.app.state.vec_store
    hybrid_search = request.app.state.hybrid_search
    reranker = request.app.state.reranker
    llm_service = request.app.state.llm_service
    image_store = request.app.state.image_store

    query_vector = embedder.embed_query(body.question)
    raw_hits = await hybrid_search.search(
        query=body.question,
        query_vector=query_vector,
        vec_store=vec_store,
        k=body.limit * 3,
        doc_ids=body.doc_ids,
    )
    reranked = reranker.rerank(query=body.question, results=raw_hits, top_k=body.limit)

    sources: list[SourceReference] = []
    for r in reranked:
        payload = r["payload"]
        doc_id = payload.get("doc_id", "")
        doc = await doc_store.get(doc_id)
        filename = doc["filename"] if doc else doc_id
        content = payload.get("content") or payload.get("caption") or ""
        sources.append(
            SourceReference(
                doc_id=doc_id,
                filename=filename,
                page=payload.get("page"),
                score=r["score"],
                snippet=content[:300],
            )
        )

    # Fetch image bytes for any image hits so the vision model can see them
    image_hit_ids = [
        r["id"] for r in reranked
        if r.get("payload", {}).get("type") == "image" and r.get("id")
    ]
    image_bytes_map: dict[str, bytes] = {}
    if image_hit_ids and settings.vision_model:
        image_bytes_map = await image_store.get_by_ids(image_hit_ids)

    use_vision = bool(image_bytes_map) and bool(settings.vision_model)
    if use_vision:
        logger.info("Vision model activated — %d image(s) in context", len(image_bytes_map))

    async def event_stream():
        yield f"data: {json.dumps({'type': 'sources', 'data': [s.model_dump() for s in sources]})}\n\n"
        try:
            if use_vision:
                gen = llm_service.stream_vision_answer(body.question, reranked, image_bytes_map)
            else:
                gen = llm_service.stream_answer(body.question, reranked)
            async for token in gen:
                yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            logger.error("LLM stream failed: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'data': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
