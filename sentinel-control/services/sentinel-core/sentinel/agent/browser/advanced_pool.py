"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.advanced_pool`.

Task 5.2 / Wave D1 (Browser Legacy Consolidation). All public names
re-exported so existing callers that import
``from sentinel.agent.browser.advanced_pool import ...`` continue to
work while the browser execution/receipt surface migrates to
:mod:`sentinel.organs.browser`.
"""

from __future__ import annotations

from sentinel.organs.browser.advanced_pool import (  # noqa: F401
    BrowserAdvancedPoolLease,
    BrowserAdvancedPoolLeaseStatus,
    BrowserAdvancedPoolResult,
    BrowserPublicPoolInstance,
    BrowserPublicPoolInstanceStatus,
    BrowserPublicPoolManager,
)

__all__ = [
    "BrowserAdvancedPoolLease",
    "BrowserAdvancedPoolLeaseStatus",
    "BrowserAdvancedPoolResult",
    "BrowserPublicPoolInstance",
    "BrowserPublicPoolInstanceStatus",
    "BrowserPublicPoolManager",
]
