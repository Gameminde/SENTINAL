from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionKernelError, ActionResult
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.operator.safety import assert_data_not_authority
from sentinel.operator.store import _filesystem_path, _path_exists
from sentinel.operator.workspace_readonly_runtime import WorkspaceReadOnlyRuntime
from sentinel.shared.models import SentinelModel, new_id


class CanonicalCoreError(RuntimeError):
    pass


class CanonicalEffectDispatchError(CanonicalCoreError):
    def __init__(self, *, failure_stage: str, cause: Exception) -> None:
        self.failure_stage = failure_stage
        self.cause = cause
        super().__init__(f"canonical_effect_dispatch_failed:{failure_stage}:{_safe_exception_code(cause)}")


class CanonicalCapabilityQuarantined(CanonicalCoreError):
    def __init__(self, capability: str, operation: str, reason: str) -> None:
        self.capability = capability
        self.operation = operation
        self.reason = reason
        super().__init__(f"canonical_capability_quarantined:{self.affordance}:{reason}")

    @property
    def affordance(self) -> str:
        return f"{self.capability}.{self.operation}"


class DecisionOrigin(StrEnum):
    MODEL_SELECTED = "MODEL_SELECTED"
    HOST_RECOVERY_INJECTED = "HOST_RECOVERY_INJECTED"
    PROGRESS_GUARD_REROUTED = "PROGRESS_GUARD_REROUTED"
    POLICY_REQUIRED = "POLICY_REQUIRED"
    DETERMINISTIC_NORMALIZATION = "DETERMINISTIC_NORMALIZATION"
    USER_SELECTED = "USER_SELECTED"


class DecisionProtocol(StrEnum):
    MODEL_NATIVE_CANONICAL_JSON_V1 = "MODEL_NATIVE_CANONICAL_JSON_V1"
    LEGACY_ACTION_ENVELOPE_ADAPTER_V1 = "LEGACY_ACTION_ENVELOPE_ADAPTER_V1"
    HOST_NATIVE_DECISION_OBJECT_V1 = "HOST_NATIVE_DECISION_OBJECT_V1"


class EffectKind(StrEnum):
    REAL = "REAL"
    SIMULATED = "SIMULATED"
    PROPOSAL = "PROPOSAL"


class RootMissionCancellationToken:
    def __init__(self) -> None:
        self.token_id = new_id("root_mission_cancel")
        self._cancelled = False
        self._reason = ""

    @property
    def safe_ref(self) -> str:
        return f"root_cancel:{stable_hash({'token_id': self.token_id})[:24]}"

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def reason(self) -> str:
        return self._reason

    def cancel(self, reason: str) -> None:
        self._cancelled = True
        self._reason = redact_operator_text(reason) or "operator_revoked"


class CanonicalCapabilityRoute(SentinelModel):
    capability: str
    operation: str
    executor_id: str
    effect_kind: EffectKind
    backend_mode: str
    required_authority: str
    arguments_schema: dict[str, Any] = Field(default_factory=dict)
    preconditions: tuple[str, ...] = Field(default_factory=tuple)
    readiness_probe: str
    materiality_verifier: str
    proof_contract: str
    recovery_policy: str
    cleanup_contract: str
    model_visible: bool = True

    @property
    def affordance(self) -> str:
        return f"{self.capability}.{self.operation}"


class QuarantinedCapability(SentinelModel):
    capability: str
    operation: str
    reason: str
    proof_tier: str
    unblock_requirement: str
    model_visible: bool = False

    @property
    def affordance(self) -> str:
        return f"{self.capability}.{self.operation}"


class ExecutableCapabilityGraph(SentinelModel):
    routes: tuple[CanonicalCapabilityRoute, ...]
    quarantined_capabilities: tuple[QuarantinedCapability, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _routes_are_unique(self) -> "ExecutableCapabilityGraph":
        seen: set[tuple[str, str]] = set()
        for route in self.routes:
            key = (route.capability, route.operation)
            if key in seen:
                raise ValueError(f"duplicate capability route: {route.affordance}")
            seen.add(key)
        for route in self.quarantined_capabilities:
            key = (route.capability, route.operation)
            if key in seen:
                raise ValueError(f"capability cannot be both executable and quarantined: {route.affordance}")
        return self

    def model_visible_affordances(self) -> tuple[str, ...]:
        return tuple(route.affordance for route in self.routes if route.model_visible)

    def model_visible_operation_schemas(self) -> tuple[dict[str, Any], ...]:
        schemas: list[dict[str, Any]] = []
        for route in self.routes:
            if not route.model_visible:
                continue
            schemas.append(
                {
                    "affordance": route.affordance,
                    "capability": route.capability,
                    "operation": route.operation,
                    "arguments_schema": route.arguments_schema,
                    "effect_kind": route.effect_kind.value,
                    "required_authority": route.required_authority,
                    "preconditions": list(route.preconditions),
                    "readiness_probe": route.readiness_probe,
                    "materiality_verifier": route.materiality_verifier,
                    "proof_contract": route.proof_contract,
                }
            )
        return tuple(schemas)

    def resolve(self, capability: str, operation: str) -> CanonicalCapabilityRoute:
        for route in self.routes:
            if route.capability == capability and route.operation == operation:
                return route
        for route in self.quarantined_capabilities:
            if route.capability == capability and route.operation == operation:
                raise CanonicalCapabilityQuarantined(route.capability, route.operation, route.reason)
        raise CanonicalCoreError(f"canonical_capability_route_missing:{capability}.{operation}")

    def quarantined_capability(self, capability: str, operation: str) -> QuarantinedCapability:
        for route in self.quarantined_capabilities:
            if route.capability == capability and route.operation == operation:
                return route
        raise CanonicalCoreError(f"canonical_capability_quarantine_missing:{capability}.{operation}")


class CanonicalBudget(SentinelModel):
    max_provider_decisions: int = 40
    max_material_actions: int = 120
    provider_decisions_reserved_for_finish: int = 6
    budgets_cumulative: bool = True
    budget_reset_on_retry: bool = False


class CanonicalState(SentinelModel):
    root_mission_id: str
    objective: str
    workspace_ref: str
    provider_decision_count: int
    material_action_count: int
    model_visible_affordances: tuple[str, ...]
    model_visible_operation_schemas: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    last_action: str | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    recent_observations: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    action_signatures_attempted: tuple[str, ...] = Field(default_factory=tuple)
    observations_without_novelty: int = 0
    duplicate_no_progress_count: int = 0
    paths_explored: tuple[str, ...] = Field(default_factory=tuple)
    objective_unresolved: bool = True
    finish_available: bool = False
    proof_gaps: tuple[str, ...] = ("external_append_only_signer_missing",)
    remaining_provider_decisions: int
    remaining_material_actions: int
    state_hash: str = ""

    @model_validator(mode="after")
    def _state_is_data_only(self) -> "CanonicalState":
        if not self.state_hash:
            self.state_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "root_mission_id": self.root_mission_id,
            "objective_hash": text_hash(self.objective),
            "workspace_ref": self.workspace_ref,
            "provider_decision_count": self.provider_decision_count,
            "material_action_count": self.material_action_count,
            "model_visible_affordances": list(self.model_visible_affordances),
            "model_visible_operation_schemas": list(self.model_visible_operation_schemas),
            "last_action": self.last_action,
            "evidence_refs": list(self.evidence_refs),
            "recent_observations": [redact_operator_value(item) for item in self.recent_observations],
            "action_signatures_attempted": list(self.action_signatures_attempted),
            "observations_without_novelty": self.observations_without_novelty,
            "duplicate_no_progress_count": self.duplicate_no_progress_count,
            "paths_explored": list(self.paths_explored),
            "objective_unresolved": self.objective_unresolved,
            "finish_available": self.finish_available,
            "proof_gaps": list(self.proof_gaps),
            "remaining_provider_decisions": self.remaining_provider_decisions,
            "remaining_material_actions": self.remaining_material_actions,
        }
        if include_hash:
            payload["state_hash"] = self.state_hash
        return payload


class CanonicalDecisionRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("canonical_decision_request"))
    root_mission_id: str
    provider_model: str
    canonical_state: CanonicalState
    prompt_summary: str
    cancellation_ref: str
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _request_is_data_only(self) -> "CanonicalDecisionRequest":
        assert_data_not_authority(
            context="canonical_decision_request",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class CanonicalDecision(SentinelModel):
    decision_id: str = Field(default_factory=lambda: new_id("canonical_decision"))
    root_mission_id: str
    provider_model: str
    decision_protocol: DecisionProtocol = DecisionProtocol.MODEL_NATIVE_CANONICAL_JSON_V1
    decision_origin: DecisionOrigin
    objective_interpretation: str = ""
    selected_capability: str
    selected_operation: str
    typed_proposed_effect: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    expected_state_delta: str = "unknown"
    evidence_needed: tuple[str, ...] = Field(default_factory=tuple)
    recovery_intent: str = ""
    decision_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _decision_is_data_only(self) -> "CanonicalDecision":
        assert_data_not_authority(
            context="canonical_decision",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.decision_hash:
            self.decision_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    @property
    def capability(self) -> str:
        return self.selected_capability

    @property
    def operation(self) -> str:
        return self.selected_operation

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "decision_id": self.decision_id,
            "root_mission_id": self.root_mission_id,
            "provider_model": redact_operator_text(self.provider_model),
            "decision_protocol": self.decision_protocol.value,
            "decision_origin": self.decision_origin.value,
            "objective_interpretation_hash": text_hash(self.objective_interpretation),
            "selected_capability": redact_operator_text(self.selected_capability),
            "selected_operation": redact_operator_text(self.selected_operation),
            "typed_proposed_effect": redact_operator_text(self.typed_proposed_effect),
            "arguments": redact_operator_value(self.arguments),
            "expected_state_delta": redact_operator_text(self.expected_state_delta),
            "evidence_needed": [redact_operator_text(item) for item in self.evidence_needed],
            "recovery_intent": redact_operator_text(self.recovery_intent),
        }
        if include_hash:
            payload["decision_hash"] = self.decision_hash
        return payload


class CanonicalEffectReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("canonical_effect_receipt"))
    root_mission_id: str
    decision_id: str
    capability: str
    operation: str
    effect_kind: EffectKind
    backend_mode: str
    status: str
    material_action: bool
    safe_summary: str
    safe_observation: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    before_state_hash: str
    after_state_hash: str
    receipt_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data_only(self) -> "CanonicalEffectReceipt":
        assert_data_not_authority(
            context="canonical_effect_receipt",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.receipt_hash:
            self.receipt_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "receipt_id": self.receipt_id,
            "root_mission_id": self.root_mission_id,
            "decision_id": self.decision_id,
            "capability": redact_operator_text(self.capability),
            "operation": redact_operator_text(self.operation),
            "effect_kind": self.effect_kind.value,
            "backend_mode": redact_operator_text(self.backend_mode),
            "status": redact_operator_text(self.status),
            "material_action": self.material_action,
            "safe_summary": redact_operator_text(self.safe_summary),
            "safe_observation": redact_operator_value(self.safe_observation),
            "evidence_refs": list(self.evidence_refs),
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "created_at": self.created_at.isoformat(),
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


class MissionProofRoot(SentinelModel):
    proof_root_id: str = Field(default_factory=lambda: new_id("mission_proof_root"))
    root_mission_id: str
    receipt_refs: tuple[str, ...]
    decision_refs: tuple[str, ...]
    integrity_model: str = "non_authentic_placeholder"
    authentic_external_ledger: bool = False
    proof_gaps: tuple[str, ...] = ("external_append_only_signer_missing",)
    record_hash_verified: bool = False
    kernel_timeline_verified: bool = False
    receipt_artifact_refs: tuple[str, ...] = Field(default_factory=tuple)
    receipt_artifacts_verified: bool = False
    proof_artifact_ref: str = ""
    proof_root_hash: str = ""

    @model_validator(mode="after")
    def _proof_root_hashes(self) -> "MissionProofRoot":
        if not self.proof_root_hash:
            self.proof_root_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "proof_root_id": self.proof_root_id,
            "root_mission_id": self.root_mission_id,
            "receipt_refs": list(self.receipt_refs),
            "decision_refs": list(self.decision_refs),
            "integrity_model": self.integrity_model,
            "authentic_external_ledger": self.authentic_external_ledger,
            "proof_gaps": list(self.proof_gaps),
            "record_hash_verified": self.record_hash_verified,
            "kernel_timeline_verified": self.kernel_timeline_verified,
            "receipt_artifact_refs": list(self.receipt_artifact_refs),
            "receipt_artifacts_verified": self.receipt_artifacts_verified,
            "proof_artifact_ref": self.proof_artifact_ref,
        }
        if include_hash:
            payload["proof_root_hash"] = self.proof_root_hash
        return payload


class CanonicalDevMissionResult(SentinelModel):
    root_mission_id: str
    status: str
    final_reason: str
    provider_model: str
    provider_decision_count: int
    material_action_count: int
    root_created_before_first_provider_call: bool
    mission_record_created_before_provider: bool = False
    decisions: tuple[CanonicalDecision, ...] = Field(default_factory=tuple)
    receipts: tuple[CanonicalEffectReceipt, ...] = Field(default_factory=tuple)
    proof_root: MissionProofRoot
    cleanup_completed: bool
    final_answer: str = ""
    cancellation_reason: str = ""
    blocked_capability: str = ""
    blocked_reason_detail: str = ""


