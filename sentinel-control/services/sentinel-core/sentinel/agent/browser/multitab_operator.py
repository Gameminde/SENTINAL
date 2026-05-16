"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.multitab_operator`.

Task 5.2 / Wave D3 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.multitab_operator import (  # noqa: F401
    BrowserMultitabStrategyResult,
    BrowserPublicMultitabOperator,
    BrowserPublicTabPlan,
)

__all__ = [
    "BrowserMultitabStrategyResult",
    "BrowserPublicMultitabOperator",
    "BrowserPublicTabPlan",
]
