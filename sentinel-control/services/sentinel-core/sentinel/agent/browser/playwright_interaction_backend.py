"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.playwright_interaction_backend`.

Task 5.2 / Wave D2 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.playwright_interaction_backend import (  # noqa: F401
    PlaywrightLimitedInteractionBackend,
)

__all__ = ["PlaywrightLimitedInteractionBackend"]
