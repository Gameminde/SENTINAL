from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized


def desktop_utc_now() -> datetime:
    return datetime.now(UTC)


class DesktopControlMode(StrEnum):
    OBSERVE_ONLY = "observe_only"
    MONITOR_ONLY = "monitor_only"
    ASSISTED_OPERATOR = "assisted_operator"
    APPROVED_ACTION_OPERATOR = "approved_action_operator"
    DELEGATED_SESSION_OPERATOR = "delegated_session_operator"
    CONTINUOUS_SUPERVISION_OPERATOR = "continuous_supervision_operator"


class DesktopSidecarMaturity(StrEnum):
    CONTRACT_ONLY = "contract_only"
    FAKE_BACKEND = "fake_backend"
    INJECTED_TRANSPORT = "injected_transport"
    LOCAL_OBSERVATION_ADAPTER = "local_observation_adapter"
    LIVE_OPT_IN_ADAPTER = "live_opt_in_adapter"
    PRODUCTION_READY_ADAPTER = "production_ready_adapter"


class DesktopSidecarKind(StrEnum):
    CONTRACT_ONLY = "contract_only"
    FAKE_BACKEND = "fake_backend"
    INJECTED_TRANSPORT = "injected_transport"
    LOCAL_OBSERVATION = "local_observation"
    LIVE_OPT_IN = "live_opt_in"


class MetricAvailability(StrEnum):
    AVAILABLE = "available"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    PERMISSION_REQUIRED = "permission_required"
    BLOCKED_BY_POLICY = "blocked_by_policy"


class DesktopActionKind(StrEnum):
    OBSERVE_SCREEN = "observe_screen"
    OBSERVE_WINDOW = "observe_window"
    LIST_WINDOWS = "list_windows"
    LIST_APPS = "list_apps"
    GROUND_TARGET = "ground_target"
    PREVIEW_ACTION = "preview_action"
    FOCUS_WINDOW = "focus_window"
    CLICK_REGION = "click_region"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    WAIT = "wait"
    SCROLL = "scroll"
    MOVE_MOUSE = "move_mouse"
    COPY_PASTE = "copy_paste"
    OPEN_APP = "open_app"
    CLOSE_WINDOW = "close_window"


class DesktopFinalGateDecision(StrEnum):
    OBSERVED = "observed"
    GROUNDED = "grounded"
    PREVIEWED = "previewed"
    BLOCKED = "blocked"
    FAILED = "failed"
    REVOKED = "revoked"
    NEEDS_APPROVAL = "needs_approval"
    SENSITIVE_REGION_BLOCKED = "sensitive_region_blocked"


class DesktopDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _desktop_data_is_not_authority(self) -> DesktopDataModel:
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


class DesktopCapabilityProfile(DesktopDataModel):
    supports_observation: bool = True
    supports_monitoring: bool = True
    supports_visual_grounding: bool = True
    supports_action_preview: bool = True
    supports_injected_actions: bool = True
    supports_live_opt_in_actions: bool = False
    supports_clipboard: bool = False
    safe_summary: str = "Desktop sidecar capability descriptor."

    @model_validator(mode="after")
    def _sanitize_summary(self) -> DesktopCapabilityProfile:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class DesktopMonitoringPolicy(DesktopDataModel):
    always_on_allowed: bool = False
    cadence_seconds: int = Field(default=60, ge=1)
    allowed_metrics: list[str] = Field(default_factory=lambda: ["cpu", "ram", "disk", "network", "process", "window", "clock"])
    blocked_apps: list[str] = Field(default_factory=list)
    blocked_windows: list[str] = Field(default_factory=list)
    retention_policy: str = "hash_and_summary_only"
    operator_visible: bool = True

    @model_validator(mode="after")
    def _normalize_monitoring_policy(self) -> DesktopMonitoringPolicy:
        self.allowed_metrics = [_safe_identifier(metric, "metric") for metric in self.allowed_metrics]
        self.blocked_apps = [redact_operator_text(item) for item in self.blocked_apps]
        self.blocked_windows = [redact_operator_text(item) for item in self.blocked_windows]
        self.retention_policy = redact_operator_text(self.retention_policy)
        return self


