"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.interaction_execution`.

Task 5.2 / Wave D3 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.interaction_execution import (  # noqa: F401
    BrowserInteractionBackend,
    BrowserLimitedInteractionExecutor,
    P3H_ALLOWED_EXECUTION_INTENTS,
)

__all__ = [
    "BrowserInteractionBackend",
    "BrowserLimitedInteractionExecutor",
    "P3H_ALLOWED_EXECUTION_INTENTS",
]
