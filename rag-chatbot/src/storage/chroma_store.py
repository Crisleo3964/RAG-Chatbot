from __future__ import annotations

import logging
from typing import Any

import chromadb

from config import get_settings
from models.schemas import ChunkRecord, RetrievedChunk

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:M": 32,
                "hnsw:construction_ef": 200,
                "hnsw:search_ef": 200,
            },
        )

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        ids = self._collection.get(include=[]).get("ids", [])
        if ids:
            self._collection.delete(ids=ids)

    def document_exists(self, document_name: str, user_id: str = "") -> bool:
        where: dict[str, Any] = {"document_name": {"$eq": document_name}}
        if user_id:
            where = {"$and": [where, {"user_id": {"$eq": user_id}}]}
        result = self._collection.get(where=where, include=[])
        ids = result.get("ids", [])
        return len(ids) > 0

    def add_chunks(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise RuntimeError("Chunk and embedding count mismatch.")

        ids = [chunk.chunk_id for chunk in chunks]
        docs = [chunk.text for chunk in chunks]
        metadatas: list[dict[str, Any]] = [
            {
                "document_name": chunk.document_name,
                "page_number": chunk.page_number,
                "chunk_id": chunk.chunk_id,
                "user_id": chunk.user_id,
                "ingestion_timestamp": chunk.ingestion_timestamp,
            }
            for chunk in chunks
        ]
        try:
            self._collection.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
        except Exception:
            logger.exception("event=add_chunks_failed batch_size=%s", len(chunks))
            raise

    def add_chunks_batched(
        self, chunks: list[ChunkRecord], embeddings: list[list[float]], batch_size: int
    ) -> None:
        committed_ids: list[str] = []
        try:
            for start in range(0, len(chunks), batch_size):
                end = start + batch_size
                batch_ids = [c.chunk_id for c in chunks[start:end]]
                self.add_chunks(chunks[start:end], embeddings[start:end])
                committed_ids.extend(batch_ids)
        except Exception:
            logger.exception(
                "event=batch_failed rolling_back=%s total_chunks=%s",
                len(committed_ids),
                len(chunks),
            )
            if committed_ids:
                self._collection.delete(ids=committed_ids)
            raise

    def get_all(self) -> dict[str, Any]:
        return self._collection.get(include=["embeddings", "documents", "metadatas"])

    def delete_document(self, document_name: str, user_id: str = "") -> None:
        where: dict[str, Any] = {"document_name": {"$eq": document_name}}
        if user_id:
            where = {"$and": [where, {"user_id": {"$eq": user_id}}]}
        ids = self._collection.get(where=where, include=[]).get("ids", [])
        if ids:
            self._collection.delete(ids=ids)
            logger.info("event=document_deleted document=%s chunks_removed=%s", document_name, len(ids))

    def query(self, query_embedding: list[float], top_k: int, user_id: str | None = None) -> list[RetrievedChunk]:
        where: dict[str, Any] | None = None
        if user_id:
            where = {"user_id": {"$eq": user_id}}
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        output: list[RetrievedChunk] = []
        for chunk_id, doc, metadata, distance in zip(ids, docs, metadatas, distances):
            output.append(
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    text=doc or "",
                    metadata=metadata or {},
                    distance=float(distance),
                )
            )
        return output
