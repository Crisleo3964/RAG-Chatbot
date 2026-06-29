from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from storage.chroma_store import ChromaVectorStore


def main() -> None:
    store = ChromaVectorStore()
    count = store._collection.count()
    page_size = 10
    offset = 0

    while offset < count:
        r = store._collection.get(offset=offset, limit=page_size, include=["documents", "metadatas"])

        ids = r["ids"]
        documents = r["documents"]
        metadatas = r["metadatas"]
        for i in range(len(ids)):
            m = metadatas[i]
            doc_name = m.get("document_name", "?")
            page = m.get("page_number", "?")
            chunk_idx = m.get("chunk_index", "?")
            print(f"[{offset + i}] page={page}  chunk={chunk_idx}  doc={doc_name}")
            print(f"    {documents[i][:200]}")
            print()

        offset += page_size
        if offset < count:
            inp = input(f"--- {offset}/{count}  press Enter for more, 'q' to quit --- ")
            if inp.strip().lower() == "q":
                break

    print(f"Done. Total chunks: {count}")


if __name__ == "__main__":
    main()
