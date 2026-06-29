"""
Backfill utility: Create status_store.json entries from existing ChromaDB data.

Run: python src/backfill_status_store.py [--user-id <uuid>]

If --user-id is omitted, entries are created for ALL users found in ChromaDB.
"""
from __future__ import annotations

import argparse
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import get_settings
from storage.chroma_store import ChromaVectorStore
from storage.document_status_store import DocumentStatus, DocumentStatusStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Matches UUID prefix like "b9573047-984d-4e4b-b4c6-fb3c1d983946_"
_UUID_PREFIX_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_")


def _strip_uuid_prefix(name: str) -> str:
    return _UUID_PREFIX_RE.sub("", name, count=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill status_store.json from existing ChromaDB data."
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="",
        help="Only backfill for this specific user ID.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    store = ChromaVectorStore()
    status_store = DocumentStatusStore(settings.status_store_path)
    result = store.get_all()
    metadatas = result.get("metadatas") or []

    from collections import defaultdict

    doc_map: dict[tuple[str, str], int] = defaultdict(int)
    for m in metadatas:
        doc_name = m.get("document_name", "unknown")
        user_id = m.get("user_id", "")
        if args.user_id and user_id != args.user_id:
            continue
        doc_map[(doc_name, user_id)] += 1

    if not doc_map:
        logger.info("No documents found in ChromaDB to backfill.")
        return

    existing = status_store.list_statuses()
    existing_docs = set()
    for rec in existing.values():
        existing_docs.add((rec.get("file_name", ""), rec.get("user_id", "")))

    created = 0
    skipped = 0
    for (doc_name, user_id), chunk_count in sorted(doc_map.items()):
        file_name = _strip_uuid_prefix(doc_name)

        if (file_name, user_id) in existing_docs:
            logger.info("Skipping existing: file=%s user=%s", file_name, user_id[:12])
            skipped += 1
            continue

        document_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        status_store.set_status(
            document_id,
            DocumentStatus.COMPLETED,
            file_name=file_name,
            user_id=user_id,
            chunks_created=chunk_count,
        )
        logger.info(
            "Created: file=%s user=%s chunks=%s doc_id=%s",
            file_name, user_id[:12], chunk_count, document_id[:8],
        )
        created += 1

    logger.info("Done: %d created, %d skipped", created, skipped)


if __name__ == "__main__":
    main()
