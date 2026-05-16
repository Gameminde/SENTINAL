"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.visual_observation`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.visual_observation import *  # noqa: F401,F403
from sentinel.organs.browser.visual_observation import (  # noqa: F401
    BrowserScreenshotRegion,
    BrowserVisualObservation,
    verify_visual_observation_hash,
)

__all__ = [
    "BrowserScreenshotRegion",
    "BrowserVisualObservation",
    "verify_visual_observation_hash",
]
