"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.operator_runtime`.

Task 5.2 / Wave D4 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.operator_runtime import (  # noqa: F401
    BrowserOperatorRouteProtocol,
    BrowserOperatorRouteResult,
    BrowserOperatorRuntimeRoute,
    BrowserOperatorRuntimeStatus,
)

__all__ = [
    "BrowserOperatorRouteProtocol",
    "BrowserOperatorRouteResult",
    "BrowserOperatorRuntimeRoute",
    "BrowserOperatorRuntimeStatus",
]
