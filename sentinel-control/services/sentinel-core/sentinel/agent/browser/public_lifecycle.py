"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.public_lifecycle`.

Task 5.2 / Wave D3 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.public_lifecycle import (  # noqa: F401
    BrowserPublicLifecycleController,
)

__all__ = ["BrowserPublicLifecycleController"]
