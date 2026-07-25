"""
core/config.py

Centralised application settings loaded from environment variables
or Streamlit Secrets, with sensible defaults.  A single Settings
singleton is created at import time and reused throughout the app.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration.

    Reads values from environment variables with fallbacks.
    On Streamlit Cloud, secrets are injected as environment variables
    automatically when using st.secrets, but this class supports
    both mechanisms transparently.

    Attributes:
        gemini_api_keys: Ordered list of Gemini API keys for failover.
        embedding_model: HuggingFace sentence-transformer model name.
        gemini_model: Gemini model identifier string.
        knowledge_base_path: Path to the CSV knowledge base file.
        vectorstore_path: Directory where the FAISS index is persisted.
        max_retrieved_docs: Number of documents to retrieve per query.
        retriever_score_threshold: Minimum similarity score to include.
    """

    gemini_api_keys: list[str] = field(default_factory=list)
    embedding_model: str = "all-MiniLM-L6-v2"
    gemini_model: str = "gemini-3.6-flash"
    knowledge_base_path: str = "data/knowledge_base.csv"
    vectorstore_path: str = "vectorstore/faiss_index"
    max_retrieved_docs: int = 6
    retriever_score_threshold: float = 0.3


def _collect_api_keys() -> list[str]:
    """Collect up to five Gemini API keys from Streamlit Secrets or environment.

    Returns:
        Non-empty list of API key strings, in priority order.
    """
    keys: list[str] = []

    # 1. Try Streamlit Secrets
    try:
        from pathlib import Path
        import streamlit as st  # type: ignore

        secrets_exist = (
            Path(".streamlit/secrets.toml").exists()
            or Path("~/.streamlit/secrets.toml").expanduser().exists()
        )

        if secrets_exist and hasattr(st, "secrets"):
            for index in range(1, 6):
                key_name = f"GEMINI_API_KEY_{index}"
                try:
                    if key_name in st.secrets:
                        val = str(st.secrets[key_name]).strip().strip("\"'")
                        if val and val not in keys:
                            keys.append(val)
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Check environment variables (.env file or system env)
    for index in range(1, 6):
        key_name = f"GEMINI_API_KEY_{index}"
        val = os.getenv(key_name)
        if val:
            val = val.strip().strip("\"'")
            if val and val not in keys:
                keys.append(val)

    return keys


def get_settings() -> Settings:
    """Build and return the application Settings singleton.

    Returns:
        A fully initialised, immutable Settings object.
    """
    api_keys = _collect_api_keys()

    if not api_keys:
        logger.warning(
            "No Gemini API keys found.  Set GEMINI_API_KEY_1 … "
            "GEMINI_API_KEY_5 in .env or Streamlit Secrets."
        )

    return Settings(
        gemini_api_keys=api_keys,
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        knowledge_base_path=os.getenv(
            "KNOWLEDGE_BASE_PATH", "data/knowledge_base.csv"
        ),
        vectorstore_path=os.getenv("VECTORSTORE_PATH", "vectorstore/faiss_index"),
        max_retrieved_docs=int(os.getenv("MAX_RETRIEVED_DOCS", "6")),
        retriever_score_threshold=float(
            os.getenv("RETRIEVER_SCORE_THRESHOLD", "0.3")
        ),
    )
