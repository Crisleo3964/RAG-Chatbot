from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    document_name: str
    page_number: int
    text: str
    user_id: str = ""
    ingestion_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float


@dataclass(frozen=True)
class SourceRef:
    document: str
    page: int


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    sources: list[SourceRef]
