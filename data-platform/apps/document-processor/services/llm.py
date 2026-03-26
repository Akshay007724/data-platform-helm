import asyncio
import base64
import logging
from collections.abc import AsyncGenerator

import httpx
from openai import AsyncOpenAI

from api.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the question based only on the provided context. "
    "If the context does not contain enough information, say so clearly."
)


class LLMService:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=f"{settings.ollama_url}/v1",
            api_key="ollama",  # Ollama does not require a real key
        )
        self._model = settings.llm_model

    async def _pull_model(self, model: str) -> None:
        """Pull a single model from Ollama (no-op if already cached)."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_url}/api/pull",
                json={"name": model},
                timeout=600.0,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        logger.debug("pull %s: %s", model, line)
        logger.info("Model %s ready", model)

    async def ensure_model(self) -> None:
        """Block until Ollama is reachable, then pull text and vision models.

        Retries for up to ~90 seconds (30 attempts × 3 s) before raising.
        This gives Ollama time to start while preventing an infinite hang if
        the URL is misconfigured.
        """
        base_url = settings.ollama_url
        max_attempts = 30
        async with httpx.AsyncClient() as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    r = await client.get(f"{base_url}/api/tags", timeout=5.0)
                    if r.status_code == 200:
                        break
                except Exception:
                    pass
                logger.info("Waiting for Ollama at %s… (%d/%d)", base_url, attempt, max_attempts)
                await asyncio.sleep(3)
            else:
                raise RuntimeError(
                    f"Ollama not reachable at {base_url} after {max_attempts * 3}s. "
                    "Check OLLAMA_URL and ensure the Ollama service is running."
                )

        logger.info("Pulling text model %s and vision model %s", self._model, settings.vision_model)
        await self._pull_model(self._model)
        if settings.vision_model:
            await self._pull_model(settings.vision_model)

    async def stream_answer(
        self, question: str, context_hits: list[dict]
    ) -> AsyncGenerator[str, None]:
        context_parts = []
        for i, hit in enumerate(context_hits, 1):
            payload = hit.get("payload", {})
            text = payload.get("content") or payload.get("caption") or ""
            context_parts.append(f"[{i}] {text}")
        context = "\n\n".join(context_parts)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ]

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def stream_vision_answer(
        self,
        question: str,
        context_hits: list[dict],
        image_bytes_map: dict[str, bytes],
    ) -> AsyncGenerator[str, None]:
        """
        Stream an answer from the vision model.  Text context chunks are passed
        as a numbered list; image chunks found in image_bytes_map are attached
        as inline base64 data URLs so the model can see them.
        """
        text_parts: list[str] = []
        for i, hit in enumerate(context_hits, 1):
            payload = hit.get("payload", {})
            if payload.get("type") == "image":
                text_parts.append(f"[{i}] (image on page {payload.get('page')})")
            else:
                text_parts.append(f"[{i}] {payload.get('content') or ''}")

        content: list[dict] = [
            {"type": "text", "text": f"Context:\n" + "\n\n".join(text_parts)},
        ]

        for hit in context_hits:
            chunk_id = hit.get("id")
            img_bytes = image_bytes_map.get(chunk_id) if chunk_id else None
            if img_bytes:
                b64 = base64.b64encode(img_bytes).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })

        content.append({"type": "text", "text": f"\nQuestion: {question}"})

        stream = await self._client.chat.completions.create(
            model=settings.vision_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
