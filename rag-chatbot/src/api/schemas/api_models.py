from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Service health status")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, description="User question to answer")
    session_id: str | None = Field(default=None, description="Session ID for chat history")


class SourceRefModel(BaseModel):
    document: str = Field(description="Source document filename")
    page: int = Field(description="Page number within the document")


class ChatResponse(BaseModel):
    answer: str = Field(description="Generated answer text")
    sources: list[SourceRefModel] = Field(description="List of source document references")
    session_id: str | None = Field(default=None, description="Session ID for chat history")


class IngestResponse(BaseModel):
    status: str = Field(description="Ingestion status")
    document: str = Field(description="Ingested document filename")
    chunks_created: int = Field(description="Number of chunks generated and stored")


class IngestAcceptedResponse(BaseModel):
    document_id: str = Field(description="Unique document identifier")
    file_name: str = Field(description="Uploaded filename")
    status: str = Field(default="PENDING", description="Ingestion status")
    user_id: str = Field(default="", description="Owner user ID")


class DocumentStatusResponse(BaseModel):
    document_id: str = Field(description="Unique document identifier")
    file_name: str = Field(description="Uploaded filename")
    status: str = Field(description="Current ingestion status")
    chunks_created: int = Field(default=0, description="Number of chunks ingested")
    error: str | None = Field(default=None, description="Error message if failed")
    user_id: str = Field(default="", description="Owner user ID")
    created_at: str = Field(description="Upload timestamp")
    updated_at: str = Field(description="Last status update timestamp")


class ChatSessionResponse(BaseModel):
    session_id: str = Field(description="Unique session identifier")
    user_id: str = Field(description="Owner user ID")
    title: str = Field(description="Session title")
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last activity timestamp")


class ChatMessageResponse(BaseModel):
    message_id: str = Field(description="Unique message identifier")
    session_id: str = Field(description="Parent session identifier")
    role: str = Field(description="Message role: user or assistant")
    content: str = Field(description="Message content")
    sources: list[SourceRefModel] | None = Field(default=None, description="Source references for assistant messages")
    created_at: str = Field(description="Creation timestamp")


class ErrorResponse(BaseModel):
    detail: str = Field(description="Error detail message")
