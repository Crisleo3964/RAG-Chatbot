from __future__ import annotations

import logging

import pika

from config import get_settings

logger = logging.getLogger(__name__)


def create_connection() -> pika.BlockingConnection:
    settings = get_settings()
    params = pika.URLParameters(settings.rabbitmq_url)
    params.heartbeat = 600
    params.blocked_connection_timeout = 300
    logger.debug("event=rabbitmq_connecting url=%s", settings.rabbitmq_url)
    return pika.BlockingConnection(params)
