from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.dependencies.auth import get_current_user, get_current_user_with_query_token, get_admin_user
from api.dependencies.containers import (
    get_chroma_store,
    get_ingestion_service_from_request,
    get_status_store_from_request,
)
from api.schemas.api_models import (
    DocumentStatusResponse,
    ErrorResponse,
    IngestAcceptedResponse,
)
from storage.chroma_store import ChromaVectorStore
from auth.auth_service import User
from config import get_settings
from ingestion.pdf_ingestion_service import PdfIngestionService
from storage.document_status_store import DocumentStatus, DocumentStatusStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])

ALLOWED_EXTENSIONS = {".pdf"}


@router.post(
    "/ingest",
    response_model=IngestAcceptedResponse,
    responses={400: {"model": ErrorResponse}},
)
async def ingest_pdf(
    file: UploadFile,
    status_store: DocumentStatusStore = Depends(get_status_store_from_request),
    current_user: User = Depends(get_current_user),
    ingestion_service: PdfIngestionService = Depends(get_ingestion_service_from_request),
) -> IngestAcceptedResponse:
    safe_name = Path(file.filename or "upload.pdf").name
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Only PDF files are allowed.",
        )

    settings = get_settings()
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    document_id = str(uuid.uuid4())
    dest = data_dir / f"{document_id}_{safe_name}"

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    uploaded_at = datetime.now(timezone.utc).isoformat()

    from messaging.publisher import publish_ingestion_task

    try:
        publish_ingestion_task(
            document_id=document_id,
            file_path=str(dest.resolve()),
            uploaded_at=uploaded_at,
            user_id=current_user.user_id,
        )
        status_store.set_status(
            document_id,
            DocumentStatus.PENDING,
            file_name=safe_name,
            user_id=current_user.user_id,
        )
        logger.info(
            "event=ingestion_queued document_id=%s file_name=%s user=%s",
            document_id,
            safe_name,
            current_user.user_id,
        )
        return IngestAcceptedResponse(
            document_id=document_id,
            file_name=safe_name,
            status=DocumentStatus.PENDING.value,
            user_id=current_user.user_id,
        )
    except Exception:
        logger.warning(
            "event=ingestion_fallback_to_inline document_id=%s file_name=%s",
            document_id,
            safe_name,
        )
        status_store.set_status(
            document_id,
            DocumentStatus.PROCESSING,
            file_name=safe_name,
            user_id=current_user.user_id,
        )

        async def _process_inline() -> None:
            try:
                chunk_count = await asyncio.to_thread(
                    ingestion_service.ingest_file, dest,
                    user_id=current_user.user_id, document_name=safe_name,
                )
                status_store.set_status(
                    document_id,
                    DocumentStatus.COMPLETED,
                    file_name=safe_name,
                    user_id=current_user.user_id,
                    chunks_created=chunk_count,
                )
                logger.info(
                    "event=ingestion_inline_completed document_id=%s chunks=%s",
                    document_id, chunk_count,
                )
            except Exception as inline_err:
                logger.error(
                    "event=ingestion_inline_failed document_id=%s error=%s",
                    document_id, inline_err,
                )
                status_store.set_status(
                    document_id,
                    DocumentStatus.FAILED,
                    file_name=safe_name,
                    user_id=current_user.user_id,
                    error=f"Inline processing failed: {inline_err}",
                )

        asyncio.create_task(_process_inline())
        return IngestAcceptedResponse(
            document_id=document_id,
            file_name=safe_name,
            status=DocumentStatus.PROCESSING.value,
            user_id=current_user.user_id,
        )


@router.get(
    "/documents/{document_id}/status",
    response_model=DocumentStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_document_status(
    document_id: str,
    status_store: DocumentStatusStore = Depends(get_status_store_from_request),
    current_user: User = Depends(get_current_user),
) -> DocumentStatusResponse:
    record = status_store.get_status(document_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )
    if current_user.role != "admin" and record.get("user_id") != current_user.user_id:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )
    return DocumentStatusResponse(
        document_id=record["document_id"],
        file_name=record.get("file_name", ""),
        status=record["status"],
        chunks_created=record.get("chunks_created", 0),
        error=record.get("error"),
        user_id=record.get("user_id", ""),
        created_at=record.get("created_at", ""),
        updated_at=record.get("updated_at", ""),
    )


