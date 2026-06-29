import asyncio
import logging
import multiprocessing
import os
import subprocess
import sys
import threading
from pathlib import Path

_src = Path(__file__).parent / "rag-chatbot" / "src"
sys.path.insert(0, str(_src))

_NGROK_PATH = os.getenv(
    "NGROK_PATH",
    "C:\\Users\\xpi0035\\Downloads\\ngrok-v3-stable-windows-amd64\\ngrok.exe",
)
_HOST = "127.0.0.1"
_PORT = 8001

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("launcher")


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
    import time
    _logger = logging.getLogger("worker")
    delay = 5
    while True:
        try:
            from workers.ingestion_worker import run_worker
            run_worker()
        except Exception as exc:
            _logger.warning(
                "event=worker_unavailable error=%s. Retrying in %ss...", exc, delay,
            )
        time.sleep(delay)
        delay = min(delay * 2, 60)


def _worker_watcher(proc: multiprocessing.Process) -> None:
    import time
    _logger = logging.getLogger("worker_watcher")
    while True:
        time.sleep(10)
        if not proc.is_alive():
            _logger.warning("event=worker_died restarting")
            new_proc = multiprocessing.Process(target=_start_worker, daemon=True, name="ingestion-worker")
            new_proc.start()
            _logger.info("event=worker_restarted pid=%s", new_proc.pid)
            proc = new_proc


def _start_ngrok() -> subprocess.Popen | None:
    if not Path(_NGROK_PATH).exists():
        logger.warning("event=ngrok_not_found path=%s", _NGROK_PATH)
        return None
    proc = subprocess.Popen(
        [_NGROK_PATH, "http", str(_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info("event=ngrok_started pid=%s", proc.pid)
    return proc


def _fetch_ngrok_url() -> str | None:
    import json
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=3)
        data = json.loads(resp.read().decode())
        return data["tunnels"][0]["public_url"]
    except Exception:
        return None


async def main() -> None:
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

    worker = None
    if _has_rabbitmq:
        worker = multiprocessing.Process(target=_start_worker, daemon=True, name="ingestion-worker")
        worker.start()
        logger.info("event=worker_started pid=%s", worker.pid)
        watcher = threading.Thread(target=_worker_watcher, args=(worker,), daemon=True, name="worker-watcher")
        watcher.start()

    import uvicorn
    config = uvicorn.Config("main:app", host=_HOST, port=_PORT, log_level="info")
    server = uvicorn.Server(config)

    ngrok_proc = _start_ngrok()

    try:
        server_task = asyncio.create_task(server.serve())

        while not server.started:
            await asyncio.sleep(0.1)

        url = _fetch_ngrok_url()
        if url:
            logger.info("ngrok_url=%s", url)
        else:
            logger.warning("event=ngrok_url_unavailable")

        await server_task
    except KeyboardInterrupt:
        logger.info("event=shutdown_initiated")
    finally:
        if ngrok_proc is not None and ngrok_proc.poll() is None:
            ngrok_proc.terminate()
            ngrok_proc.wait(timeout=5)
            logger.info("event=ngrok_stopped")
        if worker is not None and worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)
            logger.info("event=worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
