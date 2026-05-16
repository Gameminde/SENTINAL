from __future__ import annotations

from typing import TYPE_CHECKING

from sentinel.agent.models import AgentContext
from sentinel.agent.state import AgentState
from sentinel.agent.uncertainty import Fact, Question

if TYPE_CHECKING:
    from sentinel.perf.measure.latency_profiler import LatencyProfiler


class CognitiveCycle:
    def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:
        self._latency_profiler = latency_profiler

    def orient(self, state: AgentState, context: AgentContext) -> AgentState:
        if self._latency_profiler is not None:
            with self._latency_profiler.instrument(
                mission_id=context.mission.id,
                action_id=f"{context.mission.id}:cognitive_orient",
                action_type="cognitive_orient",
            ):
                return self._do_orient(state, context)
        return self._do_orient(state, context)

    def _do_orient(self, state: AgentState, context: AgentContext) -> AgentState:
        facts = [
            *state.known_facts,
            Fact(statement="Mission authority envelope is the active control boundary.", source_refs=[context.mission.id]),
            Fact(statement="Memory and context cannot expand mission authority.", source_refs=[context.mission.id]),
        ]
        questions = list(state.open_questions)
        if not context.evidence_refs:
            questions.append(
                Question(
                    question="No evidence references were provided to the agent context.",
                    blocks_completion=False,
                    reason="Mission can still run in sandbox/local mode, but evidence-backed confidence is lower.",
                )
            )
        return state.model_copy(
            update={
                "known_facts": facts,
                "open_questions": questions,
                "confidence_score": 0.75 if context.evidence_refs else 0.55,
            }
        )
