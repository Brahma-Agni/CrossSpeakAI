"""
rag/retriever.py

Builds and manages a FAISS vector store backed by sentence-transformer
embeddings.  The index is persisted to disk so it is rebuilt only when
the knowledge base changes, keeping Streamlit Cloud cold-starts fast.
"""

from __future__ import annotations

import os
from pathlib import Path

# Prevent TensorFlow from being loaded by transformers/sentence-transformers.
# TF on this host has a protobuf version mismatch; these flags tell the
# transformers library to skip TF entirely and use PyTorch only.
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

from langchain_community.vectorstores import FAISS  # type: ignore
from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
from langchain_core.documents import Document  # type: ignore

from utils.logger import get_logger

logger = get_logger(__name__)


class Retriever:
    """FAISS-backed semantic retriever for the Cross Speak AI knowledge base.

    Handles both building a fresh index from Documents and loading a
    previously persisted index from disk.  Exposes a simple
    :meth:`retrieve` interface to the RAG pipeline.

    Attributes:
        _vector_store: The underlying FAISS vector store instance.
        _max_docs: Maximum number of documents to return per query.
    """

    def __init__(
        self,
        vector_store: FAISS,
        embeddings: HuggingFaceEmbeddings,
        max_docs: int = 6,
    ) -> None:
        """Initialise the retriever with an existing FAISS vector store.

        Prefer the :meth:`build` or :meth:`load` class methods over
        direct construction.

        Args:
            vector_store: Pre-built or loaded FAISS vector store.
            max_docs: Maximum documents returned per retrieval call.
        """
        self._vector_store: FAISS = vector_store
        self._embeddings = embeddings
        self._max_docs: int = max_docs
        logger.debug("Retriever ready (max_docs=%d).", self._max_docs)

    @classmethod
    def build(
        cls,
        documents: list[Document],
        embedding_model: str,
        persist_path: str,
        max_docs: int = 6,
    ) -> "Retriever":
        """Build a FAISS index from scratch and persist it to disk.

        Args:
            documents: List of LangChain Documents to embed and index.
            embedding_model: HuggingFace model name for embeddings.
            persist_path: Directory path where the index will be saved.
            max_docs: Maximum documents returned per retrieval call.

        Returns:
            A fully initialised :class:`Retriever` instance.

        Raises:
            ValueError: If the documents list is empty.
        """
        if not documents:
            raise ValueError(
                "Cannot build a FAISS index from an empty document list."
            )

        logger.info(
            "Building FAISS index from %d documents using '%s'.",
            len(documents),
            embedding_model,
        )

        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        vector_store = FAISS.from_documents(documents, embeddings)

        persist_dir = Path(persist_path)
        persist_dir.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(persist_dir))

        logger.info("FAISS index saved to '%s'.", persist_dir)
        return cls(
            vector_store=vector_store,
            embeddings=embeddings,
            max_docs=max_docs,
        )

    @classmethod
    def load(
        cls,
        embedding_model: str,
        persist_path: str,
        max_docs: int = 6,
    ) -> "Retriever":
        """Load an existing FAISS index from disk.

        Args:
            embedding_model: HuggingFace model name used to build the index.
            persist_path: Directory path where the index is stored.
            max_docs: Maximum documents returned per retrieval call.

        Returns:
            A fully initialised :class:`Retriever` instance.

        Raises:
            FileNotFoundError: If the persist path does not contain a
                valid FAISS index.
        """
        persist_dir = Path(persist_path)
        if not persist_dir.exists():
            raise FileNotFoundError(
                f"FAISS index not found at '{persist_dir}'.  "
                "Call Retriever.build() first."
            )

        logger.info("Loading FAISS index from '%s'.", persist_dir)

        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        vector_store = FAISS.load_local(
            str(persist_dir),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        logger.info("FAISS index loaded successfully.")
        return cls(
            vector_store=vector_store,
            embeddings=embeddings,
            max_docs=max_docs,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed text with the same normalized 384-d model used by FAISS."""
        return [float(value) for value in self._embeddings.embed_query(text)]

    def retrieve(
        self,
        query: str,
        score_threshold: float = 0.3,
    ) -> list[Document]:
        """Retrieve the most semantically similar documents for a query.

        Args:
            query: The user's input text used as the search query.
            score_threshold: Minimum similarity score (0-1) to include.

        Returns:
            Ordered list of :class:`Document` objects, most relevant first.
        """
        results: list[tuple[Document, float]] = (
            self._vector_store.similarity_search_with_score(
                query, k=self._max_docs
            )
        )

        filtered: list[Document] = [
            doc
            for doc, score in results
            if score <= score_threshold  # FAISS uses L2; lower = better
        ]

        # Fallback: return top results even if all are below threshold
        if not filtered:
            filtered = [doc for doc, _ in results[: min(3, len(results))]]
            logger.debug(
                "Score threshold %.2f produced no results; "
                "falling back to top-%d.",
                score_threshold,
                len(filtered),
            )

        logger.debug("Retrieved %d document(s) for query.", len(filtered))
        return filtered
