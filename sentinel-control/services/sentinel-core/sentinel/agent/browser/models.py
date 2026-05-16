"""Backward-compatibility shim — real module lives at
:mod:`sentinel.organs.browser.models`.

Task 5.2-B1 (Browser Legacy Consolidation, Wave B data-layer relocation).
All pydantic models re-exported so existing callers that import from
``sentinel.agent.browser.models`` continue to work while the browser
legacy surface migrates to :mod:`sentinel.organs.browser`.

No behavior change. No field/validator/hash change. Any future splitting
of this module belongs to a later wave.
"""

from __future__ import annotations

# Star import carries every public name (classes, enums, constants) that
# the organ-side module exposes via ``__all__`` or top-level definitions.
from sentinel.organs.browser.models import *  # noqa: F401,F403
