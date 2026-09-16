"""Small deterministic content guard for translation requests and responses."""

from __future__ import annotations

import re
import unicodedata

_BLOCKED_WORDS = {
    "asshole",
    "bastard",
    "bitch",
    "cunt",
    "dick",
    "fuck",
    "fock",
    "fucker",
    "fucking",
    "motherfucker",
    "shit",
    "slut",
    "whore",
}
_LEET_MAP = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_OBFUSCATED_PATTERNS = tuple(
    re.compile(r"\b" + r"[\W_]*".join(map(re.escape, word)) + r"\b")
    for word in _BLOCKED_WORDS
)


def contains_abusive_language(text: str) -> bool:
    """Return true when text contains a blocked abusive word."""
    normalized = unicodedata.normalize("NFKC", text).casefold().translate(_LEET_MAP)
    words = set(re.findall(r"[a-z]+", normalized))
    return bool(words & _BLOCKED_WORDS) or any(
        pattern.search(normalized) for pattern in _OBFUSCATED_PATTERNS
    )
