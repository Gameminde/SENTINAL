"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.verifier`.

Task 5.2 / Wave D1 (Browser Legacy Consolidation). All public names
re-exported so existing callers that import
``from sentinel.agent.browser.verifier import ...`` continue to work
while the browser execution/receipt surface migrates to
:mod:`sentinel.organs.browser`.
"""

from __future__ import annotations

from sentinel.organs.browser.verifier import (  # noqa: F401
    BrowserLoopDetectionResult,
    BrowserLoopDetector,
    BrowserPostActionVerifier,
    BrowserVerificationResult,
    BrowserVerificationVerdict,
)

__all__ = [
    "BrowserLoopDetectionResult",
    "BrowserLoopDetector",
    "BrowserPostActionVerifier",
    "BrowserVerificationResult",
    "BrowserVerificationVerdict",
]
