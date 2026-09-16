"""
core/api_manager.py

Manages a pool of up to five Gemini API keys with automatic failover.
When a key hits a rate-limit (429) or quota-exhausted error, the manager
transparently retries with the next available key.  All keys are tried
before raising the final exception.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import google.generativeai as genai  # type: ignore

from core.config import Settings
from utils.logger import get_logger

logger = get_logger(__name__)

# HTTP / API status codes / substrings that trigger key rotation
_RATE_LIMIT_SIGNALS: tuple[str, ...] = (
    "429",
    "quota",
    "rate limit",
    "resource has been exhausted",
    "rateLimitExceeded",
    "userRateLimitExceeded",
)


class APIManager:
    """Manages a pool of Gemini API keys with automatic failover.

    Iterates through the provided API keys in order.  If a key raises a
    rate-limit or quota exception the manager logs a warning, waits
    briefly, and moves to the next key.  If all keys are exhausted the
    original exception is re-raised.

    Attributes:
        _keys: Ordered list of Gemini API key strings.
        _model_name: Gemini model identifier (e.g. ``gemini-1.5-flash``).
        _retry_delay_seconds: Seconds to wait between key rotations.
    """

    def __init__(
        self,
        settings: Settings,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        """Initialise the API manager.

        Args:
            settings:
                Application settings containing the list of API keys and
                the target model name.
            retry_delay_seconds:
                How long to pause before retrying with the next key.

        Raises:
            ValueError: If no API keys are configured.
        """
        if not settings.gemini_api_keys:
            raise ValueError(
                "No Gemini API keys configured.  "
                "Set GEMINI_API_KEY_1 … GEMINI_API_KEY_5 in .env or "
                "the deployment environment."
            )

        self._keys: list[str] = list(settings.gemini_api_keys)
        self._model_name: str = settings.gemini_model
        self._retry_delay_seconds: float = retry_delay_seconds
        logger.info(
            "APIManager ready with %d key(s) and model '%s'.",
            len(self._keys),
            self._model_name,
        )

    def generate(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the generated text.

        Automatically rotates keys on rate-limit errors, and tries model name
        fallbacks if a model is not found in the current region/API version.

        Args:
            prompt: The full, formatted prompt string to send.

        Returns:
            Generated text response from the model.

        Raises:
            RuntimeError: If all keys fail for non-recoverable reasons.
            Exception: The last exception if all keys are rate-limited.
        """
        last_exception: Optional[Exception] = None
        candidate_models = [
            self._model_name,
            "gemini-3.6-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-3.5-flash",
        ]
        # Deduplicate while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        for key_index, api_key in enumerate(self._keys, start=1):
            genai.configure(api_key=api_key)

            for model_name in candidate_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    logger.info(
                        "Gemini response received using key #%d and model '%s'.",
                        key_index,
                        model_name,
                    )
                    return response.text

                except Exception as exc:  # noqa: BLE001
                    error_text = str(exc).lower()
                    if "404" in error_text or "not found" in error_text:
                        logger.warning(
                            "Model '%s' not found (%s). Trying fallback model.",
                            model_name,
                            exc,
                        )
                        last_exception = exc
                        continue

                    is_rate_limit = any(
                        signal in error_text for signal in _RATE_LIMIT_SIGNALS
                    )
                    if is_rate_limit:
                        logger.warning(
                            "Key #%d hit rate limit on model '%s'. Rotating key.",
                            key_index,
                            model_name,
                        )
                        time.sleep(self._retry_delay_seconds)
                        last_exception = exc
                        break  # Break inner loop to try next key

                    # Non-recoverable error
                    logger.error(
                        "API error on key #%d model '%s': %s",
                        key_index,
                        model_name,
                        exc,
                    )
                    last_exception = exc
                    break

        logger.error("All %d API key(s) and model candidates exhausted.", len(self._keys))
        raise last_exception  # type: ignore[misc]
