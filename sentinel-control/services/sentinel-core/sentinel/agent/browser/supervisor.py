"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.supervisor`.

Task 5.2 / Wave D1 (Browser Legacy Consolidation). All public names
re-exported so existing callers that import
``from sentinel.agent.browser.supervisor import ...`` continue to
work while the browser execution/receipt surface migrates to
:mod:`sentinel.organs.browser`.
"""

from __future__ import annotations

from sentinel.organs.browser.supervisor import (  # noqa: F401
    BrowserHealthProbe,
    BrowserOperation,
    BrowserOperationError,
    BrowserReliabilitySupervisor,
)

__all__ = [
    "BrowserHealthProbe",
    "BrowserOperation",
    "BrowserOperationError",
    "BrowserReliabilitySupervisor",
]
