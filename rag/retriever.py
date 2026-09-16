"""Lightweight retrieval for the Cross Speak AI knowledge base.

The retriever intentionally uses only the Python standard library. This keeps
the FastAPI function small enough for serverless deployment while still
grounding Gemini with the most relevant curated terms.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from langchain_core.documents import Document  # type: ignore

from utils.logger import get_logger

logger = get_logger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
_EMBEDDING_DIMENSIONS = 384


def _tokens(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


class Retriever:
    """Small in-memory lexical retriever with deterministic embeddings."""

    def __init__(self, documents: list[Document], max_docs: int = 6) -> None:
        self._documents = documents
        self._max_docs = max_docs
        self._document_tokens = [Counter(_tokens(doc.page_content)) for doc in documents]
        logger.debug("Retriever ready (%d documents, max_docs=%d).", len(documents), max_docs)

    @classmethod
    def build(
        cls,
        documents: list[Document],
        embedding_model: str,
        persist_path: str,
        max_docs: int = 6,
    ) -> "Retriever":
        """Build an in-memory index and cache its documents when writable."""
        del embedding_model
        if not documents:
            raise ValueError("Cannot build an index from an empty document list.")

        retriever = cls(documents=documents, max_docs=max_docs)
        try:
            persist_dir = Path(persist_path)
            persist_dir.mkdir(parents=True, exist_ok=True)
            payload = [
                {"page_content": doc.page_content, "metadata": doc.metadata}
                for doc in documents
            ]
            (persist_dir / "documents.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            logger.info("Retriever cache is read-only; continuing in memory.")
        return retriever

    @classmethod
    def load(
        cls,
        embedding_model: str,
        persist_path: str,
        max_docs: int = 6,
    ) -> "Retriever":
        """Load the cached document index."""
        del embedding_model
        cache_file = Path(persist_path) / "documents.json"
        if not cache_file.exists():
            raise FileNotFoundError(f"Retriever cache not found at '{cache_file}'.")
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        documents = [
            Document(page_content=item["page_content"], metadata=item["metadata"])
            for item in payload
        ]
        return cls(documents=documents, max_docs=max_docs)

    def embed_text(self, text: str) -> list[float]:
        """Return a stable normalized 384-d vector for Supabase pgvector."""
        vector = [0.0] * _EMBEDDING_DIMENSIONS
        for token in _tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % _EMBEDDING_DIMENSIONS
            vector[index] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude:
            vector = [value / magnitude for value in vector]
        return vector

    def retrieve(
        self,
        query: str,
        score_threshold: float = 0.3,
    ) -> list[Document]:
        """Return documents ranked by normalized token overlap."""
        del score_threshold
        query_tokens = Counter(_tokens(query))
        if not query_tokens:
            return self._documents[: min(3, len(self._documents))]

        scored: list[tuple[float, Document]] = []
        for doc, document_tokens in zip(self._documents, self._document_tokens):
            overlap = sum((query_tokens & document_tokens).values())
            phrase_bonus = 2 if str(doc.metadata.get("term", "")).lower() in query.lower() else 0
            score = (overlap + phrase_bonus) / max(1, sum(query_tokens.values()))
            scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        relevant = [doc for score, doc in scored[: self._max_docs] if score > 0]
        if relevant:
            return relevant
        return [doc for _, doc in scored[: min(3, len(scored))]]
