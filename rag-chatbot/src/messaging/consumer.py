from __future__ import annotations

import logging

import pika

from config import get_settings
from messaging.connection import create_connection

logger = logging.getLogger(__name__)


class QueueConsumer:
    def __init__(self, queue_name: str) -> None:
        self.settings = get_settings()
        self.queue_name = queue_name
        self._connection: pika.BlockingConnection | None = None
        self._channel: pika.adapters.blocking_connection.BlockingChannel | None = None

    def start(self, callback) -> None:
        self._connection = create_connection()
        self._channel = self._connection.channel()
        self._channel.queue_declare(queue=self.queue_name, durable=True)
        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(queue=self.queue_name, on_message_callback=callback)
        logger.info("event=consumer_started queue=%s", self.queue_name)
        try:
            self._channel.start_consuming()
        except Exception as exc:
            logger.error("event=consumer_error queue=%s error=%s", self.queue_name, exc)
            raise

    def stop(self) -> None:
        if self._channel is not None:
            self._channel.stop_consuming()
        if self._connection is not None:
            self._connection.close()
        logger.info("event=consumer_stopped queue=%s", self.queue_name)
