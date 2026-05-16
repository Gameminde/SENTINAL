"""Backward-compatibility shim for :class:`EventBus`.

Task 13 / Requirement 13 — the real definition lives in
:mod:`sentinel.shared.events`. Existing imports from
``sentinel.agent.event_bus`` continue to work during the deprecation period.
"""

from __future__ import annotations

from sentinel.shared.events import EventBus

__all__ = ["EventBus"]