class CanonicalModelClient(Protocol):
    def complete(self, request: CanonicalDecisionRequest) -> Any:
        ...


def build_workspace_read_capability_graph() -> ExecutableCapabilityGraph:
    return ExecutableCapabilityGraph(
        routes=(
            _workspace_route("list", materiality_verifier="workspace_directory_observed"),
            _workspace_route("read", materiality_verifier="workspace_path_observed"),
            _workspace_route("search", materiality_verifier="workspace_search_matches_observed"),
            CanonicalCapabilityRoute(
                capability="sentinel_loop",
                operation="finish",
                executor_id="sentinel_loop.finish",
                effect_kind=EffectKind.PROPOSAL,
                backend_mode="host_terminal_decision",
                required_authority="none",
                arguments_schema={
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "safe_summary": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                preconditions=("receipt_or_honest_blocker_exists",),
                readiness_probe="always_available",
                materiality_verifier="terminal_payload_present",
                proof_contract="canonical_core_terminal_truth_v1",
                recovery_policy="block_if_no_prior_receipt",
                cleanup_contract="root_resource_scope_close",
            ),
        ),
        quarantined_capabilities=(
            QuarantinedCapability(
                capability="code_execution_sandbox",
                operation="code_exec.run_profile",
                reason="physical_sandbox_not_proven",
                proof_tier="P0_REPRODUCED_LOCAL",
                unblock_requirement="real_process_or_container_sandbox_denies_outside_workspace_read_write_network_credentials",
            ),
        )
    )


def run_canonical_dev_mission(
    *,
    objective: str,
    workspace_root: Path | str,
    model_client: CanonicalModelClient | None,
    provider_model: str,
    max_provider_decisions: int = 40,
    max_material_actions: int = 120,
    provider_decisions_reserved_for_finish: int = 6,
    cancellation_token: RootMissionCancellationToken | None = None,
    granted_authorities: tuple[str, ...] = ("workspace_read", "none"),
) -> CanonicalDevMissionResult:
    runtime = RootMissionRuntime(
        objective=objective,
        workspace_root=workspace_root,
        provider_model=provider_model,
        max_provider_decisions=max_provider_decisions,
        max_material_actions=max_material_actions,
        provider_decisions_reserved_for_finish=provider_decisions_reserved_for_finish,
        cancellation_token=cancellation_token,
        granted_authorities=granted_authorities,
        allow_legacy_action_envelope=True,
    )
    return runtime.run(model_client=model_client)


def run_canonical_product_mission(
    *,
    objective: str,
    workspace_root: Path | str,
    model_client: CanonicalModelClient | None,
    provider_model: str,
    kernel: MissionKernel,
    session_id: str,
    max_provider_decisions: int = 40,
    max_material_actions: int = 120,
    provider_decisions_reserved_for_finish: int = 6,
    cancellation_token: RootMissionCancellationToken | None = None,
    granted_authorities: tuple[str, ...] = ("workspace_read", "none"),
) -> CanonicalDevMissionResult:
    runtime = RootMissionRuntime(
        objective=objective,
        workspace_root=workspace_root,
        provider_model=provider_model,
        max_provider_decisions=max_provider_decisions,
        max_material_actions=max_material_actions,
        provider_decisions_reserved_for_finish=provider_decisions_reserved_for_finish,
        cancellation_token=cancellation_token,
        kernel=kernel,
        session_id=session_id,
        granted_authorities=granted_authorities,
        allow_legacy_action_envelope=False,
    )
    return runtime.run(model_client=model_client)


class RootMissionRuntime:
    def __init__(
        self,
        *,
        objective: str,
        workspace_root: Path | str,
        provider_model: str,
        max_provider_decisions: int = 40,
        max_material_actions: int = 120,
        provider_decisions_reserved_for_finish: int = 6,
        capability_graph: ExecutableCapabilityGraph | None = None,
        cancellation_token: RootMissionCancellationToken | None = None,
        kernel: MissionKernel | None = None,
        session_id: str = "canonical_core_dev_session",
        granted_authorities: tuple[str, ...] = ("workspace_read", "none"),
        allow_legacy_action_envelope: bool = False,
    ) -> None:
        self.root_mission_id = new_id("root_mission")
        self.objective = objective
        self.workspace_root = Path(workspace_root).resolve()
        self.provider_model = provider_model
        self.budget = CanonicalBudget(
            max_provider_decisions=max_provider_decisions,
            max_material_actions=max_material_actions,
            provider_decisions_reserved_for_finish=provider_decisions_reserved_for_finish,
        )
        self.capability_graph = capability_graph or build_workspace_read_capability_graph()
        self.cancellation_token = cancellation_token or RootMissionCancellationToken()
        self.kernel = kernel
        self.session_id = session_id
        self.granted_authorities = frozenset(granted_authorities)
        self.allow_legacy_action_envelope = allow_legacy_action_envelope
        self._workspace_backend = WorkspaceReadOnlyRuntime(workspace_root=self.workspace_root)
        self._product_action_kernel = ActionKernel({"workspace": self._execute_workspace_backend})
        self.decisions: list[CanonicalDecision] = []
        self.receipts: list[CanonicalEffectReceipt] = []
        self.evidence_refs: list[str] = []
        self.recent_observations: list[dict[str, Any]] = []
        self.last_action: str | None = None
        self.action_signatures_attempted: list[str] = []
        self._action_signature_counts: dict[str, int] = {}
        self.observations_without_novelty = 0
        self.duplicate_no_progress_count = 0
        self.paths_explored: list[str] = []
        self.provider_decision_count = 0
        self.material_action_count = 0
        self.root_created_at = datetime.now(UTC)
        self.mission_record_created_before_provider = False
        self._precondition_blocker = ""
        self._closed = False
        if self.kernel is not None:
            self._create_and_start_mission_record()

    def run(self, *, model_client: CanonicalModelClient | None) -> CanonicalDevMissionResult:
        if model_client is None:
            if self.kernel is not None:
                exc = CanonicalCoreError("canonical_model_client_required")
                self._persist_model_decision_failure(exc)
                return self._terminal_result(
                    status="blocked",
                    reason="MODEL_DECISION_FAILED",
                    blocked_reason_detail=_safe_exception_code(exc),
                )
            raise CanonicalCoreError("canonical_model_client_required")
        try:
            while True:
                if self._precondition_blocker:
                    return self._terminal_result(
                        status="blocked",
                        reason="MISSION_PRECONDITION_FAILED",
                        blocked_reason_detail=self._precondition_blocker,
                    )
                if self.cancellation_token.cancelled:
                    return self._terminal_result(
                        status="blocked",
                        reason="ROOT_MISSION_CANCELLED",
                        cancellation_reason=self.cancellation_token.reason,
                    )
                if self.provider_decision_count >= self.budget.max_provider_decisions:
                    return self._terminal_result(status="blocked", reason="PROVIDER_DECISION_BUDGET_EXHAUSTED")
                state = self.compile_state()
                request = CanonicalDecisionRequest(
                    root_mission_id=self.root_mission_id,
                    provider_model=self.provider_model,
                    canonical_state=state,
                    prompt_summary="canonical_dev_mission_next_decision",
                    cancellation_ref=self.cancellation_token.safe_ref,
                )
                self.provider_decision_count += 1
                try:
                    raw_decision = model_client.complete(request)
                except Exception as exc:
                    if self.kernel is None:
                        raise
                    self._persist_model_decision_failure(exc)
                    return self._terminal_result(
                        status="blocked",
                        reason="MODEL_DECISION_FAILED",
                        blocked_reason_detail=_safe_exception_code(exc),
                    )
                if self.cancellation_token.cancelled:
                    return self._terminal_result(
                        status="blocked",
                        reason="ROOT_MISSION_CANCELLED",
                        cancellation_reason=self.cancellation_token.reason,
                    )
                try:
                    decision = self._normalize_decision(raw_decision)
                except CanonicalCapabilityQuarantined as exc:
                    return self._terminal_result(
                        status="blocked",
                        reason="CAPABILITY_QUARANTINED",
                        blocked_capability=exc.affordance,
                        blocked_reason_detail=exc.reason,
                    )
                except Exception as exc:
                    if self.kernel is None:
                        raise
                    self._persist_model_decision_failure(exc)
                    return self._terminal_result(
                        status="blocked",
                        reason="MODEL_DECISION_FAILED",
                        blocked_reason_detail=_safe_exception_code(exc),
                    )
                self.decisions.append(decision)
                try:
                    self._persist_decision(decision)
                except Exception as exc:
                    if self.kernel is None:
                        raise
                    self._persist_effect_failure(exc, failure_stage="decision_persistence")
                    return self._terminal_result(
                        status="blocked",
                        reason="EFFECT_DISPATCH_FAILED",
                        blocked_reason_detail=_safe_exception_code(exc),
                    )
                if decision.capability == "sentinel_loop" and decision.operation == "finish":
                    route = self.capability_graph.resolve(decision.capability, decision.operation)
                    try:
                        self._assert_route_authorized(route)
                    except Exception as exc:
                        if self.kernel is None:
                            raise
                        self._persist_effect_failure(exc, failure_stage="authority_gate")
                        return self._terminal_result(
                            status="blocked",
                            reason="EFFECT_DISPATCH_FAILED",
                            blocked_reason_detail=_safe_exception_code(exc),
                        )
                    if not self.receipts:
                        return self._terminal_result(status="blocked", reason="MODEL_FINISH_BEFORE_RECEIPT")
                    return self._terminal_result(
                        status="completed",
                        reason="model_selected_finish",
                        final_answer=str(decision.arguments.get("answer") or decision.arguments.get("safe_summary") or ""),
                    )
                if self.material_action_count >= self.budget.max_material_actions:
                    return self._terminal_result(status="blocked", reason="MATERIAL_ACTION_BUDGET_EXHAUSTED")
                try:
                    receipt = self._dispatch_effect(decision, before_state=state)
                except Exception as exc:
                    if self.kernel is None:
                        raise
                    self._persist_effect_failure(exc)
                    return self._terminal_result(
                        status="blocked",
                        reason="EFFECT_DISPATCH_FAILED",
                        blocked_reason_detail=_safe_exception_code(exc),
                    )
                self.receipts.append(receipt)
                self.evidence_refs.extend(receipt.evidence_refs)
                self.recent_observations.append(receipt.safe_observation)
                self.last_action = f"{decision.capability}.{decision.operation}"
                self.material_action_count += 1
        finally:
            self.close()

    def compile_state(self) -> CanonicalState:
        return CanonicalState(
            root_mission_id=self.root_mission_id,
            objective=self.objective,
            workspace_ref=_workspace_ref(self.workspace_root),
            provider_decision_count=self.provider_decision_count,
            material_action_count=self.material_action_count,
            model_visible_affordances=self.capability_graph.model_visible_affordances(),
            model_visible_operation_schemas=self.capability_graph.model_visible_operation_schemas(),
            last_action=self.last_action,
            evidence_refs=tuple(dict.fromkeys(self.evidence_refs)),
            recent_observations=tuple(self.recent_observations[-4:]),
            action_signatures_attempted=tuple(dict.fromkeys(self.action_signatures_attempted)),
            observations_without_novelty=self.observations_without_novelty,
            duplicate_no_progress_count=self.duplicate_no_progress_count,
            paths_explored=tuple(dict.fromkeys(self.paths_explored)),
            objective_unresolved=not self._finish_available(),
            finish_available=self._finish_available(),
            remaining_provider_decisions=max(0, self.budget.max_provider_decisions - self.provider_decision_count),
            remaining_material_actions=max(0, self.budget.max_material_actions - self.material_action_count),
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.kernel is not None:
            try:
                self.kernel.store.append_event(
                    self.root_mission_id,
                    event_type="canonical_cleanup_completed",
                    safe_summary="Canonical root mission cleanup completed.",
                    metadata={"cleanup_completed": True},
                )
            except Exception:
                return

    def workspace_capability_owner(self, route: CanonicalCapabilityRoute) -> str:
        if route.capability == "workspace":
            return "ProductActionKernel:workspace"
        if route.capability == "sentinel_loop":
            return "RootMissionRuntime:terminal_decision"
        return "UNKNOWN"

    def _normalize_decision(self, raw: Any) -> CanonicalDecision:
        if isinstance(raw, CanonicalDecision):
            return raw
        if isinstance(raw, ActionEnvelope):
            if not self.allow_legacy_action_envelope:
                raise CanonicalCoreError("legacy_action_envelope_not_allowed_on_public_canonical_route")
            route = self.capability_graph.resolve(raw.capability_id, raw.operation)
            arguments = dict(raw.params)
            if raw.target_ref is not None and "target_ref" not in arguments:
                arguments["target_ref"] = raw.target_ref
            return CanonicalDecision(
                root_mission_id=self.root_mission_id,
                provider_model=self.provider_model,
                decision_protocol=DecisionProtocol.LEGACY_ACTION_ENVELOPE_ADAPTER_V1,
                decision_origin=DecisionOrigin.MODEL_SELECTED,
                selected_capability=route.capability,
                selected_operation=route.operation,
                typed_proposed_effect=route.effect_kind.value,
                arguments=redact_operator_value(arguments),
                expected_state_delta="unknown",
            )
        if not isinstance(raw, dict):
            raise CanonicalCoreError("canonical_model_decision_payload_required")
        assert_data_not_authority(
            context="canonical_model_decision_payload",
            authority_effect=str(raw.get("authority_effect", "none")),
            data_not_authority=raw.get("data_not_authority", True) is True,
            can_grant_authority=bool(raw.get("can_grant_authority", False)),
            can_execute=bool(raw.get("can_execute", False)),
        )
        capability = str(raw.get("capability") or raw.get("skill") or "").strip()
        operation = str(raw.get("operation") or "").strip()
        route = self._resolve_model_decision_route(capability=capability, operation=operation)
        if route is None:
            raise CanonicalCoreError("canonical_model_decision_capability_operation_required")
        arguments = raw.get("arguments", raw.get("params", {}))
        if not isinstance(arguments, dict):
            raise CanonicalCoreError("canonical_model_decision_arguments_must_be_object")
        return CanonicalDecision(
            root_mission_id=self.root_mission_id,
            provider_model=self.provider_model,
            decision_protocol=DecisionProtocol.MODEL_NATIVE_CANONICAL_JSON_V1,
            decision_origin=DecisionOrigin.MODEL_SELECTED,
            objective_interpretation=str(raw.get("objective_interpretation") or ""),
            selected_capability=route.capability,
            selected_operation=route.operation,
            typed_proposed_effect=route.effect_kind.value,
            arguments=redact_operator_value(arguments),
            expected_state_delta=str(raw.get("expected_state_delta") or "unknown"),
            evidence_needed=tuple(str(item) for item in raw.get("evidence_needed", ()) if str(item).strip()),
            recovery_intent=str(raw.get("recovery_intent") or ""),
        )

    def _resolve_model_decision_route(
        self,
        *,
        capability: str,
        operation: str,
    ) -> CanonicalCapabilityRoute | None:
        if capability and operation:
            return self.capability_graph.resolve(capability, operation)
        if not operation:
            return None
        affordance_matches = [route for route in self.capability_graph.routes if route.affordance == operation]
        if len(affordance_matches) == 1:
            return affordance_matches[0]
        operation_matches = [
            route
            for route in self.capability_graph.routes
            if route.model_visible and route.operation == operation
        ]
        if len(operation_matches) == 1:
            return operation_matches[0]
        return None

    def _dispatch_effect(self, decision: CanonicalDecision, *, before_state: CanonicalState) -> CanonicalEffectReceipt:
        route = self.capability_graph.resolve(decision.capability, decision.operation)
        self._assert_route_authorized(route)
        action_signature = _action_signature(decision)
        try:
            action_result = self._execute_product_kernel_action(route=route, decision=decision)
        except Exception as exc:
            raise CanonicalEffectDispatchError(failure_stage="product_action_kernel_dispatch", cause=exc) from exc
        status = action_result.status
        observation = self._observation_from_action_result(action_result)
        summary = action_result.observation_summary
        observation = self._annotate_progress(
            decision=decision,
            observation=observation,
            action_signature=action_signature,
        )
        evidence_ref = f"evidence:{str(observation.get('observation_fingerprint') or stable_hash(observation))[:24]}"
        after_state_hash = stable_hash(
            {
                "before_state_hash": before_state.state_hash,
                "decision_hash": decision.decision_hash,
                "observation_hash": stable_hash(observation),
                "receipt_index": len(self.receipts),
            }
        )
        receipt = CanonicalEffectReceipt(
            root_mission_id=self.root_mission_id,
            decision_id=decision.decision_id,
            capability=route.capability,
            operation=route.operation,
            effect_kind=route.effect_kind,
            backend_mode=route.backend_mode,
            status=status,
            material_action=action_result.material_action,
            safe_summary=summary,
            safe_observation=observation,
            evidence_refs=tuple(dict.fromkeys([evidence_ref, *action_result.evidence_refs])),
            before_state_hash=before_state.state_hash,
            after_state_hash=after_state_hash,
        )
        try:
            self._persist_receipt(receipt)
        except Exception as exc:
            raise CanonicalEffectDispatchError(failure_stage="receipt_persistence", cause=exc) from exc
        self._record_progress(
            observation=observation,
            evidence_ref=evidence_ref,
            action_signature=action_signature,
        )
        return receipt

    def _execute_product_kernel_action(
        self,
        *,
        route: CanonicalCapabilityRoute,
        decision: CanonicalDecision,
    ) -> ActionResult:
        if route.capability != "workspace":
            raise CanonicalCoreError(f"canonical_product_kernel_capability_missing:{route.affordance}")
        envelope = self._action_envelope_for_decision(route=route, decision=decision)
        return self._product_action_kernel.execute(
            envelope,
            authority=self._mission_authority_envelope(),
            context={
                "root_mission_id": self.root_mission_id,
                "decision_id": decision.decision_id,
                "canonical_route": route.model_dump(mode="json"),
                "decision_origin": decision.decision_origin.value,
                "canonical_public_route": True,
            },
        )

    def _execute_workspace_backend(self, envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        return self._workspace_backend.execute(
            envelope,
            authority=self._mission_authority_envelope(),
            context=context,
        )

    def _action_envelope_for_decision(
        self,
        *,
        route: CanonicalCapabilityRoute,
        decision: CanonicalDecision,
    ) -> ActionEnvelope:
        return ActionEnvelope(
            capability_id=route.capability,
            operation=route.operation,
            params=redact_operator_value(decision.arguments),
            idempotency_key=stable_hash(
                {
                    "root_mission_id": self.root_mission_id,
                    "decision_id": decision.decision_id,
                    "affordance": route.affordance,
                    "arguments": redact_operator_value(decision.arguments),
                }
            ),
            authority_ref=f"root_authority:{stable_hash(sorted(self.granted_authorities))[:24]}",
            decision_ref=decision.decision_id,
            expected_receipt_type=route.proof_contract,
        )

    def _mission_authority_envelope(self) -> MissionAuthorityEnvelope:
        return MissionAuthorityEnvelope(
            user_id="sentinel_canonical_core",
            mission_title="Canonical product workspace mission",
            mission_objective=self.objective,
            allowed_tools=["workspace"],
            allowed_actions=list(self.capability_graph.model_visible_affordances()),
            forbidden_actions=[
                "provider_native_tools",
                "authority_self_grant",
                "workspace_escape",
                "raw_secret_exposure",
            ],
            allowed_paths=[str(self.workspace_root)],
            max_actions=max(1, self.budget.max_material_actions),
        )

    def _observation_from_action_result(self, action_result: ActionResult) -> dict[str, Any]:
        observation = action_result.context_cards.get("workspace_readonly_observation")
        if not isinstance(observation, dict):
            observation = {
                "action_result_status": action_result.status,
                "observation_summary": action_result.observation_summary,
            }
        safe_observation = _restore_workspace_observation_types(dict(redact_operator_value(observation)))
        safe_observation.update(
            {
                "product_action_kernel_dispatch": True,
                "product_action_result_hash": action_result.result_hash,
                "product_action_receipt_refs": tuple(action_result.receipt_refs),
                "product_action_evidence_refs": tuple(action_result.evidence_refs),
            }
        )
        return safe_observation

    def _assert_route_authorized(self, route: CanonicalCapabilityRoute) -> None:
        if route.required_authority == "none":
            return
        if route.required_authority in self.granted_authorities:
            return
        raise CanonicalCoreError(f"canonical_authority_required:{route.required_authority}")

    def _finish(self, arguments: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        answer = redact_operator_text(str(arguments.get("answer") or arguments.get("safe_summary") or ""))
        return "completed", {"terminal_answer_hash": text_hash(answer)}, "canonical finish proposed."

    def _annotate_progress(
        self,
        *,
        decision: CanonicalDecision,
        observation: dict[str, Any],
        action_signature: str,
    ) -> dict[str, Any]:
        safe_observation = dict(observation)
        observed_paths = _observation_paths(safe_observation)
        new_paths = tuple(path for path in observed_paths if path not in set(self.paths_explored))
        signature_seen = self._action_signature_counts.get(action_signature, 0)
        evidence_fingerprint = stable_hash(_progress_fingerprint_payload(safe_observation))
        evidence_seen = f"evidence:{evidence_fingerprint[:24]}" in set(self.evidence_refs)
        has_match_progress = bool(new_paths)
        no_progress = signature_seen > 0 and evidence_seen and not has_match_progress
        if no_progress:
            classification = "NO_PROGRESS"
        elif has_match_progress:
            classification = "MATERIAL_PROGRESS"
        else:
            classification = "OBSERVATION_ONLY"
        safe_observation.update(
            {
                "progress_classification": classification,
                "observation_fingerprint": evidence_fingerprint,
                "action_signature": action_signature,
                "action_signature_seen_before": signature_seen,
                "new_paths": new_paths,
                "evidence_delta": not evidence_seen,
                "objective_progress": classification == "MATERIAL_PROGRESS",
                "decision_origin": decision.decision_origin.value,
            }
        )
        if no_progress:
            safe_observation["typed_observation"] = "NO_PROGRESS"
            safe_observation["replan_required"] = True
        return safe_observation

    def _record_progress(
        self,
        *,
        observation: dict[str, Any],
        evidence_ref: str,
        action_signature: str,
    ) -> None:
        self.action_signatures_attempted.append(action_signature)
        self._action_signature_counts[action_signature] = self._action_signature_counts.get(action_signature, 0) + 1
        for path in _observation_paths(observation):
            if path not in self.paths_explored:
                self.paths_explored.append(path)
        if observation.get("progress_classification") == "NO_PROGRESS":
            self.observations_without_novelty += 1
            self.duplicate_no_progress_count += 1

    def _finish_available(self) -> bool:
        return bool(self.paths_explored)

    def _result(
        self,
        *,
        status: str,
        reason: str,
        final_answer: str = "",
        cancellation_reason: str = "",
        blocked_capability: str = "",
        blocked_reason_detail: str = "",
    ) -> CanonicalDevMissionResult:
        proof = self._build_and_persist_proof_root()
        return CanonicalDevMissionResult(
            root_mission_id=self.root_mission_id,
            status=status,
            final_reason=reason,
            provider_model=redact_operator_text(self.provider_model),
            provider_decision_count=self.provider_decision_count,
            material_action_count=self.material_action_count,
            root_created_before_first_provider_call=bool(self.root_created_at),
            mission_record_created_before_provider=self.mission_record_created_before_provider,
            decisions=tuple(self.decisions),
            receipts=tuple(self.receipts),
            proof_root=proof,
            cleanup_completed=self._closed,
            final_answer=redact_operator_text(final_answer),
            cancellation_reason=redact_operator_text(cancellation_reason),
            blocked_capability=redact_operator_text(blocked_capability),
            blocked_reason_detail=redact_operator_text(blocked_reason_detail),
        )

    def _terminal_result(
        self,
        *,
        status: str,
        reason: str,
        final_answer: str = "",
        cancellation_reason: str = "",
        blocked_capability: str = "",
        blocked_reason_detail: str = "",
    ) -> CanonicalDevMissionResult:
        try:
            self._persist_terminal_status(status=status, reason=reason)
        except Exception:
            pass
        self.close()
        return self._result(
            status=status,
            reason=reason,
            final_answer=final_answer,
            cancellation_reason=cancellation_reason,
            blocked_capability=blocked_capability,
            blocked_reason_detail=blocked_reason_detail,
        )

    def _create_and_start_mission_record(self) -> None:
        assert self.kernel is not None
        draft = MissionDraft(
            title="Canonical core product workspace mission",
            objective=self.objective,
            constraints=["public product route", "read-only workspace authority"],
            expected_artifacts=["canonical receipts", "mission proof root", "terminal mission state"],
        )
        authority = MissionAuthoritySummary(
            mission_id=self.root_mission_id,
            allowed_actions=list(self.capability_graph.model_visible_affordances()),
            forbidden_actions=[
                "provider_native_tools",
                "authority_self_grant",
                "workspace_escape",
                "raw_secret_exposure",
            ],
            summary="Canonical product mission authority: read-only workspace effects and terminal finish only.",
            user_confirmation_required=False,
            finalgate_required=True,
        )
        self.kernel.create_mission(
            session_id=self.session_id,
            draft=draft,
            authority_summary=authority,
            mission_id=self.root_mission_id,
        )
        self.kernel.enqueue(
            self.root_mission_id,
            metadata={"canonical_product_route": True, "provider_decision_count": 0},
        )
        self.kernel.update_status(
            self.root_mission_id,
            OperatorMissionStatus.RUNNING,
            "Canonical root mission running before first provider decision.",
        )
        self._record_workspace_preconditions()
        self.mission_record_created_before_provider = self.kernel.store.verify_record(self.root_mission_id)

    def _record_workspace_preconditions(self) -> None:
        if self.kernel is None:
            return
        objective_terms = _normalized_search_terms(self.objective)
        north_star_requested = {"north", "star"}.issubset(set(objective_terms)) or {
            "cognitive",
            "os",
        }.issubset(set(objective_terms))
        if not north_star_requested:
            return
        candidates = [
            path
            for path in sorted(self.workspace_root.rglob("*"), key=lambda item: str(item).lower())
            if path.is_file() and "north_star" in path.name.lower()
        ]
        for path in candidates:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved != self.workspace_root and self.workspace_root not in resolved.parents:
                continue
            relative = _relative_workspace_path(self.workspace_root, resolved)
            try:
                digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            except OSError:
                continue
            observation = {
                "precondition": "known_document_present",
                "relative_path": relative,
                "sha256": digest,
            }
            self.recent_observations.append(observation)
            self.kernel.store.append_event(
                self.root_mission_id,
                event_type="canonical_workspace_precondition_verified",
                safe_summary="Canonical workspace precondition verified for a known public document.",
                metadata=observation,
            )
            return
        self._precondition_blocker = "known_north_star_document_missing"
        self.kernel.store.append_event(
            self.root_mission_id,
            event_type="canonical_workspace_precondition_failed",
            safe_summary="Canonical workspace precondition failed before provider decision.",
            metadata={"precondition": "known_document_present", "missing": "north_star_document"},
        )

    def _persist_decision(self, decision: CanonicalDecision) -> None:
        if self.kernel is None:
            return
        self.kernel.store.append_event(
            self.root_mission_id,
            event_type="canonical_decision_accepted",
            safe_summary=f"Canonical decision accepted for {decision.capability}.{decision.operation}.",
            metadata=decision.safe_model_dump(),
        )

    def _persist_model_decision_failure(self, exc: Exception) -> None:
        if self.kernel is None:
            return
        self.kernel.store.append_event(
            self.root_mission_id,
            event_type="canonical_model_decision_failed",
            safe_summary="Canonical model decision failed before executable dispatch.",
            metadata={
                "failure_stage": "provider_or_decision_normalization",
                "failure_code": _safe_exception_code(exc),
                "exception_class": exc.__class__.__name__,
                "exception_hash": stable_hash(
                    {
                        "exception_class": exc.__class__.__name__,
                        "safe_message": redact_operator_text(str(exc)),
                    }
                ),
                "provider_decision_count": self.provider_decision_count,
                "material_action_count": self.material_action_count,
            },
        )

    def _persist_effect_failure(self, exc: Exception, *, failure_stage: str | None = None) -> None:
        if self.kernel is None:
            return
        stage = failure_stage
        cause: Exception = exc
        if isinstance(exc, CanonicalEffectDispatchError):
            stage = exc.failure_stage
            cause = exc.cause
        if stage is None:
            stage = "dispatch_or_workspace_effect"
        try:
            self.kernel.store.append_event(
                self.root_mission_id,
                event_type="canonical_effect_failed",
                safe_summary="Canonical effect failed before a terminal receipt could be persisted.",
                metadata={
                    "failure_stage": stage,
                    "failure_code": _safe_exception_code(cause),
                    "exception_class": cause.__class__.__name__,
                    "exception_hash": stable_hash(
                        {
                            "exception_class": cause.__class__.__name__,
                            "safe_message": redact_operator_text(str(cause)),
                        }
                    ),
                    "provider_decision_count": self.provider_decision_count,
                    "material_action_count": self.material_action_count,
                },
            )
        except Exception:
            return

    def _persist_receipt(self, receipt: CanonicalEffectReceipt) -> None:
        if self.kernel is None:
            return
        receipt_dir = self.kernel.store.mission_dir(self.root_mission_id, create=True) / "canonical_receipts"
        receipt_path = receipt_dir / f"{receipt.receipt_id}.json"
        self.kernel.store.atomic_write_json(receipt_path, receipt.safe_model_dump())
        self._attach_receipt_ref(receipt.receipt_id)
        self.kernel.store.append_event(
            self.root_mission_id,
            event_type="canonical_effect_receipt_persisted",
            safe_summary=f"Canonical effect receipt persisted for {receipt.capability}.{receipt.operation}.",
            metadata={
                "receipt_hash": receipt.receipt_hash,
                "status": receipt.status,
                "before_state_hash": receipt.before_state_hash,
                "after_state_hash": receipt.after_state_hash,
                "effect_kind": receipt.effect_kind.value,
            },
            receipt_refs=[receipt.receipt_id],
        )

    def _attach_receipt_ref(self, receipt_id: str) -> None:
        if self.kernel is None:
            return
        with self.kernel.store.locked():
            record = self.kernel.store.load_record(self.root_mission_id)
            refs = list(dict.fromkeys([*record.receipt_refs, receipt_id]))
            updated = record.model_copy(update={"receipt_refs": refs, "updated_at": datetime.now(UTC)}).with_hash()
            self.kernel.store._write_record(updated)

    def _persist_terminal_status(self, *, status: str, reason: str) -> None:
        if self.kernel is None:
            return
        target = {
            "completed": OperatorMissionStatus.COMPLETED,
            "blocked": OperatorMissionStatus.BLOCKED,
            "failed": OperatorMissionStatus.FAILED,
        }.get(status, OperatorMissionStatus.FAILED)
        self.kernel.update_status(
            self.root_mission_id,
            target,
            f"Canonical root mission terminal state: {redact_operator_text(reason)}.",
        )

    def _build_and_persist_proof_root(self) -> MissionProofRoot:
        if self.kernel is None:
            return MissionProofRoot(
                root_mission_id=self.root_mission_id,
                receipt_refs=tuple(receipt.receipt_id for receipt in self.receipts),
                decision_refs=tuple(decision.decision_id for decision in self.decisions),
            )
        receipt_refs = tuple(receipt.receipt_id for receipt in self.receipts)
        receipt_artifact_refs = tuple(f"canonical_receipts/{receipt_id}.json" for receipt_id in receipt_refs)
        proof = MissionProofRoot(
            root_mission_id=self.root_mission_id,
            receipt_refs=receipt_refs,
            decision_refs=tuple(decision.decision_id for decision in self.decisions),
            integrity_model="mission_kernel_receipt_timeline_v1",
            authentic_external_ledger=False,
            proof_gaps=("external_append_only_signer_missing",),
            record_hash_verified=self.kernel.store.verify_record(self.root_mission_id),
            kernel_timeline_verified=self.kernel.store.verify_timeline(self.root_mission_id),
            receipt_artifact_refs=receipt_artifact_refs,
            receipt_artifacts_verified=self._receipt_artifacts_verified(receipt_refs),
            proof_artifact_ref="mission_proof_root.json",
        )
        try:
            self.kernel.store.atomic_write_json(
                self.kernel.store.mission_dir(self.root_mission_id, create=True) / "mission_proof_root.json",
                proof.safe_model_dump(),
            )
        except Exception:
            proof = proof.model_copy(
                update={
                    "proof_gaps": tuple(
                        dict.fromkeys([*proof.proof_gaps, "proof_root_persistence_failed"])
                    ),
                    "proof_artifact_ref": "",
                }
            )
        return proof

    def _receipt_artifacts_verified(self, receipt_refs: tuple[str, ...]) -> bool:
        if self.kernel is None:
            return False
        receipt_dir = self.kernel.store.mission_dir(self.root_mission_id) / "canonical_receipts"
        try:
            record = self.kernel.store.load_record(self.root_mission_id)
            events = self.kernel.store.load_events(self.root_mission_id)
        except Exception:
            return False
        record_refs = set(record.receipt_refs)
        timeline_refs = {ref for event in events for ref in event.receipt_refs}
        known_decision_ids = {decision.decision_id for decision in self.decisions}
        for receipt_id in receipt_refs:
            if receipt_id not in record_refs or receipt_id not in timeline_refs:
                return False
            receipt_path = receipt_dir / f"{receipt_id}.json"
            if not _path_exists(receipt_path):
                return False
            try:
                with open(_filesystem_path(receipt_path), encoding="utf-8") as handle:
                    payload = json.load(handle)
            except Exception:
                return False
            if payload.get("receipt_id") != receipt_id:
                return False
            if payload.get("root_mission_id") != self.root_mission_id:
                return False
            decision_id = str(payload.get("decision_id") or "")
            if not decision_id:
                return False
            if known_decision_ids and decision_id not in known_decision_ids:
                return False
            stored_hash = payload.get("receipt_hash")
            if not stored_hash:
                return False
            unsigned = dict(payload)
            unsigned.pop("receipt_hash", None)
            if stable_hash(unsigned) != stored_hash:
                return False
            try:
                CanonicalEffectReceipt(**payload)
            except Exception:
                return False
        return True


def _workspace_route(operation: str, *, materiality_verifier: str) -> CanonicalCapabilityRoute:
    return CanonicalCapabilityRoute(
        capability="workspace",
        operation=operation,
        executor_id=f"workspace.{operation}",
        effect_kind=EffectKind.REAL,
        backend_mode="workspace_read_only",
        required_authority="workspace_read",
        arguments_schema=_workspace_arguments_schema(operation),
        preconditions=("path_inside_workspace",),
        readiness_probe="workspace_root_exists",
        materiality_verifier=materiality_verifier,
        proof_contract="canonical_core_workspace_receipt_v1",
        recovery_policy="typed_path_or_decode_failure",
        cleanup_contract="root_resource_scope_close",
    )


def _workspace_arguments_schema(operation: str) -> dict[str, Any]:
    if operation == "list":
        return {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
            "additionalProperties": False,
        }
    if operation == "read":
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 1, "maximum": 4000, "default": 1200},
                "max_bytes": {"type": "integer", "minimum": 1, "maximum": 4000000, "default": 1000000},
            },
            "required": ["path"],
            "additionalProperties": False,
        }
    if operation == "search":
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "max_files": {"type": "integer", "minimum": 1, "maximum": 5000, "default": 1000},
                "max_bytes_per_file": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000000,
                    "default": 256000,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }
    return {"type": "object", "additionalProperties": False}


