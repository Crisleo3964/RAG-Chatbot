from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path

import shutil

import fitz
import pytesseract
from pypdf import PdfReader
from PIL import Image

_TESSERACT_CMD = shutil.which("tesseract")
if _TESSERACT_CMD is None:
    _WIN_CANDIDATES = [
        f"{os.environ.get('PROGRAMFILES', '')}\\Tesseract-OCR\\tesseract.exe",
        f"{os.environ.get('PROGRAMFILES(X86)', '')}\\Tesseract-OCR\\tesseract.exe",
        f"{os.environ.get('LOCALAPPDATA', '')}\\Programs\\Tesseract-OCR\\tesseract.exe",
    ]
    for _candidate in _WIN_CANDIDATES:
        if os.path.exists(_candidate):
            _TESSERACT_CMD = _candidate
            break
if _TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD

from config import get_settings
from llm.ollama_client import OllamaClient
from models.schemas import ChunkRecord
from storage.chroma_store import ChromaVectorStore
from utils.chunking import group_into_chunks, split_sentences

logger = logging.getLogger(__name__)


class PdfIngestionService:
    def __init__(self, store: ChromaVectorStore | None = None, ollama: OllamaClient | None = None) -> None:
        self.settings = get_settings()
        self.store = store or ChromaVectorStore()
        self.ollama = ollama or OllamaClient()

    def ingest_path(self, path: Path, reset_collection: bool = False, user_id: str = "") -> int:
        if path.is_dir():
            return self.ingest_directory(path, reset_collection=reset_collection, user_id=user_id)
        return self.ingest_file(path, user_id=user_id)

    def ingest_directory(self, data_dir: Path, reset_collection: bool = False, user_id: str = "") -> int:
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        if reset_collection:
            logger.info("event=collection_reset")
            self.store.reset()

        pdf_files = sorted(data_dir.glob("*.pdf"))
        if not pdf_files:
            raise RuntimeError(f"No PDF files found in: {data_dir}")

        total_chunks = 0
        for pdf_path in pdf_files:
            total_chunks += self.ingest_file(pdf_path, user_id=user_id)
        logger.info("event=ingestion_complete total_chunks=%s files=%s", total_chunks, len(pdf_files))
        return total_chunks

    def _ocr_page(self, pdf_path: Path, page_index: int) -> str:
        doc = fitz.open(str(pdf_path))
        page = doc[page_index]
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        text = pytesseract.image_to_string(img)
        return text.strip()

    def ingest_file(self, pdf_path: Path, user_id: str = "", check_duplicates: bool = True, document_name: str | None = None) -> int:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        document_name = document_name or pdf_path.name
        if check_duplicates and self.store.document_exists(document_name, user_id=user_id):
            logger.info("event=document_skipped_duplicate document=%s user=%s", document_name, user_id)
            return 0

        chunks = self._extract_chunks(pdf_path, user_id=user_id, document_name=document_name)
        if not chunks:
            logger.warning("event=document_no_chunks document=%s", document_name)
            return 0

        embeddings = self.ollama.embed_texts([chunk.text for chunk in chunks], batch_size=self.settings.batch_size)
        self.store.add_chunks_batched(chunks, embeddings, self.settings.batch_size)
        logger.info("event=document_ingested document=%s chunks=%s", document_name, len(chunks))
        return len(chunks)

    def prepare_chunks(self, pdf_path: Path, document_id: str, user_id: str = "", document_name: str | None = None) -> None:
        document_name = document_name or pdf_path.name
        chunks = self._extract_chunks(pdf_path, user_id=user_id, document_name=document_name)
        if not chunks:
            logger.warning("event=document_no_chunks document=%s", document_name)
            return

        embeddings = self.ollama.embed_texts([chunk.text for chunk in chunks], batch_size=self.settings.batch_size)
        data = {
            "document_id": document_id,
            "document_name": document_name,
            "user_id": user_id,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                    "text": c.text,
                    "user_id": c.user_id,
                    "ingestion_timestamp": c.ingestion_timestamp,
                }
                for c in chunks
            ],
            "embeddings": embeddings,
        }
        self.settings.chunks_pending_dir.mkdir(parents=True, exist_ok=True)
        dest = self.settings.chunks_pending_dir / f"{document_id}.json"
        with dest.open("w") as f:
            json.dump(data, f)
        logger.info("event=chunks_prepared document=%s chunks=%s file=%s", document_name, len(chunks), dest)

    def _extract_chunks(self, pdf_path: Path, user_id: str = "", document_name: str = "") -> list[ChunkRecord]:
        reader = PdfReader(str(pdf_path))
        chunks: list[ChunkRecord] = []
        step = self.settings.chunk_size - self.settings.chunk_overlap
        if step <= 0:
            raise ValueError("Invalid chunk settings: overlap must be smaller than chunk size.")
        if not document_name:
            document_name = pdf_path.name

        for page_index, page in enumerate(reader.pages):
            page_number = page_index + 1
            raw_text = page.extract_text() or ""
            words = raw_text.split()
            avg_word_len = sum(len(w) for w in words) / max(len(words), 1) if words else 0
            if len(raw_text.strip()) < 50 or avg_word_len < 3:
                logger.info("event=page_ocr page=%s document=%s", page_index + 1, document_name)
                raw_text = self._ocr_page(pdf_path, page_index)
            text = " ".join(raw_text.split())
            if not text:
                continue

            sentences = split_sentences(text)
            page_chunks = group_into_chunks(sentences, self.settings.chunk_size, self.settings.chunk_overlap)
            for chunk_text in page_chunks:
                chunk_id = str(uuid.uuid4())
                chunks.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        document_name=document_name,
                        page_number=page_number,
                        text=f"Title: {document_name}\n{chunk_text}",
                        user_id=user_id,
                    )
                )
        return chunks
