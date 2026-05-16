"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.controlled_runner`.

Task 5.2 / Wave D4 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.controlled_runner import (  # noqa: F401
    BrowserControlledCapabilityRunner,
)

__all__ = ["BrowserControlledCapabilityRunner"]
