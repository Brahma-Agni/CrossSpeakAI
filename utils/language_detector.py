"""
utils/language_detector.py

Heuristic-based language style detector for Corporate English and Gen Z Slang.
Classifies user input into one of four categories before routing to the RAG
translation pipeline.
"""

from __future__ import annotations

import re
from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)

# ── Vocabulary sets ────────────────────────────────────────────────────────────

_CORPORATE_TERMS: frozenset[str] = frozenset(
    {
        "leverage", "synergy", "bandwidth", "deliverable", "stakeholder",
        "paradigm", "pivot", "scalable", "agile", "robust", "optics",
        "action item", "circle back", "touch base", "deep dive",
        "move the needle", "low-hanging fruit", "boil the ocean",
        "value add", "silo", "kpi", "roi", "eod", "eom", "q1", "q2",
        "q3", "q4", "ooo", "pto", "deck", "cadence", "alignment",
        "visibility", "headcount", "ideate", "socialize", "onboard",
        "offboard", "ramp up", "scope creep", "pain point",
    }
)

_GEN_Z_TERMS: frozenset[str] = frozenset(
    {
        "no cap", "slay", "bussin", "snatched", "based", "sus", "lowkey",
        "highkey", "vibe", "hits different", "understood the assignment",
        "it's giving", "rent free", "ate", "periodt", "delulu", "rizz",
        "slaps", "dead", "cooked", "mid", "npc", "ratio", "w", "l",
        "beige flag", "main character", "glazing", "touch grass", "era",
        "fr", "ong", "lit", "goat", "bet", "fam", "yeet", "bruh",
        "bop", "snatched", "tea", "flex", "stan", "ship",
    }
)


class LanguageStyle(str, Enum):
    """Detected language style of user input."""

    CORPORATE = "Corporate"
    GEN_Z = "Gen Z"
    MIXED = "Mixed"
    GENERAL = "General English"
    AUTO = "Auto Detect"


class LanguageDetector:
    """Heuristic classifier that detects the dominant language style.

    The detector tokenises the input text, counts keyword hits from
    curated corporate and Gen Z vocabulary sets, then applies a simple
    majority rule.  Mixed inputs (both styles present) are explicitly
    flagged so the downstream prompt can handle them gracefully.

    Attributes:
        _corporate_threshold: Minimum corporate hits to classify as Corporate.
        _gen_z_threshold: Minimum Gen Z hits to classify as Gen Z.
    """

    def __init__(
        self,
        corporate_threshold: int = 1,
        gen_z_threshold: int = 1,
    ) -> None:
        """Initialise the detector with hit thresholds.

        Args:
            corporate_threshold:
                Minimum number of corporate keyword matches required to
                consider the text corporate-leaning.
            gen_z_threshold:
                Minimum number of Gen Z keyword matches required to
                consider the text Gen Z-leaning.
        """
        self._corporate_threshold = corporate_threshold
        self._gen_z_threshold = gen_z_threshold
        logger.debug("LanguageDetector initialised.")

    def detect(self, text: str) -> LanguageStyle:
        """Detect the dominant language style of the given text.

        Args:
            text: Raw user input string.

        Returns:
            One of the :class:`LanguageStyle` enum values.
        """
        normalised = text.lower().strip()
        corporate_hits = self._count_hits(normalised, _CORPORATE_TERMS)
        gen_z_hits = self._count_hits(normalised, _GEN_Z_TERMS)

        logger.debug(
            "Language detection: corporate_hits=%d, gen_z_hits=%d",
            corporate_hits,
            gen_z_hits,
        )

        has_corporate = corporate_hits >= self._corporate_threshold
        has_gen_z = gen_z_hits >= self._gen_z_threshold

        if has_corporate and has_gen_z:
            return LanguageStyle.MIXED
        if has_corporate:
            return LanguageStyle.CORPORATE
        if has_gen_z:
            return LanguageStyle.GEN_Z
        return LanguageStyle.GENERAL

    @staticmethod
    def _count_hits(text: str, vocabulary: frozenset[str]) -> int:
        """Count how many vocabulary terms appear in the text.

        Multi-word phrases are matched via substring search; single
        words are matched as whole words using word boundaries.

        Args:
            text: Lowercased, stripped input text.
            vocabulary: Frozen set of terms to search for.

        Returns:
            Integer count of matching terms.
        """
        count = 0
        for term in vocabulary:
            if " " in term:
                if term in text:
                    count += 1
            else:
                if re.search(rf"\b{re.escape(term)}\b", text):
                    count += 1
        return count