def _action_signature(decision: CanonicalDecision) -> str:
    signature_hash = stable_hash(
        {
            "capability": decision.capability,
            "operation": decision.operation,
            "arguments": redact_operator_value(decision.arguments),
        }
    )
    return f"{decision.capability}.{decision.operation}:{signature_hash[:24]}"


def _normalized_search_terms(text: str) -> tuple[str, ...]:
    normalized = _normalize_search_text(text)
    terms = [term for term in normalized.split(" ") if term]
    expanded = list(terms)
    for left, right in zip(terms, terms[1:], strict=False):
        if len(left) > 2 and len(right) > 2:
            expanded.append(f"{left[0]}{right[0]}")
    return tuple(dict.fromkeys(expanded))


def _normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-.\\/]+", " ", text).lower()).strip()


def _observation_paths(observation: dict[str, Any]) -> tuple[str, ...]:
    paths: list[str] = []
    path = observation.get("path")
    if isinstance(path, str) and path and path != ".":
        paths.append(path)
    for match in observation.get("matches", ()):
        if not isinstance(match, dict):
            continue
        match_path = match.get("path")
        if isinstance(match_path, str) and match_path and match_path != ".":
            paths.append(match_path)
    return tuple(dict.fromkeys(paths))


def _progress_fingerprint_payload(observation: dict[str, Any]) -> dict[str, Any]:
    dynamic_keys = {
        "action_signature",
        "action_signature_seen_before",
        "decision_origin",
        "evidence_delta",
        "new_paths",
        "objective_progress",
        "observation_fingerprint",
        "product_action_evidence_refs",
        "product_action_kernel_dispatch",
        "product_action_receipt_refs",
        "product_action_result_hash",
        "progress_classification",
        "replan_required",
        "typed_observation",
    }
    return {key: value for key, value in observation.items() if key not in dynamic_keys}


