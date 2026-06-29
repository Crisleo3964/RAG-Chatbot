from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from typing import Annotated

from api.dependencies.auth import get_admin_user, get_current_user
from auth.auth_service import AuthService, User, get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    email: str
    role: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    role: str


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)
    role: str = Field(default="user", pattern="^(user|admin)$")


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    if auth_service.get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = auth_service.register_user(
        email=body.email,
        password=body.password,
        role="user",
    )
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )


@router.post("/auth/token", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    user = auth_service.authenticate(
        email=form_data.username,
        password=form_data.password,
    )
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_service.create_access_token(user.user_id)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=MeResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
    )


@router.post("/auth/users", response_model=UserResponse)
async def create_user(
    body: AdminCreateUserRequest,
    auth_service: AuthService = Depends(get_auth_service),
    admin: User = Depends(get_admin_user),
) -> UserResponse:
    if auth_service.get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = auth_service.register_user(
        email=body.email,
        password=body.password,
        role=body.role,
    )
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
    )


@router.get("/auth/users", response_model=list[UserResponse])
async def list_users(
    auth_service: AuthService = Depends(get_auth_service),
    admin: User = Depends(get_admin_user),
) -> list[UserResponse]:
    users = auth_service.list_users()
    return [
        UserResponse(
            user_id=u.user_id,
            email=u.email,
            role=u.role,
        )
        for u in users
    ]
