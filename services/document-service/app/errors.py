"""Domain exceptions, mapped to HTTP responses in app/main.py."""
from __future__ import annotations


class InvalidFileError(Exception):
    """Upload validation failed (not a PDF, empty, or too large) -> 400."""


class DocumentNotFoundError(Exception):
    """No document row for the given id -> 404 (and non-retryable in ingestion)."""


class IngestionError(Exception):
    """A recoverable failure in the ingestion pipeline. The consumer retries
    these; after exhausting retries the document is marked FAILED and the event
    is parked on the DLT."""