@router.get(
    "/documents/{document_id}/file",
    response_class=FileResponse,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF file"},
        404: {"model": ErrorResponse},
    },
)
async def download_document(
    document_id: str,
    inline: bool = False,
    status_store: DocumentStatusStore = Depends(get_status_store_from_request),
    current_user: User = Depends(get_current_user_with_query_token),
) -> FileResponse:
    record = status_store.get_status(document_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )
    if current_user.role != "admin" and record.get("user_id") != current_user.user_id:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )

    settings = get_settings()
    file_name = record.get("file_name", "")
    if file_name.startswith(f"{document_id}_"):
        file_name = file_name[len(document_id) + 1:]
    file_path = settings.data_dir / f"{document_id}_{file_name}"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found on disk.",
        )

    return FileResponse(
        path=str(file_path),
        filename=file_name,
        media_type="application/pdf",
        content_disposition_type="inline" if inline else "attachment",
    )


@router.get(
    "/api/documents",
    response_model=list[DocumentStatusResponse],
)
async def list_documents(
    name: str | None = None,
    status_store: DocumentStatusStore = Depends(get_status_store_from_request),
    current_user: User = Depends(get_current_user),
) -> list[DocumentStatusResponse]:
    all_records = status_store.list_statuses()
    result: list[DocumentStatusResponse] = []
    for record in all_records.values():
        if current_user.role == "admin" or record.get("user_id") == current_user.user_id:
            if name and record.get("file_name") != name:
                continue
            result.append(
                DocumentStatusResponse(
                    document_id=record["document_id"],
                    file_name=record.get("file_name", ""),
                    status=record["status"],
                    chunks_created=record.get("chunks_created", 0),
                    error=record.get("error"),
                    user_id=record.get("user_id", ""),
                    created_at=record.get("created_at", ""),
                    updated_at=record.get("updated_at", ""),
                )
            )
    return result


@router.post(
    "/documents/{document_id}/retry",
    response_model=IngestAcceptedResponse,
    responses={404: {"model": ErrorResponse}},
)
async def retry_ingestion(
    document_id: str,
    status_store: DocumentStatusStore = Depends(get_status_store_from_request),
    current_user: User = Depends(get_current_user),
    ingestion_service: PdfIngestionService = Depends(get_ingestion_service_from_request),
) -> IngestAcceptedResponse:
    record = status_store.get_status(document_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )
    if current_user.role != "admin" and record.get("user_id") != current_user.user_id:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )
    if record["status"] not in (DocumentStatus.FAILED.value, DocumentStatus.PROCESSING.value):
        raise HTTPException(
            status_code=400,
            detail=f"Document {document_id} is not in FAILED or PROCESSING status (current: {record['status']}).",
        )

    settings = get_settings()
    file_name = record.get("file_name", "")
    if file_name.startswith(f"{document_id}_"):
        file_name = file_name[len(document_id) + 1:]
    file_path = settings.data_dir / f"{document_id}_{file_name}"

    if not file_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Original file {file_name} not found on disk.",
        )

    status_store.set_status(
        document_id,
        DocumentStatus.PROCESSING,
        file_name=file_name,
        user_id=record.get("user_id", ""),
    )

    try:
        chunk_count = ingestion_service.ingest_file(file_path, user_id=record.get("user_id", ""), document_name=file_name)
        status_store.set_status(
            document_id,
            DocumentStatus.COMPLETED,
            file_name=file_name,
            user_id=record.get("user_id", ""),
            chunks_created=chunk_count,
        )
        return IngestAcceptedResponse(
            document_id=document_id,
            file_name=file_name,
            status=DocumentStatus.COMPLETED.value,
            user_id=record.get("user_id", ""),
        )
    except Exception as exc:
        logger.error(
            "event=retry_failed document_id=%s error=%s",
            document_id,
            exc,
        )
        status_store.set_status(
            document_id,
            DocumentStatus.FAILED,
            file_name=file_name,
            user_id=record.get("user_id", ""),
            error=str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail=f"Retry failed: {exc}",
        )


@router.delete(
    "/documents/{document_id}",
    responses={
        200: {"description": "Document deleted"},
        404: {"model": ErrorResponse},
    },
)
async def delete_document(
    document_id: str,
    status_store: DocumentStatusStore = Depends(get_status_store_from_request),
    chroma_store: ChromaVectorStore = Depends(get_chroma_store),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    record = status_store.get_status(document_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )
    if current_user.role != "admin" and record.get("user_id") != current_user.user_id:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )

    file_name = record.get("file_name", "")
    if file_name.startswith(f"{document_id}_"):
        file_name = file_name[len(document_id) + 1:]
    file_path = get_settings().data_dir / f"{document_id}_{file_name}"

    if file_path.exists():
        file_path.unlink()
        logger.info("event=document_file_deleted document_id=%s file=%s", document_id, file_name)

    chroma_store.delete_document(document_name=file_name, user_id=record.get("user_id", ""))
    status_store.delete_status(document_id)

    logger.info("event=document_deleted document_id=%s file=%s", document_id, file_name)
    return {"status": "deleted", "document_id": document_id}
