"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.upload_authorized`.

Task 5.2 / Wave D3 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.upload_authorized import (  # noqa: F401
    BrowserUploadAuthorizedExecutor,
    BrowserUploadAuthorizedReceipt,
    BrowserUploadAuthorizedRequest,
    BrowserUploadAuthorizedResult,
    BrowserUploadBackend,
    BrowserUploadBackendResult,
)

__all__ = [
    "BrowserUploadAuthorizedExecutor",
    "BrowserUploadAuthorizedReceipt",
    "BrowserUploadAuthorizedRequest",
    "BrowserUploadAuthorizedResult",
    "BrowserUploadBackend",
    "BrowserUploadBackendResult",
]
