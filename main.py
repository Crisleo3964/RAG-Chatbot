import multiprocessing
import os
import sys
from pathlib import Path

_src = Path(__file__).parent / "rag-chatbot" / "src"
sys.path.insert(0, str(_src))


def _ensure_groq_key() -> None:
    if os.getenv("GROQ_API_KEY"):
        return
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        value, _ = winreg.QueryValueEx(key, "GROQ_API_KEY")
        winreg.CloseKey(key)
        if value:
            os.environ["GROQ_API_KEY"] = value
    except Exception:
        pass


def _start_worker() -> None:
    import logging
    import time

    logger = logging.getLogger("worker")
    delay = 5
    while True:
        try:
            from workers.ingestion_worker import run_worker

            run_worker()
        except Exception as exc:
            logger.warning(
                "event=worker_unavailable error=%s. "
                "RabbitMQ may not be running. "
                "Retrying in %ss...",
                exc,
                delay,
            )
        time.sleep(delay)
        delay = min(delay * 2, 60)


def _worker_watcher(proc: multiprocessing.Process) -> None:
    import logging
    import time

    logger = logging.getLogger("worker_watcher")
    while True:
        time.sleep(10)
        if not proc.is_alive():
            logger.warning("event=worker_died restarting")
            new_proc = multiprocessing.Process(target=_start_worker, daemon=True, name="ingestion-worker")
            new_proc.start()
            logger.info("event=worker_restarted pid=%s", new_proc.pid)
            proc = new_proc


if __name__ == "__main__":
    import logging
    import threading

    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    logger = logging.getLogger("launcher")

    _ensure_groq_key()

    _has_rabbitmq = False
    try:
        import pika
        from config import get_settings
        settings = get_settings()
        params = pika.URLParameters(settings.rabbitmq_url)
        params.heartbeat = 5
        params.blocked_connection_timeout = 3
        conn = pika.BlockingConnection(params)
        conn.close()
        _has_rabbitmq = True
    except Exception:
        logger.warning("event=rabbitmq_unavailable worker_disabled async_ingestion_via_api_unavailable")

    if _has_rabbitmq:
        worker = multiprocessing.Process(target=_start_worker, daemon=True, name="ingestion-worker")
        worker.start()
        logger.info("event=worker_started pid=%s", worker.pid)

        watcher = threading.Thread(target=_worker_watcher, args=(worker,), daemon=True, name="worker-watcher")
        watcher.start()
    else:
        worker = None

    try:
        uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
    except KeyboardInterrupt:
        logger.info("event=shutdown_initiated")
    finally:
        if worker is not None and worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)
            logger.info("event=worker_stopped")
