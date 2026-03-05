import asyncio
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

    async def ensure_model(self) -> None:
        """Block until Ollama is reachable, then pull the model if not already present."""
        base_url = settings.ollama_url
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    r = await client.get(f"{base_url}/api/tags", timeout=5.0)
                    if r.status_code == 200:
                        break
                except Exception:
                    pass
                logger.info("Waiting for Ollama at %s…", base_url)
                await asyncio.sleep(3)

        logger.info("Ollama reachable — pulling model %s (cached after first run)", self._model)
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/pull",
                json={"name": self._model},
                timeout=600.0,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        logger.debug("pull: %s", line)
        logger.info("Model %s ready", self._model)

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
