"""High-confidence style checks for text shown outside the private workspace."""

from __future__ import annotations

import re


_NEGATIVE_PARALLEL = re.compile(
    r"\b(?:it is|it['’]s)\s+not\b[^.!?\n]{1,160}[,;:]\s*(?:it is|it['’]s)\b",
    re.IGNORECASE,
)

_STOCK_AI_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\blet['’]s (?:dive|explore|break (?:this|it) down)\b",
        r"\bhere (?:is|are) what you need to know\b",
        r"\b(?:serves|stands) as (?:a|an) testament\b",
        r"\bin today['’]s rapidly evolving\b",
        r"\bat its core\b",
        r"\bi hope this helps\b",
        r"\bmarks a pivotal moment\b",
        r"\bshowcases? the (?:power|potential)\b",
    )
)


def validate_display_text(text: str, field: str) -> list[str]:
    """Return deterministic errors for prohibited display-text patterns."""
    if "—" in text:
        return [f"{field} contains an em dash; use a period, colon, comma, or parentheses"]
    if _NEGATIVE_PARALLEL.search(text):
        return [f"{field} uses an AI-style 'not X, it is Y' contrast; state the technical claim directly"]
    if any(pattern.search(text) for pattern in _STOCK_AI_PATTERNS):
        return [f"{field} contains stock AI-style phrasing; rewrite the statement directly"]
    return []
