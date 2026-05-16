from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from urllib.parse import urlparse

from pydantic import Field

from sentinel.agent.artifact_capture import ArtifactCaptureSandbox  # noqa: E402 — agent-layer utility used cross-layer (Wave D documented exception)
from sentinel.organs.browser.accessibility_snapshot import BrowserAccessibilitySnapshotBuilder
from sentinel.organs.browser.interaction_dry_run import verify_browser_interaction_plan_hash
from sentinel.organs.browser.models import BrowserAccessibilitySnapshot, BrowserInteractionPlan, BrowserRenderedPage
from sentinel.organs.browser.v3_authority import (
    BrowserV3AuthorityClass,
    BrowserV3AuthorityGrant,
    BrowserV3Receipt,
    browser_v3_grant_allows_url,
)
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserPrivateSessionRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bps"))
    mission_id: str
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    operation: str = "open"
    allowed_domains: list[str] = Field(default_factory=list)
    session_id: str | None = None
    profile_id: str | None = None
    storage_enabled: bool = False
    expected_effect: str = "private browser session boundary"


class BrowserPrivateSessionBackendResult(SentinelModel):
    session_id: str
    profile_id: str
    operation: str
    created: bool = False
    destroyed: bool = False
    profile_destroyed: bool = False
    storage_enabled: bool = False
    storage_state_sha256: str
    allowed_domains: list[str] = Field(default_factory=list)
    health: dict = Field(default_factory=dict)


class BrowserPrivateSessionReceipt(BrowserV3Receipt):
    authority_class: BrowserV3AuthorityClass = BrowserV3AuthorityClass.PRIVATE_SESSION
    operation: str
    session_id: str
    profile_id: str
    session_scope: str
    storage_enabled: bool = False
    storage_state_sha256: str
    allowed_domains: list[str] = Field(default_factory=list)
    created: bool = False
    destroyed: bool = False
    profile_destroyed: bool = False
    expected_effect: str
    receipt_artifact_id: str | None = None
    receipt_artifact_sha256: str | None = None


class BrowserPrivateSessionResult(SentinelModel):
    accepted: bool
    reason: str
    request_id: str
    receipt: BrowserPrivateSessionReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


BrowserPrivateSessionBackend = Callable[[BrowserPrivateSessionRequest], BrowserPrivateSessionBackendResult]


class BrowserLoginAuthorityRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("blogin"))
    mission_id: str
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    session_id: str
    profile_id: str
    private_session_trace_event_id: str
    account_id: str
    login_url: str
    plan: BrowserInteractionPlan
    plan_trace_event_id: str
    before_snapshot_trace_event_id: str
    login_ref_id: str
    expected_effect: str = "account session authenticated"
    allow_cross_origin: bool = False
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)


class BrowserLoginBackendResult(SentinelModel):
    before_snapshot: BrowserAccessibilitySnapshot
    after_page: BrowserRenderedPage | None = None
    final_url_before: str
    final_url_after: str
    login_success: bool = True
    account_id: str
    session_id: str


class BrowserLoginAuthorityReceipt(BrowserV3Receipt):
    authority_class: BrowserV3AuthorityClass = BrowserV3AuthorityClass.LOGIN_AUTHORITY
    session_id: str
    profile_id: str
    private_session_trace_event_id: str
    account_id: str
    login_url_hash: str
    final_url_hash: str
    plan_id: str
    plan_sha256: str
    plan_trace_event_id: str
    before_snapshot_trace_event_id: str
    before_snapshot_sha256: str
    after_snapshot_sha256: str
    same_origin: bool = False
    cross_origin_authorized: bool = False
    login_success: bool = False
    expected_effect: str
    post_login_snapshot_artifact_id: str | None = None
    post_login_snapshot_artifact_sha256: str | None = None


class BrowserLoginAuthorityResult(SentinelModel):
    accepted: bool
    reason: str
    request_id: str
    receipt: BrowserLoginAuthorityReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


BrowserLoginBackend = Callable[[BrowserLoginAuthorityRequest], BrowserLoginBackendResult]


class BrowserCookieStorageContractRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bcsc"))
    mission_id: str
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    session_id: str
    profile_id: str
    private_session_trace_event_id: str
    operation: str = "redacted_summary"
    target_domain: str
    expected_effect: str = "redacted cookie/storage contract applied"


class BrowserCookieStorageBackendResult(SentinelModel):
    cookie_count: int = Field(ge=0)
    storage_key_count: int = Field(ge=0)
    storage_state_sha256: str
    redacted_summary: dict = Field(default_factory=dict)
    redaction_applied: bool = True
    raw_value_exposed: bool = False
    cleared: bool = False


class BrowserCookieStorageContractReceipt(BrowserV3Receipt):
    authority_class: BrowserV3AuthorityClass = BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT
    session_id: str
    profile_id: str
    private_session_trace_event_id: str
    operation: str
    target_domain: str
    cookie_count: int = Field(ge=0)
    storage_key_count: int = Field(ge=0)
    storage_state_sha256: str
    redaction_applied: bool = True
    raw_value_exposed: bool = False
    cleared: bool = False
    summary_artifact_id: str | None = None
    summary_artifact_sha256: str | None = None


