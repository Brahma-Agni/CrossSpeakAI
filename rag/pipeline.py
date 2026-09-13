"""
rag/pipeline.py

Orchestrates the end-to-end RAG pipeline:

  User Input → Detector → Retriever → PromptBuilder → APIManager → Response

This is the single public entry point used by the Streamlit UI.  All
heavy objects (embeddings, FAISS index) are constructed once and passed
in from cached Streamlit resources.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from langchain_core.documents import Document  # type: ignore

from core.api_manager import APIManager
from core.config import Settings
from rag.knowledge_loader import load_knowledge_base
from rag.prompt_builder import PromptBuilder
from rag.retriever import Retriever
from utils.language_detector import LanguageDetector, LanguageStyle
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TranslationResult:
    """Structured result returned by the RAG pipeline.

    Attributes:
        translation: The translated text.
        terms_used: List of term mappings used during translation.
        detected_style: Detected language style of the input.
        translation_direction: Human-readable direction string.
        retrieved_docs: Raw documents retrieved from the vector store.
        raw_response: The raw LLM response string for debugging.
        error: Error message if the pipeline failed gracefully.
    """

    translation: str
    terms_used: list[dict[str, str]]
    detected_style: str
    translation_direction: str
    retrieved_docs: list[Document]
    raw_response: str
    error: Optional[str] = None


class RAGPipeline:
    """Full Retrieval-Augmented Generation pipeline for Cross Speak AI.

    Wires together the language detector, FAISS retriever, prompt
    builder, and Gemini API manager into a single coherent translate()
    call.

    Attributes:
        _detector: Heuristic language style classifier.
        _retriever: FAISS semantic retriever.
        _prompt_builder: Structured prompt constructor.
        _api_manager: Multi-key Gemini API manager with failover.
    """

    def __init__(
        self,
        detector: LanguageDetector,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        api_manager: APIManager,
        extra_retriever: Optional[Callable[[str], list[Document]]] = None,
    ) -> None:
        """Initialise the pipeline with all required components.

        Args:
            detector: Language style detector instance.
            retriever: Semantic FAISS retriever instance.
            prompt_builder: Prompt construction instance.
            api_manager: Gemini API manager with failover.
        """
        self._detector = detector
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._api_manager = api_manager
        self._extra_retriever = extra_retriever
        logger.info("RAGPipeline initialised and ready.")

    def translate(
        self,
        user_input: str,
        translation_mode: str = "auto",
        score_threshold: float = 0.3,
        conversation_context: Optional[list[dict[str, str]]] = None,
    ) -> TranslationResult:
        """Run the full RAG translation pipeline on the user's input.

        Args:
            user_input:
                The text the user wants translated.
            translation_mode:
                One of ``"auto"``, ``"corporate_to_genz"``, or
                ``"genz_to_corporate"``.
            score_threshold:
                FAISS similarity threshold for document retrieval.

        Returns:
            A :class:`TranslationResult` dataclass with all outputs.
        """
        if not user_input or not user_input.strip():
            return TranslationResult(
                translation="",
                terms_used=[],
                detected_style="Unknown",
                translation_direction="N/A",
                retrieved_docs=[],
                raw_response="",
                error="Input text cannot be empty.",
            )

        try:
            # Step 1: Detect language style
            source_style: LanguageStyle = self._detector.detect(user_input)
            logger.info("Detected style: %s", source_style.value)

            # Step 2: Retrieve relevant context from knowledge base
            retrieved_docs: list[Document] = self._retriever.retrieve(
                query=user_input,
                score_threshold=score_threshold,
            )
            if self._extra_retriever is not None:
                retrieved_docs = self._merge_documents(
                    retrieved_docs,
                    self._extra_retriever(user_input),
                )
            logger.info("Retrieved %d context document(s).", len(retrieved_docs))

            # Step 3: Build structured prompt
            prompt: str = self._prompt_builder.build_translation_prompt(
                user_input=user_input,
                retrieved_docs=retrieved_docs,
                source_style=source_style,
                translation_mode=translation_mode,
                conversation_context=conversation_context,
            )

            # Step 4: Call Gemini LLM with failover
            raw_response: str = self._api_manager.generate(prompt)
            logger.info("LLM response received (%d chars).", len(raw_response))

            # Step 5: Parse structured JSON response
            parsed = self._parse_llm_response(raw_response)

            return TranslationResult(
                translation=parsed.get("translation", raw_response),
                terms_used=parsed.get("terms_used", []),
                detected_style=parsed.get(
                    "detected_style", source_style.value
                ),
                translation_direction=parsed.get(
                    "translation_direction", "Unknown → Unknown"
                ),
                retrieved_docs=retrieved_docs,
                raw_response=raw_response,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("Pipeline error: %s", exc)
            return TranslationResult(
                translation="",
                terms_used=[],
                detected_style="Unknown",
                translation_direction="N/A",
                retrieved_docs=[],
                raw_response="",
                error=f"Translation failed: {type(exc).__name__} — {exc}",
            )

    @staticmethod
    def _merge_documents(
        local_docs: list[Document], remote_docs: list[Document]
    ) -> list[Document]:
        """Merge ranked results while removing duplicate terms."""
        merged: list[Document] = []
        seen: set[str] = set()
        for doc in [*remote_docs, *local_docs]:
            key = str(doc.metadata.get("term", doc.page_content)).strip().lower()
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged

    @staticmethod
    def _parse_llm_response(raw: str) -> dict[str, Any]:
        """Extract and parse JSON from the LLM response string.

        Handles common LLM artefacts such as markdown code fences and
        leading/trailing whitespace.

        Args:
            raw: The raw string returned by the LLM.

        Returns:
            Parsed dictionary, or a fallback dict with the raw text as
            the translation value if JSON extraction fails.
        """
        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        # Extract first JSON object found
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as exc:
                logger.warning("JSON parse failed (%s); using raw text.", exc)

        return {
            "translation": raw.strip(),
            "terms_used": [],
            "detected_style": "Unknown",
            "translation_direction": "Unknown → Unknown",
        }
