from __future__ import annotations

from llm.groq_client import GroqClient
from llm.prompt_builder import build_rag_prompt
from models.schemas import ChatResponse, SourceRef
from retrieval.retrieval_service import RetrievalService


class RagChatService:
    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        groq_client: GroqClient | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or RetrievalService()
        self.groq_client = groq_client or GroqClient()

    def ask(self, question: str, top_k: int | None = None, user_id: str | None = None) -> ChatResponse:
        chunks = self.retrieval_service.search(question=question, top_k=top_k, user_id=user_id)
        if not chunks:
            raise RuntimeError("No documents found in the knowledge base. Please upload a PDF first from the Documents page.")

        prompt = build_rag_prompt(question=question, chunks=chunks)
        answer = self.groq_client.generate(prompt=prompt)

        sources: list[SourceRef] = []
        seen: set[tuple[str, int]] = set()
        for chunk in chunks:
            document = str(chunk.metadata.get("document_name", "unknown"))
            page = int(chunk.metadata.get("page_number", -1))
            key = (document, page)
            if key not in seen:
                seen.add(key)
                sources.append(SourceRef(document=document, page=page))
        return ChatResponse(answer=answer, sources=sources)
