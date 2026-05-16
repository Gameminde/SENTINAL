"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.rendered_snapshot`.

Task 5.2 / Wave D2 (Browser Legacy Consolidation).
"""

from __future__ import annotations

from sentinel.organs.browser.rendered_snapshot import (  # noqa: F401
    BrowserRenderedSnapshotAdapter,
    BrowserRenderError,
    BrowserRenderer,
)

__all__ = [
    "BrowserRenderedSnapshotAdapter",
    "BrowserRenderError",
    "BrowserRenderer",
]
