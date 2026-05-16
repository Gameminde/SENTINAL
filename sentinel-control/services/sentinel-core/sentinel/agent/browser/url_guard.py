"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.url_guard`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.url_guard import *  # noqa: F401,F403
from sentinel.organs.browser.url_guard import (  # noqa: F401
    DnsResolver,
    PublicUrlGuard,
)

__all__ = ["DnsResolver", "PublicUrlGuard"]