class BrowserCookieStorageContractResult(SentinelModel):
    accepted: bool
    reason: str
    request_id: str
    receipt: BrowserCookieStorageContractReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


BrowserCookieStorageBackend = Callable[[BrowserCookieStorageContractRequest], BrowserCookieStorageBackendResult]


class BrowserJsEvaluateSandboxedRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bjs"))
    mission_id: str
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    page_url: str
    script_source: str
    expected_effect: str = "sandboxed script evaluated"
    max_result_bytes: int = Field(default=1_000_000, ge=1, le=100_000_000)
    timeout_ms: int = Field(default=5_000, ge=1, le=120_000)


class BrowserJsEvaluateBackendResult(SentinelModel):
    result: dict | list | str | int | float | bool | None = None
    timed_out: bool = False
    network_calls: list[str] = Field(default_factory=list)
    console: list[str] = Field(default_factory=list)


class BrowserJsEvaluateSandboxedReceipt(BrowserV3Receipt):
    authority_class: BrowserV3AuthorityClass = BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED
    page_url_hash: str
    script_sha256: str
    script_hash_allowed: bool = False
    result_sha256: str
    result_size_bytes: int = Field(ge=0)
    max_result_bytes: int = Field(ge=1)
    network_calls_blocked: bool = True
    timed_out: bool = False
    result_artifact_id: str | None = None
    result_artifact_sha256: str | None = None


class BrowserJsEvaluateSandboxedResult(SentinelModel):
    accepted: bool
    reason: str
    request_id: str
    receipt: BrowserJsEvaluateSandboxedReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


BrowserJsEvaluateBackend = Callable[[BrowserJsEvaluateSandboxedRequest], BrowserJsEvaluateBackendResult]


class BrowserHarBodyCaptureRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bhar"))
    mission_id: str
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    source_url: str
    capture_bodies: bool = True
    allowed_mime_types: list[str] = Field(default_factory=list)
    max_bytes: int = Field(default=10_000_000, ge=1, le=500_000_000)
    max_records: int = Field(default=500, ge=1, le=100_000)
    expected_effect: str = "bounded HAR/body capture"


class BrowserHarBodyCaptureBackendResult(SentinelModel):
    entries: list[dict] = Field(default_factory=list)
    total_bytes: int = Field(ge=0)
    redaction_applied: bool = True
    body_capture_sha256: str | None = None
    truncated: bool = False
    mime_types: list[str] = Field(default_factory=list)


class BrowserHarBodyCaptureReceipt(BrowserV3Receipt):
    authority_class: BrowserV3AuthorityClass = BrowserV3AuthorityClass.HAR_BODY_CAPTURE
    source_url: str
    source_url_hash: str
    capture_bodies: bool = True
    record_count: int = Field(ge=0)
    max_records: int = Field(ge=1)
    total_bytes: int = Field(ge=0)
    max_bytes: int = Field(ge=1)
    redaction_applied: bool = True
    body_capture_sha256: str
    truncated: bool = False
    har_artifact_id: str | None = None
    har_artifact_sha256: str | None = None


class BrowserHarBodyCaptureResult(SentinelModel):
    accepted: bool
    reason: str
    request_id: str
    receipt: BrowserHarBodyCaptureReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


BrowserHarBodyCaptureBackend = Callable[[BrowserHarBodyCaptureRequest], BrowserHarBodyCaptureBackendResult]


