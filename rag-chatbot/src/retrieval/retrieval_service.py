from __future__ import annotations

from config import get_settings
from llm.ollama_client import OllamaClient
from models.schemas import RetrievedChunk
from storage.chroma_store import ChromaVectorStore


class RetrievalService:
    def __init__(self, store: ChromaVectorStore | None = None, ollama: OllamaClient | None = None) -> None:
        self.settings = get_settings()
        self.store = store or ChromaVectorStore()
        self.ollama = ollama or OllamaClient()

    def search(self, question: str, top_k: int | None = None, user_id: str | None = None) -> list[RetrievedChunk]:
        query_embedding = self.ollama.embed_text(question)
        result_top_k = top_k or self.settings.top_k
        return self.store.query(query_embedding=query_embedding, top_k=result_top_k, user_id=user_id)
