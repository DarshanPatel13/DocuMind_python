"""Structured logging via structlog.

Every pipeline stage logs a one-line key=value event (stage=..., document_id=...)
so logs are greppable and machine-parseable — the same intent as the
`stage=...` logs in the Java version.
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
            structlog.processors.KeyValueRenderer(key_order=["event", "stage"]),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