class BrowserPrivateSessionExecutor:
    def __init__(self, *, backend: BrowserPrivateSessionBackend) -> None:
        self.backend = backend

    def execute(
        self,
        request: BrowserPrivateSessionRequest,
        *,
        authority_grant: BrowserV3AuthorityGrant,
        event_bus: EventBus,
        artifact_capture: ArtifactCaptureSandbox,
        policy_trace_id: str | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPrivateSessionResult:
        errors = _validate_common(request, authority_grant, BrowserV3AuthorityClass.PRIVATE_SESSION)
        if request.operation not in {"open", "close"}:
            errors.append("private_session_operation_invalid")
        if authority_grant.session_scope != "per_mission":
            errors.append("private_session_scope_not_per_mission")
        if request.storage_enabled and not authority_grant.storage_allowed:
            errors.append("private_session_storage_not_granted")
        if request.operation == "close" and (not request.session_id or not request.profile_id):
            errors.append("private_session_close_missing_session")
        for domain in request.allowed_domains:
            if not _domain_in_grant(authority_grant, domain):
                errors.append(f"private_session_domain_outside_authority:{domain}")
        if errors:
            return _advanced_rejected(
                request,
                AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED,
                BrowserV3AuthorityClass.PRIVATE_SESSION,
                "browser_private_session_request_rejected",
                errors,
                event_bus,
                policy_trace_id,
                phase,
                BrowserPrivateSessionResult,
            )
        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return _advanced_rejected(
                request,
                AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED,
                BrowserV3AuthorityClass.PRIVATE_SESSION,
                "browser_private_session_backend_failed",
                [_sanitize_backend_exception(exc)],
                event_bus,
                policy_trace_id,
                phase,
                BrowserPrivateSessionResult,
            )
        backend_errors = _validate_private_session_backend_reality(request, backend_result, authority_grant)
        if backend_errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED, BrowserV3AuthorityClass.PRIVATE_SESSION, "private_session_backend_reality_failed", backend_errors, event_bus, policy_trace_id, phase, BrowserPrivateSessionResult)
        if request.operation == "open" and not backend_result.created:
            return _advanced_rejected(request, AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED, BrowserV3AuthorityClass.PRIVATE_SESSION, "private_session_not_created", [], event_bus, policy_trace_id, phase, BrowserPrivateSessionResult)
        if request.operation == "close" and not (backend_result.destroyed and backend_result.profile_destroyed):
            return _advanced_rejected(request, AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED, BrowserV3AuthorityClass.PRIVATE_SESSION, "private_session_not_destroyed", [], event_bus, policy_trace_id, phase, BrowserPrivateSessionResult)
        receipt = BrowserPrivateSessionReceipt(
            mission_id=request.mission_id,
            authority_grant_id=authority_grant.id,
            request_id=request.id,
            context_pack_id=request.context_pack_id,
            compiled_intent_trace_id=request.compiled_intent_trace_id,
            operation=request.operation,
            session_id=backend_result.session_id,
            profile_id=backend_result.profile_id,
            session_scope=authority_grant.session_scope,
            storage_enabled=backend_result.storage_enabled,
            storage_state_sha256=backend_result.storage_state_sha256,
            allowed_domains=backend_result.allowed_domains,
            created=backend_result.created,
            destroyed=backend_result.destroyed,
            profile_destroyed=backend_result.profile_destroyed,
            expected_effect=request.expected_effect,
        )
        artifact = _capture_receipt_artifact(
            artifact_capture,
            event_bus,
            f"browser/private_session/{request.id}_{request.operation}.json",
            "browser_private_session_receipt",
            receipt.model_dump(mode="json"),
            [policy_trace_id, request.compiled_intent_trace_id],
            phase,
        )
        if not artifact.accepted or artifact.artifact is None:
            return _advanced_rejected(request, AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED, BrowserV3AuthorityClass.PRIVATE_SESSION, "private_session_receipt_capture_failed", [artifact.reason], event_bus, policy_trace_id, phase, BrowserPrivateSessionResult)
        receipt = receipt.model_copy(update={"receipt_artifact_id": artifact.artifact.id, "receipt_artifact_sha256": artifact.artifact.sha256})
        event_type = AgentEventType.BROWSER_PRIVATE_SESSION_STARTED if request.operation == "open" else AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED
        event = _append_advanced_event(event_bus, event_type, BrowserV3AuthorityClass.PRIVATE_SESSION, request, receipt, policy_trace_id, phase)
        receipt = receipt.model_copy(update={"trace_refs": [ref for ref in [policy_trace_id, request.compiled_intent_trace_id, artifact.trace_event_id, event.id] if ref]})
        return BrowserPrivateSessionResult(
            accepted=True,
            reason=f"browser_private_session_{request.operation}ed",
            request_id=request.id,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[artifact.artifact.id],
        )


