"""Eval harness CLI:  RUN_EVALS=1 python -m evals.run  [--no-fail]

Thin wrapper over evals/suite.py (the same core the UI's Run button uses):
gates -> run -> console table -> JSON/Markdown reports -> threshold exit code.
Opt-in by design: judge calls cost real API money (cents on gpt-4o-mini).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def _fmt(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def _write_reports(report: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (RESULTS_DIR / f"report-{stamp}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    aggregates, rows = report["aggregates"], report["cases"]
    lines = [
        f"# DocuMind eval report — {stamp}",
        "",
        f"Base URL: {report['base_url']} · judge: {report['judge_model']}",
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

    from evals.suite import run_suite  # lazy: imports langchain

    print("Ingesting fixture + running cases...\n")
    print(f"{'case':28} {'behavior':18} {'ground':7} {'cit v/i':8} pass")

    def print_row(row: dict) -> None:
        print(
            f"{row['id']:28} {row['behavior']:18} {_fmt(row['groundedness']):7} "
            f"{row['citations_valid']}/{row['citations_invalid']:6} "
            f"{'PASS' if row['passed'] else 'FAIL'}{' (ERRORED)' if row['errored'] else ''}"
        )

    report = run_suite(args.base_url, case_cb=print_row)

    print("\nAggregates:")
    for key_, value in report["aggregates"].items():
        print(f"  {key_:22} {_fmt(value) if isinstance(value, float) or value is None else value}")
    print(f"\nReport: {_write_reports(report)}")

    if report["failures"]:
        print("\nTHRESHOLD FAILURES:")
        for failure in report["failures"]:
            print(f"  - {failure}")
        return 0 if args.no_fail else 1
    print("\nAll thresholds met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
