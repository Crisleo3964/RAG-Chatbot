from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock


class ChatStore:
    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path
        self._lock_path = store_path.with_suffix(store_path.suffix + ".lock")

    def _read(self) -> dict[str, Any]:
        if not self._store_path.exists():
            return {"sessions": {}, "messages": {}}
        with open(self._store_path, "r") as f:
            return json.load(f)

    def _write(self, data: dict[str, Any]) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._store_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def create_session(self, user_id: str, title: str = "") -> dict[str, Any]:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            session_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            session = {
                "session_id": session_id,
                "user_id": user_id,
                "title": title or "New chat",
                "created_at": now,
                "updated_at": now,
            }
            data["sessions"][session_id] = session
            data["messages"][session_id] = []
            self._write(data)
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        data = self._read()
        return data["sessions"].get(session_id)

    def get_sessions(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        sessions = []
        for s in data["sessions"].values():
            if s["user_id"] == user_id:
                sessions.append(s)
        sessions.sort(key=lambda s: s["updated_at"], reverse=True)
        return sessions

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        data = self._read()
        return data["messages"].get(session_id, [])

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            if session_id not in data["sessions"]:
                raise ValueError(f"Session {session_id} not found")
            now = datetime.now(timezone.utc).isoformat()
            message = {
                "message_id": str(uuid.uuid4()),
                "session_id": session_id,
                "role": role,
                "content": content,
                "sources": sources,
                "created_at": now,
            }
            data["messages"][session_id].append(message)
            data["sessions"][session_id]["updated_at"] = now
            if role == "user" and data["sessions"][session_id]["title"] == "New chat":
                data["sessions"][session_id]["title"] = content[:80]
            self._write(data)
        return message

    def delete_session(self, session_id: str) -> None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            data["sessions"].pop(session_id, None)
            data["messages"].pop(session_id, None)
            self._write(data)

    def delete_user_sessions(self, user_id: str) -> None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            to_delete = [sid for sid, s in data["sessions"].items() if s["user_id"] == user_id]
            for sid in to_delete:
                data["sessions"].pop(sid, None)
                data["messages"].pop(sid, None)
            self._write(data)
