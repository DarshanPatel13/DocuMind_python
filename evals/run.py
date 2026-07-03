"""Eval harness entry point:  RUN_EVALS=1 python -m evals.run  [--no-fail]

End-to-end: login -> ingest the golden fixture -> run all cases through the
real /api/ask -> score (deterministic scorers + LLM judge) -> console table +
JSON/Markdown reports -> non-zero exit if any threshold fails (CI-friendly).
Opt-in by design: judge calls cost real API money (cents on gpt-4o-mini).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from evals.client import DocuMindClient
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
RESULTS_DIR = Path(__file__).parent / "results"


def _score_case(case: dict, result, judge: LlmJudge) -> dict:
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


def _aggregate(rows: list[dict]) -> dict:
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


def _fmt(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def _write_reports(rows: list[dict], aggregates: dict, meta: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (RESULTS_DIR / f"report-{stamp}.json").write_text(
        json.dumps({**meta, "aggregates": aggregates, "cases": rows}, indent=2), encoding="utf-8"
    )
    lines = [
        f"# DocuMind eval report — {stamp}",
        "",
        f"Base URL: {meta['base_url']} · judge: {meta['judge_model']}",
        "",
        "| metric | value |",
        "|---|---|",
        *(f"| {k} | {_fmt(v) if isinstance(v, float) or v is None else v} |" for k, v in aggregates.items()),
        "",
        "| case | behavior | groundedness | cit valid/invalid | pass |",
        "|---|---|---|---|---|",
        *(
            f"| {r['id']} | {r['behavior']} | {_fmt(r['groundedness'])} "
            f"| {r['citations_valid']}/{r['citations_invalid']} | {'PASS' if r['passed'] else 'FAIL'} |"
            for r in rows
        ),
    ]
    md_path = RESULTS_DIR / f"report-{stamp}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DocuMind behavioural evals")
    parser.add_argument("--base-url", default=os.getenv("EVAL_BASE_URL", "http://localhost:8080"))
    parser.add_argument("--no-fail", action="store_true", help="report thresholds but exit 0")
    args = parser.parse_args(argv)

    if os.getenv("RUN_EVALS") != "1":
        print("Evals are opt-in (they cost API calls). Set RUN_EVALS=1 to run.")
        return 2
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key.startswith(("sk-missing", "sk-replace")):
        print("OPENAI_API_KEY is required for the LLM judge (gpt-4o-mini; a run costs cents).")
        return 2

    dataset = json.loads((DATASET_DIR / "cases.json").read_text(encoding="utf-8"))
    judge = LlmJudge()
    client = DocuMindClient(args.base_url)

    print(f"Ingesting fixture {dataset['document']} ...")
    document_id = client.upload(DATASET_DIR / dataset["document"])
    client.wait_ready(document_id)
    print(f"Fixture READY ({document_id}). Running {len(dataset['cases'])} cases...\n")

    rows = []
    print(f"{'case':28} {'behavior':18} {'ground':7} {'cit v/i':8} pass")
    for case in dataset["cases"]:
        result = client.ask(case["question"], document_id)
        row = _score_case(case, result, judge)
        rows.append(row)
        print(
            f"{row['id']:28} {row['behavior']:18} {_fmt(row['groundedness']):7} "
            f"{row['citations_valid']}/{row['citations_invalid']:6} "
            f"{'PASS' if row['passed'] else 'FAIL'}{' (ERRORED)' if row['errored'] else ''}"
        )

    aggregates = _aggregate(rows)
    meta = {
        "base_url": args.base_url,
        "judge_model": os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini"),
        "document_id": document_id,
    }
    report = _write_reports(rows, aggregates, meta)

    print("\nAggregates:")
    for key_, value in aggregates.items():
        print(f"  {key_:22} {_fmt(value) if isinstance(value, float) or value is None else value}")
    print(f"\nReport: {report}")

    failures = threshold_failures(aggregates, Thresholds())
    if failures:
        print("\nTHRESHOLD FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        return 0 if args.no_fail else 1
    print("\nAll thresholds met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
