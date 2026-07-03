"""Run the behavioural eval suite from the UI.

POST /api/evals/run    -> 202, starts a run in a background thread (409 if busy)
GET  /api/evals/status -> {status, progress, report, error, started_at, finished_at}

The suite (the repo's `evals` package, baked into this image) hits the stack
back through the gateway exactly like the CLI harness does — so a UI-triggered
run is still a true end-to-end evaluation, JWT and rate limits included. One
run at a time; state lives in process memory (a run is minutes, not durable
data — history-worthy reports are the CLI's job).
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from documind_common.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/api/evals", tags=["evals"])

_lock = threading.Lock()
_state: dict = {
    "status": "idle",          # idle | running | done | error
    "progress": None,          # {"done": n, "total": n, "current": "case-id"}
    "report": None,            # suite report dict when done
    "error": None,
    "started_at": None,
    "finished_at": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_in_thread() -> None:
    from evals.suite import run_suite  # lazy: pulls in langchain only when used

    base_url = os.getenv("EVAL_BASE_URL", "http://gateway:8080")

    def progress(done: int, total: int, current: str) -> None:
        with _lock:
            _state["progress"] = {"done": done, "total": total, "current": current}

    try:
        report = run_suite(base_url, progress_cb=progress)
        with _lock:
            _state.update(status="done", report=report, finished_at=_now())
        log.info("eval run finished", stage="evals", failures=len(report["failures"]))
    except Exception as exc:  # noqa: BLE001 — surface anything to the UI, never crash the service
        with _lock:
            _state.update(status="error", error=str(exc), finished_at=_now())
        log.warning("eval run failed", stage="evals", error=str(exc))


@router.post("/run", status_code=202)
def start_run() -> JSONResponse:
    with _lock:
        if _state["status"] == "running":
            return JSONResponse({"status": "running", "detail": "a run is already in progress"}, 409)
        _state.update(
            status="running",
            progress={"done": 0, "total": 12, "current": "starting"},
            report=None,
            error=None,
            started_at=_now(),
            finished_at=None,
        )
    threading.Thread(target=_run_in_thread, name="eval-run", daemon=True).start()
    log.info("eval run started", stage="evals")
    return JSONResponse({"status": "running"}, 202)


@router.get("/status")
def status() -> dict:
    with _lock:
        return dict(_state)
