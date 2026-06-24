"""PDF text extraction for the resume upload flow.

``pypdf`` is imported lazily so this module loads even in environments where the
dependency is not installed (e.g. during partial test runs), and so the rest of
the app does not pay the import cost unless a resume is actually uploaded.
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger("learngraph")


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be parsed into text."""


def extract_text_from_pdf(data: bytes) -> str:
    """Extract plain text from PDF bytes.

    Raises:
        PdfExtractionError: if the bytes are not a parseable PDF.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency always present in prod
        raise PdfExtractionError("PDF support is not installed") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001 - pypdf raises a variety of errors
        logger.info("PDF parse failed: %s", exc)
        raise PdfExtractionError("Could not read the PDF") from exc

    return "\n".join(pages).strip()
