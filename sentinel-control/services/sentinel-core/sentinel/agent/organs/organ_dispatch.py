"""Organ Dispatch Bridge — connects Brain proposals to Organ execution.

Pipeline for every dispatch (no shortcuts, no bypass, even in power mode):

    LLMRoleLoopResult.action_candidates (list[dict[str, Any]])
        ↓
    OrganProposalBridge.build() → BaseOrganCandidate[]
        ↓
    DelegatedActionGate.decide() → DelegatedActionGateResult (ALLOWED / BLOCKED / ...)
        ↓
    _build_typed_sub_request() → L2LocalArtifactRequest | L3WorkspaceRequest | BrowserReadOnlyRequest | ...
        ↓
    execute_organ_runtime_request() → OrganRuntimeExecutionResult
        ↓
    OrganDispatchResult (data, not instruction)

This module creates NO new execution paths. It wires existing components:
- OrganProposalBridge (proposal_bridge.py)
- DelegatedActionGate (delegated_action_gate.py)
- execute_organ_runtime_request (runtime_execution.py)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, ValidationError, model_validator

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.model_execution.redaction import sanitize_metadata, stable_hash
from sentinel.agent.organs.browser_readonly_organ_v1 import (
    BrowserReadOnlyReceipt,
    BrowserReadOnlyRequest,
    L4BrowserReadOnlyExecutorContract,
)
from sentinel.agent.organs.browser_preparation_organ_v1 import (
    BrowserPreparationReceipt,
    BrowserPreparationRequest,
    BrowserPreparationStep,
    BrowserPreparationTargetRef,
    L4BrowserPreparationExecutorContract,
)
from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
    BrowserFormSubmitContract,
    BrowserFormSubmitRequest,
)
from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
    BrowserFileQuarantineActionKind,
    BrowserFileQuarantineContract,
    BrowserFileQuarantineRequest,
)
from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import (
    BrowserJSSandboxContract,
    BrowserJSSandboxRequest,
)
from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
    BrowserLoginCredentialSessionContract,
    BrowserLoginCredentialSessionRequest,
)
from sentinel.agent.organs.browser_semantic_extraction_organ_v1 import (
    BrowserSemanticExtractionRequest,
    L4BrowserSemanticExtractionContract,
)
from sentinel.agent.organs.browser_session_manager_l5_live import (
    BrowserSessionActionKind,
    BrowserSessionContract,
    BrowserSessionRequest,
)
from sentinel.agent.organs.delegated_action_gate import (
    DelegatedActionGate,
    DelegatedActionGateDecision,
    DelegatedActionGateInput,
    DelegatedActionGateResult,
    DelegatedActionLane,
)
from sentinel.agent.organs.local_artifact_executor import (
    L2ExecutorContract,
    L2LocalArtifactActionKind,
    L2LocalArtifactRequest,
)
from sentinel.agent.organs.proposal_bridge import (
    BaseOrganCandidate,
    OrganProposalBridge,
    OrganProposalBridgeInput,
    OrganProposalBridgeResult,
    OrganProposalBridgeStatus,
    OrganProposalKind,
)
from sentinel.agent.organs.reversible_workspace_executor import (
    L3ExecutorContract,
    L3WorkspaceActionKind,
    L3WorkspaceRequest,
)
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionResult,
    OrganRuntimeExecutionStatus,
    execute_organ_runtime_request,
)
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.models import SentinelModel


ORGAN_DISPATCH_WARNING = (
    "Organ dispatch results are scoped measurement data only. They are not instructions, "
    "not Root Authority, not permission, and not future execution approval. "
    "Every dispatch passed through DelegatedActionGate + ExecutorContract + Receipt + FinalGate."
)


def utc_now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OrganDispatchStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    ALL_REJECTED = "all_rejected"
    NO_CANDIDATES = "no_candidates"
    BRIDGE_FAILED = "bridge_failed"
    DISABLED = "disabled"


class OrganDispatchCandidateStatus(StrEnum):
    EXECUTED = "executed"
    GATE_REJECTED = "gate_rejected"
    BRIDGE_REJECTED = "bridge_rejected"
    EXECUTION_FAILED = "execution_failed"
    UNSUPPORTED_ORGAN = "unsupported_organ"
    SUB_REQUEST_BUILD_FAILED = "sub_request_build_failed"


# ---------------------------------------------------------------------------
# Result models — all follow Sentinel's firewall invariants
# ---------------------------------------------------------------------------


class OrganDispatchCandidateResult(SentinelModel):
    """Result for a single candidate dispatch attempt."""

    candidate_id: str
    organ_kind: str
    status: OrganDispatchCandidateStatus
    gate_decision: DelegatedActionGateDecision | None = None
    gate_reasons: list[str] = Field(default_factory=list)
    lane_id: str | None = None
    execution_result: OrganRuntimeExecutionResult | None = None
    blocked_reason: str | None = None
    safe_summary: str
    created_at: datetime = Field(default_factory=utc_now)
    # Firewall invariants
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute_more: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> OrganDispatchCandidateResult:
        _assert_dispatch_firewall(self)
        if self.data_not_instruction is not True:
            raise ValueError("Organ dispatch candidate results are data, not instruction.")
        return self


class OrganDispatchTrace(SentinelModel):
    """Trace of the full dispatch operation."""

    mission_id: str
    total_action_candidates: int = Field(default=0, ge=0)
    bridge_candidate_count: int = Field(default=0, ge=0)
    bridge_rejected_count: int = Field(default=0, ge=0)
    gate_allowed_count: int = Field(default=0, ge=0)
    gate_rejected_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    execution_failed_count: int = Field(default=0, ge=0)
    safe_summary: str
    input_hash: str
    # Firewall invariants
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute_more: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> OrganDispatchTrace:
        _assert_dispatch_firewall(self)
        if self.data_not_instruction is not True:
            raise ValueError("Organ dispatch traces are data, not instruction.")
        return self


class OrganDispatchResult(SentinelModel):
    """Result of a full dispatch cycle (all candidates processed)."""

    mission_id: str
    status: OrganDispatchStatus
    candidate_results: list[OrganDispatchCandidateResult] = Field(default_factory=list)
    bridge_result: OrganProposalBridgeResult | None = None
    trace: OrganDispatchTrace
    safe_summary: str
    created_at: datetime = Field(default_factory=utc_now)
    # Firewall invariants
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute_more: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _keep_firewall_closed(self) -> OrganDispatchResult:
        _assert_dispatch_firewall(self)
        if self.data_not_instruction is not True:
            raise ValueError("Organ dispatch results are data, not instruction.")
        return self

    def to_untrusted_context_block(self) -> str:
        return render_organ_dispatch_result_as_untrusted_context(self)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class OrganDispatcher:
    """Bridge from Brain proposals to Organ execution.

    Harvest-native: uses existing OrganProposalBridge + DelegatedActionGate.decide()
    + execute_organ_runtime_request(). Creates no new execution paths.

    Contract: every candidate ALWAYS passes through:
        DelegatedActionGate → ExecutorContract → Receipt → FinalGate
    regardless of preset mode. No shortcuts. No bypass. Even in power mode.
    """

    def __init__(self) -> None:
        self._bridge = OrganProposalBridge()
        self._gate = DelegatedActionGate()

    def dispatch(
        self,
        *,
        mission_id: str,
        action_candidates: list[dict[str, Any]],
        proposal_artifacts: list[dict[str, Any]] | None = None,
        config: OrganRuntimeExecutionConfig | None = None,
        authority: dict[str, Any] | None = None,
        authority_envelope: MissionAuthorityEnvelope | None = None,
        budget: dict[str, Any] | None = None,
        available_evidence_refs: list[str] | None = None,
        organ_contracts: dict[str, dict[str, Any]] | None = None,
        browser_readonly_fetcher: Any = None,
    ) -> OrganDispatchResult:
        """Dispatch brain outputs through the full Sentinel pipeline.

        Args:
            mission_id: The mission ID from the authority envelope.
            action_candidates: Raw action_candidates from LLMRoleLoopResult (list[dict]).
            proposal_artifacts: Raw proposal_artifacts from LLMRoleLoopResult (list[dict]).
            config: Organ runtime execution config (preset or manual).
            authority: Authority envelope data for gate evaluation.
            authority_envelope: The full MissionAuthorityEnvelope for runtime preflight.
            budget: Budget state for gate evaluation.
            available_evidence_refs: Evidence refs available for gate.
            organ_contracts: Typed executor contracts keyed by organ_kind string.
                             Passed to DelegatedActionGate and used to build typed sub-requests.
            browser_readonly_fetcher: Optional browser fetcher for L4 read-only.
        """
        runtime_config = config or OrganRuntimeExecutionConfig()
        resolved_organ_contracts = organ_contracts or {}
        input_hash = stable_hash(sanitize_metadata({
            "mission_id": mission_id,
            "action_candidates_count": len(action_candidates),
            "proposal_artifacts_count": len(proposal_artifacts or []),
        }))

        # Step 0: If disabled, short-circuit
        if not runtime_config.enabled:
            return _disabled_result(mission_id=mission_id, input_hash=input_hash)
        if not action_candidates and not proposal_artifacts:
            return _no_candidates_result(mission_id=mission_id, input_hash=input_hash)

        # Step 1: OrganProposalBridge — convert raw dicts → BaseOrganCandidate[]
        bridge_input = OrganProposalBridgeInput(
            mission_id=mission_id,
            proposal_artifacts=proposal_artifacts or action_candidates,
        )
        bridge_result = self._bridge.build(bridge_input)

        if bridge_result.status in {
            OrganProposalBridgeStatus.REJECTED,
            OrganProposalBridgeStatus.NO_SUPPORTED_PROPOSALS,
        } and not bridge_result.candidates:
            return _bridge_failed_result(
                mission_id=mission_id,
                bridge_result=bridge_result,
                input_hash=input_hash,
                total_candidates=len(action_candidates),
            )

        # Build a lookup from source_proposal_id → raw dict for sub-request building.
        # The bridge generates candidate_id/source_proposal_id from the raw proposal dicts.
        # We index by position so we can correlate bridged candidates back to raw data.
        raw_by_index: dict[int, dict[str, Any]] = {
            i: raw for i, raw in enumerate(action_candidates)
        }

        # Step 2+3: For each candidate → Gate → Build sub-request → Execute
        candidate_results: list[OrganDispatchCandidateResult] = []
        gate_allowed = 0
        gate_rejected = 0
        executed = 0
        execution_failed = 0

        for candidate_index, candidate in enumerate(bridge_result.candidates):
            # Step 2: DelegatedActionGate.decide() — MANDATORY, no bypass
            gate_input = DelegatedActionGateInput(
                mission_id=mission_id,
                candidate=candidate,
                authority=authority or {},
                budget=budget or {},
                available_evidence_refs=available_evidence_refs or [],
                organ_contracts=resolved_organ_contracts,
            )
            gate_result = self._gate.decide(gate_input)

            if gate_result.decision != DelegatedActionGateDecision.ALLOWED:
                gate_rejected += 1
                candidate_results.append(
                    OrganDispatchCandidateResult(
                        candidate_id=candidate.candidate_id,
                        organ_kind=candidate.organ_kind.value,
                        status=OrganDispatchCandidateStatus.GATE_REJECTED,
                        gate_decision=gate_result.decision,
                        gate_reasons=[r.value for r in gate_result.reasons],
                        blocked_reason=f"gate_decision_{gate_result.decision.value}",
                        safe_summary=f"Candidate {candidate.candidate_id} rejected by DelegatedActionGate: {gate_result.decision.value}",
                    )
                )
                continue

            gate_allowed += 1

            # Get the raw dict for this candidate (for extracting typed params)
            raw_candidate = raw_by_index.get(candidate_index, {})

            # Step 3: execute_organ_runtime_request() — builds contract + receipt + FinalGate
            exec_result = self._execute_candidate(
                candidate=candidate,
                raw_candidate=raw_candidate,
                gate_result=gate_result,
                config=runtime_config,
                authority_envelope=authority_envelope,
                organ_contracts=resolved_organ_contracts,
                browser_readonly_fetcher=browser_readonly_fetcher,
                prior_candidate_results=candidate_results,
            )

            if exec_result.status in {
                OrganRuntimeExecutionStatus.EXECUTED,
                OrganRuntimeExecutionStatus.CERTIFIED,
            }:
                executed += 1
                candidate_results.append(
                    OrganDispatchCandidateResult(
                        candidate_id=candidate.candidate_id,
                        organ_kind=candidate.organ_kind.value,
                        status=OrganDispatchCandidateStatus.EXECUTED,
                        gate_decision=gate_result.decision,
                        lane_id=gate_result.lane.lane_id if gate_result.lane else None,
                        execution_result=exec_result,
                        safe_summary=f"Candidate {candidate.candidate_id} executed successfully: {exec_result.safe_summary}",
                    )
                )
            else:
                execution_failed += 1
                candidate_results.append(
                    OrganDispatchCandidateResult(
                        candidate_id=candidate.candidate_id,
                        organ_kind=candidate.organ_kind.value,
                        status=OrganDispatchCandidateStatus.EXECUTION_FAILED,
                        gate_decision=gate_result.decision,
                        lane_id=gate_result.lane.lane_id if gate_result.lane else None,
                        execution_result=exec_result,
                        blocked_reason=exec_result.blocked_reason or "execution_failed",
                        safe_summary=f"Candidate {candidate.candidate_id} execution failed: {exec_result.blocked_reason or exec_result.status.value}",
                    )
                )

        # Step 4: Aggregate results
        status = _dispatch_status(
            bridge_candidates=len(bridge_result.candidates),
            bridge_rejected=len(bridge_result.rejected_candidates),
            executed=executed,
            gate_rejected=gate_rejected,
            execution_failed=execution_failed,
        )

        trace = OrganDispatchTrace(
            mission_id=mission_id,
            total_action_candidates=len(action_candidates),
            bridge_candidate_count=len(bridge_result.candidates),
            bridge_rejected_count=len(bridge_result.rejected_candidates),
            gate_allowed_count=gate_allowed,
            gate_rejected_count=gate_rejected,
            executed_count=executed,
            execution_failed_count=execution_failed,
            safe_summary=(
                f"Dispatch: {len(action_candidates)} raw -> "
                f"{len(bridge_result.candidates)} bridged -> "
                f"{gate_allowed} gate-allowed -> "
                f"{executed} executed, {execution_failed} failed"
            ),
            input_hash=input_hash,
        )

        return OrganDispatchResult(
            mission_id=mission_id,
            status=status,
            candidate_results=candidate_results,
            bridge_result=bridge_result,
            trace=trace,
            safe_summary=trace.safe_summary,
        )

    def _execute_candidate(
        self,
        *,
        candidate: BaseOrganCandidate,
        raw_candidate: dict[str, Any],
        gate_result: DelegatedActionGateResult,
        config: OrganRuntimeExecutionConfig,
        authority_envelope: MissionAuthorityEnvelope | None = None,
        organ_contracts: dict[str, dict[str, Any]] | None = None,
        browser_readonly_fetcher: Any = None,
        prior_candidate_results: list[OrganDispatchCandidateResult] | None = None,
    ) -> OrganRuntimeExecutionResult:
        """Route a gate-approved candidate to the correct executor.

        Builds the typed sub-request (L2/L3/BrowserReadOnly/etc.) from the raw
        candidate dict, injects the executor contract + delegated lane, and passes
        everything to execute_organ_runtime_request().
        """
        organ_kind = candidate.organ_kind
        action_level = candidate.action_level_candidate

        # Resolve the runtime organ_kind string
        runtime_organ_kind = _resolve_runtime_organ_kind(
            organ_kind=organ_kind,
            action_level=action_level,
            raw_candidate=raw_candidate,
            organ_contracts=organ_contracts or {},
            gate_result=gate_result,
        )
        if runtime_organ_kind is None:
            return _unsupported_organ_result(
                candidate=candidate,
                gate_result=gate_result,
                config=config,
            )

        # Build the typed sub-request from raw candidate data
        sub_request = _build_typed_sub_request(
            raw_candidate=raw_candidate,
            bridged_candidate=candidate,
            gate_result=gate_result,
            runtime_organ_kind=runtime_organ_kind,
            organ_contracts=organ_contracts or {},
            prior_candidate_results=prior_candidate_results or [],
            authority_envelope=authority_envelope,
        )

        if sub_request is None:
            return _sub_request_build_failed_result(
                candidate=candidate,
                gate_result=gate_result,
                config=config,
                reason=f"failed_to_build_sub_request_for_{runtime_organ_kind}",
            )

        # Build the execution request with ALL required fields populated
        exec_request = OrganRuntimeExecutionRequest(
            mission_id=candidate.mission_id,
            action_level=action_level,
            organ_kind=runtime_organ_kind,
            authority_envelope=authority_envelope,
            gate_result=gate_result,
            delegated_lane=gate_result.lane,
            # Typed sub-requests — exactly one will be non-None
            l2_request=sub_request if runtime_organ_kind == "local_artifact" else None,
            l3_request=sub_request if runtime_organ_kind == "reversible_workspace" else None,
            browser_readonly_request=sub_request if runtime_organ_kind == "browser_readonly" else None,
            browser_preparation_request=sub_request if runtime_organ_kind == "browser_preparation" else None,
            browser_semantic_extraction_request=sub_request if runtime_organ_kind == "browser_semantic_extraction" else None,
            browser_session_request=sub_request if runtime_organ_kind == "browser_session_manager" else None,
            browser_form_submit_request=sub_request if runtime_organ_kind == "browser_form_submit_special_authority" else None,
            browser_login_request=sub_request if runtime_organ_kind == "browser_login_credential_session_broker" else None,
            browser_file_quarantine_request=sub_request if runtime_organ_kind == "browser_download_upload_quarantine" else None,
            browser_js_sandbox_request=sub_request if runtime_organ_kind == "browser_js_sandbox_special_authority" else None,
            metadata={
                "source_candidate_id": candidate.candidate_id,
                "source_proposal_id": candidate.source_proposal_id,
                "params_hash": candidate.params_hash,
            },
        )

        # Execute through the standard pipeline (contract → receipt → FinalGate)
        return execute_organ_runtime_request(
            exec_request,
            config=config,
            browser_readonly_fetcher=browser_readonly_fetcher,
        )


# ---------------------------------------------------------------------------
# Sub-request builder
# ---------------------------------------------------------------------------


def _build_typed_sub_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    gate_result: DelegatedActionGateResult,
    runtime_organ_kind: str,
    organ_contracts: dict[str, dict[str, Any]],
    prior_candidate_results: list[OrganDispatchCandidateResult],
    authority_envelope: MissionAuthorityEnvelope | None = None,
) -> L2LocalArtifactRequest | L3WorkspaceRequest | BrowserReadOnlyRequest | BrowserPreparationRequest | BrowserSemanticExtractionRequest | BrowserSessionRequest | BrowserFormSubmitRequest | BrowserLoginCredentialSessionRequest | BrowserFileQuarantineRequest | BrowserJSSandboxRequest | Any | None:
    """Build the correct typed sub-request from raw candidate data.

    The raw_candidate dict contains the brain's proposed parameters (target_path,
    content, url, etc.). The gate_result provides the lane and gate metadata
    needed for the executor contract.

    Returns None if the sub-request cannot be built (missing required fields).
    """
    lane = gate_result.lane
    mission_id = bridged_candidate.mission_id

    if runtime_organ_kind == "local_artifact":
        return _build_l2_request(
            raw_candidate=raw_candidate,
            bridged_candidate=bridged_candidate,
            lane=lane,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
        )

    if runtime_organ_kind == "reversible_workspace":
        return _build_l3_request(
            raw_candidate=raw_candidate,
            bridged_candidate=bridged_candidate,
            lane=lane,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
        )

    if runtime_organ_kind == "browser_readonly":
        return _build_browser_readonly_request(
            raw_candidate=raw_candidate,
            bridged_candidate=bridged_candidate,
            lane=lane,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
        )

    if runtime_organ_kind == "browser_preparation":
        return _build_browser_preparation_request(
            raw_candidate=raw_candidate,
            bridged_candidate=bridged_candidate,
            lane=lane,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
            prior_candidate_results=prior_candidate_results,
        )

    if runtime_organ_kind == "browser_semantic_extraction":
        return _build_browser_semantic_extraction_request(
            raw_candidate=raw_candidate,
            bridged_candidate=bridged_candidate,
            lane=lane,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
            prior_candidate_results=prior_candidate_results,
        )

    if runtime_organ_kind == "browser_session_manager":
        return _build_browser_session_request(
            raw_candidate=raw_candidate,
            bridged_candidate=bridged_candidate,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
            authority_envelope=authority_envelope,
            prior_candidate_results=prior_candidate_results,
        )

    if runtime_organ_kind == "browser_form_submit_special_authority":
        return _build_browser_form_submit_request(
            raw_candidate=raw_candidate,
            bridged_candidate=bridged_candidate,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
            authority_envelope=authority_envelope,
            prior_candidate_results=prior_candidate_results,
        )

    if runtime_organ_kind == "browser_login_credential_session_broker":
        return _build_browser_login_request(
            raw_candidate=raw_candidate,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
            authority_envelope=authority_envelope,
            prior_candidate_results=prior_candidate_results,
        )

    if runtime_organ_kind == "browser_download_upload_quarantine":
        return _build_browser_file_quarantine_request(
            raw_candidate=raw_candidate,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
            authority_envelope=authority_envelope,
            prior_candidate_results=prior_candidate_results,
        )

    if runtime_organ_kind == "browser_js_sandbox_special_authority":
        return _build_browser_js_sandbox_request(
            raw_candidate=raw_candidate,
            mission_id=mission_id,
            organ_contracts=organ_contracts,
            authority_envelope=authority_envelope,
            prior_candidate_results=prior_candidate_results,
        )

    return None


def _build_l2_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
) -> L2LocalArtifactRequest | None:
    """Build a L2LocalArtifactRequest from raw candidate data.

    Required fields from raw_candidate:
    - target_relative_path (or target_path or path)
    - content (the file content to write)
    - action_kind (optional, defaults to create_local_artifact)
    """
    # Extract params from raw candidate — the brain may use different key names
    target_path = (
        raw_candidate.get("target_relative_path")
        or raw_candidate.get("target_path")
        or raw_candidate.get("path")
        or raw_candidate.get("relative_path")
    )
    content = raw_candidate.get("content", "")
    action_kind_raw = raw_candidate.get("action_kind", "create_local_artifact")

    if not target_path:
        return None

    # Resolve action_kind
    try:
        action_kind = L2LocalArtifactActionKind(action_kind_raw)
    except ValueError:
        action_kind = L2LocalArtifactActionKind.CREATE_LOCAL_ARTIFACT

    # Build the executor contract from organ_contracts
    l2_contract = _build_l2_executor_contract(
        lane=lane,
        mission_id=mission_id,
        organ_contracts=organ_contracts,
    )

    return L2LocalArtifactRequest(
        mission_id=mission_id,
        source_candidate_id=bridged_candidate.candidate_id,
        action_kind=action_kind,
        target_relative_path=str(target_path),
        content=str(content),
        metadata=sanitize_metadata(raw_candidate.get("metadata", {})),
        contract=l2_contract,
        delegated_lane=lane,
        budget_estimate=sanitize_metadata(bridged_candidate.budget_estimate),
    )


def _build_l3_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
) -> L3WorkspaceRequest | None:
    """Build a L3WorkspaceRequest from raw candidate data.

    Required fields from raw_candidate:
    - target_relative_path (or target_path or path)
    - content (the new content or patch)
    - before_hash (required for L3 reversibility)
    - action_kind (optional, defaults to replace_text_file)
    """
    target_path = (
        raw_candidate.get("target_relative_path")
        or raw_candidate.get("target_path")
        or raw_candidate.get("path")
        or raw_candidate.get("relative_path")
    )
    content = raw_candidate.get("content", "")
    before_hash = raw_candidate.get("before_hash")
    action_kind_raw = raw_candidate.get("action_kind", "replace_text_file")

    if not target_path:
        return None

    # Resolve action_kind
    try:
        action_kind = L3WorkspaceActionKind(action_kind_raw)
    except ValueError:
        action_kind = L3WorkspaceActionKind.REPLACE_TEXT_FILE

    # Build the executor contract from organ_contracts
    l3_contract = _build_l3_executor_contract(
        lane=lane,
        mission_id=mission_id,
        organ_contracts=organ_contracts,
    )

    return L3WorkspaceRequest(
        mission_id=mission_id,
        source_candidate_id=bridged_candidate.candidate_id,
        action_kind=action_kind,
        target_relative_path=str(target_path),
        content=str(content),
        before_hash=before_hash,
        metadata_patch=sanitize_metadata(raw_candidate.get("metadata_patch", {})),
        metadata=sanitize_metadata(raw_candidate.get("metadata", {})),
        contract=l3_contract,
        delegated_lane=lane,
        budget_estimate=sanitize_metadata(bridged_candidate.budget_estimate),
    )


def _build_browser_readonly_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
) -> BrowserReadOnlyRequest | None:
    """Build a BrowserReadOnlyRequest from raw candidate data.

    Required fields from raw_candidate:
    - requested_url (or url or target_url)
    - objective_summary (or objective or summary)
    - allowed_domains (extracted from contract or raw candidate)
    - validity_scope (defaults to "single_page_observation")
    """
    requested_url = (
        raw_candidate.get("requested_url")
        or raw_candidate.get("url")
        or raw_candidate.get("target_url")
    )
    objective = (
        raw_candidate.get("objective_summary")
        or raw_candidate.get("objective")
        or raw_candidate.get("summary")
        or bridged_candidate.expected_outcome
    )
    validity_scope = raw_candidate.get("validity_scope", "single_page_observation")

    if not requested_url:
        return None

    # Build the executor contract from organ_contracts
    browser_contract = _build_browser_readonly_executor_contract(
        lane=lane,
        mission_id=mission_id,
        organ_contracts=organ_contracts,
        raw_candidate=raw_candidate,
    )

    # Extract allowed_domains from contract or raw candidate
    allowed_domains = (
        raw_candidate.get("allowed_domains")
        or (browser_contract.allowed_domains if browser_contract else [])
    )
    if not allowed_domains:
        # Derive from URL as fallback
        from urllib.parse import urlsplit
        parsed = urlsplit(str(requested_url))
        if parsed.hostname:
            allowed_domains = [parsed.hostname]

    return BrowserReadOnlyRequest(
        mission_id=mission_id,
        objective_summary=str(objective),
        requested_url=str(requested_url),
        allowed_domains=allowed_domains or [],
        validity_scope=str(validity_scope),
        authority_refs=list(bridged_candidate.evidence_refs),
        evidence_refs=list(bridged_candidate.evidence_refs),
        receipt_refs=list(bridged_candidate.receipt_refs),
        metadata=sanitize_metadata(raw_candidate.get("metadata", {})),
        contract=browser_contract,
        delegated_lane=lane,
    )


def _build_browser_preparation_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> BrowserPreparationRequest | None:
    readonly_receipts = _browser_readonly_receipts(raw_candidate, prior_candidate_results)
    if not readonly_receipts:
        return None
    readonly = readonly_receipts[0]
    objective = (
        raw_candidate.get("objective_summary")
        or raw_candidate.get("objective")
        or raw_candidate.get("summary")
        or bridged_candidate.expected_outcome
    )
    target_refs = _browser_preparation_target_refs(raw_candidate, readonly)
    proposed_steps = _browser_preparation_steps(raw_candidate, target_refs)
    contract = _build_browser_preparation_executor_contract(
        lane=lane,
        mission_id=mission_id,
        organ_contracts=organ_contracts,
        source_readonly_receipts=readonly_receipts,
    )
    return BrowserPreparationRequest(
        mission_id=mission_id,
        objective_summary=str(objective),
        source_readonly_receipts=readonly_receipts,
        source_dom_snapshot_hash=readonly.dom_snapshot_hash,
        source_ax_snapshot_hash=readonly.ax_snapshot_hash,
        candidate_goal=str(raw_candidate.get("candidate_goal") or bridged_candidate.expected_outcome),
        target_refs=target_refs,
        proposed_steps=proposed_steps,
        validity_scope=str(raw_candidate.get("validity_scope") or f"{mission_id}:browser_preparation"),
        authority_refs=list(bridged_candidate.evidence_refs),
        evidence_refs=list(bridged_candidate.evidence_refs),
        receipt_refs=list(bridged_candidate.receipt_refs),
        contract=contract,
        delegated_lane=lane,
    )


def _build_browser_semantic_extraction_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> BrowserSemanticExtractionRequest | None:
    readonly_receipts = _browser_readonly_receipts(raw_candidate, prior_candidate_results)
    if not readonly_receipts:
        return None
    preparation_receipts = _browser_preparation_receipts(raw_candidate, prior_candidate_results)
    objective = (
        raw_candidate.get("objective_summary")
        or raw_candidate.get("objective")
        or raw_candidate.get("summary")
        or bridged_candidate.expected_outcome
    )
    safe_summaries = raw_candidate.get("safe_observation_summaries")
    if not isinstance(safe_summaries, dict):
        safe_summaries = {receipt.receipt_id: receipt.safe_summary for receipt in readonly_receipts}
    contract = _build_browser_semantic_extraction_contract(
        lane=lane,
        mission_id=mission_id,
        organ_contracts=organ_contracts,
        source_readonly_receipts=readonly_receipts,
    )
    return BrowserSemanticExtractionRequest(
        mission_id=mission_id,
        objective_summary=str(objective),
        source_readonly_receipts=readonly_receipts,
        source_preparation_receipts=preparation_receipts,
        safe_observation_summaries=sanitize_metadata(safe_summaries),
        semantic_focus=[str(item) for item in raw_candidate.get("semantic_focus", [])],
        contradiction_refs=[str(item) for item in raw_candidate.get("contradiction_refs", [])],
        validity_scope=str(raw_candidate.get("validity_scope") or f"{mission_id}:browser_semantic_extraction"),
        authority_refs=list(bridged_candidate.evidence_refs),
        evidence_refs=list(bridged_candidate.evidence_refs),
        receipt_refs=list(bridged_candidate.receipt_refs),
        contract=contract,
        delegated_lane=lane,
    )


def _build_browser_session_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    authority_envelope: MissionAuthorityEnvelope | None,
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> BrowserSessionRequest | None:
    if authority_envelope is None:
        return None
    url = raw_candidate.get("url") or raw_candidate.get("requested_url") or raw_candidate.get("target_url")
    if not url:
        return None
    contract_data = (
        organ_contracts.get("browser_session_manager")
        or organ_contracts.get("browser")
        or {}
    )
    allowed_domains = (
        raw_candidate.get("allowed_domains")
        or contract_data.get("allowed_domains")
        or authority_envelope.allowed_domains
        or []
    )
    action_kind = _browser_session_action_kind(raw_candidate.get("action_kind") or raw_candidate.get("browser_action_kind") or "open")
    allowed_action_kinds = _browser_session_allowed_action_kinds(raw_candidate, contract_data, action_kind)
    session_id = raw_candidate.get("session_id")
    if not session_id and action_kind in {BrowserSessionActionKind.OBSERVE, BrowserSessionActionKind.CLOSE}:
        session_id = _latest_browser_session_id(prior_candidate_results)
    try:
        contract = BrowserSessionContract(
            mission_id=mission_id,
            allowed_domains=[str(domain) for domain in allowed_domains],
            allowed_action_kinds=allowed_action_kinds,
            max_steps=int(contract_data.get("max_steps") or raw_candidate.get("max_steps") or 10),
        )
        return BrowserSessionRequest(
            mission=authority_envelope,
            url=str(url),
            contract=contract,
            session_id=session_id,
            action_kind=action_kind,
            target_role=raw_candidate.get("target_role"),
            target_name=raw_candidate.get("target_name"),
            target_nth=int(raw_candidate.get("target_nth") or 0),
            text=raw_candidate.get("text"),
            values=[str(value) for value in raw_candidate.get("values", [])],
            timeout_ms=int(raw_candidate.get("timeout_ms") or 15_000),
            capture_screenshot=bool(raw_candidate.get("capture_screenshot", True)),
        )
    except (TypeError, ValueError, ValidationError):
        return None


def _browser_session_action_kind(value: Any) -> BrowserSessionActionKind:
    try:
        return value if isinstance(value, BrowserSessionActionKind) else BrowserSessionActionKind(str(value))
    except ValueError:
        return BrowserSessionActionKind.OPEN


def _browser_session_allowed_action_kinds(
    raw_candidate: dict[str, Any],
    contract_data: dict[str, Any],
    action_kind: BrowserSessionActionKind,
) -> list[BrowserSessionActionKind]:
    raw_values = raw_candidate.get("allowed_action_kinds") or contract_data.get("allowed_action_kinds") or []
    result: list[BrowserSessionActionKind] = []
    for value in raw_values:
        try:
            result.append(value if isinstance(value, BrowserSessionActionKind) else BrowserSessionActionKind(str(value)))
        except ValueError:
            continue
    if action_kind not in {BrowserSessionActionKind.OPEN, BrowserSessionActionKind.OBSERVE, BrowserSessionActionKind.CLOSE}:
        result.append(action_kind)
    return list(dict.fromkeys(result))


def _build_browser_form_submit_request(
    *,
    raw_candidate: dict[str, Any],
    bridged_candidate: BaseOrganCandidate,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    authority_envelope: MissionAuthorityEnvelope | None,
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> BrowserFormSubmitRequest | None:
    if authority_envelope is None:
        return None
    url = raw_candidate.get("url") or raw_candidate.get("requested_url") or raw_candidate.get("target_url")
    if not url:
        return None
    contract_data = (
        organ_contracts.get("browser_form_submit_special_authority")
        or organ_contracts.get("browser")
        or {}
    )
    allowed_domains = (
        raw_candidate.get("allowed_domains")
        or contract_data.get("allowed_domains")
        or authority_envelope.allowed_domains
        or []
    )
    session_id = raw_candidate.get("session_id") or _latest_browser_session_id(prior_candidate_results)
    if not session_id:
        return None
    try:
        contract = BrowserFormSubmitContract(
            mission_id=mission_id,
            allowed_domains=[str(domain) for domain in allowed_domains],
            allow_form_submit=bool(raw_candidate.get("allow_form_submit") or contract_data.get("allow_form_submit")),
        )
        return BrowserFormSubmitRequest(
            mission=authority_envelope,
            url=str(url),
            session_id=str(session_id),
            contract=contract,
            target_role=str(raw_candidate.get("target_role") or "button"),
            target_name=raw_candidate.get("target_name"),
            target_nth=int(raw_candidate.get("target_nth") or 0),
            source_snapshot_hash=raw_candidate.get("source_snapshot_hash") or _latest_browser_snapshot_hash(prior_candidate_results),
            operator_note=raw_candidate.get("operator_note"),
            timeout_ms=int(raw_candidate.get("timeout_ms") or 15_000),
            capture_screenshot=bool(raw_candidate.get("capture_screenshot", True)),
        )
    except (TypeError, ValueError, ValidationError):
        return None


def _latest_browser_session_id(prior_candidate_results: list[OrganDispatchCandidateResult]) -> str | None:
    for result in reversed(prior_candidate_results):
        receipt = result.execution_result.receipt if result.execution_result is not None else None
        session_id = getattr(receipt, "session_id", None)
        if session_id:
            return str(session_id)
    return None


def _latest_browser_snapshot_hash(prior_candidate_results: list[OrganDispatchCandidateResult]) -> str | None:
    for result in reversed(prior_candidate_results):
        receipt = result.execution_result.receipt if result.execution_result is not None else None
        snapshot_hash = getattr(receipt, "before_snapshot_hash", None) or getattr(receipt, "after_snapshot_hash", None)
        if snapshot_hash:
            return str(snapshot_hash)
    return None


def _build_browser_login_request(
    *,
    raw_candidate: dict[str, Any],
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    authority_envelope: MissionAuthorityEnvelope | None,
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> BrowserLoginCredentialSessionRequest | None:
    if authority_envelope is None:
        return None
    url = raw_candidate.get("url") or raw_candidate.get("requested_url") or raw_candidate.get("target_url")
    session_id = raw_candidate.get("session_id") or _latest_browser_session_id(prior_candidate_results)
    if not url or not session_id:
        return None
    contract_data = (
        organ_contracts.get("browser_login_credential_session_broker")
        or organ_contracts.get("browser")
        or {}
    )
    allowed_domains = raw_candidate.get("allowed_domains") or contract_data.get("allowed_domains") or authority_envelope.allowed_domains or []
    username_ref = raw_candidate.get("username_credential_ref_id") or contract_data.get("username_credential_ref_id")
    password_ref = raw_candidate.get("password_credential_ref_id") or contract_data.get("password_credential_ref_id")
    if not username_ref or not password_ref:
        return None
    try:
        contract = BrowserLoginCredentialSessionContract(
            mission_id=mission_id,
            allowed_domains=[str(domain) for domain in allowed_domains],
            username_credential_ref_id=str(username_ref),
            password_credential_ref_id=str(password_ref),
            allow_login=bool(raw_candidate.get("allow_login") or contract_data.get("allow_login")),
        )
        return BrowserLoginCredentialSessionRequest(
            mission=authority_envelope,
            url=str(url),
            session_id=str(session_id),
            contract=contract,
            username_target_role=str(raw_candidate.get("username_target_role") or "textbox"),
            username_target_name=raw_candidate.get("username_target_name"),
            password_target_role=str(raw_candidate.get("password_target_role") or "textbox"),
            password_target_name=raw_candidate.get("password_target_name"),
            submit_target_role=str(raw_candidate.get("submit_target_role") or "button"),
            submit_target_name=raw_candidate.get("submit_target_name"),
            operator_note=raw_candidate.get("operator_note"),
            timeout_ms=int(raw_candidate.get("timeout_ms") or 15_000),
            capture_screenshot=bool(raw_candidate.get("capture_screenshot", True)),
        )
    except (TypeError, ValueError, ValidationError):
        return None


def _build_browser_file_quarantine_request(
    *,
    raw_candidate: dict[str, Any],
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    authority_envelope: MissionAuthorityEnvelope | None,
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> BrowserFileQuarantineRequest | None:
    if authority_envelope is None:
        return None
    url = raw_candidate.get("url") or raw_candidate.get("requested_url") or raw_candidate.get("target_url")
    session_id = raw_candidate.get("session_id") or _latest_browser_session_id(prior_candidate_results)
    if not url or not session_id:
        return None
    contract_data = (
        organ_contracts.get("browser_download_upload_quarantine")
        or organ_contracts.get("browser")
        or {}
    )
    allowed_domains = raw_candidate.get("allowed_domains") or contract_data.get("allowed_domains") or authority_envelope.allowed_domains or []
    upload_root = raw_candidate.get("approved_upload_root") or contract_data.get("approved_upload_root")
    quarantine_root = raw_candidate.get("approved_download_quarantine_root") or contract_data.get("approved_download_quarantine_root")
    if not upload_root or not quarantine_root:
        return None
    try:
        action_kind = _browser_file_action_kind(raw_candidate.get("file_action_kind") or raw_candidate.get("action_kind") or "download")
        contract = BrowserFileQuarantineContract(
            mission_id=mission_id,
            allowed_domains=[str(domain) for domain in allowed_domains],
            approved_upload_root=str(upload_root),
            approved_download_quarantine_root=str(quarantine_root),
            allow_upload=bool(raw_candidate.get("allow_upload") or contract_data.get("allow_upload")),
            allow_download=bool(raw_candidate.get("allow_download") or contract_data.get("allow_download")),
        )
        return BrowserFileQuarantineRequest(
            mission=authority_envelope,
            url=str(url),
            session_id=str(session_id),
            contract=contract,
            action_kind=action_kind,
            target_role=str(raw_candidate.get("target_role") or ("button" if action_kind is BrowserFileQuarantineActionKind.UPLOAD else "link")),
            target_name=raw_candidate.get("target_name"),
            local_upload_path=raw_candidate.get("local_upload_path"),
            operator_note=raw_candidate.get("operator_note"),
            timeout_ms=int(raw_candidate.get("timeout_ms") or 15_000),
            capture_screenshot=bool(raw_candidate.get("capture_screenshot", True)),
        )
    except (TypeError, ValueError, ValidationError):
        return None


def _build_browser_js_sandbox_request(
    *,
    raw_candidate: dict[str, Any],
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    authority_envelope: MissionAuthorityEnvelope | None,
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> BrowserJSSandboxRequest | None:
    if authority_envelope is None:
        return None
    url = raw_candidate.get("url") or raw_candidate.get("requested_url") or raw_candidate.get("target_url")
    session_id = raw_candidate.get("session_id") or _latest_browser_session_id(prior_candidate_results)
    script = raw_candidate.get("script")
    if not url or not session_id or not script:
        return None
    contract_data = (
        organ_contracts.get("browser_js_sandbox_special_authority")
        or organ_contracts.get("browser")
        or {}
    )
    allowed_domains = raw_candidate.get("allowed_domains") or contract_data.get("allowed_domains") or authority_envelope.allowed_domains or []
    try:
        contract = BrowserJSSandboxContract(
            mission_id=mission_id,
            allowed_domains=[str(domain) for domain in allowed_domains],
            allow_js_sandbox=bool(raw_candidate.get("allow_js_sandbox") or contract_data.get("allow_js_sandbox")),
            max_script_bytes=int(raw_candidate.get("max_script_bytes") or contract_data.get("max_script_bytes") or 4_000),
        )
        return BrowserJSSandboxRequest(
            mission=authority_envelope,
            url=str(url),
            session_id=str(session_id),
            contract=contract,
            script=str(script),
            intent_summary=str(raw_candidate.get("intent_summary") or raw_candidate.get("safe_summary") or "Browser JS sandbox request."),
            timeout_ms=int(raw_candidate.get("timeout_ms") or 15_000),
            capture_screenshot=bool(raw_candidate.get("capture_screenshot", True)),
        )
    except (TypeError, ValueError, ValidationError):
        return None


def _browser_file_action_kind(value: Any) -> BrowserFileQuarantineActionKind:
    try:
        return value if isinstance(value, BrowserFileQuarantineActionKind) else BrowserFileQuarantineActionKind(str(value))
    except ValueError:
        return BrowserFileQuarantineActionKind.DOWNLOAD


# ---------------------------------------------------------------------------
# Executor contract builders
# ---------------------------------------------------------------------------


def _build_l2_executor_contract(
    *,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
) -> L2ExecutorContract | None:
    """Build a L2ExecutorContract from organ_contracts and lane metadata."""
    contract_data = organ_contracts.get("file_operation") or organ_contracts.get("local_artifact")
    if not contract_data or not isinstance(contract_data, dict):
        return None
    lane_id = lane.lane_id if lane else ""
    # Derive a gate_result_id from the lane for traceability
    gate_result_id = _derive_gate_result_id(lane)
    try:
        return L2ExecutorContract(
            mission_id=mission_id,
            lane_id=lane_id,
            gate_result_id=gate_result_id,
            allowed_workspace_root=str(contract_data.get("allowed_workspace_root", "")),
            allowed_artifact_subdir=str(contract_data.get("allowed_artifact_subdir", "generated")),
            max_artifact_bytes=int(contract_data.get("max_artifact_bytes", 100_000)),
            allow_overwrite=bool(contract_data.get("allow_overwrite", False)),
            allow_rollback_cleanup=bool(contract_data.get("allow_rollback_cleanup", False)),
            receipt_required=True,
            tombstone_required_for_cleanup=True,
            finalgate_posture_required=True,
            execution_enabled_for_l2=True,
            contract_version=str(contract_data.get("contract_version", "l2-dispatch-v1")),
        )
    except (ValueError, ValidationError):
        return None


def _build_l3_executor_contract(
    *,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
) -> L3ExecutorContract | None:
    """Build a L3ExecutorContract from organ_contracts and lane metadata."""
    contract_data = organ_contracts.get("code_patch") or organ_contracts.get("reversible_workspace") or organ_contracts.get("file_operation")
    if not contract_data or not isinstance(contract_data, dict):
        return None
    lane_id = lane.lane_id if lane else ""
    gate_result_id = _derive_gate_result_id(lane)
    try:
        return L3ExecutorContract(
            mission_id=mission_id,
            lane_id=lane_id,
            gate_result_id=gate_result_id,
            allowed_workspace_root=str(contract_data.get("allowed_workspace_root", "")),
            allowed_workspace_subdir=str(contract_data.get("allowed_workspace_subdir", "")),
            max_file_bytes=int(contract_data.get("max_file_bytes", 500_000)),
            max_patch_bytes=int(contract_data.get("max_patch_bytes", 100_000)),
            allow_overwrite=bool(contract_data.get("allow_overwrite", True)),
            allow_delete=bool(contract_data.get("allow_delete", False)),
            tombstone_required_for_delete=True,
            rollback_required=True,
            rollback_must_be_tested_before_mutation=True,
            receipt_required=True,
            finalgate_posture_required=True,
            execution_enabled_for_l3=True,
            contract_version=str(contract_data.get("contract_version", "l3-dispatch-v1")),
        )
    except (ValueError, ValidationError):
        return None


def _build_browser_readonly_executor_contract(
    *,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    raw_candidate: dict[str, Any],
) -> L4BrowserReadOnlyExecutorContract | None:
    """Build a L4BrowserReadOnlyExecutorContract from organ_contracts."""
    contract_data = organ_contracts.get("browser") or organ_contracts.get("browser_readonly")
    if not contract_data or not isinstance(contract_data, dict):
        return None
    lane_id = lane.lane_id if lane else ""
    gate_result_id = _derive_gate_result_id(lane)

    # Extract allowed_domains from contract or raw candidate
    allowed_domains = (
        contract_data.get("allowed_domains")
        or raw_candidate.get("allowed_domains")
        or []
    )
    if not allowed_domains:
        from urllib.parse import urlsplit
        url = raw_candidate.get("requested_url") or raw_candidate.get("url") or ""
        parsed = urlsplit(str(url))
        if parsed.hostname:
            allowed_domains = [parsed.hostname]

    try:
        return L4BrowserReadOnlyExecutorContract(
            mission_id=mission_id,
            lane_id=lane_id,
            gate_result_id=gate_result_id,
            allowed_domains=allowed_domains or ["localhost"],
            allowed_schemes=list(contract_data.get("allowed_schemes", ["https"])),
            max_page_bytes=int(contract_data.get("max_page_bytes", 1_000_000)),
            max_extracted_text_bytes=int(contract_data.get("max_extracted_text_bytes", 100_000)),
            max_redirects=int(contract_data.get("max_redirects", 3)),
            max_render_seconds=float(contract_data.get("max_render_seconds", 10.0)),
            receipt_required=True,
            finalgate_posture_required=True,
            execution_enabled_for_l4_readonly=True,
            contract_version=str(contract_data.get("contract_version", "browser-readonly-l4-v1")),
        )
    except (ValueError, ValidationError):
        return None


def _build_browser_preparation_executor_contract(
    *,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    source_readonly_receipts: list[BrowserReadOnlyReceipt],
) -> L4BrowserPreparationExecutorContract | None:
    contract_data = organ_contracts.get("browser_preparation") or organ_contracts.get("browser")
    if not contract_data or not isinstance(contract_data, dict):
        return None
    lane_id = lane.lane_id if lane else ""
    gate_result_id = _derive_gate_result_id(lane)
    try:
        return L4BrowserPreparationExecutorContract(
            mission_id=mission_id,
            lane_id=lane_id,
            gate_result_id=gate_result_id,
            source_readonly_receipt_refs=[receipt.receipt_id for receipt in source_readonly_receipts],
            max_candidate_targets=int(contract_data.get("max_candidate_targets", 8)),
            max_proposed_steps=int(contract_data.get("max_proposed_steps", 8)),
            max_plan_bytes=int(contract_data.get("max_plan_bytes", 100_000)),
            receipt_required=True,
            finalgate_posture_required=True,
            execution_enabled_for_l4_preparation=True,
            contract_version=str(contract_data.get("contract_version", "browser-preparation-l4-v1")),
        )
    except (ValueError, ValidationError):
        return None


def _build_browser_semantic_extraction_contract(
    *,
    lane: DelegatedActionLane | None,
    mission_id: str,
    organ_contracts: dict[str, dict[str, Any]],
    source_readonly_receipts: list[BrowserReadOnlyReceipt],
) -> L4BrowserSemanticExtractionContract | None:
    contract_data = organ_contracts.get("browser_semantic_extraction") or organ_contracts.get("browser")
    if not contract_data or not isinstance(contract_data, dict):
        return None
    lane_id = lane.lane_id if lane else ""
    gate_result_id = _derive_gate_result_id(lane)
    try:
        return L4BrowserSemanticExtractionContract(
            mission_id=mission_id,
            lane_id=lane_id,
            gate_result_id=gate_result_id,
            source_readonly_receipt_refs=[receipt.receipt_id for receipt in source_readonly_receipts],
            max_evidence_cards=int(contract_data.get("max_evidence_cards", 8)),
            max_claims_per_source=int(contract_data.get("max_claims_per_source", 4)),
            receipt_required=True,
            finalgate_posture_required=True,
            evidence_verifier_required=True,
            execution_enabled_for_l4_semantic_extraction=True,
            contract_version=str(contract_data.get("contract_version", "browser-semantic-extraction-l4-v1")),
        )
    except (ValueError, ValidationError):
        return None


def _browser_readonly_receipts(
    raw_candidate: dict[str, Any],
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> list[BrowserReadOnlyReceipt]:
    receipts: list[BrowserReadOnlyReceipt] = []
    for item in raw_candidate.get("source_readonly_receipts", []) or []:
        if isinstance(item, BrowserReadOnlyReceipt):
            receipts.append(item)
        elif isinstance(item, dict):
            try:
                receipts.append(BrowserReadOnlyReceipt.model_validate(item))
            except ValidationError:
                continue
    for result in prior_candidate_results:
        execution = result.execution_result
        receipt = getattr(execution, "receipt", None) if execution is not None else None
        if isinstance(receipt, BrowserReadOnlyReceipt):
            receipts.append(receipt)
    return _dedupe_readonly_receipts(receipts)


def _browser_preparation_receipts(
    raw_candidate: dict[str, Any],
    prior_candidate_results: list[OrganDispatchCandidateResult],
) -> list[BrowserPreparationReceipt]:
    receipts: list[BrowserPreparationReceipt] = []
    for item in raw_candidate.get("source_preparation_receipts", []) or []:
        if isinstance(item, BrowserPreparationReceipt):
            receipts.append(item)
        elif isinstance(item, dict):
            try:
                receipts.append(BrowserPreparationReceipt.model_validate(item))
            except ValidationError:
                continue
    for result in prior_candidate_results:
        execution = result.execution_result
        receipt = getattr(execution, "receipt", None) if execution is not None else None
        if isinstance(receipt, BrowserPreparationReceipt):
            receipts.append(receipt)
    return _dedupe_preparation_receipts(receipts)


def _browser_preparation_target_refs(
    raw_candidate: dict[str, Any],
    readonly: BrowserReadOnlyReceipt,
) -> list[BrowserPreparationTargetRef]:
    refs: list[BrowserPreparationTargetRef] = []
    for item in raw_candidate.get("target_refs", []) or []:
        if isinstance(item, BrowserPreparationTargetRef):
            refs.append(item)
        elif isinstance(item, dict):
            try:
                refs.append(BrowserPreparationTargetRef.model_validate(item))
            except ValidationError:
                continue
    if refs:
        return refs
    source_hash = readonly.ax_snapshot_hash or readonly.dom_snapshot_hash or readonly.extracted_text_hash or readonly.page_content_hash or readonly.receipt_hash
    if not source_hash:
        return []
    return [
        BrowserPreparationTargetRef(
            ref_id="observed_page",
            role="document",
            name="Observed page",
            source_kind="browser_readonly_receipt",
            source_hash=source_hash,
            source_receipt_id=readonly.receipt_id,
        )
    ]


def _browser_preparation_steps(
    raw_candidate: dict[str, Any],
    target_refs: list[BrowserPreparationTargetRef],
) -> list[BrowserPreparationStep]:
    steps: list[BrowserPreparationStep] = []
    for item in raw_candidate.get("proposed_steps", []) or []:
        if isinstance(item, BrowserPreparationStep):
            steps.append(item)
        elif isinstance(item, dict):
            try:
                steps.append(BrowserPreparationStep.model_validate(item))
            except ValidationError:
                continue
    if steps:
        return steps
    target_ref_id = target_refs[0].ref_id if target_refs else None
    return [
        BrowserPreparationStep(
            step_id="step_wait_observed_page",
            action_class="wait",
            target_ref_id=target_ref_id,
            safe_intent_summary="Prepare non-executing wait over the observed page.",
        )
    ]


def _dedupe_readonly_receipts(receipts: list[BrowserReadOnlyReceipt]) -> list[BrowserReadOnlyReceipt]:
    seen: set[str] = set()
    result: list[BrowserReadOnlyReceipt] = []
    for receipt in receipts:
        if receipt.receipt_id in seen:
            continue
        seen.add(receipt.receipt_id)
        result.append(receipt)
    return result


def _dedupe_preparation_receipts(receipts: list[BrowserPreparationReceipt]) -> list[BrowserPreparationReceipt]:
    seen: set[str] = set()
    result: list[BrowserPreparationReceipt] = []
    for receipt in receipts:
        if receipt.receipt_id in seen:
            continue
        seen.add(receipt.receipt_id)
        result.append(receipt)
    return result


def _derive_gate_result_id(lane: DelegatedActionLane | None) -> str:
    """Derive a deterministic gate_result_id from the lane metadata."""
    if lane is None:
        return "no_lane"
    return f"gate_for_{lane.lane_id}"


# ---------------------------------------------------------------------------
# Browser organ kind resolution
# ---------------------------------------------------------------------------


def _resolve_runtime_organ_kind(
    *,
    organ_kind: OrganProposalKind,
    action_level: DelegatedActionLevel,
    raw_candidate: dict[str, Any] | None = None,
    organ_contracts: dict[str, dict[str, Any]],
    gate_result: DelegatedActionGateResult,
) -> str | None:
    """Resolve OrganProposalKind + action_level to the organ_kind string
    that runtime_execution.py understands.

    For BROWSER, uses organ_contracts and gate_result to select between
    browser_readonly, browser_preparation, and browser_semantic_extraction.
    """
    if organ_kind == OrganProposalKind.FILE_OPERATION:
        if action_level == DelegatedActionLevel.L2:
            return "local_artifact"
        if action_level == DelegatedActionLevel.L3:
            return "reversible_workspace"
        return None

    if organ_kind == OrganProposalKind.CODE_PATCH:
        # CODE_PATCH is always L3 reversible workspace
        return "reversible_workspace"

    if organ_kind == OrganProposalKind.BROWSER:
        return _resolve_browser_organ_kind(
            action_level=action_level,
            raw_candidate=raw_candidate or {},
            organ_contracts=organ_contracts,
            gate_result=gate_result,
        )

    # API, CHANNEL_DRAFT, RESEARCH, SELF_IMPROVEMENT — not yet supported
    return None


def _resolve_browser_organ_kind(
    *,
    action_level: DelegatedActionLevel,
    raw_candidate: dict[str, Any],
    organ_contracts: dict[str, dict[str, Any]],
    gate_result: DelegatedActionGateResult,
) -> str:
    """Resolve the specific browser organ_kind based on contracts and gate result.

    Priority order:
    1. If gate_result.selected_backend_id explicitly names a browser type → use it
    2. If organ_contracts contains "browser_semantic_extraction" → semantic extraction
    3. If organ_contracts contains "browser_preparation" → preparation
    4. Default → browser_readonly (safest)
    """
    explicit_kind = str(
        raw_candidate.get("browser_organ_kind")
        or raw_candidate.get("runtime_organ_kind")
        or raw_candidate.get("organ_runtime_kind")
        or ""
    ).strip().lower()
    if explicit_kind in {
        "browser_readonly",
        "browser_preparation",
        "browser_semantic_extraction",
        "browser_session_manager",
        "browser_form_submit_special_authority",
        "browser_login_credential_session_broker",
        "browser_download_upload_quarantine",
        "browser_js_sandbox_special_authority",
    }:
        return explicit_kind

    # Check if gate explicitly selected a backend
    backend_id = (gate_result.selected_backend_id or "") if gate_result is not None else ""
    if "semantic_extraction" in backend_id:
        return "browser_semantic_extraction"
    if "preparation" in backend_id:
        return "browser_preparation"

    # Check organ_contracts for specific browser types
    if "browser_semantic_extraction" in organ_contracts:
        contract = organ_contracts["browser_semantic_extraction"]
        if isinstance(contract, dict) and contract.get("available"):
            return "browser_semantic_extraction"

    if "browser_preparation" in organ_contracts:
        contract = organ_contracts["browser_preparation"]
        if isinstance(contract, dict) and contract.get("available"):
            return "browser_preparation"

    # Default: browser_readonly (safest option)
    return "browser_readonly"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _dispatch_status(
    *,
    bridge_candidates: int,
    bridge_rejected: int,
    executed: int,
    gate_rejected: int,
    execution_failed: int,
) -> OrganDispatchStatus:
    if bridge_candidates == 0:
        return OrganDispatchStatus.NO_CANDIDATES
    if executed == bridge_candidates:
        return OrganDispatchStatus.COMPLETED
    if executed > 0:
        return OrganDispatchStatus.PARTIAL
    return OrganDispatchStatus.ALL_REJECTED


def _disabled_result(*, mission_id: str, input_hash: str) -> OrganDispatchResult:
    return OrganDispatchResult(
        mission_id=mission_id,
        status=OrganDispatchStatus.DISABLED,
        candidate_results=[],
        trace=OrganDispatchTrace(
            mission_id=mission_id,
            safe_summary="Organ dispatch is disabled in current config.",
            input_hash=input_hash,
        ),
        safe_summary="Organ dispatch is disabled in current config.",
    )


def _no_candidates_result(*, mission_id: str, input_hash: str) -> OrganDispatchResult:
    return OrganDispatchResult(
        mission_id=mission_id,
        status=OrganDispatchStatus.NO_CANDIDATES,
        candidate_results=[],
        trace=OrganDispatchTrace(
            mission_id=mission_id,
            total_action_candidates=0,
            safe_summary="Organ dispatch found no typed action candidates.",
            input_hash=input_hash,
        ),
        safe_summary="Organ dispatch found no typed action candidates.",
    )


def _bridge_failed_result(
    *,
    mission_id: str,
    bridge_result: OrganProposalBridgeResult,
    input_hash: str,
    total_candidates: int,
) -> OrganDispatchResult:
    return OrganDispatchResult(
        mission_id=mission_id,
        status=OrganDispatchStatus.BRIDGE_FAILED,
        candidate_results=[],
        bridge_result=bridge_result,
        trace=OrganDispatchTrace(
            mission_id=mission_id,
            total_action_candidates=total_candidates,
            bridge_rejected_count=len(bridge_result.rejected_candidates),
            safe_summary=f"Bridge rejected all {total_candidates} raw candidates: {bridge_result.status.value}",
            input_hash=input_hash,
        ),
        safe_summary=f"Proposal bridge failed: {bridge_result.status.value}",
    )


def _unsupported_organ_result(
    *,
    candidate: BaseOrganCandidate,
    gate_result: DelegatedActionGateResult,
    config: OrganRuntimeExecutionConfig,
) -> OrganRuntimeExecutionResult:
    from sentinel.agent.organs.runtime_execution import (
        OrganRuntimeExecutionSafetyValidationResult,
        OrganRuntimeExecutionTrace,
    )

    return OrganRuntimeExecutionResult(
        mission_id=candidate.mission_id,
        status=OrganRuntimeExecutionStatus.BLOCKED,
        action_level=candidate.action_level_candidate,
        organ_kind=candidate.organ_kind.value,
        blocked_reason=f"unsupported_organ_kind_{candidate.organ_kind.value}",
        safety_validation=OrganRuntimeExecutionSafetyValidationResult(
            payload_hash=stable_hash(sanitize_metadata({"candidate_id": candidate.candidate_id})),
        ),
        trace=OrganRuntimeExecutionTrace(
            mission_id=candidate.mission_id,
            status=OrganRuntimeExecutionStatus.BLOCKED,
            action_level=candidate.action_level_candidate,
            organ_kind=candidate.organ_kind.value,
            blocked_reason=f"unsupported_organ_kind_{candidate.organ_kind.value}",
            input_hash=stable_hash(sanitize_metadata({"candidate_id": candidate.candidate_id})),
        ),
        safe_summary=f"Organ kind {candidate.organ_kind.value} is not yet supported for runtime execution.",
    )


def _sub_request_build_failed_result(
    *,
    candidate: BaseOrganCandidate,
    gate_result: DelegatedActionGateResult,
    config: OrganRuntimeExecutionConfig,
    reason: str,
) -> OrganRuntimeExecutionResult:
    """Return a blocked result when the typed sub-request cannot be built."""
    from sentinel.agent.organs.runtime_execution import (
        OrganRuntimeExecutionSafetyValidationResult,
        OrganRuntimeExecutionTrace,
    )

    return OrganRuntimeExecutionResult(
        mission_id=candidate.mission_id,
        status=OrganRuntimeExecutionStatus.BLOCKED,
        action_level=candidate.action_level_candidate,
        organ_kind=candidate.organ_kind.value,
        blocked_reason=reason,
        safety_validation=OrganRuntimeExecutionSafetyValidationResult(
            payload_hash=stable_hash(sanitize_metadata({"candidate_id": candidate.candidate_id, "reason": reason})),
        ),
        trace=OrganRuntimeExecutionTrace(
            mission_id=candidate.mission_id,
            status=OrganRuntimeExecutionStatus.BLOCKED,
            action_level=candidate.action_level_candidate,
            organ_kind=candidate.organ_kind.value,
            blocked_reason=reason,
            input_hash=stable_hash(sanitize_metadata({"candidate_id": candidate.candidate_id, "reason": reason})),
        ),
        safe_summary=f"Sub-request build failed for {candidate.organ_kind.value}: {reason}",
    )


def render_organ_dispatch_result_as_untrusted_context(result: OrganDispatchResult) -> str:
    lines = [
        ORGAN_DISPATCH_WARNING,
        "data_not_instruction=true",
        f"mission_id={result.mission_id}",
        f"status={result.status.value}",
        f"candidate_count={len(result.candidate_results)}",
    ]
    for cr in result.candidate_results:
        lines.append(
            f"- candidate={cr.candidate_id}; organ={cr.organ_kind}; "
            f"status={cr.status.value}; gate={cr.gate_decision.value if cr.gate_decision else 'none'}; "
            f"summary={cr.safe_summary}"
        )
    return "\n".join(lines)


def _assert_dispatch_firewall(model: Any) -> None:
    """Firewall: dispatch results cannot grant authority or execution."""
    if getattr(model, "authority_effect", "none") != "none":
        raise ValueError("Organ dispatch cannot grant authority.")
    if getattr(model, "execution_effect", "none") != "none":
        raise ValueError("Organ dispatch cannot grant execution effect.")
    forbidden_flags = {
        "can_grant_authority": "grant authority",
        "can_approve_future_execution": "approve future execution",
        "can_create_delegated_lane": "create delegated lanes",
        "can_execute_more": "execute more",
        "can_override_provider_model": "override provider/model",
    }
    for field, message in forbidden_flags.items():
        if bool(getattr(model, field, False)):
            raise ValueError(f"Organ dispatch cannot {message}.")
