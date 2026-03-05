import logging

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class HybridSearch:
    def __init__(self) -> None:
        self._index: BM25Okapi | None = None
        self._ids: list[str] = []
        self._dirty = True
        self._chunk_store = None

    def set_chunk_store(self, chunk_store) -> None:
        self._chunk_store = chunk_store

    def build(self, chunks: list[dict]) -> None:
        """Build BM25 index from chunk list [{id, text, ...}]"""
        self._ids = [c["id"] for c in chunks]
        corpus = [c["text"].lower().split() for c in chunks]
        self._index = BM25Okapi(corpus) if corpus else None
        self._dirty = False
        logger.info("BM25 index built: %d chunks", len(self._ids))

    def mark_dirty(self) -> None:
        self._dirty = True

    async def _maybe_rebuild(self) -> None:
        if self._dirty and self._chunk_store is not None:
            chunks = await self._chunk_store.get_all()
            self.build(chunks)

    def bm25_search(self, query: str, k: int) -> list[tuple[str, float]]:
        if self._index is None or not self._ids:
            return []
        tokens = query.lower().split()
        scores = self._index.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self._ids[i], float(scores[i])) for i in top_indices if scores[i] > 0]

    @staticmethod
    def rrf_fuse(
        bm25_hits: list[tuple[str, float]],
        vector_hits: list[tuple[str, float]],
        k: int = 60,
    ) -> list[tuple[str, float]]:
        scores: dict[str, float] = {}
        for rank, (cid, _) in enumerate(bm25_hits):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        for rank, (cid, _) in enumerate(vector_hits):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    async def search(
        self,
        query: str,
        query_vector: list[float],
        vec_store,
        k: int,
        doc_ids: list[str] | None = None,
    ) -> list[dict]:
        await self._maybe_rebuild()

        # Vector search returns [{id, score, payload}]
        vec_results = await vec_store.search(
            query_vector=query_vector, limit=k, doc_ids=doc_ids
        )
        vector_hits = [(r["id"], r["score"]) for r in vec_results]
        payload_map = {r["id"]: r["payload"] for r in vec_results}

        # BM25 search
        bm25_hits = self.bm25_search(query, k)
        logger.info("BM25 hits: %d, vector hits: %d", len(bm25_hits), len(vector_hits))

        # RRF fusion
        fused = self.rrf_fuse(bm25_hits, vector_hits)[:k]

        # Fetch payloads for IDs only in BM25 results (not in vector results)
        missing_ids = [cid for cid, _ in fused if cid not in payload_map]
        if missing_ids and self._chunk_store is not None:
            extra_chunks = await self._chunk_store.get_by_ids(missing_ids)
            for c in extra_chunks:
                payload_map[c["id"]] = {
                    "doc_id": c["doc_id"],
                    "type": c.get("type", "text"),
                    "page": c.get("page"),
                    "content": c["text"],
                    "caption": None,
                }

        results = []
        for cid, score in fused:
            payload = payload_map.get(cid)
            if payload:
                results.append({"id": cid, "score": score, "payload": payload})

        return results