class BrowserLoginAuthorityExecutor:
    def __init__(self, *, backend: BrowserLoginBackend) -> None:
        self.backend = backend

    def execute(self, request: BrowserLoginAuthorityRequest, *, authority_grant: BrowserV3AuthorityGrant, event_bus: EventBus, artifact_capture: ArtifactCaptureSandbox, policy_trace_id: str | None = None, phase: AgentPhase = AgentPhase.EXECUTING) -> BrowserLoginAuthorityResult:
        errors = _validate_common(request, authority_grant, BrowserV3AuthorityClass.LOGIN_AUTHORITY)
        if request.account_id not in authority_grant.allowed_accounts:
            errors.append("login_account_not_granted")
        if not browser_v3_grant_allows_url(authority_grant, request.login_url):
            errors.append("login_url_outside_authority")
        errors.extend(_validate_plan_ref(request.plan, request.login_ref_id, request.login_url))
        if not request.private_session_trace_event_id:
            errors.append("login_missing_private_session_trace")
        if errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, "browser_login_request_rejected", errors, event_bus, policy_trace_id, phase, BrowserLoginAuthorityResult)
        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return _advanced_rejected(request, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, "browser_login_backend_failed", [_sanitize_backend_exception(exc)], event_bus, policy_trace_id, phase, BrowserLoginAuthorityResult)
        if not backend_result.login_success or backend_result.session_id != request.session_id or backend_result.account_id != request.account_id:
            return _advanced_rejected(request, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, "browser_login_not_confirmed", [], event_bus, policy_trace_id, phase, BrowserLoginAuthorityResult)
        backend_errors = _validate_login_backend_reality(request, backend_result)
        if backend_errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, "browser_login_backend_reality_failed", backend_errors, event_bus, policy_trace_id, phase, BrowserLoginAuthorityResult)
        same_origin = _same_origin(backend_result.final_url_before, backend_result.final_url_after)
        if not same_origin and not (authority_grant.allow_cross_origin or request.allow_cross_origin):
            return _advanced_rejected(request, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, "browser_login_cross_origin_result", [], event_bus, policy_trace_id, phase, BrowserLoginAuthorityResult)
        after_page = backend_result.after_page
        if after_page is None:
            return _advanced_rejected(request, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, "browser_login_post_snapshot_missing", [], event_bus, policy_trace_id, phase, BrowserLoginAuthorityResult)
        after_snapshot = after_page.accessibility_snapshot or BrowserAccessibilitySnapshotBuilder().build(html=after_page.html, text=after_page.text)
        artifact = _capture_receipt_artifact(
            artifact_capture,
            event_bus,
            f"browser/login_authority/{request.id}_post_snapshot.json",
            "browser_login_authority_post_snapshot",
            {"after_snapshot": after_snapshot.model_dump(mode="json"), "account_id": request.account_id, "session_id": request.session_id},
            [policy_trace_id, request.compiled_intent_trace_id, request.private_session_trace_event_id, request.plan_trace_event_id],
            phase,
        )
        if not artifact.accepted or artifact.artifact is None:
            return _advanced_rejected(request, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, "browser_login_artifact_capture_failed", [artifact.reason], event_bus, policy_trace_id, phase, BrowserLoginAuthorityResult)
        receipt = BrowserLoginAuthorityReceipt(
            mission_id=request.mission_id,
            authority_grant_id=authority_grant.id,
            request_id=request.id,
            context_pack_id=request.context_pack_id,
            compiled_intent_trace_id=request.compiled_intent_trace_id,
            session_id=request.session_id,
            profile_id=request.profile_id,
            private_session_trace_event_id=request.private_session_trace_event_id,
            account_id=request.account_id,
            login_url_hash=_sha256_text(request.login_url),
            final_url_hash=_sha256_text(backend_result.final_url_after),
            plan_id=request.plan.id,
            plan_sha256=request.plan.plan_sha256,
            plan_trace_event_id=request.plan_trace_event_id,
            before_snapshot_trace_event_id=request.before_snapshot_trace_event_id,
            before_snapshot_sha256=request.plan.snapshot_sha256,
            after_snapshot_sha256=after_snapshot.snapshot_sha256,
            same_origin=same_origin,
            cross_origin_authorized=authority_grant.allow_cross_origin or request.allow_cross_origin,
            login_success=True,
            expected_effect=request.expected_effect,
            post_login_snapshot_artifact_id=artifact.artifact.id,
            post_login_snapshot_artifact_sha256=artifact.artifact.sha256,
        )
        event = _append_advanced_event(event_bus, AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED, BrowserV3AuthorityClass.LOGIN_AUTHORITY, request, receipt, policy_trace_id, phase)
        receipt = receipt.model_copy(update={"trace_refs": [ref for ref in [policy_trace_id, request.compiled_intent_trace_id, request.private_session_trace_event_id, request.plan_trace_event_id, artifact.trace_event_id, event.id] if ref]})
        return BrowserLoginAuthorityResult(
            accepted=True,
            reason="browser_login_authority_executed",
            request_id=request.id,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[artifact.artifact.id],
        )


