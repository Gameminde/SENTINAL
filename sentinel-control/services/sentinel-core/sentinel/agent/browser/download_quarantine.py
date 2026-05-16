"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.download_quarantine`.

Task 5.2 / Wave D3 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.download_quarantine import (  # noqa: F401
    BrowserDownloadBackend,
    BrowserDownloadBackendResult,
    BrowserDownloadQuarantineExecutor,
    BrowserDownloadQuarantineReceipt,
    BrowserDownloadQuarantineRequest,
    BrowserDownloadQuarantineResult,
)

__all__ = [
    "BrowserDownloadBackend",
    "BrowserDownloadBackendResult",
    "BrowserDownloadQuarantineExecutor",
    "BrowserDownloadQuarantineReceipt",
    "BrowserDownloadQuarantineRequest",
    "BrowserDownloadQuarantineResult",
]
