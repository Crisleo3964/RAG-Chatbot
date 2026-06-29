from __future__ import annotations

import logging
from typing import Any, Sequence

import requests

from config import get_settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, timeout_seconds: float = 600.0) -> None:
        settings = get_settings()
        self._settings = settings
        self._base_url = settings.ollama_base_url
        self._timeout_seconds = timeout_seconds

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed empty text.")

        endpoint = f"{self._base_url}/api/embed"
        payload: dict[str, Any] = {
            "model": self._settings.embedding_model,
            "input": text,
        }
        try:
            response = requests.post(endpoint, json=payload, timeout=self._timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Ollama embedding request failed: {exc}") from exc

        data = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise RuntimeError(f"Unexpected embedding response keys={list(data.keys())}")
        vector = embeddings[0]
        if not isinstance(vector, list) or not vector:
            raise RuntimeError("Received empty embedding vector.")
        return [float(value) for value in vector]

    def embed_texts(self, texts: Sequence[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        valid_texts = [t for t in texts if t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty.")

        endpoint = f"{self._base_url}/api/embed"
        all_embeddings: list[list[float]] = []
        for start in range(0, len(valid_texts), batch_size):
            batch = valid_texts[start:start + batch_size]
            payload: dict[str, Any] = {
                "model": self._settings.embedding_model,
                "input": list(batch),
            }
            try:
                response = requests.post(endpoint, json=payload, timeout=self._timeout_seconds)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(f"Ollama batch embedding request failed at offset {start}: {exc}") from exc

            data = response.json()
            embeddings = data.get("embeddings")
            if not isinstance(embeddings, list) or len(embeddings) != len(batch):
                raise RuntimeError(
                    f"Unexpected embedding response at offset {start}: expected {len(batch)} vectors, "
                    f"got {len(embeddings) if isinstance(embeddings, list) else 'none'}"
                )
            all_embeddings.extend([[float(v) for v in vec] for vec in embeddings])
        return all_embeddings

    def chat(self, prompt: str, model: str | None = None) -> str:
        endpoint = f"{self._base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": model or self._settings.chat_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "num_predict": self._settings.num_predict,
            },
        }
        try:
            response = requests.post(endpoint, json=payload, timeout=self._timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Ollama chat request failed: {exc}") from exc

        data = response.json()
        message = data.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Unexpected chat response format from Ollama.")
        return content.strip()