class BrowserCookieStorageContractExecutor:
    def __init__(self, *, backend: BrowserCookieStorageBackend) -> None:
        self.backend = backend

    def execute(self, request: BrowserCookieStorageContractRequest, *, authority_grant: BrowserV3AuthorityGrant, event_bus: EventBus, artifact_capture: ArtifactCaptureSandbox, policy_trace_id: str | None = None, phase: AgentPhase = AgentPhase.EXECUTING) -> BrowserCookieStorageContractResult:
        errors = _validate_common(request, authority_grant, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT)
        if not _domain_in_grant(authority_grant, request.target_domain):
            errors.append("cookie_storage_domain_outside_authority")
        if request.operation not in {"redacted_summary", "clear_scoped_storage"}:
            errors.append("cookie_storage_operation_invalid")
        if not request.private_session_trace_event_id:
            errors.append("cookie_storage_missing_private_session_trace")
        if errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT, "browser_cookie_storage_request_rejected", errors, event_bus, policy_trace_id, phase, BrowserCookieStorageContractResult)
        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return _advanced_rejected(request, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT, "browser_cookie_storage_backend_failed", [_sanitize_backend_exception(exc)], event_bus, policy_trace_id, phase, BrowserCookieStorageContractResult)
        if authority_grant.redaction_required and (not backend_result.redaction_applied or backend_result.raw_value_exposed):
            return _advanced_rejected(request, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT, "browser_cookie_storage_redaction_failed", [], event_bus, policy_trace_id, phase, BrowserCookieStorageContractResult)
        backend_errors = _validate_cookie_storage_backend_reality(backend_result)
        if backend_errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT, "browser_cookie_storage_backend_reality_failed", backend_errors, event_bus, policy_trace_id, phase, BrowserCookieStorageContractResult)
        artifact = _capture_receipt_artifact(
            artifact_capture,
            event_bus,
            f"browser/cookie_storage/{request.id}_summary.json",
            "browser_cookie_storage_contract_summary",
            {
                "operation": request.operation,
                "target_domain": request.target_domain,
                "cookie_count": backend_result.cookie_count,
                "storage_key_count": backend_result.storage_key_count,
                "redacted_summary": backend_result.redacted_summary,
                "redaction_applied": backend_result.redaction_applied,
                "raw_value_exposed": backend_result.raw_value_exposed,
            },
            [policy_trace_id, request.compiled_intent_trace_id, request.private_session_trace_event_id],
            phase,
        )
        if not artifact.accepted or artifact.artifact is None:
            return _advanced_rejected(request, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT, "browser_cookie_storage_artifact_capture_failed", [artifact.reason], event_bus, policy_trace_id, phase, BrowserCookieStorageContractResult)
        receipt = BrowserCookieStorageContractReceipt(
            mission_id=request.mission_id,
            authority_grant_id=authority_grant.id,
            request_id=request.id,
            context_pack_id=request.context_pack_id,
            compiled_intent_trace_id=request.compiled_intent_trace_id,
            session_id=request.session_id,
            profile_id=request.profile_id,
            private_session_trace_event_id=request.private_session_trace_event_id,
            operation=request.operation,
            target_domain=request.target_domain,
            cookie_count=backend_result.cookie_count,
            storage_key_count=backend_result.storage_key_count,
            storage_state_sha256=backend_result.storage_state_sha256,
            redaction_applied=backend_result.redaction_applied,
            raw_value_exposed=backend_result.raw_value_exposed,
            cleared=backend_result.cleared,
            summary_artifact_id=artifact.artifact.id,
            summary_artifact_sha256=artifact.artifact.sha256,
        )
        event = _append_advanced_event(event_bus, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT, request, receipt, policy_trace_id, phase)
        receipt = receipt.model_copy(update={"trace_refs": [ref for ref in [policy_trace_id, request.compiled_intent_trace_id, request.private_session_trace_event_id, artifact.trace_event_id, event.id] if ref]})
        return BrowserCookieStorageContractResult(
            accepted=True,
            reason="browser_cookie_storage_contract_applied",
            request_id=request.id,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[artifact.artifact.id],
        )


class BrowserJsEvaluateSandboxedExecutor:
    def __init__(self, *, backend: BrowserJsEvaluateBackend) -> None:
        self.backend = backend

    def execute(self, request: BrowserJsEvaluateSandboxedRequest, *, authority_grant: BrowserV3AuthorityGrant, event_bus: EventBus, artifact_capture: ArtifactCaptureSandbox, policy_trace_id: str | None = None, phase: AgentPhase = AgentPhase.EXECUTING) -> BrowserJsEvaluateSandboxedResult:
        errors = _validate_common(request, authority_grant, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED)
        script_hash = _sha256_text(request.script_source)
        if script_hash not in authority_grant.allowed_script_hashes:
            errors.append("js_script_hash_not_granted")
        if not browser_v3_grant_allows_url(authority_grant, request.page_url):
            errors.append("js_page_url_outside_authority")
        max_result_bytes = min(request.max_result_bytes, authority_grant.max_result_bytes or request.max_result_bytes)
        if errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED, "browser_js_evaluate_request_rejected", errors, event_bus, policy_trace_id, phase, BrowserJsEvaluateSandboxedResult)
        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return _advanced_rejected(request, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED, "browser_js_evaluate_backend_failed", [_sanitize_backend_exception(exc)], event_bus, policy_trace_id, phase, BrowserJsEvaluateSandboxedResult)
        if backend_result.network_calls:
            return _advanced_rejected(request, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED, "browser_js_evaluate_network_call_detected", backend_result.network_calls, event_bus, policy_trace_id, phase, BrowserJsEvaluateSandboxedResult)
        result_payload = {"result": backend_result.result, "console": backend_result.console, "timed_out": backend_result.timed_out}
        result_bytes = _canonical_bytes(result_payload)
        if len(result_bytes) > max_result_bytes:
            return _advanced_rejected(request, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED, "browser_js_evaluate_result_too_large", [f"bytes:{len(result_bytes)}"], event_bus, policy_trace_id, phase, BrowserJsEvaluateSandboxedResult)
        artifact = artifact_capture.capture_json(
            relative_path=f"browser/js_evaluate_sandboxed/{request.id}_result.json",
            payload=result_payload,
            artifact_type="browser_js_evaluate_sandboxed_result",
            event_bus=event_bus,
            provenance_refs=[ref for ref in [policy_trace_id, request.compiled_intent_trace_id] if ref],
            phase=phase,
        )
        if not artifact.accepted or artifact.artifact is None:
            return _advanced_rejected(request, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED, "browser_js_evaluate_artifact_capture_failed", [artifact.reason], event_bus, policy_trace_id, phase, BrowserJsEvaluateSandboxedResult)
        receipt = BrowserJsEvaluateSandboxedReceipt(
            mission_id=request.mission_id,
            authority_grant_id=authority_grant.id,
            request_id=request.id,
            context_pack_id=request.context_pack_id,
            compiled_intent_trace_id=request.compiled_intent_trace_id,
            page_url_hash=_sha256_text(request.page_url),
            script_sha256=script_hash,
            script_hash_allowed=True,
            result_sha256=hashlib.sha256(result_bytes).hexdigest(),
            result_size_bytes=len(result_bytes),
            max_result_bytes=max_result_bytes,
            network_calls_blocked=True,
            timed_out=backend_result.timed_out,
            result_artifact_id=artifact.artifact.id,
            result_artifact_sha256=artifact.artifact.sha256,
        )
        event = _append_advanced_event(event_bus, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED, request, receipt, policy_trace_id, phase)
        receipt = receipt.model_copy(update={"trace_refs": [ref for ref in [policy_trace_id, request.compiled_intent_trace_id, artifact.trace_event_id, event.id] if ref]})
        return BrowserJsEvaluateSandboxedResult(
            accepted=True,
            reason="browser_js_evaluate_sandboxed_executed",
            request_id=request.id,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[artifact.artifact.id],
        )


