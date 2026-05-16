"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.dom_snapshot`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.dom_snapshot import *  # noqa: F401,F403
from sentinel.organs.browser.dom_snapshot import (  # noqa: F401
    BrowserDomSnapshot,
    BrowserDomSnapshotAdapter,
    verify_dom_snapshot_hash,
)

__all__ = [
    "BrowserDomSnapshot",
    "BrowserDomSnapshotAdapter",
    "verify_dom_snapshot_hash",
]
