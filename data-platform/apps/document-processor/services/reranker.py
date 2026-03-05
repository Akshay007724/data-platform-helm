import logging

import numpy as np
from sentence_transformers import CrossEncoder

from api.config import settings

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker — much more accurate than bi-encoder similarity alone."""

    def __init__(self) -> None:
        logger.info("Loading reranker: %s", settings.reranker_model)
        self._model = CrossEncoder(settings.reranker_model, max_length=512)

    def rerank(self, query: str, results: list[dict], top_k: int) -> list[dict]:
        """
        Score (query, passage) pairs with the cross-encoder and return the
        top_k results sorted by descending relevance score in [0, 1].
        """
        if not results:
            return results

        pairs = []
        for r in results:
            payload = r["payload"]
            text = payload.get("content") or payload.get("caption") or ""
            pairs.append((query, text))

        raw_scores = self._model.predict(pairs)
        # Sigmoid maps raw logits → probability-style scores in (0, 1)
        scores = 1.0 / (1.0 + np.exp(-np.array(raw_scores, dtype=float)))

        for r, score in zip(results, scores):
            r["score"] = float(score)

        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
