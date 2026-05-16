from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sentinel.agent.capability_selector import capabilities_from_actions
from sentinel.agent.models import AgentContext
from sentinel.mission.models import MissionAuthorityEnvelope

if TYPE_CHECKING:
    from sentinel.perf.measure.latency_profiler import LatencyProfiler


class ContextBuilder:
    def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:
        self._latency_profiler = latency_profiler

    def build(
        self,
        envelope: MissionAuthorityEnvelope,
        *,
        user_input: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
        memory_items: list[dict[str, Any]] | None = None,
    ) -> AgentContext:
        if self._latency_profiler is not None:
            with self._latency_profiler.instrument(
                mission_id=envelope.id,
                action_id=f"{envelope.id}:context_builder_build",
                action_type="context_builder_build",
            ):
                return self._do_build(
                    envelope,
                    user_input=user_input,
                    evidence_refs=evidence_refs,
                    memory_items=memory_items,
                )
        return self._do_build(
            envelope,
            user_input=user_input,
            evidence_refs=evidence_refs,
            memory_items=memory_items,
        )

    def _do_build(
        self,
        envelope: MissionAuthorityEnvelope,
        *,
        user_input: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
        memory_items: list[dict[str, Any]] | None = None,
    ) -> AgentContext:
        constraints = [
            f"mission_type={envelope.mission_type.value if hasattr(envelope.mission_type, 'value') else envelope.mission_type}",
            f"max_actions={envelope.max_actions}",
            f"max_cost_usd={envelope.max_cost_usd}",
            "memory_is_context_not_authority",
            "unknown_capabilities_must_be_reported_not_executed",
        ]
        summary = f"{envelope.mission_title}: {envelope.mission_objective}"
        return AgentContext(
            mission=envelope,
            user_input=user_input or {},
            evidence_refs=evidence_refs or [],
            memory_items=memory_items or [],
            constraints=constraints,
            available_capabilities=capabilities_from_actions(list(envelope.allowed_actions)),
            available_tools=list(envelope.allowed_tools),
            world_model_refs=["mission_authority", "local_filesystem_boundary", "memory_not_authority"],
            summary=summary,
        )
