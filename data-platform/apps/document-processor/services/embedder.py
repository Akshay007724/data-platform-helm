import io
import logging

from PIL import Image
from sentence_transformers import SentenceTransformer

from api.config import settings

logger = logging.getLogger(__name__)

_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def _model_family(model_name: str) -> str:
    name = model_name.lower()
    if "nomic" in name:
        return "nomic"
    if "bge" in name:
        return "bge"
    if "gte-qwen" in name:
        return "gte-qwen"
    return "generic"


class Embedder:
    def __init__(self) -> None:
        logger.info("Loading text model: %s", settings.text_model)
        self._text_model = SentenceTransformer(settings.text_model, trust_remote_code=True)
        self._family = _model_family(settings.text_model)
        logger.info("Loading image model: %s", settings.image_model)
        self._image_model = SentenceTransformer(settings.image_model)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Encode passages for indexing (document-side prefix where the model requires it)."""
        kwargs = dict(normalize_embeddings=True, show_progress_bar=False)
        if self._family == "nomic":
            kwargs["prompt_name"] = "search_document"
        vectors = self._text_model.encode(texts, **kwargs)
        return [v.tolist() for v in vectors]

    def embed_query(self, query: str) -> list[float]:
        """Encode a search query with the model's query-side instruction."""
        kwargs = dict(normalize_embeddings=True, show_progress_bar=False)
        if self._family == "nomic":
            kwargs["prompt_name"] = "search_query"
            vector = self._text_model.encode(query, **kwargs)
        elif self._family == "bge":
            vector = self._text_model.encode(
                f"{_BGE_QUERY_PREFIX}{query}", **kwargs
            )
        elif self._family == "gte-qwen":
            vector = self._text_model.encode(query, prompt_name="query", **kwargs)
        else:
            vector = self._text_model.encode(query, **kwargs)
        return vector.tolist()

    def embed_image_caption(self, caption: str) -> list[float]:
        """Encode a caption for indexing (same space as text chunks)."""
        return self.embed_texts([caption])[0]

    def embed_image(self, image_bytes: bytes) -> list[float]:
        """Encode an image with CLIP."""
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        vector = self._image_model.encode(image, show_progress_bar=False)
        return vector.tolist()

    @property
    def text_dim(self) -> int:
        return self._text_model.get_sentence_embedding_dimension()

    @property
    def image_dim(self) -> int:
        return self._image_model.get_sentence_embedding_dimension()
