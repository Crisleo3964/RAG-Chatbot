from __future__ import annotations

import logging
import time

from groq import Groq

from config import get_settings

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.groq_api_key
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Set the GROQ_API_KEY environment variable."
            )
        self._client = Groq(api_key=api_key)
        self._model = settings.groq_model
        self._temperature = settings.groq_temperature
        self._max_tokens = settings.groq_max_tokens

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        merged_model = model or self._model
        merged_temperature = temperature if temperature is not None else self._temperature
        merged_max_tokens = max_tokens or self._max_tokens

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                logger.info(
                    "groq_generate_start model=%s temperature=%s max_tokens=%s attempt=%s",
                    merged_model,
                    merged_temperature,
                    merged_max_tokens,
                    attempt + 1,
                )
                t0 = time.perf_counter()
                response = self._client.chat.completions.create(
                    model=merged_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=merged_temperature,
                    max_tokens=merged_max_tokens,
                )
                elapsed = time.perf_counter() - t0
                logger.info("groq_generate_done elapsed=%.2fs attempt=%s", elapsed, attempt + 1)

                text = response.choices[0].message.content
                if not text or not text.strip():
                    raise RuntimeError("Groq returned empty response")

                return text.strip()

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "groq_generate_retry attempt=%s error=%s",
                    attempt + 1,
                    exc,
                )
                if attempt < 2:
                    time.sleep(2 ** attempt)

        raise RuntimeError(
            f"Groq generation failed after 3 attempts: {last_error}"
        ) from last_error
