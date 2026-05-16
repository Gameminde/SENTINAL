"""Backward-compatibility shim for ``AgentEventType``.

Task 13 / Requirement 13 — the real definition lives in
:mod:`sentinel.shared.events`. Existing imports from
``sentinel.agent.events`` continue to work during the deprecation period.
"""

from __future__ import annotations

from sentinel.shared.events import AgentEventType

__all__ = ["AgentEventType"]
