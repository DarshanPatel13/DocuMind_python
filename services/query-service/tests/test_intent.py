"""Aggregate-intent detection (drives whole-document mode)."""
from __future__ import annotations

import pytest

from app.intent import is_aggregate_query


@pytest.mark.parametrize(
    "text",
    [
        "Can you list all the system design questions mentioned",
        "Summarize this document",
        "Give me an overview of the paper",
        "What are all the topics covered?",
        "How many sections are there?",
        "Outline the whole document",
    ],
)
def test_detects_aggregate_queries(text: str) -> None:
    assert is_aggregate_query(text)


@pytest.mark.parametrize(
    "text",
    [
        "What is the refund window?",
        "Who is the author?",
        "Explain the caching strategy for LeetCode",
    ],
)
def test_ignores_focused_queries(text: str) -> None:
    assert not is_aggregate_query(text)
