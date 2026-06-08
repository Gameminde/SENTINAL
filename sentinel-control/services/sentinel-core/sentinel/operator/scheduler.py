from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.operator.daemon_models import (
    ProactiveProposal,
    ProactiveSchedulerConfig,
    SchedulerDecision,
    SchedulerDecisionKind,
    SchedulerPolicy,
    sanitize_daemon_metadata,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class ProactiveTrigger(SentinelModel):
    trigger_id: str = Field(default_factory=lambda: new_id("scheduler_trigger"))
    mission_id: str
    trigger_type: str
    safe_reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _trigger_is_data_only(self) -> ProactiveTrigger:
        assert_data_not_authority(
            context="proactive_trigger",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_reason = redact_operator_text(self.safe_reason)
        self.metadata = sanitize_daemon_metadata(self.metadata)
        return self


class ProactiveSchedulerRuntime:
    """Proposal-only proactive scheduler.

    A trigger can create an operator-visible proposal. It cannot execute,
    create authority, spawn workers, unlock credentials, or call organs.
    """

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        config: ProactiveSchedulerConfig | None = None,
        policy: SchedulerPolicy | None = None,
    ) -> None:
        self.kernel = kernel
        self.config = config or ProactiveSchedulerConfig()
        self.policy = policy or SchedulerPolicy()

    def evaluate(self, trigger: ProactiveTrigger) -> SchedulerDecision:
        self.kernel.store.load_record(trigger.mission_id)
        self.kernel.store.append_event(
            trigger.mission_id,
            event_type="scheduler_trigger_evaluated",
            safe_summary="Proactive scheduler trigger evaluated.",
            metadata={
                "trigger_id": trigger.trigger_id,
                "trigger_type": trigger.trigger_type,
                **trigger.metadata,
            },
        )
        unsafe_reasons = _unsafe_scheduler_reasons(trigger)
        if unsafe_reasons:
            decision = SchedulerDecision(
                kind=SchedulerDecisionKind.REJECTED,
                mission_id=trigger.mission_id,
                reasons=unsafe_reasons,
                safe_summary="Scheduler trigger rejected without execution.",
            )
            self._record_metric(trigger.mission_id, "scheduler_proposal_count", 0, "count", "Rejected scheduler proposal sample.", {"trigger_id": trigger.trigger_id})
            self._record_metric(trigger.mission_id, "scheduler_proposal_acceptance_rate", 0, "ratio", "Rejected scheduler acceptance sample.", {"trigger_id": trigger.trigger_id})
            self.kernel.store.append_event(
                trigger.mission_id,
                event_type="scheduler_proposal_rejected",
                safe_summary=decision.safe_summary,
                metadata={"trigger_id": trigger.trigger_id, "reasons": unsafe_reasons},
            )
            return decision
        proposal = ProactiveProposal(
            mission_id=trigger.mission_id,
            trigger_type=trigger.trigger_type,
            safe_summary=f"Scheduler proposes operator checkpoint: {trigger.safe_reason}",
            suggested_action="operator_checkpoint",
            metadata={"trigger_id": trigger.trigger_id, **trigger.metadata},
        )
        self.kernel.store.append_event(
            trigger.mission_id,
            event_type="scheduler_proposal_created",
            safe_summary=proposal.safe_summary,
            metadata={"proposal_id": proposal.proposal_id, "trigger_id": trigger.trigger_id},
        )
        self._record_metric(trigger.mission_id, "scheduler_proposal_count", 1, "count", "Created scheduler proposal sample.", {"trigger_id": trigger.trigger_id})
        self._record_metric(trigger.mission_id, "scheduler_proposal_acceptance_rate", 1, "ratio", "Accepted scheduler proposal sample.", {"trigger_id": trigger.trigger_id})
        return SchedulerDecision(
            kind=SchedulerDecisionKind.PROPOSED,
            mission_id=trigger.mission_id,
            proposal=proposal,
            safe_summary="Scheduler created a proposal-only checkpoint.",
        )

    def _record_metric(
        self,
        mission_id: str,
        metric_kind: str,
        value: Any,
        unit: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        telemetry = getattr(self.kernel, "telemetry_sink", None)
        if telemetry is None or not hasattr(telemetry, "store"):
            return
        try:
            from sentinel.telemetry import TelemetryDomain, TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface

            telemetry.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.PROACTIVE_SCHEDULER,
                    domain=TelemetryDomain.OPERATIONAL,
                    metric_kind=TelemetryMetricKind(metric_kind),
                    value=value,
                    unit=unit,
                    safe_summary=safe_summary,
                    metadata=metadata or {},
                )
            )
        except Exception:
            return


def _unsafe_scheduler_reasons(trigger: ProactiveTrigger) -> list[str]:
    payload = trigger.metadata
    forbidden_keys = {
        "organ_call",
        "direct_organ_call",
        "execute",
        "execute_now",
        "authority_grant",
        "grant_authority",
        "credential_unlock",
        "payment",
        "trading",
        "desktop_action",
        "channel_send",
        "provider_override",
    }
    reasons: list[str] = []
    for key in payload:
        if str(key).lower() in forbidden_keys:
            reasons.append("unsafe_scheduler_payload")
            break
    if trigger.trigger_type.lower() in {"unsafe_direct_execution", "direct_execution", "ambient_cron_action"}:
        reasons.append("unsafe_scheduler_payload")
    return list(dict.fromkeys(reasons))
