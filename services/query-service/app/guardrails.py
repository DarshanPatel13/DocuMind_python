"""Input guardrails.

DocuMind has two layers of defence against the model misbehaving:

  1. Grounded-only answering (in ask_service): if retrieval finds nothing, we
     return a fixed sentinel and NEVER call the LLM — it can't hallucinate from
     an empty context. This is the strongest guard and it already exists.

  2. Prompt-injection screening (here): a cheap heuristic that flags inputs
     trying to override the system prompt ("ignore previous instructions",
     "reveal your system prompt", "you are now …"). Flagged inputs get a fixed
     refusal instead of reaching retrieval or the LLM.

Heuristics are deliberately simple and explainable. They are a first filter, not
a complete defence — a stronger setup adds output checks and an LLM-based
classifier (noted in docs/ai/guardrails.md). Java analogy: a request-validation
filter that rejects malicious payloads before they hit the controller.
"""
from __future__ import annotations

import re

INJECTION_REFUSAL = (
    "I can only answer questions about your uploaded documents, and I can't follow "
    "instructions that try to change how I work."
)

# Case-insensitive phrases that signal an attempt to override instructions.
_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+|any\s+|the\s+|your\s+|previous\s+|prior\s+|above\s+)*instructions",
    r"disregard\s+(?:the\s+|all\s+|your\s+|previous\s+|above\s+)*(?:instructions|context|prompt|rules)",
    r"forget\s+(?:everything|all|the|your|previous)\b",
    r"reveal\s+(?:your\s+|the\s+)?(?:system\s+)?prompt",
    r"(?:what\s+(?:is|are)|show\s+me)\s+your\s+(?:system\s+)?(?:prompt|instructions)",
    r"you\s+are\s+now\b",
    r"act\s+as\s+(?:a|an|if)\b",
    r"override\s+(?:the\s+|your\s+)?(?:instructions|rules|system)",
    r"developer\s+mode",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def detect_prompt_injection(text: str) -> bool:
    """True if the input looks like a prompt-injection / jailbreak attempt."""
    return any(pattern.search(text) for pattern in _COMPILED)
