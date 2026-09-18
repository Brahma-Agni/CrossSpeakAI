"""
rag/prompt_builder.py

Constructs structured, deterministic prompts for the Cross Speak AI
translation pipeline.  Every prompt includes: Role, Objective, Context
(retrieved documents), Constraints, and Output format — as per the
project's Prompt Engineering guidelines.
"""

from __future__ import annotations

from langchain_core.documents import Document  # type: ignore

from utils.language_detector import LanguageStyle
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Translation mode mappings ──────────────────────────────────────────────────

_TRANSLATION_DIRECTIONS: dict[str, tuple[str, str]] = {
    "corporate_to_genz": (
        "Corporate English",
        "Gen Z Slang",
    ),
    "genz_to_corporate": (
        "Gen Z Slang",
        "Corporate English",
    ),
    "auto": (
        "its detected style",
        "the opposite style",
    ),
}


class PromptBuilder:
    """Constructs structured translation prompts for the Gemini LLM.

    All prompts follow the Role → Objective → Context → Constraints →
    Output Format structure mandated by the project's engineering
    guidelines.

    Attributes:
        _max_context_docs: Maximum number of retrieved documents to
            include in the prompt context section.
    """

    def __init__(self, max_context_docs: int = 6) -> None:
        """Initialise the prompt builder.

        Args:
            max_context_docs:
                Maximum retrieved documents to embed in the context
                section of each prompt.  Excess documents are silently
                dropped.
        """
        self._max_context_docs = max_context_docs
        logger.debug(
            "PromptBuilder initialised (max_context_docs=%d).",
            max_context_docs,
        )

    def build_translation_prompt(
        self,
        user_input: str,
        retrieved_docs: list[Document],
        source_style: LanguageStyle,
        translation_mode: str = "auto",
        conversation_context: list[dict[str, str]] | None = None,
    ) -> str:
        """Build a complete translation prompt ready to send to the LLM.

        Args:
            user_input:
                The raw text the user wants translated.
            retrieved_docs:
                Documents retrieved from the curated knowledge base.
            source_style:
                Detected language style of the user's input.
            translation_mode:
                One of ``"corporate_to_genz"``, ``"genz_to_corporate"``,
                or ``"auto"`` (default).

        Returns:
            Fully formatted prompt string.
        """
        context_block = self._build_context_block(
            retrieved_docs[: self._max_context_docs]
        )

        source_label, target_label = self._resolve_labels(
            source_style, translation_mode
        )
        memory_block = self._build_memory_block(conversation_context or [])

        prompt = f"""You are CrossSpeakAI, an expert bilingual translator \
specialising in Corporate English and Gen Z Slang.

## OBJECTIVE
Translate the following text from {source_label} into {target_label}.

## USER INPUT
\"\"\"{user_input}\"\"\"

## DETECTED STYLE
The input has been detected as: {source_style.value}

## RECENT CONVERSATION
{memory_block}

## CONTEXT — KNOWLEDGE BASE EXCERPTS
The following terminology definitions have been retrieved from the \
knowledge base to assist with accurate translation:

{context_block}

## CONSTRAINTS
1. Translate every significant phrase or term that has a known equivalent.
2. Preserve the original meaning and intent precisely.
3. Use only terminology grounded in the context above — do not invent slang.
4. Maintain a professional and clear tone.
5. If a term has no direct equivalent, provide a natural paraphrase.
6. If the input contains mixed styles, translate the dominant style.
7. Do NOT add commentary, disclaimers, or meta-text about the translation.
8. If confidence is low for a specific term, include it in parentheses \
as-is and note uncertainty inline using (uncertain).
9. Also rewrite the original meaning in clear, neutral, everyday English. \
Do not use corporate jargon or Gen Z slang in this version.

## OUTPUT FORMAT
Return ONLY the following JSON object — no markdown fences, no extra text:

{{
  "translation": "<translated text here>",
  "normal_english": "<clear everyday English version here>",
  "terms_used": [
    {{"original": "<term>", "translated": "<equivalent>", "confidence": "<high|medium|low>"}}
  ],
  "detected_style": "{source_style.value}",
  "translation_direction": "{source_label} → {target_label}"
}}"""

        logger.debug(
            "Built translation prompt (%d chars, %d context docs).",
            len(prompt),
            len(retrieved_docs[: self._max_context_docs]),
        )
        return prompt

    @staticmethod
    def _build_memory_block(turns: list[dict[str, str]]) -> str:
        if not turns:
            return "No previous conversation turns."
        sections: list[str] = []
        for turn in turns:
            sections.append(
                f"User: {turn.get('input_text', '')}\n"
                f"Assistant: {turn.get('output_text', '')}"
            )
        return "\n\n".join(sections)

    def _resolve_labels(
        self, source_style: LanguageStyle, translation_mode: str
    ) -> tuple[str, str]:
        """Determine source and target labels for the prompt.

        Args:
            source_style: Detected style of the input text.
            translation_mode: Explicit mode override or ``"auto"``.

        Returns:
            Tuple of (source_label, target_label) strings.
        """
        if translation_mode in _TRANSLATION_DIRECTIONS:
            return _TRANSLATION_DIRECTIONS[translation_mode]

        # Auto-resolve based on detected style
        if source_style == LanguageStyle.CORPORATE:
            return "Corporate English", "Gen Z Slang"
        if source_style == LanguageStyle.GEN_Z:
            return "Gen Z Slang", "Corporate English"
        if source_style == LanguageStyle.MIXED:
            return "Mixed Corporate/Gen Z", "a balanced, clear English blend"
        return "General English", "Gen Z Slang"

    @staticmethod
    def _build_context_block(documents: list[Document]) -> str:
        """Format retrieved documents into a readable context block.

        Args:
            documents: Retrieved knowledge base documents.

        Returns:
            Formatted string ready for prompt insertion.
        """
        if not documents:
            return "No relevant terms retrieved from the knowledge base."

        sections: list[str] = []
        for index, doc in enumerate(documents, start=1):
            sections.append(f"[{index}] {doc.page_content}")

        return "\n\n".join(sections)
