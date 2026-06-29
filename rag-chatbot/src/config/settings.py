from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    chroma_path: Path
    collection_name: str
    chat_model: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    batch_size: int
    chunks_pending_dir: Path
    ollama_base_url: str
    num_predict: int
    groq_api_key: str
    groq_model: str
    groq_temperature: float
    groq_max_tokens: int
    rabbitmq_url: str
    rabbitmq_ingestion_queue: str
    status_store_path: Path
    chat_store_path: Path
    auth_store_path: Path
    auth_enabled: bool
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int


@lru_cache
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parent.parent.parent
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    auth_enabled_str = os.getenv("RAG_AUTH_ENABLED", "true")
    return Settings(
        project_root=project_root,
        data_dir=project_root / "data",
        chroma_path=project_root / "chroma_db",
        collection_name=os.getenv("RAG_COLLECTION_NAME", "pdf_chunks"),
        chat_model=os.getenv("RAG_CHAT_MODEL", "qwen3:4b"),
        embedding_model=os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text"),
        chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "200")),
        top_k=top_k,
        batch_size=int(os.getenv("RAG_BATCH_SIZE", "32")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_predict=int(os.getenv("RAG_NUM_PREDICT", "1024")),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        groq_temperature=float(os.getenv("GROQ_TEMPERATURE", "0.3")),
        groq_max_tokens=int(os.getenv("GROQ_MAX_TOKENS", "2048")),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        rabbitmq_ingestion_queue=os.getenv("RABBITMQ_INGESTION_QUEUE", "ingestion_tasks"),
        chunks_pending_dir=project_root / "data" / "chunks_pending",
        status_store_path=project_root / "status_store.json",
        chat_store_path=project_root / "chat_store.json",
        auth_store_path=project_root / "auth_store.json",
        auth_enabled=auth_enabled_str.lower() in ("1", "true", "yes"),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-at-least-32-chars!"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")),
    )
