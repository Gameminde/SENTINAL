from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.desktop_sidecar_models import (
    DesktopActionKind,
    DesktopBeforeAfterEvidence,
    DesktopControlMode,
    DesktopDataModel,
    DesktopFinalGateDecision,
    DesktopHardwareMetricSnapshot,
    DesktopMetricValue,
    DesktopMonitoringPolicy,
    DesktopMonitoringResult,
    DesktopMonitoringSession,
    DesktopPermissionPolicy,
    DesktopSensorSnapshot,
    DesktopSidecarFinalGateCertificate,
    DesktopSidecarReceipt,
)
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id


def live_desktop_utc_now() -> datetime:
    return datetime.now(UTC)


class LiveDesktopBackendKind(StrEnum):
    CONTRACT_ONLY = "contract_only"
    FAKE_BACKEND = "fake_backend"
    INJECTED_TRANSPORT = "injected_transport"
    LOCAL_OBSERVATION_BACKEND = "local_observation_backend"
    LOCAL_MONITORING_BACKEND = "local_monitoring_backend"
    LIVE_OPT_IN_ACTION_BACKEND = "live_opt_in_action_backend"


class LiveDesktopBackendMaturity(StrEnum):
    CONTRACT_ONLY = "contract_only"
    FAKE_BACKEND = "fake_backend"
    INJECTED_TRANSPORT = "injected_transport"
    LOCAL_OBSERVATION_BACKEND = "local_observation_backend"
    LOCAL_MONITORING_BACKEND = "local_monitoring_backend"
    LIVE_OPT_IN_ACTION_BACKEND = "live_opt_in_action_backend"
    PRODUCTION_READY_BACKEND = "production_ready_backend"


