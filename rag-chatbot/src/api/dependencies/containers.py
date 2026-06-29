from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Request

from config import get_settings
from ingestion.pdf_ingestion_service import PdfIngestionService
from llm.groq_client import GroqClient
from llm.ollama_client import OllamaClient
from messaging.publisher import publish_ingestion_task
from retrieval.retrieval_service import RetrievalService
from services.rag_service import RagChatService
from storage.chroma_store import ChromaVectorStore
from storage.document_status_store import DocumentStatusStore
from storage.chat_store import ChatStore


@lru_cache
def get_chroma_store() -> ChromaVectorStore:
    return ChromaVectorStore()


@lru_cache
def get_ollama_client() -> OllamaClient:
    return OllamaClient()


@lru_cache
def get_groq_client() -> GroqClient:
    return GroqClient()


@lru_cache
def get_retrieval_service() -> RetrievalService:
    return RetrievalService(
        store=get_chroma_store(),
        ollama=get_ollama_client(),
    )


@lru_cache
def get_rag_service() -> RagChatService:
    return RagChatService(
        retrieval_service=get_retrieval_service(),
        groq_client=get_groq_client(),
    )


@lru_cache
def get_ingestion_service() -> PdfIngestionService:
    return PdfIngestionService(
        store=get_chroma_store(),
        ollama=get_ollama_client(),
    )


@lru_cache
def get_status_store() -> DocumentStatusStore:
    settings = get_settings()
    return DocumentStatusStore(store_path=settings.status_store_path)


def get_rag_service_from_request(request: Request) -> RagChatService:
    return get_rag_service()


def get_ingestion_service_from_request(request: Request) -> PdfIngestionService:
    return get_ingestion_service()


def get_publisher_from_request(request: Request):
    return publish_ingestion_task


def get_status_store_from_request(request: Request) -> DocumentStatusStore:
    return get_status_store()


@lru_cache
def get_chat_store() -> ChatStore:
    settings = get_settings()
    return ChatStore(store_path=settings.chat_store_path)


def get_chat_store_from_request(request: Request) -> ChatStore:
    return get_chat_store()
