"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.form_submit`.

Task 5.2 / Wave D3 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.form_submit import (  # noqa: F401
    BrowserFormSubmitBackend,
    BrowserFormSubmitBackendResult,
    BrowserFormSubmitExecutor,
    BrowserFormSubmitReceipt,
    BrowserFormSubmitRequest,
    BrowserFormSubmitResult,
)

__all__ = [
    "BrowserFormSubmitBackend",
    "BrowserFormSubmitBackendResult",
    "BrowserFormSubmitExecutor",
    "BrowserFormSubmitReceipt",
    "BrowserFormSubmitRequest",
    "BrowserFormSubmitResult",
]
