from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

from workers.ingestion_worker import run_worker  # noqa: E402

if __name__ == "__main__":
    run_worker()