class DesktopOperatorSessionStateKind(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    REVOKED = "revoked"


class LiveDesktopBackendCapabilityProfile(DesktopDataModel):
    supports_live_observation: bool = True
    supports_system_monitoring: bool = True
    supports_fake_actions: bool = True
    supports_live_opt_in_actions: bool = False
    supports_clipboard: bool = False
    supports_service_shape: bool = True
    supports_tray_shape: bool = True
    safe_summary: str = "Live desktop backend capability descriptor."

    @model_validator(mode="after")
    def _summary_is_safe(self) -> LiveDesktopBackendCapabilityProfile:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class DesktopPermissionProfile(DesktopDataModel):
    monitoring_enabled: bool = False
    control_mode: DesktopControlMode = DesktopControlMode.OBSERVE_ONLY
    allowed_apps: list[str] = Field(default_factory=list)
    blocked_apps: list[str] = Field(default_factory=list)
    allowed_windows: list[str] = Field(default_factory=list)
    blocked_windows: list[str] = Field(default_factory=list)
    blocked_region_labels: list[str] = Field(default_factory=list)
    allow_clipboard: bool = False
    always_on_allowed: bool = False
    retention_policy: str = "hash_and_summary_only"
    operator_visible: bool = True
    production_service_ready: bool = False

    @model_validator(mode="after")
    def _profile_is_safe(self) -> DesktopPermissionProfile:
        if self.production_service_ready:
            raise ValueError("live desktop v1 cannot claim production OS-service readiness")
        self.allowed_apps = [redact_operator_text(item) for item in self.allowed_apps]
        self.blocked_apps = [redact_operator_text(item) for item in self.blocked_apps]
        self.allowed_windows = [redact_operator_text(item) for item in self.allowed_windows]
        self.blocked_windows = [redact_operator_text(item) for item in self.blocked_windows]
        self.blocked_region_labels = [_safe_label(item) for item in self.blocked_region_labels]
        self.retention_policy = redact_operator_text(self.retention_policy)
        return self


class LiveDesktopBackendConfig(DesktopDataModel):
    backend_id: str
    sidecar_id: str
    kind: LiveDesktopBackendKind
    maturity: LiveDesktopBackendMaturity
    display_name: str
    capability_profile: LiveDesktopBackendCapabilityProfile = Field(default_factory=LiveDesktopBackendCapabilityProfile)
    permission_policy: DesktopPermissionPolicy = Field(default_factory=DesktopPermissionPolicy)
    action_policy: Any = None
    permission_profile: DesktopPermissionProfile = Field(default_factory=DesktopPermissionProfile)
    explicit_live_opt_in: bool = False
    endpoint_ref_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=live_desktop_utc_now)
    config_hash: str = ""

    @model_validator(mode="after")
    def _config_is_safe(self) -> LiveDesktopBackendConfig:
        if not self.backend_id.strip():
            raise ValueError("live desktop backend id is required")
        if not self.sidecar_id.strip():
            raise ValueError("live desktop backend requires sidecar id")
        if self.maturity is LiveDesktopBackendMaturity.PRODUCTION_READY_BACKEND:
            raise ValueError("live desktop v1 cannot claim production-ready backend maturity")
        if (self.kind is LiveDesktopBackendKind.LIVE_OPT_IN_ACTION_BACKEND or self.maturity is LiveDesktopBackendMaturity.LIVE_OPT_IN_ACTION_BACKEND) and not self.explicit_live_opt_in:
            raise ValueError("desktop live action backend is opt-in")
        self.display_name = redact_operator_text(self.display_name)
        self.metadata = _sanitize_live_payload(self.metadata, context="live_desktop_backend_config")
        return self

    def with_hash(self) -> LiveDesktopBackendConfig:
        payload = self.safe_model_dump()
        payload["config_hash"] = ""
        return self.model_copy(update={"config_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["config_hash"]
        payload["config_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopOperatorSessionPolicy(DesktopDataModel):
    control_mode: DesktopControlMode = DesktopControlMode.OBSERVE_ONLY
    monitoring_enabled: bool = False
    always_on_allowed: bool = False
    operator_visible: bool = True
    allowed_apps: list[str] = Field(default_factory=list)
    allowed_windows: list[str] = Field(default_factory=list)
    allowed_action_kinds: list[DesktopActionKind] = Field(default_factory=list)
    max_actions_per_session: int = Field(default=10, ge=0)
    require_approval_for_actions: bool = True

    @model_validator(mode="after")
    def _session_policy_is_safe(self) -> DesktopOperatorSessionPolicy:
        if not self.operator_visible:
            raise ValueError("desktop operator sessions must be operator-visible")
        self.allowed_apps = [redact_operator_text(item) for item in self.allowed_apps]
        self.allowed_windows = [redact_operator_text(item) for item in self.allowed_windows]
        return self


class DesktopOperatorSession(DesktopDataModel):
    session_id: str = Field(default_factory=lambda: new_id("desktop_operator_session"))
    backend_id: str
    mission_id: str
    policy: DesktopOperatorSessionPolicy
    state: DesktopOperatorSessionStateKind = DesktopOperatorSessionStateKind.RUNNING
    action_count: int = 0
    last_snapshot_ref: str | None = None
    last_action_ref: str | None = None
    kill_switch_engaged: bool = False
    started_at: datetime = Field(default_factory=live_desktop_utc_now)
    completed_at: datetime | None = None
    session_hash: str = ""

    def with_hash(self) -> DesktopOperatorSession:
        payload = self.safe_model_dump()
        payload["session_hash"] = ""
        return self.model_copy(update={"session_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["session_hash"]
        payload["session_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopPermissionUiShape(DesktopDataModel):
    backend_id: str
    mission_id: str
    control_mode: DesktopControlMode
    monitoring_enabled: bool = False
    blocked_apps: list[str] = Field(default_factory=list)
    blocked_windows: list[str] = Field(default_factory=list)
    retention_policy: str = "hash_and_summary_only"
    operator_visible: bool = True
    safe_summary: str = "Desktop permission UI shape created."


class DesktopTrayServiceShape(DesktopDataModel):
    backend_id: str
    mission_id: str
    tray_state: str = "modeled_only"
    monitoring_enabled: bool = False
    active_mission_ref: str | None = None
    last_observation_ref: str | None = None
    last_action_ref: str | None = None
    kill_switch_state: str = "ready"
    operator_visible_audit_summary: str = "Desktop tray/service shape is modeled; no production tray service is installed."


class DesktopServiceSupervisorShape(DesktopDataModel):
    backend_id: str
    mission_id: str
    service_state: str = "modeled_only"
    production_os_service_ready: bool = False
    supervisor_ref_hash: str = ""

    @model_validator(mode="after")
    def _no_service_overclaim(self) -> DesktopServiceSupervisorShape:
        if self.production_os_service_ready:
            raise ValueError("live desktop v1 cannot claim production OS service readiness")
        if not self.supervisor_ref_hash:
            self.supervisor_ref_hash = stable_hash({"backend_id": self.backend_id, "mission_id": self.mission_id, "service_state": self.service_state})
        return self


class DesktopActionIdempotencyKey(DesktopDataModel):
    key_hash: str

    @classmethod
    def from_command(cls, mission_ref: str, backend_id: str, action_kind: str, target_ref: str) -> DesktopActionIdempotencyKey:
        return cls(key_hash=stable_hash({"mission_ref": mission_ref, "backend_id": backend_id, "action_kind": action_kind, "target_ref": target_ref}))


class DesktopActionCommand(DesktopDataModel):
    command_id: str = Field(default_factory=lambda: new_id("desktop_live_command"))
    backend_id: str
    action_kind: DesktopActionKind
    app_ref: str | None = None
    window_ref: str | None = None
    target_region_label: str | None = None
    idempotency_key: DesktopActionIdempotencyKey
    requested_by: str = "operator"
    text: str | None = Field(default=None, exclude=True, repr=False)
    hotkey: str | None = None
    clipboard_text: str | None = Field(default=None, exclude=True, repr=False)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    command_hash: str = ""

    @model_validator(mode="after")
    def _command_is_safe(self) -> DesktopActionCommand:
        if self.requested_by not in {"operator", "operator_policy", "manual_operator"}:
            return self
        if self.clipboard_text is not None:
            raise ValueError("desktop clipboard text is blocked by default in v1")
        if self.text and _looks_secret_like(self.text):
            raise ValueError("desktop action text contains secret-like content")
        self.app_ref = redact_operator_text(self.app_ref) if self.app_ref else None
        self.window_ref = redact_operator_text(self.window_ref) if self.window_ref else None
        self.target_region_label = _safe_label(self.target_region_label) if self.target_region_label else None
        self.hotkey = redact_operator_text(self.hotkey) if self.hotkey else None
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        if not self.evidence_refs:
            raise ValueError("desktop action command requires evidence refs")
        self.metadata = _sanitize_live_payload(self.metadata, context="desktop_action_command")
        if not self.command_hash:
            self.command_hash = stable_hash(self.safe_model_dump())
        return self


class DesktopActionSafetyCheck(DesktopDataModel):
    check_name: str
    passed: bool
    reason_hash: str | None = None

    @model_validator(mode="after")
    def _check_name_is_safe(self) -> DesktopActionSafetyCheck:
        self.check_name = _safe_label(self.check_name)
        return self


class DesktopActionExecutionPlan(DesktopDataModel):
    plan_id: str = Field(default_factory=lambda: new_id("desktop_action_plan"))
    backend_id: str
    mission_id: str
    session_id: str
    command: DesktopActionCommand
    safety_checks: list[DesktopActionSafetyCheck] = Field(default_factory=list)
    approval_required: bool = True
    blocked_reason: str | None = None
    plan_hash: str = ""

    @model_validator(mode="after")
    def _plan_is_not_execution(self) -> DesktopActionExecutionPlan:
        self.blocked_reason = _safe_label(self.blocked_reason) if self.blocked_reason else None
        return self

    def with_hash(self) -> DesktopActionExecutionPlan:
        payload = self.safe_model_dump()
        payload["plan_hash"] = ""
        return self.model_copy(update={"plan_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["plan_hash"]
        payload["plan_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopActionApprovalRecord(DesktopDataModel):
    approval_id: str = Field(default_factory=lambda: new_id("desktop_live_action_approval"))
    plan_id: str
    approved: bool = True
    approval_source: str = "operator"
    approved_by: str = "operator"
    created_at: datetime = Field(default_factory=live_desktop_utc_now)
    approval_hash: str = ""

    @model_validator(mode="after")
    def _approval_is_operator_only(self) -> DesktopActionApprovalRecord:
        if self.approval_source not in {"operator", "operator_policy", "manual_operator"}:
            raise ValueError("operator approval source required for desktop live action")
        self.approved_by = redact_operator_text(self.approved_by)
        return self

    def with_hash(self) -> DesktopActionApprovalRecord:
        payload = self.safe_model_dump()
        payload["approval_hash"] = ""
        return self.model_copy(update={"approval_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["approval_hash"]
        payload["approval_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopActionReceipt(DesktopSidecarReceipt):
    command_id: str | None = None
    plan_id: str | None = None
    idempotency_key_hash: str | None = None


class DesktopActionExecutionResult(DesktopDataModel):
    execution_result_id: str = Field(default_factory=lambda: new_id("desktop_live_action_result"))
    backend_id: str
    mission_id: str
    session_id: str
    plan_id: str
    action_kind: DesktopActionKind
    status: str
    blocked_reason: str | None = None
    before_after_evidence: DesktopBeforeAfterEvidence | None = None
    action_receipt: DesktopActionReceipt | None = None
    finalgate_certificate: DesktopSidecarFinalGateCertificate | None = None
    safe_summary: str = "Desktop live action result."
    created_at: datetime = Field(default_factory=live_desktop_utc_now)
    result_hash: str = ""

    @model_validator(mode="after")
    def _result_is_safe(self) -> DesktopActionExecutionResult:
        self.status = _safe_label(self.status)
        self.blocked_reason = _safe_label(self.blocked_reason) if self.blocked_reason else None
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> DesktopActionExecutionResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["result_hash"]
        payload["result_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopMonitoringTick(DesktopDataModel):
    tick_id: str = Field(default_factory=lambda: new_id("desktop_monitoring_tick"))
    session_id: str
    backend_id: str
    mission_id: str
    monotonic_index: int = Field(default=0, ge=0)
    result: DesktopMonitoringResult | None = None
    status: str = "completed"
    tick_hash: str = ""

    def with_hash(self) -> DesktopMonitoringTick:
        payload = self.safe_model_dump()
        payload["tick_hash"] = ""
        return self.model_copy(update={"tick_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["tick_hash"]
        payload["tick_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopBenchmarkTask(DesktopDataModel):
    task_id: str = Field(default_factory=lambda: new_id("desktop_benchmark_task"))
    name: str
    expected_status: str = "passed"


class DesktopBenchmarkScenario(DesktopDataModel):
    scenario_id: str = Field(default_factory=lambda: new_id("desktop_benchmark_scenario"))
    name: str
    tasks: list[DesktopBenchmarkTask] = Field(default_factory=list)
    fake_backend_only: bool = True

    @classmethod
    def standard_fake_gauntlet(cls) -> DesktopBenchmarkScenario:
        names = [
            "observe active window",
            "list running apps",
            "collect CPU/RAM snapshot",
            "collect process snapshot",
            "preview click action",
            "execute fake click action",
            "execute fake type action",
            "blocked sensitive region",
            "blocked unauthorized app",
            "blocked action after kill",
            "blocked action after revocation",
            "replay without re-action",
        ]
        return cls(name="live desktop fake backend gauntlet", tasks=[DesktopBenchmarkTask(name=name) for name in names])


class DesktopBenchmarkResult(DesktopDataModel):
    result_id: str = Field(default_factory=lambda: new_id("desktop_benchmark_result"))
    passed_task_count: int = Field(default=0, ge=0)
    failed_task_count: int = Field(default=0, ge=0)
    pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    replay_no_reaction_verified: bool = False
    safe_summary: str = "Desktop benchmark result."
    result_hash: str = ""

    def with_hash(self) -> DesktopBenchmarkResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})


class DesktopBenchmarkRun(DesktopDataModel):
    run_id: str = Field(default_factory=lambda: new_id("desktop_benchmark_run"))
    backend_id: str
    mission_id: str
    scenario: DesktopBenchmarkScenario
    result: DesktopBenchmarkResult | None = None
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=live_desktop_utc_now)
    completed_at: datetime | None = None
    run_hash: str = ""

    def with_hash(self) -> DesktopBenchmarkRun:
        payload = self.safe_model_dump()
        payload["run_hash"] = ""
        return self.model_copy(update={"run_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["run_hash"]
        payload["run_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopMonitoringReplayView(DesktopDataModel):
    mission_id: str
    monitoring_ticks: list[DesktopMonitoringTick] = Field(default_factory=list)
    recollected_system_metrics: bool = False
    reexecuted_actions: bool = False


class DesktopBenchmarkReplayView(DesktopDataModel):
    mission_id: str
    benchmark_runs: list[DesktopBenchmarkRun] = Field(default_factory=list)
    recollected_system_metrics: bool = False
    reexecuted_actions: bool = False


class LiveDesktopBackendReplayView(DesktopDataModel):
    mission_id: str
    configs: list[LiveDesktopBackendConfig] = Field(default_factory=list)
    sessions: list[DesktopOperatorSession] = Field(default_factory=list)
    monitoring_results: list[DesktopMonitoringResult] = Field(default_factory=list)
    monitoring_ticks: list[DesktopMonitoringTick] = Field(default_factory=list)
    action_plans: list[DesktopActionExecutionPlan] = Field(default_factory=list)
    action_results: list[DesktopActionExecutionResult] = Field(default_factory=list)
    benchmark_runs: list[DesktopBenchmarkRun] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    recollected_system_metrics: bool = False
    reexecuted_actions: bool = False


class LiveDesktopBackendTelemetrySummary(DesktopDataModel):
    mission_id: str
    event_refs: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Live desktop backend telemetry summary."


class DesktopLiveBackendRegistry(DesktopDataModel):
    registry_ref: str = "live_desktop_backend_registry"


class DesktopLiveObservationBackend(DesktopDataModel):
    backend_ref: str = "live_observation_backend_contract"


class DesktopLiveActionBackend(DesktopDataModel):
    backend_ref: str = "live_action_backend_contract"


class LiveDesktopBackendRuntimeSummary(DesktopDataModel):
    mission_id: str
    backend_id: str
    maturity: LiveDesktopBackendMaturity
    safe_summary: str = "Live desktop backend runtime summary."


class DesktopLiveActionContract(SentinelModel):
    """Data-only contract marker for future live adapters."""

    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _contract_is_data_only(self) -> DesktopLiveActionContract:
        assert_data_not_authority(
            context="desktop_live_action_contract",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


def _sanitize_live_payload(value: Any, *, context: str) -> Any:
    sanitized = redact_operator_value(value)
    reject_operator_control_payload(sanitized, context=context)
    return sanitized


def _looks_secret_like(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("password", "secret", "token", "api_key", "apikey", "seed phrase", "recovery code", "2fa"))


def _safe_label(value: str | None) -> str:
    if not value:
        return "unspecified"
    text = redact_operator_text(value).lower()
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-", ":"} else "_" for ch in text)
    return safe[:80] or "unspecified"
