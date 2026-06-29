from __future__ import annotations

import argparse
import logging
import uuid
from pathlib import Path
from ingestion.pdf_ingestion_service import PdfIngestionService
from storage.document_status_store import DocumentStatus, DocumentStatusStore
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a PDF file or all PDFs in a directory into ChromaDB."
    )
    parser.add_argument("path", type=Path, help="Path to input PDF file or directory.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the existing collection before ingestion (default: keep existing data).",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="",
        help="UUID of the user to own these documents.",
    )
    parser.add_argument(
        "--email",
        type=str,
        default="",
        help="Email of the user to own these documents (alternative to --user-id).",
    )
    return parser.parse_args()


def _resolve_user_id(user_id: str, email: str) -> str:
    if user_id:
        return user_id
    from auth.auth_service import get_auth_service
    auth = get_auth_service()
    if email:
        user = auth.get_user_by_email(email)
        if user is None:
            logger.error("No user found with email: %s", email)
            raise SystemExit(1)
        return user.user_id
    users = auth.list_users()
    logger.error(
        "Missing --user-id or --email. Available users:\n%s",
        "\n".join(f"  {u.user_id}  ({u.email}) [{u.role}]" for u in users),
    )
    raise SystemExit(1)


def _ingest_file(
    service: PdfIngestionService,
    status_store: DocumentStatusStore,
    pdf_path: Path,
    user_id: str,
) -> int:
    document_id = str(uuid.uuid4())
    file_name = pdf_path.name

    status_store.set_status(
        document_id,
        DocumentStatus.PROCESSING,
        file_name=file_name,
        user_id=user_id,
    )

    try:
        chunk_count = service.ingest_file(pdf_path, user_id=user_id)
        status_store.set_status(
            document_id,
            DocumentStatus.COMPLETED,
            file_name=file_name,
            user_id=user_id,
            chunks_created=chunk_count,
        )
        logger.info(
            "event=cli_file_ingested file=%s chunks=%s document_id=%s",
            file_name, chunk_count, document_id,
        )
        return chunk_count
    except Exception as exc:
        status_store.set_status(
            document_id,
            DocumentStatus.FAILED,
            file_name=file_name,
            user_id=user_id,
            error=str(exc),
        )
        logger.error("event=cli_file_failed file=%s error=%s", file_name, exc)
        raise


def main() -> None:
    args = parse_args()
    user_id = _resolve_user_id(args.user_id, args.email)
    status_store = DocumentStatusStore(settings.status_store_path)
    service = PdfIngestionService()

    pdf_paths: list[Path] = []
    if args.path.is_dir():
        pdf_paths = sorted(args.path.glob("*.pdf"))
        if not pdf_paths:
            logger.error("No PDF files found in: %s", args.path)
            raise SystemExit(1)
        if args.reset:
            logger.info("event=collection_reset")
            service.store.reset()
    else:
        pdf_paths = [args.path]
        if args.reset:
            logger.info("event=collection_reset")
            service.store.reset()

    total_chunks = 0
    exit_code = 0
    for pdf_path in pdf_paths:
        try:
            total_chunks += _ingest_file(service, status_store, pdf_path, user_id)
        except Exception:
            exit_code = 1

    if exit_code:
        logger.error(
            "event=cli_ingest_partial_failure total_chunks=%s files=%s",
            total_chunks, len(pdf_paths),
        )
        raise SystemExit(1)

    logger.info(
        "event=cli_ingest_success total_chunks=%s files=%s user=%s",
        total_chunks, len(pdf_paths), user_id,
    )


if __name__ == "__main__":
    main()
