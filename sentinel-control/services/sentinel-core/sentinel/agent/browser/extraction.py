"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.extraction`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.extraction import *  # noqa: F401,F403
from sentinel.organs.browser.extraction import (  # noqa: F401
    BrowserExtractionStrategy,
    ReadablePageExtraction,
    ReadablePageExtractor,
)

__all__ = [
    "BrowserExtractionStrategy",
    "ReadablePageExtraction",
    "ReadablePageExtractor",
]
