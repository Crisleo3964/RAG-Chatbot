from __future__ import annotations

from models.schemas import RetrievedChunk

RAG_PROMPT_TEMPLATE = (
    "You are a document assistant.\n"
    "\n"
    "Answer only using the provided context.\n"
    "\n"
    "If the answer is not present in the context, say that the information "
    "is not available in the provided documents.\n"
    "\n"
    "Context:\n"
    "{retrieved_context}\n"
    "\n"
    "Question:\n"
    "{user_question}"
)


def build_rag_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_blocks: list[str] = []
    for chunk in chunks:
        doc_name = chunk.metadata.get("document_name", "unknown")
        page_number = chunk.metadata.get("page_number", "unknown")
        chunk_id = chunk.metadata.get("chunk_id", chunk.chunk_id)
        context_blocks.append(
            f"[Document: {doc_name} | Page: {page_number} | Chunk: {chunk_id}]\n{chunk.text}"
        )

    retrieved_context = "\n\n".join(context_blocks)
    return RAG_PROMPT_TEMPLATE.format(
        retrieved_context=retrieved_context,
        user_question=question,
    )
