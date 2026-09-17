"""
core/config.py

Centralised application settings loaded from environment variables.
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

    Attributes:
        gemini_api_keys: Ordered list of Gemini API keys for failover.
        embedding_model: Compatibility label for the retrieval strategy.
        gemini_model: Gemini model identifier string.
        knowledge_base_path: Path to the CSV knowledge base file.
        vectorstore_path: Directory where the retrieval cache is persisted.
        max_retrieved_docs: Number of documents to retrieve per query.
        retriever_score_threshold: Minimum similarity score to include.
    """

    gemini_api_keys: list[str] = field(default_factory=list)
    embedding_model: str = "lexical-hash-384"
    gemini_model: str = "gemini-3.6-flash"
    knowledge_base_path: str = "data/knowledge_base.csv"
    vectorstore_path: str = "vectorstore/faiss_index"
    max_retrieved_docs: int = 6
    retriever_score_threshold: float = 0.3
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_enabled: bool = False
    dynamic_kb_enabled: bool = False
    conversation_memory_turns: int = 4
    payments_enabled: bool = False
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    paid_plan_amount_subunits: int = 49900
    paid_plan_currency: str = "INR"
    paid_plan_duration_days: int = 30

    @property
    def billing_ready(self) -> bool:
        """Whether every server-side dependency for checkout is configured."""
        return bool(
            self.payments_enabled
            and self.supabase_enabled
            and self.supabase_url
            and self.supabase_publishable_key
            and self.supabase_secret_key
            and self.razorpay_key_id
            and self.razorpay_key_secret
            and self.razorpay_webhook_secret
            and self.paid_plan_amount_subunits > 0
            and self.paid_plan_duration_days > 0
        )


def _collect_api_keys() -> list[str]:
    """Collect Gemini API keys from environment variables.

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

    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        _add_key(os.getenv(key_name))

    for index in range(1, 6):
        _add_key(os.getenv(f"GEMINI_API_KEY_{index}"))

    return keys


def _setting(name: str, default: str = "") -> str:
    """Read one setting from the environment."""
    return os.getenv(name, default).strip()


def get_settings() -> Settings:
    """Build and return the application Settings singleton.

    Returns:
        A fully initialised, immutable Settings object.
    """
    api_keys = _collect_api_keys()

    if not api_keys:
        logger.warning(
            "No Gemini API keys found.  Set GEMINI_API_KEY_1 … "
            "GEMINI_API_KEY_5 in .env or the deployment environment."
        )

    return Settings(
        gemini_api_keys=api_keys,
        embedding_model=_setting("EMBEDDING_MODEL", "lexical-hash-384"),
        gemini_model=_setting("GEMINI_MODEL", "gemini-1.5-flash"),
        knowledge_base_path=_setting(
            "KNOWLEDGE_BASE_PATH", "data/knowledge_base.csv"
        ),
        vectorstore_path=_setting("VECTORSTORE_PATH", "vectorstore/faiss_index"),
        max_retrieved_docs=int(_setting("MAX_RETRIEVED_DOCS", "6")),
        retriever_score_threshold=float(
            _setting("RETRIEVER_SCORE_THRESHOLD", "0.3")
        ),
        supabase_url=_setting("SUPABASE_URL"),
        supabase_publishable_key=_setting("SUPABASE_PUBLISHABLE_KEY"),
        supabase_secret_key=(
            _setting("SUPABASE_SECRET_KEY")
            or _setting("SUPABASE_SERVICE_ROLE_KEY")
        ),
        supabase_enabled=_setting("SUPABASE_ENABLED", "false").lower()
        in {"1", "true", "yes", "on"},
        dynamic_kb_enabled=_setting("DYNAMIC_KB_ENABLED", "false").lower()
        in {"1", "true", "yes", "on"},
        conversation_memory_turns=int(
            _setting("CONVERSATION_MEMORY_TURNS", "4")
        ),
        payments_enabled=_setting("PAYMENTS_ENABLED", "false").lower()
        in {"1", "true", "yes", "on"},
        razorpay_key_id=_setting("RAZORPAY_KEY_ID"),
        razorpay_key_secret=_setting("RAZORPAY_KEY_SECRET"),
        razorpay_webhook_secret=_setting("RAZORPAY_WEBHOOK_SECRET"),
        paid_plan_amount_subunits=int(
            _setting("PAID_PLAN_AMOUNT_SUBUNITS", "49900")
        ),
        paid_plan_currency=_setting("PAID_PLAN_CURRENCY", "INR").upper(),
        paid_plan_duration_days=int(
            _setting("PAID_PLAN_DURATION_DAYS", "30")
        ),
    )
