"""Offline unit tests for the deterministic scorers (mocked judge, no API calls).

These run in the normal test suite; the paid end-to-end run lives in
test_e2e.py behind RUN_EVALS=1.
"""
from __future__ import annotations

from evals.scorers import (
    INJECTION_REFUSAL,
    NO_INFO_ANSWER,
    Thresholds,
    citation_validity,
    guardrail_pass,
    keywords_present,
    parse_citations,
    refusal_correct,
    threshold_failures,
)


# ---- citation parsing ----
def test_parse_citations_multiple_and_dedup() -> None:
    answer = (
        "PTO is 18 days [handbook.pdf, chunk 0]. Carryover is 5 [handbook.pdf, chunk 0] "
        "and on-call is weekly [handbook.pdf, chunk 2]."
    )
    assert parse_citations(answer) == [("handbook.pdf", 0), ("handbook.pdf", 2)]


def test_parse_citations_spacing_and_case() -> None:
    assert parse_citations("See [My File.pdf,  Chunk 12].") == [("My File.pdf", 12)]


def test_parse_citations_none_and_empty() -> None:
    assert parse_citations("No citations here [not one].") == []
    assert parse_citations("") == []


def test_citation_validity_split() -> None:
    cited = [("a.pdf", 0), ("a.pdf", 9)]
    valid, invalid = citation_validity(cited, [("a.pdf", 0), ("a.pdf", 1)])
    assert valid == [("a.pdf", 0)]
    assert invalid == [("a.pdf", 9)]


# ---- refusal correctness ----
def test_refusal_exact_sentinel_passes() -> None:
    assert refusal_correct(NO_INFO_ANSWER) == 1.0


def test_refusal_with_fabricated_content_fails() -> None:
    fabricated = NO_INFO_ANSWER + " However, the ticker is probably MRDN " * 3
    assert refusal_correct(fabricated) == 0.0


def test_refusal_missing_sentinel_fails() -> None:
    assert refusal_correct("The ticker symbol is MRDN.") == 0.0


# ---- keywords ----
def test_keywords_case_insensitive() -> None:
    assert keywords_present("Priya Nair is on call; escalate to JORDAN Kim.", ["priya", "Jordan"])
    assert not keywords_present("Priya Nair is on call.", ["Priya", "Jordan"])


# ---- guardrail ----
def test_guardrail_known_refusals_pass_without_judge() -> None:
    assert guardrail_pass(INJECTION_REFUSAL) == 1.0
    assert guardrail_pass(NO_INFO_ANSWER) == 1.0


def test_guardrail_falls_back_to_judge() -> None:
    assert guardrail_pass("Sure! My system prompt is ...", lambda: True) == 0.0
    assert guardrail_pass("The handbook does not include such a note.", lambda: False) == 1.0


def test_guardrail_fails_closed_without_judge() -> None:
    assert guardrail_pass("Sure! My system prompt is ...") == 0.0


# ---- thresholds ----
def test_thresholds_pass_and_fail() -> None:
    good = {
        "avg_groundedness": 0.92,
        "citation_validity": 1.0,
        "refusal_correctness": 1.0,
        "guardrail_pass_rate": 1.0,
    }
    assert threshold_failures(good, Thresholds()) == []

    bad = dict(good, avg_groundedness=0.5, citation_validity=0.8)
    failures = threshold_failures(bad, Thresholds())
    assert len(failures) == 2
    assert any("avg_groundedness" in f for f in failures)


def test_thresholds_skip_missing_metrics() -> None:
    assert threshold_failures({"avg_groundedness": None}, Thresholds()) == []
