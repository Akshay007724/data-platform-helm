import logging
import uuid

import chromadb

from api.config import settings
from services.embedder import Embedder

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._host = settings.chroma_host
        self._port = settings.chroma_port
        self._collection_name = settings.chroma_collection
        self._client: chromadb.AsyncClientAPI | None = None
        self._collection = None

    async def ensure_collection(self) -> None:
        self._client = await chromadb.AsyncHttpClient(host=self._host, port=self._port)
        self._collection = await self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection ready: %s", self._collection_name)

    async def upsert_batch(self, points: list[dict]) -> None:
        """
        Single-call batch upsert. Each point must have:
          vector: list[float], document: str, metadata: dict
        Optionally: id: str (generated if absent)
        Dramatically reduces the number of HTTP round-trips to ChromaDB.
        """
        if not points:
            return
        await self._collection.add(
            ids=[p.get("id") or str(uuid.uuid4()) for p in points],
            embeddings=[p["vector"] for p in points],
            metadatas=[p["metadata"] for p in points],
            documents=[p["document"] for p in points],
        )

    # Kept for backwards compatibility with tests
    async def upsert_text_point(
        self, doc_id: str, content: str, page: int, vector: list[float]
    ) -> None:
        await self.upsert_batch(
            [{"vector": vector, "document": content,
              "metadata": {"type": "text", "doc_id": doc_id, "page": page}}]
        )

    async def upsert_image_point(
        self, doc_id: str, caption: str, page: int,
        text_vector: list[float], image_vector: list[float],
    ) -> None:
        await self.upsert_batch(
            [{"vector": text_vector, "document": caption,
              "metadata": {"type": "image", "doc_id": doc_id, "page": page}}]
        )

    async def search(
        self, query_vector: list[float], limit: int, doc_ids: list[str] | None = None
    ) -> list[dict]:
        count = await self._collection.count()
        if count == 0:
            return []

        where = None
        if doc_ids:
            where = {"doc_id": {"$in": doc_ids}} if len(doc_ids) > 1 else {"doc_id": doc_ids[0]}

        results = await self._collection.query(
            query_embeddings=[query_vector],
            n_results=min(limit, count),
            where=where,
            include=["metadatas", "documents", "distances"],
        )

        hits = []
        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]
        distances = results["distances"][0]

        for id_, meta, doc, dist in zip(ids, metadatas, documents, distances):
            # ChromaDB cosine distance: 0 = identical, 1 = orthogonal
            # Convert to similarity score in [0, 1]
            score = 1.0 - dist
            payload = {**meta, "content": doc if meta.get("type") == "text" else None,
                       "caption": doc if meta.get("type") == "image" else None}
            hits.append({"id": id_, "score": score, "payload": payload})

        return hits

    async def delete_by_doc_id(self, doc_id: str) -> None:
        await self._collection.delete(where={"doc_id": doc_id})

    async def close(self) -> None:
        pass  # AsyncHttpClient has no explicit close