class BrowserHarBodyCaptureExecutor:
    def __init__(self, *, backend: BrowserHarBodyCaptureBackend) -> None:
        self.backend = backend

    def execute(self, request: BrowserHarBodyCaptureRequest, *, authority_grant: BrowserV3AuthorityGrant, event_bus: EventBus, artifact_capture: ArtifactCaptureSandbox, policy_trace_id: str | None = None, phase: AgentPhase = AgentPhase.EXECUTING) -> BrowserHarBodyCaptureResult:
        errors = _validate_common(request, authority_grant, BrowserV3AuthorityClass.HAR_BODY_CAPTURE)
        if not browser_v3_grant_allows_url(authority_grant, request.source_url):
            errors.append("har_source_url_outside_authority")
        max_bytes = min(request.max_bytes, authority_grant.max_bytes or request.max_bytes)
        max_records = min(request.max_records, authority_grant.max_records or request.max_records)
        if errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, "browser_har_capture_request_rejected", errors, event_bus, policy_trace_id, phase, BrowserHarBodyCaptureResult)
        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return _advanced_rejected(request, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, "browser_har_capture_backend_failed", [_sanitize_backend_exception(exc)], event_bus, policy_trace_id, phase, BrowserHarBodyCaptureResult)
        if len(backend_result.entries) > max_records or backend_result.total_bytes > max_bytes:
            return _advanced_rejected(request, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, "browser_har_capture_bounds_exceeded", [f"records:{len(backend_result.entries)}", f"bytes:{backend_result.total_bytes}"], event_bus, policy_trace_id, phase, BrowserHarBodyCaptureResult)
        if authority_grant.redaction_required and not backend_result.redaction_applied:
            return _advanced_rejected(request, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, "browser_har_capture_redaction_missing", [], event_bus, policy_trace_id, phase, BrowserHarBodyCaptureResult)
        backend_errors = _validate_har_backend_reality(backend_result)
        if backend_errors:
            return _advanced_rejected(request, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, "browser_har_capture_backend_reality_failed", backend_errors, event_bus, policy_trace_id, phase, BrowserHarBodyCaptureResult)
        allowed_mimes = request.allowed_mime_types or authority_grant.allowed_mime_types
        if allowed_mimes:
            allowed = {item.lower() for item in allowed_mimes}
            for mime in backend_result.mime_types:
                if mime.split(";", 1)[0].lower() not in allowed:
                    return _advanced_rejected(request, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, "browser_har_capture_mime_not_allowed", [mime], event_bus, policy_trace_id, phase, BrowserHarBodyCaptureResult)
        payload = {
            "source_url_hash": _sha256_text(request.source_url),
            "entries": backend_result.entries,
            "total_bytes": backend_result.total_bytes,
            "redaction_applied": backend_result.redaction_applied,
            "truncated": backend_result.truncated,
        }
        body_hash = backend_result.body_capture_sha256 or hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        artifact = artifact_capture.capture_json(
            relative_path=f"browser/har_body_capture/{request.id}_har.json",
            payload=payload,
            artifact_type="browser_har_body_capture",
            event_bus=event_bus,
            provenance_refs=[ref for ref in [policy_trace_id, request.compiled_intent_trace_id] if ref],
            phase=phase,
        )
        if not artifact.accepted or artifact.artifact is None:
            return _advanced_rejected(request, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, "browser_har_capture_artifact_failed", [artifact.reason], event_bus, policy_trace_id, phase, BrowserHarBodyCaptureResult)
        receipt = BrowserHarBodyCaptureReceipt(
            mission_id=request.mission_id,
            authority_grant_id=authority_grant.id,
            request_id=request.id,
            context_pack_id=request.context_pack_id,
            compiled_intent_trace_id=request.compiled_intent_trace_id,
            source_url=request.source_url,
            source_url_hash=_sha256_text(request.source_url),
            capture_bodies=request.capture_bodies,
            record_count=len(backend_result.entries),
            max_records=max_records,
            total_bytes=backend_result.total_bytes,
            max_bytes=max_bytes,
            redaction_applied=backend_result.redaction_applied,
            body_capture_sha256=body_hash,
            truncated=backend_result.truncated,
            har_artifact_id=artifact.artifact.id,
            har_artifact_sha256=artifact.artifact.sha256,
        )
        event = _append_advanced_event(event_bus, AgentEventType.BROWSER_HAR_BODY_CAPTURED, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, request, receipt, policy_trace_id, phase)
        receipt = receipt.model_copy(update={"trace_refs": [ref for ref in [policy_trace_id, request.compiled_intent_trace_id, artifact.trace_event_id, event.id] if ref]})
        return BrowserHarBodyCaptureResult(
            accepted=True,
            reason="browser_har_body_captured",
            request_id=request.id,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[artifact.artifact.id],
        )