class DesktopPermissionPolicy(DesktopDataModel):
    active_mode: DesktopControlMode = DesktopControlMode.OBSERVE_ONLY
    allowed_modes: list[DesktopControlMode] = Field(default_factory=lambda: [DesktopControlMode.OBSERVE_ONLY])
    allowed_apps: list[str] = Field(default_factory=list)
    blocked_apps: list[str] = Field(default_factory=list)
    allowed_windows: list[str] = Field(default_factory=list)
    blocked_windows: list[str] = Field(default_factory=list)
    allowed_displays: list[str] = Field(default_factory=list)
    blocked_region_labels: list[str] = Field(default_factory=list)
    persist_full_screenshot_allowed: bool = False
    persist_full_ocr_text_allowed: bool = False
    allow_clipboard: bool = False
    always_on_allowed: bool = False
    production_always_on_ready: bool = False
    operator_visible: bool = True
    monitoring_policy: DesktopMonitoringPolicy = Field(default_factory=DesktopMonitoringPolicy)

    @model_validator(mode="after")
    def _permission_policy_is_bounded(self) -> DesktopPermissionPolicy:
        if self.active_mode not in self.allowed_modes:
            raise ValueError("desktop active mode must be explicitly allowed")
        if self.production_always_on_ready:
            raise ValueError("desktop v1 cannot claim production always-on readiness")
        if self.persist_full_screenshot_allowed or self.persist_full_ocr_text_allowed:
            raise ValueError("desktop raw screenshot/OCR persistence is blocked by default in v1")
        self.allowed_apps = [redact_operator_text(item) for item in self.allowed_apps]
        self.blocked_apps = [redact_operator_text(item) for item in self.blocked_apps]
        self.allowed_windows = [redact_operator_text(item) for item in self.allowed_windows]
        self.blocked_windows = [redact_operator_text(item) for item in self.blocked_windows]
        self.allowed_displays = [redact_operator_text(item) for item in self.allowed_displays]
        self.blocked_region_labels = [_safe_identifier(item, "blocked_region") for item in self.blocked_region_labels]
        return self


class DesktopActionPolicy(DesktopDataModel):
    allowed_action_kinds: list[DesktopActionKind] = Field(default_factory=lambda: [
        DesktopActionKind.CLICK_REGION,
        DesktopActionKind.TYPE_TEXT,
        DesktopActionKind.WAIT,
    ])
    approval_required_for_each_action: bool = True
    allow_live_actions: bool = False
    allow_copy_paste: bool = False
    allow_open_app: bool = False
    allow_close_window: bool = False
    max_actions_per_session: int = Field(default=10, ge=0)

    @model_validator(mode="after")
    def _action_policy_is_safe(self) -> DesktopActionPolicy:
        if self.allow_live_actions:
            raise ValueError("desktop live actions are not production-ready in v1")
        if DesktopActionKind.COPY_PASTE in self.allowed_action_kinds and not self.allow_copy_paste:
            raise ValueError("desktop copy/paste requires explicit policy")
        if DesktopActionKind.OPEN_APP in self.allowed_action_kinds and not self.allow_open_app:
            raise ValueError("desktop open_app requires explicit policy")
        if DesktopActionKind.CLOSE_WINDOW in self.allowed_action_kinds and not self.allow_close_window:
            raise ValueError("desktop close_window requires explicit policy")
        return self