def _restore_workspace_observation_types(observation: dict[str, Any]) -> dict[str, Any]:
    if isinstance(observation.get("entries"), list):
        observation["entries"] = tuple(observation["entries"])
    if isinstance(observation.get("matches"), list):
        matches: list[dict[str, Any]] = []
        for item in observation["matches"]:
            if not isinstance(item, dict):
                continue
            match = dict(item)
            if isinstance(match.get("match_channels"), list):
                match["match_channels"] = tuple(match["match_channels"])
            matches.append(match)
        observation["matches"] = tuple(matches)
    search_scope = observation.get("search_scope")
    if isinstance(search_scope, dict) and isinstance(search_scope.get("channels"), list):
        observation["search_scope"] = {**search_scope, "channels": tuple(search_scope["channels"])}
    return observation


def _workspace_ref(path: Path) -> str:
    return f"workspace:{stable_hash(str(path))[:24]}"


def _relative_workspace_path(root: Path, path: Path) -> str:
    if path == root:
        return "."
    return path.relative_to(root).as_posix()


def _safe_exception_code(exc: Exception) -> str:
    text = str(exc)
    if isinstance(exc, (CanonicalCoreError, ActionKernelError)) and text and "\n" not in text and len(text) <= 120:
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", text):
            return redact_operator_text(text)
    if isinstance(exc, CanonicalCoreError) and text and "\n" not in text and len(text) <= 120:
        return redact_operator_text(text)
    return exc.__class__.__name__


__all__ = [
    "CanonicalBudget",
    "CanonicalCapabilityQuarantined",
    "CanonicalCapabilityRoute",
    "CanonicalCoreError",
    "CanonicalDecision",
    "CanonicalDecisionRequest",
    "CanonicalDevMissionResult",
    "CanonicalEffectReceipt",
    "CanonicalModelClient",
    "CanonicalState",
    "DecisionOrigin",
    "DecisionProtocol",
    "EffectKind",
    "ExecutableCapabilityGraph",
    "MissionProofRoot",
    "QuarantinedCapability",
    "RootMissionRuntime",
    "RootMissionCancellationToken",
    "build_workspace_read_capability_graph",
    "run_canonical_dev_mission",
    "run_canonical_product_mission",
]
