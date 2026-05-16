"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.v3_authority`.

Task 5.2-B2 (Browser Legacy Consolidation, Wave B authority-base layer).
All authority enums, grants, request/receipt base models, and helpers
re-exported so existing callers that import from
``sentinel.agent.browser.v3_authority`` continue to work while the
browser legacy surface migrates to :mod:`sentinel.organs.browser`.

No behavior change. ``BrowserV3Receipt`` is NOT yet converted to an
``OrganExecutionReceipt`` subclass — that belongs to a later
executor-migration wave.
"""

from __future__ import annotations

from sentinel.organs.browser.v3_authority import *  # noqa: F401,F403
from sentinel.organs.browser.v3_authority import (  # noqa: F401
    BrowserV3AuthorityClass,
    BrowserV3AuthorityGrant,
    BrowserV3Receipt,
    BrowserV3RequestModel,
    browser_v3_grant_allows_url,
    find_browser_v3_authority_grant,
    parse_browser_v3_authority_grants,
)

__all__ = [
    "BrowserV3AuthorityClass",
    "BrowserV3AuthorityGrant",
    "BrowserV3Receipt",
    "BrowserV3RequestModel",
    "browser_v3_grant_allows_url",
    "find_browser_v3_authority_grant",
    "parse_browser_v3_authority_grants",
]
