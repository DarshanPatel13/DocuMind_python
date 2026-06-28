"""Tiny query-intent heuristic.

Top-k retrieval is great for a *focused* question but can't satisfy a request to
enumerate or summarize a WHOLE document (it only ever sees k chunks). This detects
that "aggregate" intent so the ask flow can switch to whole-document mode.

Heuristic by design — explainable and dependency-free (same spirit as the
guardrail). Java analogy: a small rules-based request classifier.
"""
from __future__ import annotations

import re

_AGGREGATE_PATTERNS = [
    r"\blist\s+(all|every|out|the|down)\b",
    r"\b(summari[sz]e|summary|overview|outline|recap)\b",
    r"\ball\s+(the|of|questions|topics|sections|points|items)\b",
    r"\bevery\b",
    r"\bhow\s+many\b",
    r"\benumerate\b",
    r"\btable\s+of\s+contents\b",
    r"\b(entire|whole|full)\s+(document|doc|pdf|file|paper)\b",
    r"\b(key|main)\s+(points|topics|ideas|takeaways)\b",
    r"\bwhat\s+are\s+all\b",
    r"\bgive\s+me\s+all\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _AGGREGATE_PATTERNS]


def is_aggregate_query(text: str) -> bool:
    """True if the question asks to enumerate/summarize across a whole document."""
    return any(pattern.search(text) for pattern in _COMPILED)
