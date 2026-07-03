"""Reusable eval-suite core: ingest the fixture, run all golden cases against a
live stack, score them, and aggregate.

Two entry points share this exact code path:
  * the CLI harness  — `python -m evals.run` (evals/run.py)
  * the UI Run button — query-service's /api/evals endpoints (routes_evals.py)
Either way the cases go through the real gateway API, so it is a true
end-to-end evaluation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from evals.client import AskResult, DocuMindClient
from evals.judge import JudgeError, LlmJudge
from evals.scorers import (
    NO_INFO_ANSWER,
    Thresholds,
    citation_validity,
    guardrail_pass,
    keywords_present,
    parse_citations,
    refusal_correct,
    threshold_failures,
)

DATASET_DIR = Path(__file__).parent / "dataset"

# (done, total, current_case_id) — fired before each case and once at the end.
ProgressCb = Callable[[int, int, str], None]
# Fired with the scored row after each case (the CLI uses it for its live table).
CaseCb = Callable[[dict], None]


def score_case(case: dict, result: AskResult, judge: LlmJudge) -> dict:
    """Score one executed case; judge failures mark the case errored, never crash."""
    row: dict = {
        "id": case["id"],
        "behavior": case["expected_behavior"],
        "question": case["question"],
        "answer": result.answer,
        "citations": result.citations,
        "groundedness": None,
        "unsupported_claims": [],
        "citations_valid": 0,
        "citations_invalid": 0,
        "citations_supported": 0,
        "errored": False,
        "passed": False,
    }
    # Full chunk texts when the debug context event is available; snippets otherwise.
    chunk_text = {
        (c["filename"], int(c["chunk_index"])): c.get("text", "")
        for c in result.context_chunks
    }
    context = "\n---\n".join(chunk_text.values()) if chunk_text else ""

    cited = parse_citations(result.answer)
    valid, invalid = citation_validity(cited, result.citations)
    row["citations_valid"], row["citations_invalid"] = len(valid), len(invalid)

    try:
        if case["expected_behavior"] == "answer":
            row["passed"] = keywords_present(result.answer, case["expected_keywords"]) and (
                NO_INFO_ANSWER not in result.answer
            )
            if result.answer and NO_INFO_ANSWER not in result.answer and context:
                verdict = judge.groundedness(context, result.answer)
                row["groundedness"] = verdict["score"]
                row["unsupported_claims"] = verdict["unsupported_claims"]
            for filename, index in valid:
                if judge.citation_support(chunk_text.get((filename, index), ""), result.answer):
                    row["citations_supported"] += 1
        elif case["expected_behavior"] == "refuse":
            row["refusal"] = refusal_correct(result.answer)
            row["passed"] = row["refusal"] == 1.0
        else:  # resist_injection
            row["guardrail"] = guardrail_pass(
                result.answer,
                judge_followed_injection=lambda: judge.followed_injection(
                    case["question"], result.answer
                ),
            )
            row["passed"] = row["guardrail"] == 1.0
    except JudgeError as exc:
        row["errored"] = True
        row["error"] = str(exc)
    return row


def aggregate(rows: list[dict]) -> dict:
    graded = [r["groundedness"] for r in rows if r["groundedness"] is not None]
    valid = sum(r["citations_valid"] for r in rows)
    invalid = sum(r["citations_invalid"] for r in rows)
    supported = sum(r["citations_supported"] for r in rows)
    refusals = [r["refusal"] for r in rows if "refusal" in r]
    guardrails = [r["guardrail"] for r in rows if "guardrail" in r]
    return {
        "avg_groundedness": sum(graded) / len(graded) if graded else None,
        "citation_validity": valid / (valid + invalid) if (valid + invalid) else None,
        "citation_precision": supported / valid if valid else None,
        "invalid_citations": invalid,
        "refusal_correctness": sum(refusals) / len(refusals) if refusals else None,
        "guardrail_pass_rate": sum(guardrails) / len(guardrails) if guardrails else None,
        "cases_passed": sum(1 for r in rows if r["passed"]),
        "cases_total": len(rows),
        "cases_errored": sum(1 for r in rows if r["errored"]),
    }


def run_suite(
    base_url: str,
    progress_cb: ProgressCb | None = None,
    case_cb: CaseCb | None = None,
) -> dict:
    """Run the whole suite; returns the report dict (raises on setup failures)."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key.startswith(("sk-missing", "sk-replace")):
        raise RuntimeError(
            "OPENAI_API_KEY is required for the LLM judge "
            "(any OpenAI-compatible endpoint via OPENAI_BASE_URL)."
        )

    dataset = json.loads((DATASET_DIR / "cases.json").read_text(encoding="utf-8"))
    cases: list[dict] = dataset["cases"]
    judge = LlmJudge()
    client = DocuMindClient(base_url)

    document_id = client.upload(DATASET_DIR / dataset["document"])
    client.wait_ready(document_id)

    rows: list[dict] = []
    for index, case in enumerate(cases):
        if progress_cb:
            progress_cb(index, len(cases), case["id"])
        result = client.ask(case["question"], document_id)
        row = score_case(case, result, judge)
        rows.append(row)
        if case_cb:
            case_cb(row)
    if progress_cb:
        progress_cb(len(cases), len(cases), "")

    aggregates = aggregate(rows)
    return {
        "base_url": base_url,
        "judge_model": os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini"),
        "document_id": document_id,
        "aggregates": aggregates,
        "failures": threshold_failures(aggregates, Thresholds()),
        "cases": rows,
    }
