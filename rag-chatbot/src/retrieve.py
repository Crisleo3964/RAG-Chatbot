from __future__ import annotations

import argparse
import json
import logging
from retrieval.retrieval_service import RetrievalService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve similar chunks for a question.")
    parser.add_argument("question", type=str, help="Question to search for.")
    parser.add_argument("--top-k", type=int, default=None, help="Number of chunks to retrieve.")
    parser.add_argument(
        "--user-id",
        type=str,
        default="",
        help="User ID to scope document access.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_id = args.user_id
    if not user_id:
        from auth.auth_service import get_auth_service
        auth = get_auth_service()
        users = auth.list_users()
        if users:
            user_id = users[0].user_id
    service = RetrievalService()
    try:
        chunks = service.search(question=args.question, top_k=args.top_k, user_id=user_id or None)
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        raise SystemExit(1) from exc

    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "metadata": chunk.metadata,
            "distance": chunk.distance,
            "text_preview": chunk.text[:300],
        }
        for chunk in chunks
    ]
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
