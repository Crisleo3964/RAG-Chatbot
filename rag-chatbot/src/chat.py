from __future__ import annotations

import argparse
import json
import logging
from llm.rag_chat_service import RagChatService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def interactive_chat(user_id: str = "") -> None:
    service = RagChatService()
    print("RAG chatbot is ready. Type your question (or 'exit' to quit).")
    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return
        if not question:
            print("Please enter a question.")
            continue

        try:
            result = service.ask(question, user_id=user_id)
        except Exception as exc:
            logger.error("Failed to answer question: %s", exc)
            continue

        print(f"\nAnswer: {result.answer}\n")
        print("Sources:")
        for source in result.sources:
            print(f"- {source.document} (Page {source.page})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask questions over ingested PDF content.")
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="Ask a single question and exit (non-interactive mode).",
    )
    parser.add_argument("--top-k", type=int, default=None, help="Override retrieval top_k.")
    parser.add_argument(
        "--user-id",
        type=str,
        default="",
        help="User ID to scope document access.",
    )
    return parser.parse_args()


def _resolve_user_id(user_id: str) -> str:
    if user_id:
        return user_id
    from auth.auth_service import get_auth_service
    auth = get_auth_service()
    users = auth.list_users()
    if users:
        return users[0].user_id
    return ""


def main() -> None:
    args = parse_args()
    user_id = _resolve_user_id(args.user_id)
    service = RagChatService()
    if args.question:
        try:
            result = service.ask(args.question, top_k=args.top_k, user_id=user_id)
        except Exception as exc:
            logger.error("Failed to answer question: %s", exc)
            raise SystemExit(1) from exc

        payload = {
            "answer": result.answer,
            "sources": [{"document": source.document, "page": source.page} for source in result.sources],
        }
        print(json.dumps(payload, indent=2))
        return

    interactive_chat(user_id)


if __name__ == "__main__":
    main()
