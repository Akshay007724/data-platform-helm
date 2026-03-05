from fastapi import APIRouter, HTTPException
from fastapi.requests import Request

from api.config import settings
from models.schemas import SearchRequest, SearchResponse, SearchResult

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(body: SearchRequest, request: Request) -> SearchResponse:
    embedder = request.app.state.embedder
    vec_store = request.app.state.vec_store
    doc_store = request.app.state.doc_store
    reranker = request.app.state.reranker

    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty")

    # Retrieve more candidates than requested so the reranker has room to work
    retrieve_k = body.limit * settings.retrieve_multiplier
    query_vector = embedder.embed_query(body.query)
    hybrid_search = request.app.state.hybrid_search
    raw_results = await hybrid_search.search(
        query=body.query,
        query_vector=query_vector,
        vec_store=vec_store,
        k=retrieve_k,
        doc_ids=body.doc_ids,
    )

    # Rerank candidates with cross-encoder → accurate relevance scores
    reranked = reranker.rerank(query=body.query, results=raw_results, top_k=body.limit)

    results: list[SearchResult] = []
    for r in reranked:
        payload = r["payload"]
        doc_id = payload.get("doc_id", "")
        doc = await doc_store.get(doc_id)
        filename = doc["filename"] if doc else doc_id

        result_type = payload.get("type", "text")
        content = payload.get("content") or payload.get("caption", "")

        results.append(
            SearchResult(
                doc_id=doc_id,
                filename=filename,
                score=r["score"],
                content=content,
                page=payload.get("page"),
                result_type=result_type,
            )
        )

    return SearchResponse(results=results, query=body.query)
