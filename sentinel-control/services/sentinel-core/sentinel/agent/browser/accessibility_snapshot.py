"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.accessibility_snapshot`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.accessibility_snapshot import *  # noqa: F401,F403
from sentinel.organs.browser.accessibility_snapshot import (  # noqa: F401
    BrowserAccessibilitySnapshotBuilder,
)

__all__ = ["BrowserAccessibilitySnapshotBuilder"]
