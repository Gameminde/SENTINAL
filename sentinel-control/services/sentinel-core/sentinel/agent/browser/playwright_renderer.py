"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.playwright_renderer`.

Task 5.2 / Wave D2 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.playwright_renderer import (  # noqa: F401
    PlaywrightReadOnlyRenderer,
)

__all__ = ["PlaywrightReadOnlyRenderer"]
