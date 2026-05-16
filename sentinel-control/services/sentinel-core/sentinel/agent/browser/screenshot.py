"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.screenshot`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.screenshot import (  # noqa: F401
    BrowserScreenshotNormalizationError,
    BrowserScreenshotNormalizer,
    normalize_browser_screenshot,
    screenshot_metadata,
)

__all__ = [
    "BrowserScreenshotNormalizationError",
    "BrowserScreenshotNormalizer",
    "normalize_browser_screenshot",
    "screenshot_metadata",
]