class DesktopSidecarConfig(DesktopDataModel):
    sidecar_id: str
    kind: DesktopSidecarKind
    maturity: DesktopSidecarMaturity
    display_name: str
    capability_profile: DesktopCapabilityProfile = Field(default_factory=DesktopCapabilityProfile)
    permission_policy: DesktopPermissionPolicy = Field(default_factory=DesktopPermissionPolicy)
    action_policy: DesktopActionPolicy = Field(default_factory=DesktopActionPolicy)
    identity_ref: str | None = None
    session_ref: str | None = None
    endpoint_ref_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=desktop_utc_now)
    config_hash: str = ""

    @model_validator(mode="after")
    def _config_is_safe(self) -> DesktopSidecarConfig:
        if not self.sidecar_id.strip():
            raise ValueError("desktop sidecar id is required")
        self.display_name = redact_operator_text(self.display_name)
        self.metadata = _sanitize_desktop_payload(self.metadata, context="desktop_sidecar_config")
        if self.maturity is DesktopSidecarMaturity.PRODUCTION_READY_ADAPTER:
            raise ValueError("desktop v1 cannot claim production-ready adapter maturity")
        return self

    def with_hash(self) -> DesktopSidecarConfig:
        payload = self.safe_model_dump()
        payload["config_hash"] = ""
        return self.model_copy(update={"config_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["config_hash"]
        payload["config_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopDisplayRef(DesktopDataModel):
    display_id: str = "display:main"
    display_hash: str = ""

    def with_hash(self) -> DesktopDisplayRef:
        return self.model_copy(update={"display_hash": stable_hash(self.display_id)})


class DesktopAppRef(DesktopDataModel):
    app_id: str = Field(default_factory=lambda: new_id("desktop_app"))
    app_ref: str
    app_hash: str = ""

    def with_hash(self) -> DesktopAppRef:
        return self.model_copy(update={"app_hash": stable_hash(self.app_ref)})


class DesktopWindowRef(DesktopDataModel):
    window_id: str = Field(default_factory=lambda: new_id("desktop_window"))
    window_ref: str
    app_ref: str | None = None
    title_hash: str = ""

    def with_hash(self) -> DesktopWindowRef:
        return self.model_copy(update={"title_hash": stable_hash(self.window_ref)})


class DesktopRegionRef(DesktopDataModel):
    region_id: str = Field(default_factory=lambda: new_id("desktop_region"))
    label: str
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    sensitive: bool = False
    sensitivity_reasons: list[str] = Field(default_factory=list)
    region_hash: str = ""

    @model_validator(mode="after")
    def _region_is_safe(self) -> DesktopRegionRef:
        self.label = _safe_identifier(self.label, "region_label")
        reasons = list(self.sensitivity_reasons)
        if _is_sensitive_label(self.label):
            reasons.append(self.label)
            self.sensitive = True
        self.sensitivity_reasons = sorted(set(_safe_identifier(reason, "sensitivity_reason") for reason in reasons))
        if not self.region_hash:
            self.region_hash = stable_hash({"label": self.label, "x": self.x, "y": self.y, "width": self.width, "height": self.height})
        return self


class DesktopObservationRequest(DesktopDataModel):
    request_id: str = Field(default_factory=lambda: new_id("desktop_observation_request"))
    sidecar_id: str = "desktop_default"
    display_ref: str = "display:main"
    window_ref: str | None = None
    app_ref: str | None = None
    regions: list[DesktopRegionRef] = Field(default_factory=list)
    purpose: str
    operator_visible: bool = True
    ambient_loop: bool = False
    requested_by: str = "operator"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _observation_request_is_visible(self) -> DesktopObservationRequest:
        self.purpose = redact_operator_text(self.purpose)
        self.metadata = _sanitize_desktop_payload(self.metadata, context="desktop_observation_request")
        return self


class DesktopScreenshotRef(DesktopDataModel):
    screenshot_id: str = Field(default_factory=lambda: new_id("desktop_screenshot"))
    screenshot_hash: str
    byte_count: int = Field(default=0, ge=0)
    redacted_image_ref_hash: str | None = None
    raw_screenshot_persisted: bool = False

    @model_validator(mode="after")
    def _raw_screenshot_default_blocked(self) -> DesktopScreenshotRef:
        if self.raw_screenshot_persisted:
            raise ValueError("desktop raw screenshot persistence is blocked in v1")
        return self


class DesktopRedactionResult(DesktopDataModel):
    redaction_id: str = Field(default_factory=lambda: new_id("desktop_redaction"))
    sensitive_region_detected: bool = False
    sensitive_region_count: int = 0
    redacted: bool = False
    uncertain: bool = False
    safe_summary: str = "Desktop redaction summary."
    result_hash: str = ""

    def with_hash(self) -> DesktopRedactionResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})


class DesktopSensitiveRegionPolicy(DesktopDataModel):
    block_live_action_on_sensitive_region: bool = True
    sensitive_labels: list[str] = Field(default_factory=lambda: [
        "password",
        "credential",
        "payment",
        "banking",
        "private_message",
        "health",
        "legal",
        "identity",
        "api_key",
        "seed_phrase",
        "recovery_code",
        "2fa",
        "browser_login",
    ])


class DesktopObservationResult(DesktopDataModel):
    observation_id: str = Field(default_factory=lambda: new_id("desktop_observation"))
    sidecar_id: str
    mission_id: str
    status: str = "observed"
    display_ref: DesktopDisplayRef
    window_ref: DesktopWindowRef | None = None
    app_ref: DesktopAppRef | None = None
    region_refs: list[DesktopRegionRef] = Field(default_factory=list)
    screenshot_ref: DesktopScreenshotRef | None = None
    safe_text_snippet_hashes: list[str] = Field(default_factory=list)
    redaction_result: DesktopRedactionResult = Field(default_factory=DesktopRedactionResult)
    receipt: DesktopSidecarReceipt | None = None
    finalgate_certificate: DesktopSidecarFinalGateCertificate | None = None
    created_at: datetime = Field(default_factory=desktop_utc_now)
    observation_hash: str = ""

    def with_hash(self) -> DesktopObservationResult:
        payload = self.safe_model_dump()
        payload["observation_hash"] = ""
        return self.model_copy(update={"observation_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["observation_hash"]
        payload["observation_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopTargetCandidate(DesktopDataModel):
    target_id: str = Field(default_factory=lambda: new_id("desktop_target"))
    observation_id: str
    target_ref_hash: str
    region_ref: DesktopRegionRef
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    ambiguous: bool = False
    sensitive: bool = False
    authoritative_for_action: bool = False

    @model_validator(mode="after")
    def _target_cannot_authorize(self) -> DesktopTargetCandidate:
        if self.authoritative_for_action:
            raise ValueError("desktop target candidate cannot authorize action")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.sensitive = self.sensitive or self.region_ref.sensitive
        return self


class DesktopVisualGroundingRequest(DesktopDataModel):
    request_id: str = Field(default_factory=lambda: new_id("desktop_grounding_request"))
    sidecar_id: str
    observation_id: str
    target_description: str
    evidence_refs: list[str] = Field(default_factory=list)
    ambiguity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _grounding_request_is_safe(self) -> DesktopVisualGroundingRequest:
        self.target_description = redact_operator_text(self.target_description)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        if not self.evidence_refs:
            raise ValueError("desktop grounding requires evidence refs")
        return self


class DesktopVisualGroundingResult(DesktopDataModel):
    grounding_id: str = Field(default_factory=lambda: new_id("desktop_grounding"))
    sidecar_id: str
    mission_id: str
    observation_id: str
    status: str = "grounded"
    target_candidates: list[DesktopTargetCandidate] = Field(default_factory=list)
    uncertainty_flags: list[str] = Field(default_factory=list)
    action_executed: bool = False
    grounding_receipt: DesktopSidecarReceipt
    finalgate_certificate: DesktopSidecarFinalGateCertificate
    created_at: datetime = Field(default_factory=desktop_utc_now)
    grounding_hash: str = ""

    @model_validator(mode="after")
    def _grounding_never_executes(self) -> DesktopVisualGroundingResult:
        if self.action_executed:
            raise ValueError("desktop visual grounding cannot execute actions")
        return self

    def with_hash(self) -> DesktopVisualGroundingResult:
        payload = self.safe_model_dump()
        payload["grounding_hash"] = ""
        return self.model_copy(update={"grounding_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["grounding_hash"]
        payload["grounding_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopActionProposal(DesktopDataModel):
    proposal_id: str = Field(default_factory=lambda: new_id("desktop_proposal"))
    sidecar_id: str
    action_kind: DesktopActionKind
    target_candidate_id: str | None = None
    app_ref_hash: str | None = None
    window_ref_hash: str | None = None
    safe_summary: str = "Desktop action proposal."
    evidence_refs: list[str] = Field(default_factory=list)
    proposal_hash: str = ""

    @model_validator(mode="after")
    def _proposal_is_data(self) -> DesktopActionProposal:
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        return self

    def with_hash(self) -> DesktopActionProposal:
        payload = self.safe_model_dump()
        payload["proposal_hash"] = ""
        return self.model_copy(update={"proposal_hash": stable_hash(payload)})


class DesktopActionRequest(DesktopDataModel):
    request_id: str = Field(default_factory=lambda: new_id("desktop_request"))
    sidecar_id: str
    action_kind: DesktopActionKind
    target_candidate_id: str | None = None
    app_ref: str | None = Field(default=None, exclude=True, repr=False)
    window_ref: str | None = Field(default=None, exclude=True, repr=False)
    text: str | None = Field(default=None, exclude=True, repr=False)
    hotkey: str | None = None
    approval_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    requested_by: str = "operator"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _action_request_is_safe_data(self) -> DesktopActionRequest:
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        if not self.evidence_refs:
            raise ValueError("desktop action request requires evidence refs")
        if self.text and _looks_like_raw_secret(self.text):
            raise ValueError("desktop action text contains secret-like content")
        self.hotkey = redact_operator_text(self.hotkey) if self.hotkey else None
        self.metadata = _sanitize_desktop_payload(self.metadata, context="desktop_action_request")
        return self


class DesktopActionPreview(DesktopDataModel):
    preview_id: str = Field(default_factory=lambda: new_id("desktop_preview"))
    sidecar_id: str
    action_request: DesktopActionRequest
    action_proposal: DesktopActionProposal | None = None
    safe_summary: str = "Desktop action preview created; no action executed."
    action_executed: bool = False
    created_at: datetime = Field(default_factory=desktop_utc_now)
    preview_hash: str = ""

    @model_validator(mode="after")
    def _preview_never_executes(self) -> DesktopActionPreview:
        if self.action_executed:
            raise ValueError("desktop action preview cannot execute")
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> DesktopActionPreview:
        payload = self.safe_model_dump()
        payload["preview_hash"] = ""
        return self.model_copy(update={"preview_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["preview_hash"]
        payload["preview_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopActionApproval(DesktopDataModel):
    approval_id: str = Field(default_factory=lambda: new_id("desktop_approval"))
    sidecar_id: str
    preview_id: str
    approved_by: str = "operator"
    approval_source: str = "operator"
    approved: bool = True
    safe_summary: str = "Operator approved desktop action."
    created_at: datetime = Field(default_factory=desktop_utc_now)
    approval_hash: str = ""

    @model_validator(mode="after")
    def _approval_is_operator_only(self) -> DesktopActionApproval:
        if self.approval_source not in {"operator", "operator_policy", "manual_operator"}:
            raise ValueError("operator approval source required for desktop action")
        self.approved_by = redact_operator_text(self.approved_by)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> DesktopActionApproval:
        payload = self.safe_model_dump()
        payload["approval_hash"] = ""
        return self.model_copy(update={"approval_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["approval_hash"]
        payload["approval_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopBeforeAfterEvidence(DesktopDataModel):
    evidence_id: str = Field(default_factory=lambda: new_id("desktop_before_after"))
    before_hash: str
    after_hash: str
    before_ref_hash: str | None = None
    after_ref_hash: str | None = None
    safe_summary: str = "Desktop before/after evidence recorded."
    evidence_hash: str = ""

    def with_hash(self) -> DesktopBeforeAfterEvidence:
        payload = self.safe_model_dump()
        payload["evidence_hash"] = ""
        return self.model_copy(update={"evidence_hash": stable_hash(payload)})


class DesktopQuarantineRecord(DesktopDataModel):
    quarantine_id: str = Field(default_factory=lambda: new_id("desktop_quarantine"))
    reason: str
    target_ref_hash: str | None = None
    safe_summary: str = "Desktop target quarantined."


class DesktopKillSwitchBinding(DesktopDataModel):
    sidecar_id: str
    mission_id: str
    killed: bool = False
    reason_hash: str | None = None
    created_at: datetime = Field(default_factory=desktop_utc_now)


class DesktopRevocationCheck(DesktopDataModel):
    check_id: str = Field(default_factory=lambda: new_id("desktop_revocation_check"))
    mission_id: str
    sidecar_id: str
    revoked: bool = False
    expired: bool = False
    checked_at: datetime = Field(default_factory=desktop_utc_now)


class DesktopSidecarReceipt(DesktopDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("desktop_sidecar_receipt"))
    sidecar_id: str
    mission_id: str
    operation_type: str
    status: str
    authority_envelope_ref: str | None = None
    display_ref_hash: str | None = None
    window_ref_hash: str | None = None
    app_ref_hash: str | None = None
    region_ref_hashes: list[str] = Field(default_factory=list)
    screenshot_hash: str | None = None
    target_candidate_refs: list[str] = Field(default_factory=list)
    policy_hash: str | None = None
    approval_ref: str | None = None
    before_after_hash: str | None = None
    sensitive_region_flags: list[str] = Field(default_factory=list)
    revocation_check_ref: str | None = None
    telemetry_refs: list[str] = Field(default_factory=list)
    future_permission: bool = False
    created_at: datetime = Field(default_factory=desktop_utc_now)
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _receipt_is_evidence_only(self) -> DesktopSidecarReceipt:
        if self.future_permission:
            raise ValueError("desktop receipt cannot become future permission")
        self.region_ref_hashes = sanitize_operator_refs(self.region_ref_hashes)
        self.target_candidate_refs = sanitize_operator_refs(self.target_candidate_refs)
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        self.sensitive_region_flags = [_safe_identifier(flag, "sensitive_flag") for flag in self.sensitive_region_flags]
        return self

    def with_hash(self) -> DesktopSidecarReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["receipt_hash"]
        payload["receipt_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopSidecarFinalGateCertificate(DesktopDataModel):
    certificate_id: str = Field(default_factory=lambda: new_id("desktop_finalgate"))
    sidecar_id: str
    mission_id: str
    decision: DesktopFinalGateDecision
    passed: bool
    receipt_ref: str | None = None
    failures: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=desktop_utc_now)


class DesktopActionResult(DesktopDataModel):
    action_result_id: str = Field(default_factory=lambda: new_id("desktop_result"))
    sidecar_id: str
    mission_id: str
    action_kind: DesktopActionKind
    status: str
    blocked_reason: str | None = None
    before_after_evidence: DesktopBeforeAfterEvidence | None = None
    receipt: DesktopSidecarReceipt | None = None
    finalgate_certificate: DesktopSidecarFinalGateCertificate | None = None
    safe_summary: str = "Desktop action result."
    created_at: datetime = Field(default_factory=desktop_utc_now)
    result_hash: str = ""

    def with_hash(self) -> DesktopActionResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["result_hash"]
        payload["result_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopMetricValue(DesktopDataModel):
    status: MetricAvailability = MetricAvailability.UNKNOWN
    value: float | None = None
    unit: str | None = None
    safe_summary: str = "Metric unavailable or unknown."


class DesktopProcessSnapshot(DesktopDataModel):
    process_id_hash: str
    name_hash: str
    cpu_percent: DesktopMetricValue = Field(default_factory=DesktopMetricValue)
    memory_mb: DesktopMetricValue = Field(default_factory=DesktopMetricValue)


class DesktopWindowSnapshot(DesktopDataModel):
    window_ref_hash: str
    app_ref_hash: str | None = None
    active: bool = False
    visible: bool = True


class DesktopAppSnapshot(DesktopDataModel):
    app_ref_hash: str
    running: bool = True


class DesktopHardwareMetricSnapshot(DesktopDataModel):
    cpu_percent: DesktopMetricValue = Field(default_factory=DesktopMetricValue)
    ram_used_mb: DesktopMetricValue = Field(default_factory=DesktopMetricValue)
    disk_used_percent: DesktopMetricValue = Field(default_factory=DesktopMetricValue)
    network_rx_kbps: DesktopMetricValue = Field(default_factory=DesktopMetricValue)
    battery_percent: DesktopMetricValue = Field(default_factory=DesktopMetricValue)
    gpu_percent: DesktopMetricValue = Field(default_factory=DesktopMetricValue)


class DesktopSensorSnapshot(DesktopDataModel):
    temperature_c: DesktopMetricValue = Field(default_factory=DesktopMetricValue)
    fan_rpm: DesktopMetricValue = Field(default_factory=DesktopMetricValue)


class DesktopClockSnapshot(DesktopDataModel):
    system_time_hash: str
    timers_status: MetricAvailability = MetricAvailability.UNKNOWN
    scheduled_tasks_status: MetricAvailability = MetricAvailability.UNKNOWN


class DesktopSystemSnapshot(DesktopDataModel):
    snapshot_id: str = Field(default_factory=lambda: new_id("desktop_system_snapshot"))
    platform_system: str
    current_session_ref_hash: str
    display_count: int = Field(default=1, ge=0)
    active_window_hash: str | None = None
    snapshot_hash: str = ""

    def with_hash(self) -> DesktopSystemSnapshot:
        payload = self.safe_model_dump()
        payload["snapshot_hash"] = ""
        return self.model_copy(update={"snapshot_hash": stable_hash(payload)})


class DesktopBackgroundActivitySnapshot(DesktopDataModel):
    visible_window_count: int = Field(default=0, ge=0)
    running_app_count: int = Field(default=0, ge=0)
    process_count: int = Field(default=0, ge=0)


class DesktopMonitoringReceipt(DesktopSidecarReceipt):
    monitoring_session_id: str | None = None


class DesktopMonitoringSession(DesktopDataModel):
    session_id: str = Field(default_factory=lambda: new_id("desktop_monitoring_session"))
    sidecar_id: str
    mission_id: str
    policy_hash: str
    always_on_allowed: bool = False
    cadence_seconds: int = Field(default=60, ge=1)


class DesktopMonitoringResult(DesktopDataModel):
    monitoring_result_id: str = Field(default_factory=lambda: new_id("desktop_monitoring_result"))
    sidecar_id: str
    mission_id: str
    system_snapshot: DesktopSystemSnapshot
    processes: list[DesktopProcessSnapshot] = Field(default_factory=list)
    windows: list[DesktopWindowSnapshot] = Field(default_factory=list)
    apps: list[DesktopAppSnapshot] = Field(default_factory=list)
    hardware_metrics: DesktopHardwareMetricSnapshot = Field(default_factory=DesktopHardwareMetricSnapshot)
    sensor_snapshot: DesktopSensorSnapshot = Field(default_factory=DesktopSensorSnapshot)
    clock_snapshot: DesktopClockSnapshot
    background_activity: DesktopBackgroundActivitySnapshot
    monitoring_receipt: DesktopMonitoringReceipt | None = None
    created_at: datetime = Field(default_factory=desktop_utc_now)
    result_hash: str = ""

    def with_hash(self) -> DesktopMonitoringResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["result_hash"]
        payload["result_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class DesktopSidecarTelemetrySummary(DesktopDataModel):
    mission_id: str
    event_refs: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Desktop sidecar telemetry summary."


class DesktopMonitoringReplayView(DesktopDataModel):
    mission_id: str
    monitoring_results: list[DesktopMonitoringResult] = Field(default_factory=list)
    recaptured_screenshots: bool = False
    reexecuted_actions: bool = False


class DesktopSidecarReplayView(DesktopDataModel):
    mission_id: str
    configs: list[DesktopSidecarConfig] = Field(default_factory=list)
    observations: list[DesktopObservationResult] = Field(default_factory=list)
    monitoring_results: list[DesktopMonitoringResult] = Field(default_factory=list)
    grounding_results: list[DesktopVisualGroundingResult] = Field(default_factory=list)
    action_previews: list[DesktopActionPreview] = Field(default_factory=list)
    approvals: list[DesktopActionApproval] = Field(default_factory=list)
    action_results: list[DesktopActionResult] = Field(default_factory=list)
    receipts: list[DesktopSidecarReceipt] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    recaptured_screenshots: bool = False
    reexecuted_actions: bool = False

    @model_validator(mode="after")
    def _replay_never_reacts(self) -> DesktopSidecarReplayView:
        if self.recaptured_screenshots or self.reexecuted_actions:
            raise ValueError("desktop replay must not recapture screenshots or re-execute actions")
        return self


def _sanitize_desktop_payload(value: Any, *, context: str) -> Any:
    _reject_desktop_forbidden_payload(value)
    sanitized = redact_operator_value(value)
    reject_operator_control_payload(sanitized, context=context)
    return sanitized


def _reject_desktop_forbidden_payload(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {
                "raw_token",
                "token_value",
                "credential_value",
                "raw_credential",
                "password",
                "api_key",
                "provider_key",
                "seed_phrase",
                "recovery_code",
            }:
                raise ValueError("raw desktop token or credential persistence is not allowed")
            if lowered in {"raw_screenshot", "raw_screenshot_bytes", "screenshot_bytes", "raw_ocr", "raw_ocr_text"}:
                raise ValueError("raw desktop screenshot/OCR persistence is not allowed")
            if lowered in {"raw_prompt", "prompt", "prompt_text"} and "hash" not in lowered:
                raise ValueError("raw prompt persistence is not allowed")
            if lowered in {"raw_provider_response", "provider_response", "raw_response"} and "hash" not in lowered:
                raise ValueError("raw provider response persistence is not allowed")
            if lowered in {"raw_reasoning", "reasoning", "thinking"} and "hash" not in lowered:
                raise ValueError("raw reasoning persistence is not allowed")
            if lowered in {"fallback", "auto", "auto_route", "provider_override", "model_override"}:
                raise ValueError("provider fallback/AUTO or override is not allowed")
            _reject_desktop_forbidden_payload(item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _reject_desktop_forbidden_payload(item)
        return
    if isinstance(value, str):
        if _looks_like_raw_secret(value):
            raise ValueError("raw desktop token or credential persistence is not allowed")
        lowered = value.lower()
        if "fallback" in lowered or lowered.strip() == "auto":
            raise ValueError("provider fallback/AUTO or override is not allowed")
        if any(term in lowered for term in ("hidden keylogger", "credential harvesting", "remote desktop takeover")):
            raise ValueError("unsafe desktop control payload is not allowed")


def _looks_like_raw_secret(value: str) -> bool:
    redacted = redact_operator_text(value)
    if redacted != value:
        return True
    scan = scan_forbidden_payload_categorized(value, path="$")
    return bool(scan[OrganSafetyScanCategory.SECRET.value])


def _is_sensitive_label(value: str) -> bool:
    lowered = value.lower()
    sensitive_terms = {
        "password",
        "credential",
        "payment",
        "bank",
        "private",
        "health",
        "legal",
        "identity",
        "api_key",
        "token",
        "seed",
        "recovery",
        "2fa",
        "login",
    }
    return any(term in lowered for term in sensitive_terms)


def _safe_identifier(value: str, field_name: str) -> str:
    safe = redact_operator_text(str(value)).strip().lower().replace(" ", "_").replace("-", "_")
    safe = "".join(ch for ch in safe if ch.isalnum() or ch in {"_", ":", "."})
    if not safe:
        raise ValueError(f"{field_name} is required")
    return safe
