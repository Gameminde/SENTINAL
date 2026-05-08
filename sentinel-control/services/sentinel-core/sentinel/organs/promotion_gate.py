from __future__ import annotations

from pydantic import Field

from sentinel.agent.event_bus import EventBus
from sentinel.agent.events import AgentEventType
from sentinel.organs.contracts import ExternalOrganContract, OrganPromotionLevel, PROMOTION_ORDER
from sentinel.shared.models import SentinelModel, new_id


class OrganPromotionDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("opromo"))
    organ_id: str
    current_level: OrganPromotionLevel
    target_level: OrganPromotionLevel
    accepted: bool
    errors: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    authority_expansion: bool = False
    execution_enabled: bool = False
    trace_refs: list[str] = Field(default_factory=list)


class OrganPromotionGate:
    def evaluate(
        self,
        contract: ExternalOrganContract,
        *,
        target_level: OrganPromotionLevel,
        fake_eval_passed: bool = False,
        eval_dataset_present: bool = False,
        risk_map_present: bool = False,
        failure_modes_present: bool = False,
        dry_run_schema_present: bool = False,
        receipt_schema_present: bool = False,
        kill_switch_present: bool = False,
        rollback_disable_plan_present: bool = False,
        final_gate_adapter_present: bool = False,
        event_bus: EventBus | None = None,
    ) -> OrganPromotionDecision:
        errors = []
        if PROMOTION_ORDER[target_level] < PROMOTION_ORDER[contract.promotion_level]:
            errors.append("target_level_below_current_level")
        if target_level in {
            OrganPromotionLevel.L3_FAKE_EVAL,
            OrganPromotionLevel.L4_DRY_RUN,
            OrganPromotionLevel.L5_SANDBOX,
            OrganPromotionLevel.L6_LIMITED_EXECUTION,
            OrganPromotionLevel.L7_PRODUCTION_SCOPED_EXECUTION,
            OrganPromotionLevel.L8_CONTINUOUS_ORGANBENCH_MONITORING,
        } and not fake_eval_passed:
            errors.append("fake_eval_required")
        if PROMOTION_ORDER[target_level] >= PROMOTION_ORDER[OrganPromotionLevel.L3_FAKE_EVAL] and not eval_dataset_present:
            errors.append("eval_dataset_required")
        if PROMOTION_ORDER[target_level] >= PROMOTION_ORDER[OrganPromotionLevel.L4_DRY_RUN]:
            if not risk_map_present:
                errors.append("risk_map_required")
            if not failure_modes_present:
                errors.append("failure_modes_required")
        if PROMOTION_ORDER[target_level] >= PROMOTION_ORDER[OrganPromotionLevel.L4_DRY_RUN] and not dry_run_schema_present:
            errors.append("dry_run_schema_required")
        if PROMOTION_ORDER[target_level] >= PROMOTION_ORDER[OrganPromotionLevel.L6_LIMITED_EXECUTION]:
            if not receipt_schema_present:
                errors.append("receipt_schema_required")
            if not kill_switch_present:
                errors.append("kill_switch_required")
            if not rollback_disable_plan_present:
                errors.append("rollback_disable_plan_required")
            if not final_gate_adapter_present:
                errors.append("final_gate_adapter_required")
        if contract.vendor_code_copied:
            errors.append("vendor_code_copied")
        if contract.vendor_runtime_bridge:
            errors.append("vendor_runtime_bridge")

        decision = OrganPromotionDecision(
            organ_id=contract.id,
            current_level=contract.promotion_level,
            target_level=target_level,
            accepted=not errors,
            errors=errors,
            required_evidence=[
                "contract",
                "authority_mapping",
                "risk_profile",
                "eval_dataset",
                "risk_map",
                "failure_modes",
                "dry_run_schema",
                "receipt_schema",
                "kill_switch",
                "rollback_disable_plan",
                "final_gate_compatibility",
            ],
            execution_enabled=False,
        )
        if event_bus is None:
            return decision
        event = event_bus.append(
            AgentEventType.ORGAN_PROMOTION_EVALUATED,
            "External organ promotion evaluated without enabling runtime execution.",
            payload={
                "promotion_decision_id": decision.id,
                "organ_id": contract.id,
                "current_level": contract.promotion_level.value,
                "target_level": target_level.value,
                "accepted": decision.accepted,
                "errors": decision.errors,
                "execution_enabled": False,
                "authority_expansion": False,
            },
        )
        return decision.model_copy(update={"trace_refs": [event.id]})
