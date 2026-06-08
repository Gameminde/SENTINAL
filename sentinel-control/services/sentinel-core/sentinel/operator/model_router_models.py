from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_contract import ModelCapabilityProfile, UserModelContract
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id


def router_utc_now() -> datetime:
    return datetime.now(UTC)


class ModelCandidateSource(StrEnum):
    EXPLICIT_USER_MODEL_CONTRACT = "explicit_user_model_contract"
    PROVIDER_CATALOG = "provider_catalog"
    LOCAL_RUNTIME_DESCRIPTOR = "local_runtime_descriptor"
    API_DESCRIPTOR = "api_descriptor"


class ModelRuntimeKind(StrEnum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    VLLM = "vllm"
    SGLANG = "sglang"
    OPENAI_COMPATIBLE = "openai_compatible"
    OPENAI_NATIVE = "openai_native"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    GEMINI_NATIVE = "gemini_native"
    DEEPSEEK_COMPATIBLE = "deepseek_compatible"
    MISTRAL_COMPATIBLE = "mistral_compatible"
    XAI_COMPATIBLE = "xai_compatible"
    COHERE_NATIVE = "cohere_native"
    UNKNOWN = "unknown"


class ModelBackendKind(StrEnum):
    OPENAI_COMPATIBLE_CHAT = "openai_compatible_chat"
    OPENAI_RESPONSES = "openai_responses"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    GEMINI_GENERATE_CONTENT = "gemini_generate_content"
    COHERE_CHAT = "cohere_chat"
    DESCRIPTOR_ONLY = "descriptor_only"
    UNKNOWN = "unknown"


class RuntimeProbeStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    REJECTED = "rejected"


class RouterDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _router_data_is_not_authority(self) -> RouterDataModel:
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return redact_operator_value(self.model_dump(mode="json"))


class ModelLatencyProfile(RouterDataModel):
    estimated_latency_seconds: float | None = Field(default=None, ge=0.0)
    latency_class: str = "unknown"
    source: str = "declared_or_catalog_metadata"


class ModelQualityProfile(RouterDataModel):
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    quality_floor_supported: bool = True
    evidence_summary: str = "quality estimate is heuristic"

    @model_validator(mode="after")
    def _sanitize_quality_summary(self) -> ModelQualityProfile:
        self.evidence_summary = redact_operator_text(self.evidence_summary)
        return self


class ModelPrivacyProfile(RouterDataModel):
    local_only: bool = False
    cloud_provider: bool = True
    privacy_score: float = Field(default=0.5, ge=0.0, le=1.0)
    prompt_retention: str = "unknown"
    safe_summary: str = "privacy posture is metadata-only"

    @model_validator(mode="after")
    def _sanitize_privacy_summary(self) -> ModelPrivacyProfile:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class ModelEnergyProfile(RouterDataModel):
    energy_estimate_status: str = "unknown"
    energy_score: float | None = Field(default=None, ge=0.0, le=1.0)
    safe_summary: str = "energy estimate unavailable"

    @model_validator(mode="after")
    def _sanitize_energy_summary(self) -> ModelEnergyProfile:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class ModelContextWindowProfile(RouterDataModel):
    candidate_context_window_tokens: int = Field(gt=0)
    required_context_tokens: int | None = Field(default=None, ge=0)
    context_fit_score: float = Field(default=1.0, ge=0.0, le=1.0)
    fits_required_context: bool = True

    def for_requirement(self, required_tokens: int | None) -> ModelContextWindowProfile:
        if required_tokens is None or required_tokens <= 0:
            return self.model_copy(
                update={
                    "required_context_tokens": required_tokens,
                    "context_fit_score": 1.0,
                    "fits_required_context": True,
                }
            )
        ratio = min(1.0, self.candidate_context_window_tokens / max(required_tokens, 1))
        return self.model_copy(
            update={
                "required_context_tokens": required_tokens,
                "context_fit_score": round(ratio, 6),
                "fits_required_context": self.candidate_context_window_tokens >= required_tokens,
            }
        )


class ModelHardwareProfile(RouterDataModel):
    required_runtime_kind: ModelRuntimeKind = ModelRuntimeKind.UNKNOWN
    requires_gpu: bool = False
    min_memory_mb: int | None = Field(default=None, ge=0)
    safe_summary: str = "hardware requirement is metadata-only"

    @model_validator(mode="after")
    def _sanitize_hardware_summary(self) -> ModelHardwareProfile:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class HardwareProbeResult(RouterDataModel):
    probe_id: str = Field(default_factory=lambda: new_id("hardware_probe"))
    read_only: bool = True
    network_scan_attempted: bool = False
    credential_probe_attempted: bool = False
    config_mutation_attempted: bool = False
    safe_summary: str = "Local hardware metadata collected read-only."

    @model_validator(mode="after")
    def _hardware_probe_stays_safe(self) -> HardwareProbeResult:
        if not self.read_only or self.network_scan_attempted or self.credential_probe_attempted or self.config_mutation_attempted:
            raise ValueError("hardware probe must be local read-only metadata")
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class HardwareInventorySnapshot(RouterDataModel):
    snapshot_id: str = Field(default_factory=lambda: new_id("hardware_snapshot"))
    mission_id: str | None = None
    route_id: str | None = None
    platform_system: str
    platform_release: str
    machine: str
    processor_hash: str | None = None
    python_runtime: str
    cpu_count: int = Field(ge=1)
    memory_total_mb: int | None = Field(default=None, ge=0)
    gpu_available: bool | None = None
    gpu_probe_status: str = "unknown"
    hardware_probe_result: HardwareProbeResult = Field(default_factory=HardwareProbeResult)
    created_at: datetime = Field(default_factory=router_utc_now)
    snapshot_hash: str = ""

    def with_hash(self) -> HardwareInventorySnapshot:
        payload = self.safe_model_dump()
        payload["snapshot_hash"] = ""
        return self.model_copy(update={"snapshot_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["snapshot_hash"]
        payload["snapshot_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RuntimeAvailabilityProbe(RouterDataModel):
    probe_id: str = Field(default_factory=lambda: new_id("runtime_probe"))
    mission_id: str | None = None
    route_id: str | None = None
    candidate_id: str
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None
    runtime_kind: ModelRuntimeKind = ModelRuntimeKind.UNKNOWN
    status: RuntimeProbeStatus = RuntimeProbeStatus.UNKNOWN
    endpoint_ref_hash: str | None = None
    endpoint_is_loopback: bool = False
    read_only: bool = True
    network_scan_attempted: bool = False
    credential_probe_attempted: bool = False
    config_mutation_attempted: bool = False
    provider_call_attempted: bool = False
    model_server_started: bool = False
    model_download_attempted: bool = False
    latency_ms: float | None = Field(default=None, ge=0.0)
    safe_summary: str = "Runtime availability not probed."
    created_at: datetime = Field(default_factory=router_utc_now)
    probe_hash: str = ""

    @model_validator(mode="after")
    def _runtime_probe_stays_safe(self) -> RuntimeAvailabilityProbe:
        if (
            not self.read_only
            or self.network_scan_attempted
            or self.credential_probe_attempted
            or self.config_mutation_attempted
            or self.provider_call_attempted
            or self.model_server_started
            or self.model_download_attempted
        ):
            raise ValueError("runtime availability probe must be read-only and non-mutating")
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> RuntimeAvailabilityProbe:
        payload = self.safe_model_dump()
        payload["probe_hash"] = ""
        return self.model_copy(update={"probe_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["probe_hash"]
        payload["probe_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ModelCandidate(RouterDataModel):
    candidate_id: str = Field(default_factory=lambda: new_id("model_candidate"))
    route_id: str | None = None
    source: ModelCandidateSource
    runtime_kind: ModelRuntimeKind
    backend_kind: ModelBackendKind
    provider_id: str
    backend_id: str
    model_id: str
    display_name: str
    runtime_endpoint: str | None = None
    selected_user_model_contract_id: str | None = None
    user_model_contract_hash: str | None = None
    provider_catalog_ref_hash: str | None = None
    cost_profile: ModelCostProfile | None = None
    capability_profile: ModelCapabilityProfile | None = None
    hardware_profile: ModelHardwareProfile | None = None
    latency_profile: ModelLatencyProfile = Field(default_factory=ModelLatencyProfile)
    quality_profile: ModelQualityProfile = Field(default_factory=ModelQualityProfile)
    privacy_profile: ModelPrivacyProfile = Field(default_factory=ModelPrivacyProfile)
    energy_profile: ModelEnergyProfile = Field(default_factory=ModelEnergyProfile)
    context_window_profile: ModelContextWindowProfile | None = None
    provider_native_tools_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=router_utc_now)
    candidate_hash: str = ""

    @property
    def is_local_runtime(self) -> bool:
        return self.runtime_kind in {
            ModelRuntimeKind.OLLAMA,
            ModelRuntimeKind.LLAMA_CPP,
            ModelRuntimeKind.VLLM,
            ModelRuntimeKind.SGLANG,
        } or self.privacy_profile.local_only

    @model_validator(mode="after")
    def _candidate_is_safe_descriptor(self) -> ModelCandidate:
        self.display_name = redact_operator_text(self.display_name)
        self.metadata = _sanitize_router_metadata(self.metadata)
        if self.provider_native_tools_enabled:
            raise ValueError("provider-native tools are not allowed in model router candidates")
        if not self.provider_id.strip() or not self.backend_id.strip() or not self.model_id.strip():
            raise ValueError("model router candidate requires explicit provider/backend/model identity")
        return self

    def with_hash(self) -> ModelCandidate:
        payload = self.safe_model_dump()
        payload["candidate_hash"] = ""
        return self.model_copy(update={"candidate_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["candidate_hash"]
        payload["candidate_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteConstraint(RouterDataModel):
    name: str
    value: Any
    required: bool = True
    safe_reason: str = "route constraint"

    @model_validator(mode="after")
    def _sanitize_constraint(self) -> RouteConstraint:
        self.name = redact_operator_text(self.name)
        self.safe_reason = redact_operator_text(self.safe_reason)
        self.value = redact_operator_value(self.value)
        reject_operator_control_payload({"name": self.name, "value": self.value}, context="route_constraint")
        return self


class RoutePolicy(RouterDataModel):
    policy_id: str = Field(default_factory=lambda: new_id("route_policy"))
    quality_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    max_estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    max_estimated_latency_seconds: float | None = Field(default=None, ge=0.0)
    privacy_requirement: str = "operator_policy"
    local_only: bool = False
    cloud_allowed: bool = True
    hardware_requirement: str | None = None
    context_window_requirement: int | None = Field(default=None, ge=0)
    energy_preference: str = "unknown"
    reliability_requirement: str = "unknown"
    operator_confirmation_required: bool = False
    allowed_provider_ids: list[str] = Field(default_factory=list)
    allowed_backend_ids: list[str] = Field(default_factory=list)
    allowed_model_ids: list[str] = Field(default_factory=list)
    blocked_provider_ids: list[str] = Field(default_factory=list)
    blocked_backend_ids: list[str] = Field(default_factory=list)
    blocked_model_ids: list[str] = Field(default_factory=list)
    constraints: list[RouteConstraint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    policy_hash: str = ""

    @model_validator(mode="after")
    def _policy_is_constraint_only(self) -> RoutePolicy:
        self.privacy_requirement = redact_operator_text(self.privacy_requirement)
        self.hardware_requirement = redact_operator_text(self.hardware_requirement) if self.hardware_requirement else None
        self.energy_preference = redact_operator_text(self.energy_preference)
        self.reliability_requirement = redact_operator_text(self.reliability_requirement)
        self.metadata = _sanitize_router_metadata(self.metadata)
        return self

    def with_hash(self) -> RoutePolicy:
        payload = self.safe_model_dump()
        payload["policy_hash"] = ""
        return self.model_copy(update={"policy_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["policy_hash"]
        payload["policy_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ModelRouterConfig(RouterDataModel):
    require_operator_approval_for_cloud_binding: bool = True
    allow_remote_availability_probes: bool = False
    allow_provider_native_tools: bool = False
    safe_local_probe_timeout_seconds: float = Field(default=0.2, gt=0.0, le=2.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _config_is_safe(self) -> ModelRouterConfig:
        if self.allow_provider_native_tools:
            raise ValueError("provider-native tools are not allowed in ModelRouterConfig")
        self.metadata = _sanitize_router_metadata(self.metadata)
        return self


class RouteObjective(RouterDataModel):
    objective_id: str = Field(default_factory=lambda: new_id("route_objective"))
    mission_id: str | None = None
    run_id: str | None = None
    task_summary: str
    required_context_tokens: int | None = Field(default=None, ge=0)
    quality_goal: str = "balanced"
    privacy_goal: str = "operator_policy"
    metadata: dict[str, Any] = Field(default_factory=dict)
    objective_hash: str = ""

    @model_validator(mode="after")
    def _objective_is_safe(self) -> RouteObjective:
        self.task_summary = redact_operator_text(self.task_summary)
        self.quality_goal = redact_operator_text(self.quality_goal)
        self.privacy_goal = redact_operator_text(self.privacy_goal)
        self.metadata = _sanitize_router_metadata(self.metadata)
        return self

    def with_hash(self) -> RouteObjective:
        payload = self.safe_model_dump()
        payload["objective_hash"] = ""
        return self.model_copy(update={"objective_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["objective_hash"]
        payload["objective_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteSimulationRequest(RouterDataModel):
    request_id: str = Field(default_factory=lambda: new_id("route_request"))
    route_id: str = Field(default_factory=lambda: new_id("model_route"))
    mission_id: str | None = None
    run_id: str | None = None
    objective: RouteObjective
    policy: RoutePolicy
    candidates: list[ModelCandidate] = Field(default_factory=list)
    hardware_snapshot: HardwareInventorySnapshot
    runtime_probes: list[RuntimeAvailabilityProbe] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=router_utc_now)
    request_hash: str = ""

    def with_hash(self) -> RouteSimulationRequest:
        payload = self.safe_model_dump()
        payload["request_hash"] = ""
        return self.model_copy(update={"request_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["request_hash"]
        payload["request_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteRejectionReason(RouterDataModel):
    code: str
    detail: str
    blocking: bool = True
    policy_field: str | None = None

    @model_validator(mode="after")
    def _sanitize_reason(self) -> RouteRejectionReason:
        self.code = redact_operator_text(self.code)
        self.detail = redact_operator_text(self.detail)
        self.policy_field = redact_operator_text(self.policy_field) if self.policy_field else None
        return self


class RouteCandidateScore(RouterDataModel):
    candidate_id: str
    provider_id: str
    backend_id: str
    model_id: str
    quality_score: float = Field(ge=0.0, le=1.0)
    cost_score: float = Field(ge=0.0, le=1.0)
    latency_score: float = Field(ge=0.0, le=1.0)
    privacy_score: float = Field(ge=0.0, le=1.0)
    hardware_fit_score: float = Field(ge=0.0, le=1.0)
    context_fit_score: float = Field(ge=0.0, le=1.0)
    energy_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reliability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    policy_fit: bool
    overall_score: float = Field(ge=0.0, le=1.0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    estimated_latency_seconds: float | None = Field(default=None, ge=0.0)
    privacy_posture: str = "unknown"
    hardware_fit: str = "unknown"
    context_fit: str = "unknown"
    rejection_reasons: list[RouteRejectionReason] = Field(default_factory=list)


class RouteSimulationResult(RouterDataModel):
    simulation_id: str = Field(default_factory=lambda: new_id("route_sim"))
    route_id: str
    mission_id: str | None = None
    request_hash: str
    policy_hash: str
    objective_hash: str
    candidate_scores: list[RouteCandidateScore] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    estimated_latency_seconds: float | None = Field(default=None, ge=0.0)
    privacy_posture: str = "unknown"
    hardware_fit: str = "unknown"
    context_fit: str = "unknown"
    requires_operator_approval: bool = False
    created_at: datetime = Field(default_factory=router_utc_now)
    simulation_hash: str = ""

    def with_hash(self) -> RouteSimulationResult:
        payload = self.safe_model_dump()
        payload["simulation_hash"] = ""
        return self.model_copy(update={"simulation_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["simulation_hash"]
        payload["simulation_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteDecision(RouterDataModel):
    decision_id: str = Field(default_factory=lambda: new_id("route_decision"))
    route_id: str
    mission_id: str | None = None
    route_policy_ref: str
    route_policy_hash: str
    simulation_id: str
    simulation_hash: str
    candidate_scores: list[RouteCandidateScore] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    rejected_candidate_reasons: dict[str, list[RouteRejectionReason]] = Field(default_factory=dict)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    estimated_latency_seconds: float | None = Field(default=None, ge=0.0)
    privacy_posture: str = "unknown"
    hardware_fit: str = "unknown"
    context_fit: str = "unknown"
    requires_operator_approval: bool = False
    route_receipt_ref: str | None = None
    route_receipt_hash: str | None = None
    accepted: bool = False
    safe_summary: str = "Route decision is advisory data only."
    created_at: datetime = Field(default_factory=router_utc_now)
    decision_hash: str = ""

    @model_validator(mode="after")
    def _decision_summary_is_safe(self) -> RouteDecision:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> RouteDecision:
        payload = self.safe_model_dump()
        payload["decision_hash"] = ""
        return self.model_copy(update={"decision_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["decision_hash"]
        payload["decision_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteApprovalRecord(RouterDataModel):
    approval_id: str = Field(default_factory=lambda: new_id("route_approval"))
    route_id: str
    decision_id: str
    mission_id: str | None = None
    approved_by: str
    approval_source: str = "operator"
    approved: bool = True
    safe_summary: str = "Operator approved route binding."
    created_at: datetime = Field(default_factory=router_utc_now)
    approval_hash: str = ""

    @model_validator(mode="after")
    def _approval_source_must_be_operator(self) -> RouteApprovalRecord:
        if self.approval_source not in {"operator", "operator_policy", "manual_operator"}:
            raise ValueError("operator approval source required for model route binding")
        self.approved_by = redact_operator_text(self.approved_by)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> RouteApprovalRecord:
        payload = self.safe_model_dump()
        payload["approval_hash"] = ""
        return self.model_copy(update={"approval_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["approval_hash"]
        payload["approval_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteExecutionBinding(RouterDataModel):
    binding_id: str = Field(default_factory=lambda: new_id("route_binding"))
    route_id: str
    decision_id: str
    candidate_id: str
    mission_id: str | None = None
    selected_provider_id: str
    selected_backend_id: str
    selected_model_id: str
    user_model_contract: UserModelContract
    operator_approval_ref: str | None = None
    created_at: datetime = Field(default_factory=router_utc_now)
    binding_hash: str = ""

    @model_validator(mode="after")
    def _binding_is_explicit_contract_only(self) -> RouteExecutionBinding:
        contract = self.user_model_contract
        if contract.model_override_attempted:
            raise ValueError("UserModelContract model override is not allowed")
        if (
            contract.selected_provider_id != self.selected_provider_id
            or contract.selected_backend_id != self.selected_backend_id
            or contract.selected_model != self.selected_model_id
        ):
            raise ValueError("RouteExecutionBinding selected identity must match explicit UserModelContract")
        return self

    def with_hash(self) -> RouteExecutionBinding:
        payload = self.safe_model_dump()
        payload["binding_hash"] = ""
        return self.model_copy(update={"binding_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["binding_hash"]
        payload["binding_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteDecisionReceipt(RouterDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("route_receipt"))
    route_id: str
    decision_id: str
    mission_id: str | None = None
    candidate_ids: list[str] = Field(default_factory=list)
    policy_hash: str
    simulation_hash: str
    selected_candidate_id: str | None = None
    rejection_reasons: dict[str, list[RouteRejectionReason]] = Field(default_factory=dict)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    estimated_latency_seconds: float | None = Field(default=None, ge=0.0)
    privacy_summary: str = "unknown"
    hardware_summary: str = "unknown"
    context_summary: str = "unknown"
    operator_approval_ref: str | None = None
    user_model_contract_binding_hash: str | None = None
    telemetry_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    selected_provider_id: str | None = None
    selected_backend_id: str | None = None
    selected_model_id: str | None = None
    created_at: datetime = Field(default_factory=router_utc_now)
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _receipt_is_safe(self) -> RouteDecisionReceipt:
        self.privacy_summary = redact_operator_text(self.privacy_summary)
        self.hardware_summary = redact_operator_text(self.hardware_summary)
        self.context_summary = redact_operator_text(self.context_summary)
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        return self

    def with_hash(self) -> RouteDecisionReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["receipt_hash"]
        payload["receipt_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteTelemetrySummary(RouterDataModel):
    route_id: str
    mission_id: str | None = None
    event_refs: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Model router telemetry summary."
    certified_mode: bool | None = None
    tampered: bool = False
    summary_hash: str = ""

    @model_validator(mode="after")
    def _telemetry_summary_is_safe(self) -> RouteTelemetrySummary:
        self.event_refs = sanitize_operator_refs(self.event_refs)
        self.metric_refs = sanitize_operator_refs(self.metric_refs)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> RouteTelemetrySummary:
        payload = self.safe_model_dump()
        payload["summary_hash"] = ""
        return self.model_copy(update={"summary_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["summary_hash"]
        payload["summary_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RouteReplayView(RouterDataModel):
    mission_id: str
    route_id: str
    candidates: list[ModelCandidate] = Field(default_factory=list)
    hardware_snapshot: HardwareInventorySnapshot | None = None
    runtime_probes: list[RuntimeAvailabilityProbe] = Field(default_factory=list)
    route_policy: RoutePolicy | None = None
    simulation: RouteSimulationResult | None = None
    decision: RouteDecision | None = None
    receipt: RouteDecisionReceipt | None = None
    approval_record: RouteApprovalRecord | None = None
    binding_record: RouteExecutionBinding | None = None
    telemetry_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    final_selected_user_model_contract: UserModelContract | None = None
    tampered: bool = False
    reexecuted_actions: bool = False


def _sanitize_router_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    _reject_router_forbidden_payload(metadata)
    sanitized = redact_operator_value(metadata)
    reject_operator_control_payload(sanitized, context="model_router_metadata")
    return sanitized


def _reject_router_forbidden_payload(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if "provider_native_tool" in lowered or "server_side_tool" in lowered:
                raise ValueError("provider-native tools are not allowed")
            if "fallback" in lowered or lowered in {"auto", "auto_route", "autoroute", "auto_routing"}:
                raise ValueError("fallback/AUTO routing is not allowed")
            if lowered in {"provider_key", "api_key", "api_key_value", "credential_value", "raw_secret"}:
                raise ValueError("provider key persistence is not allowed")
            if lowered in {"raw_prompt", "prompt_text", "prompt"} and "hash" not in lowered:
                raise ValueError("raw prompt persistence is not allowed")
            if lowered in {"raw_provider_response", "provider_response", "raw_response"} and "hash" not in lowered:
                raise ValueError("raw provider response persistence is not allowed")
            if lowered in {"raw_reasoning", "reasoning", "reasoning_content", "thinking"} and "hash" not in lowered:
                raise ValueError("raw reasoning persistence is not allowed")
            _reject_router_forbidden_payload(item, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            _reject_router_forbidden_payload(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        redacted = redact_operator_text(value)
        if redacted != value:
            raise ValueError("provider key or raw secret persistence is not allowed")
        lowered = value.lower()
        if "provider_native_tools" in lowered:
            raise ValueError("provider-native tools are not allowed")
        if "fallback" in lowered or lowered.strip() == "auto":
            raise ValueError("fallback/AUTO routing is not allowed")
