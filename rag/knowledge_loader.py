"""
rag/knowledge_loader.py

Loads the Corporate ↔ Gen Z terminology CSV and constructs
LangChain Document objects ready for embedding and vector indexing.

Each CSV row becomes a rich Document whose page_content is a
human-readable summary and whose metadata preserves every field for
downstream filtering and display.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document  # type: ignore

from utils.logger import get_logger

logger = get_logger(__name__)

_REQUIRED_COLUMNS: tuple[str, ...] = (
    "term",
    "category",
    "meaning",
    "translation",
)


def load_knowledge_base(csv_path: str) -> list[Document]:
    """Load the knowledge base CSV and return a list of LangChain Documents.

    Each row in the CSV is converted into a single Document.  The
    ``page_content`` field is a natural-language summary designed to be
    embedded effectively.  All CSV columns are preserved in ``metadata``.

    Args:
        csv_path:
            Absolute or relative path to the knowledge base CSV file.

    Returns:
        List of :class:`langchain_core.documents.Document` objects.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns are missing.
        csv.Error: If the CSV file is malformed.
    """
    resolved_path = Path(csv_path).resolve()

    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Knowledge base not found at: {resolved_path}"
        )

    documents: list[Document] = []

    with resolved_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError("CSV file appears to be empty.")

        missing = [
            col for col in _REQUIRED_COLUMNS if col not in reader.fieldnames
        ]
        if missing:
            raise ValueError(
                f"Knowledge base CSV is missing required columns: {missing}"
            )

        for row_number, row in enumerate(reader, start=2):  # 2 = after header
            term = row.get("term", "").strip()
            if not term:
                logger.warning("Row %d has an empty 'term' — skipping.", row_number)
                continue

            page_content = _build_page_content(row)
            metadata = _build_metadata(row)

            documents.append(
                Document(page_content=page_content, metadata=metadata)
            )

    logger.info(
        "Loaded %d documents from '%s'.", len(documents), resolved_path.name
    )
    return documents


def _build_page_content(row: dict[str, str]) -> str:
    """Construct a rich, embeddable text summary for a knowledge base row.

    Args:
        row: A single CSV row as a dictionary.

    Returns:
        Formatted natural-language string for embedding.
    """
    term = row.get("term", "").strip()
    category = row.get("category", "").strip()
    meaning = row.get("meaning", "").strip()
    translation = row.get("translation", "").strip()
    aliases = row.get("aliases", "").strip()
    examples = row.get("examples", "").strip()
    notes = row.get("notes", "").strip()

    parts = [
        f"Term: {term}",
        f"Category: {category}",
        f"Meaning: {meaning}",
        f"Translation: {translation}",
    ]

    if aliases:
        parts.append(f"Also known as: {aliases.replace(';', ', ')}")
    if examples:
        parts.append(f"Example: {examples}")
    if notes:
        parts.append(f"Notes: {notes}")

    return "\n".join(parts)


def _build_metadata(row: dict[str, str]) -> dict[str, str]:
    """Extract clean metadata from a CSV row for filtering and display.

    Args:
        row: A single CSV row as a dictionary.

    Returns:
        Dictionary of string metadata fields.
    """
    return {
        "term": row.get("term", "").strip(),
        "category": row.get("category", "").strip(),
        "meaning": row.get("meaning", "").strip(),
        "translation": row.get("translation", "").strip(),
        "aliases": row.get("aliases", "").strip(),
        "examples": row.get("examples", "").strip(),
        "notes": row.get("notes", "").strip(),
    }
