"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.live_fetch`.

Task 5.2 / Wave D2 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.live_fetch import (  # noqa: F401
    DEFAULT_BROWSER_FETCH_TIMEOUT_SECONDS,
    DEFAULT_BROWSER_FETCH_USER_AGENT,
    ReadOnlyHttpFetcher,
)

__all__ = [
    "DEFAULT_BROWSER_FETCH_TIMEOUT_SECONDS",
    "DEFAULT_BROWSER_FETCH_USER_AGENT",
    "ReadOnlyHttpFetcher",
]
