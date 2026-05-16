"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.ui_observation`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.ui_observation import *  # noqa: F401,F403
from sentinel.organs.browser.ui_observation import (  # noqa: F401
    BrowserBoundingBox,
    BrowserUIObservation,
    BrowserUIObservationBuilder,
    BrowserUIObservationSet,
    verify_ui_observation_hash,
)

__all__ = [
    "BrowserBoundingBox",
    "BrowserUIObservation",
    "BrowserUIObservationBuilder",
    "BrowserUIObservationSet",
    "verify_ui_observation_hash",
]
