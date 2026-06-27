"""Structured logging via structlog, shared by every service.

Every pipeline stage logs a one-line key=value event (stage=..., document_id=...)
so logs are greppable and machine-parseable. `service=` is bound per-service in
each app's startup so a single log stream stays attributable.
"""
from __future__ import annotations

import logging

import structlog


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.KeyValueRenderer(key_order=["event", "service", "stage"]),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
