"""
utils/logger.py

Centralised logging configuration for Cross Speak AI.
Provides a factory function that returns a consistently formatted
logger instance for any module.
"""

from __future__ import annotations

import logging
import sys
from functools import lru_cache


_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_root_configured = False


def _configure_root_logger() -> None:
    """Configure the root logger exactly once with a stream handler."""
    global _root_configured
    if _root_configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Avoid duplicate handlers when modules are reloaded.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "faiss", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _root_configured = True


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """Return a named logger, configuring the root logger on first call.

    Args:
        name: Module or component name, typically ``__name__``.

    Returns:
        Configured :class:`logging.Logger` instance.
    """
    _configure_root_logger()
    return logging.getLogger(name)