def _validate_common(request: SentinelModel, grant: BrowserV3AuthorityGrant, authority_class: BrowserV3AuthorityClass) -> list[str]:
    errors: list[str] = []
    if grant.authority_class != authority_class:
        errors.append("authority_grant_class_mismatch")
    if grant.id != getattr(request, "authority_grant_id"):
        errors.append("authority_grant_id_mismatch")
    if not getattr(request, "context_pack_id"):
        errors.append("missing_context_pack_id")
    if not getattr(request, "compiled_intent_trace_id"):
        errors.append("missing_compiled_intent_trace_id")
    return errors


def _validate_plan_ref(plan: BrowserInteractionPlan, ref_id: str, final_url: str) -> list[str]:
    errors: list[str] = []
    if not verify_browser_interaction_plan_hash(plan.model_dump(mode="json"), plan.plan_sha256):
        errors.append("plan_hash_invalid")
    plan_ref_ids = set(plan.required_ref_ids)
    plan_ref_ids.update(step.target.ref for step in plan.steps if step.target.ref)
    if ref_id not in plan_ref_ids:
        errors.append("runtime_ref_not_in_certified_plan")
    if plan.final_url and _normalize_origin(plan.final_url) != _normalize_origin(final_url):
        errors.append("request_final_url_origin_mismatch")
    return errors


def _advanced_rejected(
    request: SentinelModel,
    event_type: AgentEventType,
    authority_class: BrowserV3AuthorityClass,
    reason: str,
    errors: list[str],
    event_bus: EventBus,
    policy_trace_id: str | None,
    phase: AgentPhase,
    result_type: type[SentinelModel],
):
    event = event_bus.append(
        event_type,
        f"{authority_class.value} rejected before certified completion.",
        phase_before=phase,
        phase_after=phase,
        payload={
            "request_id": getattr(request, "id"),
            "authority_class": authority_class.value,
            "authority_grant_id": getattr(request, "authority_grant_id"),
            "context_pack_id": getattr(request, "context_pack_id"),
            "compiled_intent_trace_id": getattr(request, "compiled_intent_trace_id"),
            "reason": reason,
            "errors": errors,
            "policy_trace_id": policy_trace_id,
        },
        trace_refs=[ref for ref in [policy_trace_id, getattr(request, "compiled_intent_trace_id", None)] if ref],
    )
    return result_type(accepted=False, reason=reason, request_id=getattr(request, "id"), trace_event_id=event.id, errors=errors)


def _append_advanced_event(
    event_bus: EventBus,
    event_type: AgentEventType,
    authority_class: BrowserV3AuthorityClass,
    request: SentinelModel,
    receipt: BrowserV3Receipt,
    policy_trace_id: str | None,
    phase: AgentPhase,
):
    payload = receipt.model_dump(mode="json")
    payload.update(
        {
            "receipt_id": receipt.id,
            "authority_class": authority_class.value,
            "policy_trace_id": policy_trace_id,
        }
    )
    return event_bus.append(
        event_type,
        f"{authority_class.value} completed through explicit Browser V3 authority.",
        phase_before=phase,
        phase_after=phase,
        payload=payload,
        trace_refs=[ref for ref in [policy_trace_id, getattr(request, "compiled_intent_trace_id", None), *getattr(receipt, "trace_refs", [])] if ref],
    )


def _capture_receipt_artifact(
    artifact_capture: ArtifactCaptureSandbox,
    event_bus: EventBus,
    relative_path: str,
    artifact_type: str,
    payload: dict,
    provenance_refs: list[str | None],
    phase: AgentPhase,
):
    return artifact_capture.capture_json(
        relative_path=relative_path,
        payload=payload,
        artifact_type=artifact_type,
        event_bus=event_bus,
        provenance_refs=[ref for ref in provenance_refs if ref],
        phase=phase,
    )


