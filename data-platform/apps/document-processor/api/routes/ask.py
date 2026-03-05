import json
import logging

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import StreamingResponse

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

    async def event_stream():
        yield f"data: {json.dumps({'type': 'sources', 'data': [s.model_dump() for s in sources]})}\n\n"
        try:
            async for token in llm_service.stream_answer(body.question, reranked):
                yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            logger.error("LLM stream failed: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'data': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
