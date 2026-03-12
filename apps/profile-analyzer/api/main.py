import json
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import dating, linkedin, resume
from services.llm_client import OLLAMA_BASE_URL, TEXT_MODEL, VISION_MODEL


async def _ensure_model(client: httpx.AsyncClient, model: str) -> None:
    """Pull an Ollama model if it isn't already cached."""
    ollama_root = OLLAMA_BASE_URL.replace("/v1", "")
    resp = await client.get(f"{ollama_root}/api/tags", timeout=10)
    cached = [m["name"] for m in resp.json().get("models", [])]
    if any(model.split(":")[0] in n for n in cached):
        print(f"[startup] model '{model}' already cached — skipping pull")
        return

    print(f"[startup] pulling '{model}' (this may take a while on first boot)…")
    async with client.stream(
        "POST", f"{ollama_root}/api/pull", json={"name": model}, timeout=600
    ) as r:
        async for line in r.aiter_lines():
            if line:
                data = json.loads(line)
                if status := data.get("status"):
                    print(f"[{model}] {status}", flush=True)
    print(f"[startup] '{model}' ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("uploads", exist_ok=True)

    # Pull required models into Ollama on first boot
    async with httpx.AsyncClient() as http:
        try:
            await _ensure_model(http, VISION_MODEL)
            await _ensure_model(http, TEXT_MODEL)
        except Exception as exc:
            print(f"[startup] WARNING: could not pull models — {exc}")

    yield


app = FastAPI(
    title="Profile Analyzer",
    description=(
        "AI-powered profile analyzer for dating apps and LinkedIn, "
        "with resume optimization and auto-apply. "
        "Runs fully locally via Ollama."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dating.router)
app.include_router(linkedin.router)
app.include_router(resume.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/models")
async def models_info():
    return {
        "vision_model": VISION_MODEL,
        "text_model": TEXT_MODEL,
        "ollama_url": OLLAMA_BASE_URL,
    }


# Serve UI
app.mount("/static", StaticFiles(directory="ui"), name="static")


@app.get("/")
async def serve_ui():
    return FileResponse("ui/index.html")


@app.get("/{path:path}")
async def catch_all(path: str):
    return FileResponse("ui/index.html")
