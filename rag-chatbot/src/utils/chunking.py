from __future__ import annotations

import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.?!])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]


def group_into_chunks(
    sentences: list[str], chunk_size: int, overlap: int
) -> list[str]:
    if not sentences:
        return []
    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    i = 0
    while i < len(sentences):
        group: list[str] = []
        total = 0
        j = i
        while j < len(sentences) and total + len(sentences[j]) <= chunk_size:
            total += len(sentences[j])
            group.append(sentences[j])
            j += 1

        if not group:
            chunks.append(sentences[i][:chunk_size])
            i += 1
            continue

        chunks.append(" ".join(group))

        consumed = 0
        k = i
        while k < j and consumed + len(sentences[k]) < step:
            consumed += len(sentences[k])
            k += 1
        i = k if k > i else i + 1
    return chunks
