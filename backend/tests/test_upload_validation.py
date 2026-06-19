"""Upload validation: type, magic bytes, and size limit."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.document_service import validate_pdf
from app.services.errors import InvalidFileError


def test_rejects_empty_content() -> None:
    with pytest.raises(InvalidFileError):
        validate_pdf("doc.pdf", "application/pdf", b"")


def test_rejects_non_pdf_file() -> None:
    with pytest.raises(InvalidFileError):
        validate_pdf("notes.txt", "text/plain", b"hello")


def test_rejects_spoofed_pdf_extension() -> None:
    # Right name + content type, wrong bytes: the %PDF magic check must catch it.
    with pytest.raises(InvalidFileError):
        validate_pdf("fake.pdf", "application/pdf", b"definitely not a pdf")


def test_rejects_oversized_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_upload_bytes", 8)
    with pytest.raises(InvalidFileError):
        validate_pdf("big.pdf", "application/pdf", b"%PDF-1.7 and then some more bytes")


def test_accepts_valid_pdf() -> None:
    # Should not raise.
    validate_pdf("report.pdf", "application/pdf", b"%PDF-1.7 minimal content")
