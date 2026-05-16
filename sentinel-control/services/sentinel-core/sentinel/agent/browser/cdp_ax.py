"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.cdp_ax`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.cdp_ax import *  # noqa: F401,F403
from sentinel.organs.browser.cdp_ax import (  # noqa: F401
    BrowserCdpAccessibilityAdapter,
    BrowserCdpAxCaptureResult,
    BrowserCdpAxTree,
    verify_cdp_ax_tree_hash,
)

__all__ = [
    "BrowserCdpAccessibilityAdapter",
    "BrowserCdpAxCaptureResult",
    "BrowserCdpAxTree",
    "verify_cdp_ax_tree_hash",
]
