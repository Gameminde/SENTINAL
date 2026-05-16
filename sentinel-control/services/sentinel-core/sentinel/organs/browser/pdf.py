from __future__ import annotations

import re

from sentinel.organs.browser.models import BrowserPdfMetadata


def pdf_metadata(data: bytes, *, max_bytes: int) -> BrowserPdfMetadata:
    warnings: list[str] = []
    if not data.startswith(b"%PDF-"):
        warnings.append("invalid_pdf_header")
    if len(data) > max_bytes:
        warnings.append("bytes_exceed_max")
    return BrowserPdfMetadata(
        bytes=len(data),
        max_bytes=max_bytes,
        page_count_estimate=_page_count_estimate(data),
        warnings=warnings,
    )


def _page_count_estimate(data: bytes) -> int | None:
    if not data.startswith(b"%PDF-"):
        return None
    # Conservative estimate used only for metadata; it is not a PDF parser.
    return len(re.findall(rb"/Type\s*/Page\b", data))
