from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from filelock import FileLock


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentStatusStore:
    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path
        self._lock_path = store_path.with_suffix(".lock")

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self._store_path.exists():
            return {}
        with open(self._store_path, "r") as f:
            return json.load(f)

    def _write(self, data: dict[str, dict[str, Any]]) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._store_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def set_status(
        self,
        document_id: str,
        status: DocumentStatus,
        file_name: str = "",
        user_id: str = "",
        error: str | None = None,
        chunks_created: int = 0,
    ) -> None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            now = datetime.now(timezone.utc).isoformat()
            entry = data.get(document_id, {})
            entry["document_id"] = document_id
            entry["file_name"] = file_name
            entry["user_id"] = user_id
            entry["status"] = status.value
            entry["chunks_created"] = chunks_created
            entry["updated_at"] = now
            if error is not None:
                entry["error"] = error
            elif "error" in entry:
                del entry["error"]
            if "created_at" not in entry:
                entry["created_at"] = now
            data[document_id] = entry
            self._write(data)

    def get_status(self, document_id: str) -> dict[str, Any] | None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            return data.get(document_id)

    def delete_status(self, document_id: str) -> bool:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            if document_id not in data:
                return False
            del data[document_id]
            self._write(data)
            return True

    def list_statuses(self) -> dict[str, dict[str, Any]]:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            return dict(data)
