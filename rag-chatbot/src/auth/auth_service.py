from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import jwt
from filelock import FileLock
from pwdlib import PasswordHash

from config import get_settings

logger = logging.getLogger(__name__)

password_hash = PasswordHash.recommended()


@dataclass
class User:
    user_id: str
    email: str
    hashed_password: str
    role: str = "user"


class AuthService:
    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path
        self._lock_path = store_path.with_suffix(".lock")
        self._ensure_admin_user()

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self._store_path.exists():
            return {}
        with open(self._store_path, "r") as f:
            return json.load(f)

    def _write(self, data: dict[str, dict[str, Any]]) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._store_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _ensure_admin_user(self) -> None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            if not data:
                admin_password = str(uuid.uuid4())[:12]
                admin_id = str(uuid.uuid4())
                data[admin_id] = {
                    "user_id": admin_id,
                    "email": "admin@localhost",
                    "hashed_password": password_hash.hash(admin_password),
                    "role": "admin",
                }
                self._write(data)
                logger.info(
                    "event=auth_admin_created "
                    "email=admin@localhost password=%s",
                    admin_password,
                )
                print("=" * 60)
                print("  ADMIN USER CREATED")
                print(f"  email:    admin@localhost")
                print(f"  password: {admin_password}")
                print("=" * 60)

    def hash_password(self, password: str) -> str:
        return password_hash.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        return password_hash.verify(password, hashed)

    def create_access_token(self, user_id: str) -> str:
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
        payload = {"sub": user_id, "exp": expires_at}
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> dict:
        settings = get_settings()
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": True, "require": ["exp"]},
        )

    def authenticate(self, email: str, password: str) -> User | None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
        for entry in data.values():
            if entry["email"] == email:
                if self.verify_password(password, entry["hashed_password"]):
                    return User(**entry)
        return None

    def get_user(self, user_id: str) -> User | None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
        entry = data.get(user_id)
        if entry is None:
            return None
        return User(**entry)

    def get_user_by_email(self, email: str) -> User | None:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
        for entry in data.values():
            if entry["email"] == email:
                return User(**entry)
        return None

    def register_user(self, email: str, password: str, role: str = "user") -> User:
        user_id = str(uuid.uuid4())
        hashed = self.hash_password(password)
        user = User(
            user_id=user_id,
            email=email,
            hashed_password=hashed,
            role=role,
        )
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
            for entry in data.values():
                if entry["email"] == email:
                    raise ValueError(f"Email already registered: {email}")
            data[user_id] = {
                "user_id": user.user_id,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "role": user.role,
            }
            self._write(data)
        logger.info("event=auth_user_registered user_id=%s email=%s", user_id, email)
        return user

    def list_users(self) -> list[User]:
        lock = FileLock(str(self._lock_path))
        with lock:
            data = self._read()
        return [User(**entry) for entry in data.values()]


@lru_cache
def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(store_path=settings.auth_store_path)
