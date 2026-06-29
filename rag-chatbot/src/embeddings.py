from __future__ import annotations

import logging
from typing import Sequence

from llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    """Backward-compatible wrapper around OllamaClient embeddings."""

    def __init__(self, model: str | None = None, timeout_seconds: float = 60.0) -> None:
        self.client = OllamaClient(timeout_seconds=timeout_seconds)
        self.model = model

    def embed_text(self, text: str) -> list[float]:
        return self.client.embed_text(text)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return self.client.embed_texts(texts)
