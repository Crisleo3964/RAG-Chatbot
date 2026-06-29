from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path

_src = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src))

import pika

from auth.auth_service import get_auth_service
from config import get_settings
from ingestion.pdf_ingestion_service import PdfIngestionService
from messaging.consumer import QueueConsumer
from storage.document_status_store import DocumentStatus, DocumentStatusStore

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _get_retry_count(body: dict) -> int:
    return body.get("retry_count", 0)


def process_ingestion_task(
    channel: pika.adapters.blocking_connection.BlockingChannel,
    method: pika.spec.Basic.Deliver,
    properties: pika.spec.BasicProperties,
    body: bytes,
) -> None:
    settings = get_settings()
    status_store = DocumentStatusStore(settings.status_store_path)

    try:
        message = json.loads(body)
        document_id = message["document_id"]
        file_path = message["file_path"]
        user_id = message.get("user_id", "")
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("event=invalid_message error=%s body=%s", exc, body)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    logger.info(
        "event=worker_received document_id=%s file_path=%s user=%s",
        document_id,
        file_path,
        user_id,
    )

    if user_id:
        auth_service = get_auth_service()
        if auth_service.get_user(user_id) is None:
            logger.error(
                "event=worker_unknown_user document_id=%s user_id=%s",
                document_id,
                user_id,
            )
            status_store.set_status(
                document_id,
                DocumentStatus.FAILED,
                file_name=Path(file_path).name,
                user_id=user_id,
                error=f"Unknown user: {user_id}",
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

    current = status_store.get_status(document_id)
    if current and current.get("status") in (
        DocumentStatus.COMPLETED.value,
        DocumentStatus.PROCESSING.value,
    ):
        logger.info(
            "event=document_skipped document_id=%s status=%s",
            document_id,
            current["status"],
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    pdf_path = Path(file_path)
    file_name_stored = pdf_path.name
    if file_name_stored.startswith(f"{document_id}_"):
        file_name_stored = file_name_stored[len(document_id) + 1:]

    status_store.set_status(
        document_id,
        DocumentStatus.PROCESSING,
        file_name=file_name_stored,
        user_id=user_id,
    )

    try:
        ingestion_service = PdfIngestionService()
        ingestion_service.prepare_chunks(pdf_path, document_id=document_id, user_id=user_id, document_name=file_name_stored)
        logger.info(
            "event=worker_chunks_prepared document_id=%s file=%s",
            document_id,
            file_name_stored,
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        retry_count = _get_retry_count(message)
        logger.error(
            "event=worker_failed document_id=%s error=%s retry=%s/%s",
            document_id,
            exc,
            retry_count,
            MAX_RETRIES,
        )
        logger.debug(traceback.format_exc())

        if retry_count >= MAX_RETRIES:
            status_store.set_status(
                document_id,
                DocumentStatus.FAILED,
                file_name=file_name_stored,
                user_id=user_id,
                error=f"Failed after {MAX_RETRIES} retries: {exc}",
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            delay = min(2 ** (retry_count + 1), 30)
            logger.info("event=worker_retry_scheduled document_id=%s delay=%ss retry=%s/%s", document_id, delay, retry_count + 1, MAX_RETRIES)
            time.sleep(delay)
            message["retry_count"] = retry_count + 1
            channel.basic_publish(
                exchange="",
                routing_key=settings.rabbitmq_ingestion_queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)


def run_worker() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    settings = get_settings()
    retry_delay = 5
    while True:
        try:
            consumer = QueueConsumer(settings.rabbitmq_ingestion_queue)
            consumer.start(process_ingestion_task)
        except KeyboardInterrupt:
            logger.info("event=worker_shutdown")
            break
        except Exception as exc:
            logger.warning(
                "event=worker_connection_failed error=%s retry_in=%ss",
                exc,
                retry_delay,
            )
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


if __name__ == "__main__":
    run_worker()
