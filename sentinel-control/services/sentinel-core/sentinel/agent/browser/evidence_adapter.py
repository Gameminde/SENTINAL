"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.evidence_adapter`.

Task 5.2 / Wave D2 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.evidence_adapter import (  # noqa: F401
    BrowserEvidenceAdapter,
    BrowserFetcher,
    BrowserFetchError,
)

__all__ = [
    "BrowserEvidenceAdapter",
    "BrowserFetcher",
    "BrowserFetchError",
]
