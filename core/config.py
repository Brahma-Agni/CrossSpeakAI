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
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_enabled: bool = False


def _collect_api_keys() -> list[str]:
    """Collect Gemini API keys from Streamlit Secrets or environment variables.

    Supports single key names (GEMINI_API_KEY, GOOGLE_API_KEY) and
    numbered failover keys (GEMINI_API_KEY_1 ... GEMINI_API_KEY_5).

    Returns:
        List of API key strings in priority order.
    """
    keys: list[str] = []

    def _add_key(val: Optional[str]) -> None:
        if val:
            cleaned = str(val).strip().strip("\"'")
            if cleaned and cleaned not in keys:
                keys.append(cleaned)

    # 1. Try Streamlit Secrets (Streamlit Cloud injects st.secrets dynamically)
    try:
        import streamlit as st  # type: ignore

        if hasattr(st, "secrets"):
            for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                try:
                    if key_name in st.secrets:
                        _add_key(st.secrets[key_name])
                except Exception:
                    pass

            for index in range(1, 6):
                key_name = f"GEMINI_API_KEY_{index}"
                try:
                    if key_name in st.secrets:
                        _add_key(st.secrets[key_name])
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Check environment variables (.env file or system env)
    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        _add_key(os.getenv(key_name))

    for index in range(1, 6):
        _add_key(os.getenv(f"GEMINI_API_KEY_{index}"))

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
        supabase_url=os.getenv("SUPABASE_URL", "").strip(),
        supabase_publishable_key=os.getenv(
            "SUPABASE_PUBLISHABLE_KEY", ""
        ).strip(),
        supabase_enabled=os.getenv("SUPABASE_ENABLED", "false").strip().lower()
        in {"1", "true", "yes", "on"},
    )
