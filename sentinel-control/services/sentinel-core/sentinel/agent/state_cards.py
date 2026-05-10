from __future__ import annotations

from typing import Any

from sentinel.agent.context_engine import ContextNeed


class StateCardBuilder:
    def mission_card(self, need: ContextNeed) -> dict[str, Any]:
        return {
            "mission_id": need.mission_id,
            "objective": need.objective,
            "required_evidence_refs": need.required_evidence_refs,
        }

    def progress_card(self, *, completed: list[str], pending: list[str]) -> dict[str, Any]:
        return {
            "completed": completed,
            "pending": pending,
        }


class AuthorityCardBuilder:
    def authority_card(
        self,
        *,
        allowed_tools: list[str],
        forbidden_tools: list[str],
        constraints: list[str],
    ) -> dict[str, Any]:
        return {
            "allowed_tools": sorted(allowed_tools),
            "forbidden_tools": sorted(forbidden_tools),
            "constraints": constraints,
            "authority_expansion": False,
        }