def _validate_private_session_backend_reality(request: BrowserPrivateSessionRequest, result: BrowserPrivateSessionBackendResult, grant: BrowserV3AuthorityGrant) -> list[str]:
    errors: list[str] = []
    if result.operation != request.operation:
        errors.append("private_session_backend_operation_mismatch")
    if not result.session_id or not result.profile_id:
        errors.append("private_session_backend_missing_ids")
    if not _looks_like_sha256(result.storage_state_sha256):
        errors.append("private_session_backend_storage_hash_invalid")
    if result.storage_enabled and not grant.storage_allowed:
        errors.append("private_session_backend_storage_not_granted")
    if result.storage_enabled and not request.storage_enabled:
        errors.append("private_session_backend_storage_enabled_without_request")
    for domain in result.allowed_domains:
        if not _domain_in_grant(grant, domain):
            errors.append(f"private_session_backend_domain_outside_authority:{domain}")
    if request.operation == "open":
        if not result.created:
            errors.append("private_session_backend_open_not_created")
        if result.destroyed or result.profile_destroyed:
            errors.append("private_session_backend_open_destroyed_flags")
    if request.operation == "close":
        if request.session_id and result.session_id != request.session_id:
            errors.append("private_session_backend_close_session_mismatch")
        if request.profile_id and result.profile_id != request.profile_id:
            errors.append("private_session_backend_close_profile_mismatch")
        if not result.destroyed or not result.profile_destroyed:
            errors.append("private_session_backend_close_not_destroyed")
    return errors


def _validate_login_backend_reality(request: BrowserLoginAuthorityRequest, result: BrowserLoginBackendResult) -> list[str]:
    errors: list[str] = []
    if result.before_snapshot.snapshot_sha256 != request.plan.snapshot_sha256:
        errors.append("browser_login_before_snapshot_mismatch")
    if result.after_page is not None and result.after_page.final_url != result.final_url_after:
        errors.append("browser_login_after_page_url_mismatch")
    if _contains_sensitive_browser_payload(
        {
            "final_url_before": result.final_url_before,
            "final_url_after": result.final_url_after,
            "after_title": result.after_page.title if result.after_page else "",
            "after_text": result.after_page.text if result.after_page else "",
        }
    ):
        errors.append("browser_login_backend_sensitive_payload")
    return errors


def _validate_cookie_storage_backend_reality(result: BrowserCookieStorageBackendResult) -> list[str]:
    errors: list[str] = []
    if not _looks_like_sha256(result.storage_state_sha256):
        errors.append("browser_cookie_storage_state_hash_invalid")
    if result.redaction_applied and _contains_sensitive_browser_payload(result.redacted_summary):
        errors.append("browser_cookie_storage_redacted_summary_contains_sensitive_payload")
    return errors


def _validate_har_backend_reality(result: BrowserHarBodyCaptureBackendResult) -> list[str]:
    errors: list[str] = []
    if result.body_capture_sha256 is not None and not _looks_like_sha256(result.body_capture_sha256):
        errors.append("browser_har_body_hash_invalid")
    if result.redaction_applied and _contains_sensitive_browser_payload(result.entries):
        errors.append("browser_har_entries_contain_sensitive_payload")
    return errors


def _domain_in_grant(grant: BrowserV3AuthorityGrant, domain: str) -> bool:
    if not grant.allowed_domains:
        return True
    host = domain.lower().removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    return any(host == allowed.lower() or host.endswith(f".{allowed.lower()}") for allowed in grant.allowed_domains)


def _same_origin(left: str, right: str) -> bool:
    return _normalize_origin(left) == _normalize_origin(right)


def _normalize_origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlparse(value)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")


def _looks_like_sha256(value: str | None) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdefABCDEF" for character in value)


def _contains_sensitive_browser_payload(value: object) -> bool:
    haystack = json.dumps(value, sort_keys=True, default=str).lower()
    markers = (
        "authorization:",
        "bearer ",
        "set-cookie:",
        "document.cookie",
        "password=",
        "secret=",
        "credential=",
        "cookie:",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "session_token",
        "private_key",
    )
    if any(marker in haystack for marker in markers):
        return True
    return re.search(
        r"(?i)(authorization|cookie|set-cookie|password|secret|token|credential|api[_-]?key|access[_-]?token)\s*[\"':=]",
        haystack,
    ) is not None


def _sanitize_backend_exception(exc: Exception) -> str:
    message = str(exc)[:300]
    redacted = re.sub(r"(?i)(authorization\s*[:=]\s*)[^\r\n,;]+", r"\1[REDACTED]", message)
    redacted = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", redacted)
    redacted = re.sub(r"(?i)(password|secret|token|credential|authorization|cookie)(\s*[:=]\s*)[^\s,;]+", r"\1\2[REDACTED]", redacted)
    return f"{type(exc).__name__}:{redacted}"
