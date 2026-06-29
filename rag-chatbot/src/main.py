from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from api.routes import auth_routes, chat, health, ingest
from api.schemas.api_models import ErrorResponse
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _validate_chromadb(chroma_path: Path) -> None:
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_path))
        client.heartbeat()
        logger.info("startup_validator=chromadb path=%s", chroma_path)
    except Exception as exc:
        raise RuntimeError(
            f"ChromaDB is not accessible at {chroma_path}. Error: {exc}"
        ) from exc


def _validate_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("startup_validator=data_dir path=%s", data_dir)


def _validate_rabbitmq(rabbitmq_url: str) -> None:
    try:
        import pika

        params = pika.URLParameters(rabbitmq_url)
        params.heartbeat = 10
        params.blocked_connection_timeout = 5
        conn = pika.BlockingConnection(params)
        conn.close()
        logger.info("startup_validator=rabbitmq url=%s", rabbitmq_url)
    except Exception as exc:
        logger.warning(
            "startup_validator=rabbitmq_unavailable url=%s error=%s. "
            "Async ingestion via API will not work. "
            "CLI ingestion and chat are unaffected.",
            rabbitmq_url,
            exc,
        )


app = FastAPI(
    title="RAG Chatbot API",
    description=(
        "Multi-document Retrieval-Augmented Generation chatbot powered by Groq "
        "and ChromaDB. Supports PDF ingestion, semantic search, and Q&A with "
        "source citations.\n\n"
        "## Authentication\n"
        "All endpoints (except `/health` and `/auth/register`) require authentication.\n"
        "1. `POST /auth/register` — create an account (email, password)\n"
        "2. `POST /auth/token` — login, get a JWT token\n"
        "3. Use the token as `Authorization: Bearer <token>` for all other endpoints\n\n"
        "Default admin credentials are printed on first server start.\n"
        "Use `python src/manage_users.py --reset-admin-password` to reset it."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


def _custom_openapi() -> dict:
    from fastapi.openapi.utils import get_openapi
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/auth/token",
                    "scopes": {},
                },
            },
            "description": "Enter email and password. Swagger will call /auth/token and use the JWT.",
        },
    }
    schema.setdefault("paths", {})
    for path in schema["paths"].values():
        for operation in path.values():
            if "security" in operation:
                del operation["security"]
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi


async def _process_pending_chunks() -> None:
    from api.dependencies.containers import get_chroma_store
    from storage.document_status_store import DocumentStatus

    store = get_chroma_store()
    settings = get_settings()
    status_store = None
    poll_interval = 2

    while True:
        try:
            pending_dir = settings.chunks_pending_dir
            if not pending_dir.exists():
                await asyncio.sleep(poll_interval)
                continue

            for f in sorted(pending_dir.glob("*.json")):
                try:
                    data = json.loads(f.read_text())
                    document_id = data["document_id"]
                    chunks_data = data["chunks"]
                    embeddings = data["embeddings"]

                    from models.schemas import ChunkRecord
                    chunks = [ChunkRecord(**c) for c in chunks_data]

                    store.add_chunks(chunks, embeddings)
                    f.unlink()

                    if status_store is None:
                        from storage.document_status_store import DocumentStatusStore
                        status_store = DocumentStatusStore(settings.status_store_path)

                    status_store.set_status(
                        document_id,
                        DocumentStatus.COMPLETED,
                        file_name=data["document_name"],
                        user_id=data.get("user_id", ""),
                        chunks_created=len(chunks),
                    )
                    logger.info(
                        "event=pending_chunks_written document_id=%s chunks=%s",
                        document_id,
                        len(chunks),
                    )
                except Exception as exc:
                    logger.exception(
                        "event=pending_chunks_failed file=%s error=%s",
                        f.name,
                        exc,
                    )
        except Exception as exc:
            logger.exception("event=pending_chunks_poll_error error=%s", exc)

        await asyncio.sleep(poll_interval)


@app.on_event("startup")
async def startup_validation() -> None:
    settings = get_settings()
    logger.info("startup_validator=starting")
    _validate_data_dir(settings.data_dir)
    _validate_data_dir(settings.chunks_pending_dir)
    _validate_chromadb(settings.chroma_path)
    _validate_rabbitmq(settings.rabbitmq_url)
    status = "available" if _frontend_available else "not_built"
    logger.info("frontend=%s path=%s", status, _frontend_dist)
    logger.info("startup_validator=all_checks_passed")
    asyncio.create_task(_process_pending_chunks())


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error path=%s error=%s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(detail=str(exc)).model_dump(),
    )


app.include_router(health.router)
app.include_router(chat.router)
app.include_router(ingest.router)
app.include_router(auth_routes.router)

_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_frontend_available = _frontend_dist.joinpath("index.html").exists()

_SPA_ROUTES = frozenset({"/", "/login", "/chat", "/documents", "/admin/users"})


@app.middleware("http")
async def _spa_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method

    is_api_or_asset = (
        path.startswith("/api")
        or path.startswith("/auth")
        or path.startswith("/docs")
        or path.startswith("/redoc")
        or path.startswith("/health")
        or path.startswith("/ingest")
        or path == "/openapi.json"
        or Path(path).suffix
        or (path.startswith("/documents") and path != "/documents")
    )

    if _frontend_available and method == "GET" and path in _SPA_ROUTES:
        accept = request.headers.get("accept", "")
        sec_fetch_mode = request.headers.get("sec-fetch-mode", "")
        is_browser_nav = sec_fetch_mode == "navigate" or accept.startswith("text/html")
        if is_browser_nav:
            return FileResponse(str(_frontend_dist / "index.html"))

    response = await call_next(request)

    if _frontend_available and response.status_code == 404 and method == "GET" and not is_api_or_asset:
        return FileResponse(str(_frontend_dist / "index.html"))

    return response


if _frontend_available:
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")
    static_files = {"/favicon.svg", "/icons.svg"}
    for name in ("favicon.svg", "icons.svg"):
        file_path = _frontend_dist / name
        if file_path.exists():
            app.add_api_route(f"/{name}", lambda n=name: FileResponse(str(_frontend_dist / n)), include_in_schema=False)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
