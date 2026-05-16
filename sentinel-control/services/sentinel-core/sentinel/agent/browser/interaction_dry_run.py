"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.interaction_dry_run`.

Task 5.2-B3 (Browser Legacy Consolidation, Wave B dry-run planner).
Plan builder, hash helpers, and constants re-exported so existing callers
that import from ``sentinel.agent.browser.interaction_dry_run`` continue
to work while the browser legacy surface migrates to
:mod:`sentinel.organs.browser`.

No behavior change. Hash computation (``hash_browser_interaction_plan_payload``
and ``verify_browser_interaction_plan_hash``) is byte-equivalent to the
pre-migration implementation. ``BrowserInteractionDryRunProof`` is NOT yet
integrated with ``OrganDryRunReceipt`` — that belongs to a later wave.
"""

from __future__ import annotations

from sentinel.organs.browser.interaction_dry_run import *  # noqa: F401,F403
from sentinel.organs.browser.interaction_dry_run import (  # noqa: F401
    BrowserInteractionDryRunPlanner,
    P3G_FORBIDDEN_INTERACTION_NAMES,
    REF_REQUIRED_INTENTS,
    hash_browser_interaction_plan_payload,
    verify_browser_interaction_plan_hash,
)

__all__ = [
    "BrowserInteractionDryRunPlanner",
    "P3G_FORBIDDEN_INTERACTION_NAMES",
    "REF_REQUIRED_INTENTS",
    "hash_browser_interaction_plan_payload",
    "verify_browser_interaction_plan_hash",
]
