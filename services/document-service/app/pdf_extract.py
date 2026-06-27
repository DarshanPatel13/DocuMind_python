"""PDF text extraction via pypdf, behind a one-function seam (easy to mock,
easy to extend with OCR for scanned PDFs later). Ingestion-only — stays in
document-service rather than the shared lib."""
from __future__ import annotations

from pypdf import PdfReader


def extract_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
