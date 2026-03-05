from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_version: str = "0.1.0"
    log_level: str = "INFO"

    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "documents"

    sqlite_path: str = "./data/documents.db"

    text_model: str = "nomic-ai/nomic-embed-text-v1.5"
    image_model: str = "clip-ViT-B-32"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieve_multiplier: int = 3  # fetch limit * multiplier candidates before reranking

    max_workers: int = 50
    chunk_size: int = 512
    chunk_overlap: int = 64

    ollama_url: str = "http://ollama:11434"
    llm_model: str = "qwen2.5:0.5b"
    rag_context_chunks: int = 5


settings = Settings()
