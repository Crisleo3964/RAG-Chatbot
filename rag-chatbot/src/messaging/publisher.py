from __future__ import annotations

import json
import logging

import pika

from config import get_settings
from messaging.connection import create_connection

logger = logging.getLogger(__name__)


def publish_ingestion_task(document_id: str, file_path: str, uploaded_at: str, user_id: str = "") -> None:
    settings = get_settings()
    connection = create_connection()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=settings.rabbitmq_ingestion_queue, durable=True)

        payload = {
            "document_id": document_id,
            "file_path": file_path,
            "uploaded_at": uploaded_at,
            "user_id": user_id,
        }

        channel.basic_publish(
            exchange="",
            routing_key=settings.rabbitmq_ingestion_queue,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info(
            "event=message_published document_id=%s queue=%s",
            document_id,
            settings.rabbitmq_ingestion_queue,
        )
    finally:
        connection.close()
