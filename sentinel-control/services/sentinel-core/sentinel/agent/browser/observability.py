"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.observability`. See Task 5.2-A.
"""

from __future__ import annotations

from sentinel.organs.browser.observability import (  # noqa: F401
    build_browser_network_ledger,
    hash_browser_network_ledger_payload,
    minimal_browser_network_ledger,
    verify_browser_network_ledger_hash,
)

__all__ = [
    "build_browser_network_ledger",
    "hash_browser_network_ledger_payload",
    "minimal_browser_network_ledger",
    "verify_browser_network_ledger_hash",
]
