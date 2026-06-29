from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies.auth import get_current_user
from api.dependencies.containers import get_rag_service_from_request, get_chat_store_from_request
from api.schemas.api_models import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatMessageResponse,
    SourceRefModel,
)
from auth.auth_service import User
from services.rag_service import RagChatService
from storage.chat_store import ChatStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    rag_service: RagChatService = Depends(get_rag_service_from_request),
    current_user: User = Depends(get_current_user),
    chat_store: ChatStore = Depends(get_chat_store_from_request),
) -> ChatResponse:
    user_id: str | None = current_user.user_id if current_user.role != "admin" else None

    session_id = body.session_id
    if not session_id:
        session = chat_store.create_session(user_id=current_user.user_id)
        session_id = session["session_id"]

    chat_store.add_message(session_id, "user", body.question)

    try:
        result = rag_service.ask(question=body.question, user_id=user_id)
        sources = [
            SourceRefModel(document=s.document, page=s.page) for s in result.sources
        ]
        chat_store.add_message(
            session_id,
            "assistant",
            result.answer,
            sources=[s.model_dump() for s in sources],
        )
        return ChatResponse(
            answer=result.answer,
            sources=sources,
            session_id=session_id,
        )
    except RuntimeError as exc:
        msg = str(exc)
        chat_store.add_message(session_id, "assistant", f"Error: {msg}")
        if "No chunks found" in msg or "No documents found" in msg:
            raise HTTPException(status_code=400, detail="Please upload a document before asking questions.")
        raise HTTPException(status_code=500, detail=msg)


@router.get("/chat/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    chat_store: ChatStore = Depends(get_chat_store_from_request),
) -> list[ChatSessionResponse]:
    return chat_store.get_sessions(current_user.user_id)


def _check_session_ownership(
    session_id: str,
    current_user: User,
    chat_store: ChatStore,
) -> None:
    session = chat_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role != "admin" and session.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/chat/sessions/{session_id}", response_model=list[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    chat_store: ChatStore = Depends(get_chat_store_from_request),
) -> list[ChatMessageResponse]:
    _check_session_ownership(session_id, current_user, chat_store)
    messages = chat_store.get_messages(session_id)
    return messages


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    chat_store: ChatStore = Depends(get_chat_store_from_request),
) -> dict[str, str]:
    _check_session_ownership(session_id, current_user, chat_store)
    chat_store.delete_session(session_id)
    return {"status": "deleted"}
