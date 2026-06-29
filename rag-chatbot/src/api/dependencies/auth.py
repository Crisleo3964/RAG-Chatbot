from __future__ import annotations

import logging

import jwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer

from auth.auth_service import AuthService, User, get_auth_service
from config import get_settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def _resolve_token(
    header_token: str | None,
    query_token: str | None = None,
) -> str | None:
    if header_token:
        return header_token
    return query_token


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        return User(
            user_id="00000000-0000-0000-0000-000000000000",
            email="admin@bypass",
            hashed_password="",
            role="admin",
        )
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = auth_service.decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception from None

    user = auth_service.get_user(subject)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_with_query_token(
    header_token: str | None = Depends(oauth2_scheme),
    token: str | None = Query(None, description="JWT token as query param fallback"),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    resolved = _resolve_token(header_token, token)
    settings = get_settings()
    if not settings.auth_enabled:
        return User(
            user_id="00000000-0000-0000-0000-000000000000",
            email="admin@bypass",
            hashed_password="",
            role="admin",
        )
    if resolved is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = auth_service.decode_access_token(resolved)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception from None

    user = auth_service.get_user(subject)
    if user is None:
        raise credentials_exception
    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user
