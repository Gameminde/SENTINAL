from __future__ import annotations

from pathlib import Path

from sentinel.mission.models import MissionAction, MissionAuthorityEnvelope, MissionState
from sentinel.mission.posture import MissionExecutionPosture
from sentinel.mission.risk import RiskRouter, RouteDecision
from sentinel.mission.trace_timeline import MissionTraceTimeline


class AutonomyEngine:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self.router = RiskRouter(project_root)

    def decide(
        self,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
        action: MissionAction,
        timeline: MissionTraceTimeline | None = None,
        posture: MissionExecutionPosture | None = None,
    ) -> RouteDecision:
        # Task 6.5-A / F-A3.8 — route through the SPINE_01 §5 ordered
        # gate sequence in addition to the router's existing checks.
        # ``RiskRouter.route_via_sequence`` runs
        # :meth:`GateSequence.evaluate` for audit/ordering evidence,
        # then delegates to :meth:`RiskRouter.route` for the existing
        # :class:`RouteDecision` shape and ``RISK_ROUTE_DECIDED``
        # timeline event payload (preserved exactly). The sequence
        # result is available on ``self.router.last_sequence_result``
        # for tests and audit tooling.
        return self.router.route_via_sequence(
            envelope, state, action, timeline=timeline, posture=posture
        )
