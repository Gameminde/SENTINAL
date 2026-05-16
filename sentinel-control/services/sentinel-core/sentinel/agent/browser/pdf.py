"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.pdf`.

Task 5.2-A (Browser Legacy Consolidation, Wave A). All names re-exported so
existing callers that import ``from sentinel.agent.browser.pdf import ...``
continue to work while the browser legacy surface migrates to
:mod:`sentinel.organs.browser`.
"""

from __future__ import annotations

from sentinel.organs.browser.pdf import *  # noqa: F401,F403
from sentinel.organs.browser.pdf import pdf_metadata  # noqa: F401

__all__ = ["pdf_metadata"]
