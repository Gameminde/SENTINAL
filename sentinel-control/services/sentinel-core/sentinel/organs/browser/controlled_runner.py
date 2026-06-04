from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from sentinel.agent.artifact_capture import ArtifactCaptureSandbox, CapturedArtifact  # noqa: E402 — agent-layer utility used cross-layer (Wave D documented exception)
from sentinel.agent.tool_call_protocol import CanonicalToolCall  # noqa: E402 — agent-layer cognitive bridge used by browser orchestrator (Wave D documented exception)
from sentinel.capabilities.models import ToolInvocation
from sentinel.capabilities.registry import ToolRegistry
from sentinel.capabilities.risk import ToolExecutionStatus, ToolSideEffect
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.organs.browser.download_quarantine import (
    BrowserDownloadBackend,
    BrowserDownloadQuarantineExecutor,
    BrowserDownloadQuarantineRequest,
)
from sentinel.organs.browser.evidence_adapter import BrowserEvidenceAdapter, BrowserFetcher
from sentinel.organs.browser.form_submit import (
    BrowserFormSubmitBackend,
    BrowserFormSubmitExecutor,
    BrowserFormSubmitRequest,
)
from sentinel.organs.browser.interaction_execution import (
    BrowserInteractionBackend,
    BrowserLimitedInteractionExecutor,
)
from sentinel.organs.browser.live_fetch import ReadOnlyHttpFetcher
from sentinel.organs.browser.models import (
    BrowserControlledCapabilityResult,
    BrowserControlledCapabilityStatus,
    BrowserEvidenceFetchRequest,
    BrowserInteractionExecutionRequest,
    BrowserInteractionPlan,
    BrowserRenderedSnapshotRequest,
)
from sentinel.organs.browser.rendered_snapshot import BrowserRenderedSnapshotAdapter, BrowserRenderer
from sentinel.organs.browser.upload_authorized import (
    BrowserUploadAuthorizedExecutor,
    BrowserUploadAuthorizedRequest,
    BrowserUploadBackend,
)
from sentinel.organs.browser.url_guard import DnsResolver
from sentinel.organs.browser.v3_advanced_authorities import (
    BrowserCookieStorageBackend,
    BrowserCookieStorageContractExecutor,
    BrowserCookieStorageContractRequest,
    BrowserHarBodyCaptureBackend,
    BrowserHarBodyCaptureExecutor,
    BrowserHarBodyCaptureRequest,
    BrowserJsEvaluateBackend,
    BrowserJsEvaluateSandboxedExecutor,
    BrowserJsEvaluateSandboxedRequest,
    BrowserLoginAuthorityExecutor,
    BrowserLoginAuthorityRequest,
    BrowserPrivateSessionBackend,
    BrowserPrivateSessionExecutor,
    BrowserPrivateSessionRequest,
)
from sentinel.organs.browser.v3_authority import BrowserV3AuthorityClass, find_browser_v3_authority_grant
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.safety_scanner import parse_authority_bool, parse_evidence_bool


class BrowserControlledCapabilityRunner:
    SUPPORTED_ACTIONS = frozenset(
        {
            "browser_read_public_page",
            "browser_render_public_page",
            "browser_interaction_limited",
            "browser_form_submit",
            "browser_download_quarantine",
            "browser_upload_authorized",
            "browser_private_session",
            "browser_login_authority",
            "browser_cookie_storage_contract",
            "browser_js_evaluate_sandboxed",
            "browser_har_body_capture",
        }
    )

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        capture_root: str | Path,
        renderer: BrowserRenderer | None = None,
        fetcher: BrowserFetcher | None = None,
        interaction_backend: BrowserInteractionBackend | None = None,
        form_submit_backend: BrowserFormSubmitBackend | None = None,
        download_backend: BrowserDownloadBackend | None = None,
        upload_backend: BrowserUploadBackend | None = None,
        private_session_backend: BrowserPrivateSessionBackend | None = None,
        login_backend: BrowserLoginBackend | None = None,
        cookie_storage_backend: BrowserCookieStorageBackend | None = None,
        js_evaluate_backend: BrowserJsEvaluateBackend | None = None,
        har_body_backend: BrowserHarBodyCaptureBackend | None = None,
        resolver: DnsResolver | None = None,
    ) -> None:
        self.registry = registry
        self.capture_root = Path(capture_root).resolve()
        self.renderer = renderer
        self.fetcher = fetcher or ReadOnlyHttpFetcher()
        self.interaction_backend = interaction_backend
        self.form_submit_backend = form_submit_backend
        self.download_backend = download_backend
        self.upload_backend = upload_backend
        self.private_session_backend = private_session_backend
        self.login_backend = login_backend
        self.cookie_storage_backend = cookie_storage_backend
        self.js_evaluate_backend = js_evaluate_backend
        self.har_body_backend = har_body_backend
        self.resolver = resolver

    def run(
        self,
        call: CanonicalToolCall,
        envelope: MissionAuthorityEnvelope,
        *,
        event_bus: EventBus,
    ) -> BrowserControlledCapabilityResult:
        if event_bus.mission_id != envelope.id:
            raise ValueError("Browser capability trace mission_id must match the mission authority envelope.")

        manifest = self.registry.maybe_get(call.tool_id)
        manifest_effects = manifest.side_effects if manifest is not None else []
        requested_effects = self._unique_effects([*manifest_effects, *call.requested_side_effects])
        policy_decision = self.registry.decide(
            ToolInvocation(
                tool_id=call.tool_id,
                action=call.action,
                requested_side_effects=requested_effects,
                capability=call.capability,
                target=call.target,
            ),
            envelope,
            event_bus=event_bus,
        )
        if not policy_decision.allowed:
            return self._rejected(
                call,
                reason=policy_decision.reason,
                event_bus=event_bus,
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
            )
        if call.action not in self.SUPPORTED_ACTIONS:
            return self._rejected(
                call,
                reason="browser_action_not_supported",
                event_bus=event_bus,
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
            )
        authority_bool_error = _authority_bool_error(call.action, call.arguments)
        if authority_bool_error:
            return self._rejected(
                call,
                reason=authority_bool_error,
                event_bus=event_bus,
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
            )

        sandbox = ArtifactCaptureSandbox(mission_id=envelope.id, capture_root=self.capture_root)
        url = str(call.arguments.get("url") or call.target or "")
        purpose = str(call.arguments.get("purpose") or call.action)
        allowed_domains = call.arguments.get("allowed_domains") or []
        if not isinstance(allowed_domains, list):
            allowed_domains = []
        if call.action == "browser_read_public_page":
            result = BrowserEvidenceAdapter(fetcher=self.fetcher).collect(
                BrowserEvidenceFetchRequest(
                    mission_id=envelope.id,
                    url=url,
                    purpose=purpose,
                    allowed_domains=[str(domain) for domain in allowed_domains],
                    max_redirects=int(call.arguments.get("max_redirects") or 3),
                    max_bytes=int(call.arguments.get("max_bytes") or 1_000_000),
                    max_chars=int(call.arguments.get("max_chars") or 100_000),
                ),
                event_bus=event_bus,
                artifact_capture=sandbox,
                resolver=self.resolver,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(call, result.reason, event_bus, policy_decision.status, policy_decision.trace_event_id, result.trace_event_id, result.errors)
            return BrowserControlledCapabilityResult(
                accepted=True,
                status=BrowserControlledCapabilityStatus.EXECUTED,
                tool_id=call.tool_id,
                action=call.action,
                reason="browser_read_public_page_executed",
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
                browser_trace_event_id=result.trace_event_id,
                trace_event_id=result.trace_event_id,
                receipt_id=result.receipt.id,
                artifact_ids=[result.receipt.artifact_id] if result.receipt.artifact_id else [],
            )

        if call.action == "browser_interaction_limited":
            if self.interaction_backend is None:
                return self._rejected(
                    call,
                    reason="browser_interaction_backend_not_configured",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            plan_payload = call.arguments.get("plan")
            if not isinstance(plan_payload, dict):
                return self._rejected(
                    call,
                    reason="browser_interaction_plan_missing",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            try:
                plan = BrowserInteractionPlan(**plan_payload)
            except Exception as exc:
                return self._rejected(
                    call,
                    reason="browser_interaction_plan_invalid",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                ).model_copy(update={"errors": [f"{type(exc).__name__}:{str(exc)[:300]}"]})

            plan_trace_event_id = str(call.arguments.get("plan_trace_event_id") or "")
            before_snapshot_trace_event_id = str(call.arguments.get("before_snapshot_trace_event_id") or "")
            final_url = str(call.arguments.get("final_url") or plan.final_url or call.target or "")
            result = BrowserLimitedInteractionExecutor(backend=self.interaction_backend).execute(
                BrowserInteractionExecutionRequest(
                    mission_id=envelope.id,
                    plan=plan,
                    plan_trace_event_id=plan_trace_event_id,
                    before_snapshot_trace_event_id=before_snapshot_trace_event_id,
                    final_url=final_url,
                    allowed_domains=[str(domain) for domain in allowed_domains],
                    max_chars=int(call.arguments.get("max_chars") or 100_000),
                    max_html_chars=int(call.arguments.get("max_html_chars") or 200_000),
                    max_screenshot_bytes=int(call.arguments.get("max_screenshot_bytes") or 2_000_000),
                    capture_screenshot=parse_browser_evidence_bool_arg(call.arguments.get("capture_screenshot"), field_name="capture_screenshot", default=True),
                    timeout_ms=int(call.arguments.get("timeout_ms") or 15_000),
                ),
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(
                    call,
                    result.reason,
                    event_bus,
                    policy_decision.status,
                    policy_decision.trace_event_id,
                    result.trace_event_id,
                    result.errors,
                )
            return BrowserControlledCapabilityResult(
                accepted=True,
                status=BrowserControlledCapabilityStatus.EXECUTED,
                tool_id=call.tool_id,
                action=call.action,
                reason="browser_interaction_limited_executed",
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
                browser_trace_event_id=result.trace_event_id,
                trace_event_id=result.trace_event_id,
                receipt_id=result.receipt.id,
                artifact_ids=result.artifact_ids,
            )

        if call.action == "browser_form_submit":
            if self.form_submit_backend is None:
                return self._rejected(
                    call,
                    reason="browser_form_submit_backend_not_configured",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            plan_payload = call.arguments.get("plan")
            if not isinstance(plan_payload, dict):
                return self._rejected(
                    call,
                    reason="browser_form_submit_plan_missing",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            authority_grant_id = str(call.arguments.get("authority_grant_id") or "")
            authority_grant = find_browser_v3_authority_grant(
                envelope.browser_v3_authority_grants,
                BrowserV3AuthorityClass.FORM_SUBMIT,
                grant_id=authority_grant_id or None,
            )
            if authority_grant is None:
                return self._rejected(
                    call,
                    reason="browser_v3_authority_grant_missing",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            try:
                plan = BrowserInteractionPlan(**plan_payload)
            except Exception as exc:
                return self._rejected(
                    call,
                    reason="browser_form_submit_plan_invalid",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                ).model_copy(update={"errors": [f"{type(exc).__name__}:{str(exc)[:300]}"]})

            result = BrowserFormSubmitExecutor(backend=self.form_submit_backend).execute(
                BrowserFormSubmitRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    plan=plan,
                    plan_trace_event_id=str(call.arguments.get("plan_trace_event_id") or ""),
                    before_snapshot_trace_event_id=str(call.arguments.get("before_snapshot_trace_event_id") or ""),
                    final_url=str(call.arguments.get("final_url") or plan.final_url or call.target or ""),
                    form_ref_id=str(call.arguments.get("form_ref_id") or ""),
                    submit_ref_id=str(call.arguments.get("submit_ref_id") or ""),
                    expected_effect=str(call.arguments.get("expected_effect") or ""),
                    submit_kind=str(call.arguments.get("submit_kind") or "submit"),
                    flow_type=str(call.arguments.get("flow_type") or "generic"),
                    allow_cross_origin=parse_browser_authority_bool_arg(call.arguments.get("allow_cross_origin"), field_name="allow_cross_origin", default=False),
                    capture_screenshot=parse_browser_evidence_bool_arg(call.arguments.get("capture_screenshot"), field_name="capture_screenshot", default=True),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(
                    call,
                    result.reason,
                    event_bus,
                    policy_decision.status,
                    policy_decision.trace_event_id,
                    result.trace_event_id,
                    result.errors,
                )
            return BrowserControlledCapabilityResult(
                accepted=True,
                status=BrowserControlledCapabilityStatus.EXECUTED,
                tool_id=call.tool_id,
                action=call.action,
                reason="browser_form_submit_executed",
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
                browser_trace_event_id=result.trace_event_id,
                trace_event_id=result.trace_event_id,
                receipt_id=result.receipt.id,
                artifact_ids=result.artifact_ids,
            )

        if call.action == "browser_download_quarantine":
            if self.download_backend is None:
                return self._rejected(
                    call,
                    reason="browser_download_backend_not_configured",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            authority_grant_id = str(call.arguments.get("authority_grant_id") or "")
            authority_grant = find_browser_v3_authority_grant(
                envelope.browser_v3_authority_grants,
                BrowserV3AuthorityClass.DOWNLOAD_QUARANTINE,
                grant_id=authority_grant_id or None,
            )
            if authority_grant is None:
                return self._rejected(
                    call,
                    reason="browser_v3_authority_grant_missing",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            result = BrowserDownloadQuarantineExecutor(backend=self.download_backend).execute(
                BrowserDownloadQuarantineRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    source_url=str(call.arguments.get("source_url") or call.arguments.get("url") or call.target or ""),
                    expected_effect=str(call.arguments.get("expected_effect") or "file captured into quarantine"),
                    source_ref_id=str(call.arguments.get("source_ref_id") or call.arguments.get("ref_id") or "") or None,
                    filename_hint=str(call.arguments.get("filename_hint") or "") or None,
                    allowed_mime_types=[str(item) for item in (call.arguments.get("allowed_mime_types") or [])],
                    max_bytes=int(call.arguments.get("max_bytes") or authority_grant.max_bytes or 50_000_000),
                    quarantine_subdir=str(call.arguments.get("quarantine_subdir") or authority_grant.quarantine_path),
                    allow_cross_origin=parse_browser_authority_bool_arg(call.arguments.get("allow_cross_origin"), field_name="allow_cross_origin", default=False),
                    require_https=parse_browser_authority_bool_arg(call.arguments.get("require_https"), field_name="require_https", default=True),
                    require_dns_resolution=parse_browser_authority_bool_arg(call.arguments.get("require_dns_resolution"), field_name="require_dns_resolution", default=False),
                    max_redirects=int(call.arguments.get("max_redirects") or 3),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
                resolver=self.resolver,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(
                    call,
                    result.reason,
                    event_bus,
                    policy_decision.status,
                    policy_decision.trace_event_id,
                    result.trace_event_id,
                    result.errors,
                )
            return BrowserControlledCapabilityResult(
                accepted=True,
                status=BrowserControlledCapabilityStatus.EXECUTED,
                tool_id=call.tool_id,
                action=call.action,
                reason="browser_download_quarantined",
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
                browser_trace_event_id=result.trace_event_id,
                trace_event_id=result.trace_event_id,
                receipt_id=result.receipt.id,
                artifact_ids=result.artifact_ids,
            )

        if call.action == "browser_upload_authorized":
            if self.upload_backend is None:
                return self._rejected(
                    call,
                    reason="browser_upload_backend_not_configured",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            plan_payload = call.arguments.get("plan")
            if not isinstance(plan_payload, dict):
                return self._rejected(
                    call,
                    reason="browser_upload_plan_missing",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            source_artifact_payload = call.arguments.get("source_artifact")
            if not isinstance(source_artifact_payload, dict):
                return self._rejected(
                    call,
                    reason="browser_upload_source_artifact_missing",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            authority_grant_id = str(call.arguments.get("authority_grant_id") or "")
            authority_grant = find_browser_v3_authority_grant(
                envelope.browser_v3_authority_grants,
                BrowserV3AuthorityClass.UPLOAD_AUTHORIZED,
                grant_id=authority_grant_id or None,
            )
            if authority_grant is None:
                return self._rejected(
                    call,
                    reason="browser_v3_authority_grant_missing",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            try:
                plan = BrowserInteractionPlan(**plan_payload)
                source_artifact = CapturedArtifact(**source_artifact_payload)
            except Exception as exc:
                return self._rejected(
                    call,
                    reason="browser_upload_request_invalid",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                ).model_copy(update={"errors": [f"{type(exc).__name__}:{str(exc)[:300]}"]})
            result = BrowserUploadAuthorizedExecutor(backend=self.upload_backend).execute(
                BrowserUploadAuthorizedRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    plan=plan,
                    plan_trace_event_id=str(call.arguments.get("plan_trace_event_id") or ""),
                    before_snapshot_trace_event_id=str(call.arguments.get("before_snapshot_trace_event_id") or ""),
                    final_url=str(call.arguments.get("final_url") or plan.final_url or call.target or ""),
                    upload_ref_id=str(call.arguments.get("upload_ref_id") or ""),
                    form_ref_id=str(call.arguments.get("form_ref_id") or "") or None,
                    source_artifact=source_artifact,
                    expected_effect=str(call.arguments.get("expected_effect") or ""),
                    field_name_hash=str(call.arguments.get("field_name_hash") or "") or None,
                    flow_type=str(call.arguments.get("flow_type") or "artifact_upload"),
                    allow_cross_origin=parse_browser_authority_bool_arg(call.arguments.get("allow_cross_origin"), field_name="allow_cross_origin", default=False),
                    capture_screenshot=parse_browser_evidence_bool_arg(call.arguments.get("capture_screenshot"), field_name="capture_screenshot", default=True),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(
                    call,
                    result.reason,
                    event_bus,
                    policy_decision.status,
                    policy_decision.trace_event_id,
                    result.trace_event_id,
                    result.errors,
                )
            return BrowserControlledCapabilityResult(
                accepted=True,
                status=BrowserControlledCapabilityStatus.EXECUTED,
                tool_id=call.tool_id,
                action=call.action,
                reason="browser_upload_authorized_executed",
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
                browser_trace_event_id=result.trace_event_id,
                trace_event_id=result.trace_event_id,
                receipt_id=result.receipt.id,
                artifact_ids=result.artifact_ids,
            )

        if call.action == "browser_private_session":
            if self.private_session_backend is None:
                return self._rejected(
                    call,
                    reason="browser_private_session_backend_not_configured",
                    event_bus=event_bus,
                    policy_status=policy_decision.status,
                    policy_trace_id=policy_decision.trace_event_id,
                )
            authority_grant = find_browser_v3_authority_grant(
                envelope.browser_v3_authority_grants,
                BrowserV3AuthorityClass.PRIVATE_SESSION,
                grant_id=str(call.arguments.get("authority_grant_id") or "") or None,
            )
            if authority_grant is None:
                return self._rejected(call, reason="browser_v3_authority_grant_missing", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            result = BrowserPrivateSessionExecutor(backend=self.private_session_backend).execute(
                BrowserPrivateSessionRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    operation=str(call.arguments.get("operation") or "open"),
                    allowed_domains=[str(item) for item in (call.arguments.get("allowed_domains") or envelope.allowed_domains)],
                    session_id=str(call.arguments.get("session_id") or "") or None,
                    profile_id=str(call.arguments.get("profile_id") or "") or None,
                    storage_enabled=parse_browser_authority_bool_arg(call.arguments.get("storage_enabled"), field_name="storage_enabled", default=False),
                    expected_effect=str(call.arguments.get("expected_effect") or "private browser session boundary"),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(call, result.reason, event_bus, policy_decision.status, policy_decision.trace_event_id, result.trace_event_id, result.errors)
            return BrowserControlledCapabilityResult(
                accepted=True,
                status=BrowserControlledCapabilityStatus.EXECUTED,
                tool_id=call.tool_id,
                action=call.action,
                reason=result.reason,
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
                browser_trace_event_id=result.trace_event_id,
                trace_event_id=result.trace_event_id,
                receipt_id=result.receipt.id,
                artifact_ids=result.artifact_ids,
            )

        if call.action == "browser_cookie_storage_contract":
            if self.cookie_storage_backend is None:
                return self._rejected(call, reason="browser_cookie_storage_backend_not_configured", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            authority_grant = find_browser_v3_authority_grant(envelope.browser_v3_authority_grants, BrowserV3AuthorityClass.COOKIE_STORAGE_CONTRACT, grant_id=str(call.arguments.get("authority_grant_id") or "") or None)
            if authority_grant is None:
                return self._rejected(call, reason="browser_v3_authority_grant_missing", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            result = BrowserCookieStorageContractExecutor(backend=self.cookie_storage_backend).execute(
                BrowserCookieStorageContractRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    session_id=str(call.arguments.get("session_id") or ""),
                    profile_id=str(call.arguments.get("profile_id") or ""),
                    private_session_trace_event_id=str(call.arguments.get("private_session_trace_event_id") or ""),
                    operation=str(call.arguments.get("operation") or "redacted_summary"),
                    target_domain=str(call.arguments.get("target_domain") or ""),
                    expected_effect=str(call.arguments.get("expected_effect") or "redacted cookie/storage contract applied"),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(call, result.reason, event_bus, policy_decision.status, policy_decision.trace_event_id, result.trace_event_id, result.errors)
            return BrowserControlledCapabilityResult(accepted=True, status=BrowserControlledCapabilityStatus.EXECUTED, tool_id=call.tool_id, action=call.action, reason=result.reason, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id, browser_trace_event_id=result.trace_event_id, trace_event_id=result.trace_event_id, receipt_id=result.receipt.id, artifact_ids=result.artifact_ids)

        if call.action == "browser_js_evaluate_sandboxed":
            if self.js_evaluate_backend is None:
                return self._rejected(call, reason="browser_js_evaluate_backend_not_configured", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            authority_grant = find_browser_v3_authority_grant(envelope.browser_v3_authority_grants, BrowserV3AuthorityClass.JS_EVALUATE_SANDBOXED, grant_id=str(call.arguments.get("authority_grant_id") or "") or None)
            if authority_grant is None:
                return self._rejected(call, reason="browser_v3_authority_grant_missing", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            result = BrowserJsEvaluateSandboxedExecutor(backend=self.js_evaluate_backend).execute(
                BrowserJsEvaluateSandboxedRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    page_url=str(call.arguments.get("page_url") or call.target or ""),
                    script_source=str(call.arguments.get("script_source") or ""),
                    expected_effect=str(call.arguments.get("expected_effect") or "sandboxed script evaluated"),
                    max_result_bytes=int(call.arguments.get("max_result_bytes") or authority_grant.max_result_bytes or 1_000_000),
                    timeout_ms=int(call.arguments.get("timeout_ms") or 5_000),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(call, result.reason, event_bus, policy_decision.status, policy_decision.trace_event_id, result.trace_event_id, result.errors)
            return BrowserControlledCapabilityResult(accepted=True, status=BrowserControlledCapabilityStatus.EXECUTED, tool_id=call.tool_id, action=call.action, reason=result.reason, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id, browser_trace_event_id=result.trace_event_id, trace_event_id=result.trace_event_id, receipt_id=result.receipt.id, artifact_ids=result.artifact_ids)

        if call.action == "browser_har_body_capture":
            if self.har_body_backend is None:
                return self._rejected(call, reason="browser_har_body_backend_not_configured", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            authority_grant = find_browser_v3_authority_grant(envelope.browser_v3_authority_grants, BrowserV3AuthorityClass.HAR_BODY_CAPTURE, grant_id=str(call.arguments.get("authority_grant_id") or "") or None)
            if authority_grant is None:
                return self._rejected(call, reason="browser_v3_authority_grant_missing", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            result = BrowserHarBodyCaptureExecutor(backend=self.har_body_backend).execute(
                BrowserHarBodyCaptureRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    source_url=str(call.arguments.get("source_url") or call.target or ""),
                    capture_bodies=parse_browser_authority_bool_arg(call.arguments.get("capture_bodies"), field_name="capture_bodies", default=True),
                    allowed_mime_types=[str(item) for item in (call.arguments.get("allowed_mime_types") or authority_grant.allowed_mime_types)],
                    max_bytes=int(call.arguments.get("max_bytes") or authority_grant.max_bytes or 10_000_000),
                    max_records=int(call.arguments.get("max_records") or authority_grant.max_records or 500),
                    expected_effect=str(call.arguments.get("expected_effect") or "bounded HAR/body capture"),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(call, result.reason, event_bus, policy_decision.status, policy_decision.trace_event_id, result.trace_event_id, result.errors)
            return BrowserControlledCapabilityResult(accepted=True, status=BrowserControlledCapabilityStatus.EXECUTED, tool_id=call.tool_id, action=call.action, reason=result.reason, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id, browser_trace_event_id=result.trace_event_id, trace_event_id=result.trace_event_id, receipt_id=result.receipt.id, artifact_ids=result.artifact_ids)

        if call.action == "browser_login_authority":
            if self.login_backend is None:
                return self._rejected(call, reason="browser_login_backend_not_configured", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            plan_payload = call.arguments.get("plan")
            if not isinstance(plan_payload, dict):
                return self._rejected(call, reason="browser_login_plan_missing", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            authority_grant = find_browser_v3_authority_grant(envelope.browser_v3_authority_grants, BrowserV3AuthorityClass.LOGIN_AUTHORITY, grant_id=str(call.arguments.get("authority_grant_id") or "") or None)
            if authority_grant is None:
                return self._rejected(call, reason="browser_v3_authority_grant_missing", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id)
            try:
                plan = BrowserInteractionPlan(**plan_payload)
            except Exception as exc:
                return self._rejected(call, reason="browser_login_plan_invalid", event_bus=event_bus, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id).model_copy(update={"errors": [f"{type(exc).__name__}:{str(exc)[:300]}"]})
            result = BrowserLoginAuthorityExecutor(backend=self.login_backend).execute(
                BrowserLoginAuthorityRequest(
                    mission_id=envelope.id,
                    authority_grant_id=authority_grant.id,
                    context_pack_id=str(call.arguments.get("context_pack_id") or ""),
                    compiled_intent_trace_id=str(call.arguments.get("compiled_intent_trace_id") or ""),
                    session_id=str(call.arguments.get("session_id") or ""),
                    profile_id=str(call.arguments.get("profile_id") or ""),
                    private_session_trace_event_id=str(call.arguments.get("private_session_trace_event_id") or ""),
                    account_id=str(call.arguments.get("account_id") or ""),
                    login_url=str(call.arguments.get("login_url") or call.target or ""),
                    plan=plan,
                    plan_trace_event_id=str(call.arguments.get("plan_trace_event_id") or ""),
                    before_snapshot_trace_event_id=str(call.arguments.get("before_snapshot_trace_event_id") or ""),
                    login_ref_id=str(call.arguments.get("login_ref_id") or ""),
                    expected_effect=str(call.arguments.get("expected_effect") or "account session authenticated"),
                    allow_cross_origin=parse_browser_authority_bool_arg(call.arguments.get("allow_cross_origin"), field_name="allow_cross_origin", default=False),
                    timeout_ms=int(call.arguments.get("timeout_ms") or 30_000),
                ),
                authority_grant=authority_grant,
                event_bus=event_bus,
                artifact_capture=sandbox,
                policy_trace_id=policy_decision.trace_event_id,
            )
            if not result.accepted or result.receipt is None:
                return self._browser_rejected(call, result.reason, event_bus, policy_decision.status, policy_decision.trace_event_id, result.trace_event_id, result.errors)
            return BrowserControlledCapabilityResult(accepted=True, status=BrowserControlledCapabilityStatus.EXECUTED, tool_id=call.tool_id, action=call.action, reason=result.reason, policy_status=policy_decision.status, policy_trace_id=policy_decision.trace_event_id, browser_trace_event_id=result.trace_event_id, trace_event_id=result.trace_event_id, receipt_id=result.receipt.id, artifact_ids=result.artifact_ids)

        if self.renderer is None:
            return self._rejected(
                call,
                reason="browser_renderer_not_configured",
                event_bus=event_bus,
                policy_status=policy_decision.status,
                policy_trace_id=policy_decision.trace_event_id,
            )
        result = BrowserRenderedSnapshotAdapter(renderer=self.renderer).capture(
            BrowserRenderedSnapshotRequest(
                mission_id=envelope.id,
                url=url,
                purpose=purpose,
                allowed_domains=[str(domain) for domain in allowed_domains],
                max_redirects=int(call.arguments.get("max_redirects") or 3),
                max_chars=int(call.arguments.get("max_chars") or 100_000),
                max_html_chars=int(call.arguments.get("max_html_chars") or 200_000),
                max_screenshot_bytes=int(call.arguments.get("max_screenshot_bytes") or 2_000_000),
                max_screenshot_side=int(call.arguments.get("max_screenshot_side") or 4_000),
                capture_screenshot=parse_browser_evidence_bool_arg(call.arguments.get("capture_screenshot"), field_name="capture_screenshot", default=True),
                capture_pdf=parse_browser_evidence_bool_arg(call.arguments.get("capture_pdf"), field_name="capture_pdf", default=False),
                max_pdf_bytes=int(call.arguments.get("max_pdf_bytes") or 10_000_000),
                capture_element_screenshots=parse_browser_evidence_bool_arg(call.arguments.get("capture_element_screenshots"), field_name="capture_element_screenshots", default=False),
                element_screenshot_ref_ids=[str(ref_id) for ref_id in (call.arguments.get("element_screenshot_ref_ids") or [])],
                max_element_screenshots=int(call.arguments.get("max_element_screenshots") or 8),
                max_element_screenshot_bytes=int(call.arguments.get("max_element_screenshot_bytes") or 1_000_000),
                max_element_screenshot_side=int(call.arguments.get("max_element_screenshot_side") or 2_000),
            ),
            event_bus=event_bus,
            artifact_capture=sandbox,
            resolver=self.resolver,
        )
        if not result.accepted or result.receipt is None:
            return self._browser_rejected(call, result.reason, event_bus, policy_decision.status, policy_decision.trace_event_id, result.trace_event_id, result.errors)
        artifact_ids = [
            result.receipt.snapshot_artifact_id,
            result.receipt.screenshot_artifact_id,
            result.receipt.pdf_artifact_id,
            *(item.get("artifact_id") for item in result.receipt.element_screenshot_artifacts),
        ]
        return BrowserControlledCapabilityResult(
            accepted=True,
            status=BrowserControlledCapabilityStatus.EXECUTED,
            tool_id=call.tool_id,
            action=call.action,
            reason="browser_render_public_page_executed",
            policy_status=policy_decision.status,
            policy_trace_id=policy_decision.trace_event_id,
            browser_trace_event_id=result.trace_event_id,
            trace_event_id=result.trace_event_id,
            receipt_id=result.receipt.id,
            artifact_ids=[artifact_id for artifact_id in artifact_ids if artifact_id],
        )

    @staticmethod
    def _unique_effects(effects: Iterable[ToolSideEffect]) -> list[ToolSideEffect]:
        return list(dict.fromkeys(effects))

    @staticmethod
    def _rejected(
        call: CanonicalToolCall,
        *,
        reason: str,
        event_bus: EventBus,
        policy_status: ToolExecutionStatus | None = None,
        policy_trace_id: str | None = None,
    ) -> BrowserControlledCapabilityResult:
        event = event_bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
            "Browser capability request rejected before execution.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "tool_id": call.tool_id,
                "action": call.action,
                "reason": reason,
                "policy_status": policy_status,
                "policy_trace_id": policy_trace_id,
            },
            trace_refs=[policy_trace_id] if policy_trace_id else [],
        )
        return BrowserControlledCapabilityResult(
            accepted=False,
            status=BrowserControlledCapabilityStatus.REJECTED,
            tool_id=call.tool_id,
            action=call.action,
            reason=reason,
            policy_status=policy_status,
            policy_trace_id=policy_trace_id,
            trace_event_id=event.id,
        )

    @classmethod
    def _browser_rejected(
        cls,
        call: CanonicalToolCall,
        reason: str,
        event_bus: EventBus,
        policy_status: ToolExecutionStatus | None,
        policy_trace_id: str | None,
        browser_trace_event_id: str | None,
        errors: list[str],
    ) -> BrowserControlledCapabilityResult:
        event = event_bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_REJECTED,
            "Browser capability request rejected by browser boundary.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={
                "tool_id": call.tool_id,
                "action": call.action,
                "reason": reason,
                "policy_status": policy_status,
                "policy_trace_id": policy_trace_id,
                "browser_trace_event_id": browser_trace_event_id,
                "errors": errors,
            },
            trace_refs=[ref for ref in [policy_trace_id, browser_trace_event_id] if ref],
        )
        return BrowserControlledCapabilityResult(
            accepted=False,
            status=BrowserControlledCapabilityStatus.REJECTED,
            tool_id=call.tool_id,
            action=call.action,
            reason=reason,
            policy_status=policy_status,
            policy_trace_id=policy_trace_id,
            browser_trace_event_id=browser_trace_event_id,
            trace_event_id=event.id,
            errors=errors,
        )


_AUTHORITY_BOOL_FIELDS_BY_ACTION: dict[str, set[str]] = {
    "browser_form_submit": {"allow_cross_origin"},
    "browser_download_quarantine": {"allow_cross_origin", "require_https", "require_dns_resolution"},
    "browser_upload_authorized": {"allow_cross_origin"},
    "browser_private_session": {"storage_enabled"},
    "browser_har_body_capture": {"capture_bodies"},
    "browser_login_authority": {"allow_cross_origin"},
}


def _authority_bool_error(action: str, arguments: dict[str, object]) -> str | None:
    for field_name in _AUTHORITY_BOOL_FIELDS_BY_ACTION.get(action, set()):
        if field_name not in arguments:
            continue
        try:
            parse_browser_authority_bool_arg(arguments.get(field_name), field_name=field_name, default=False)
        except ValueError:
            return f"authority_boolean_must_be_literal:{field_name}"
    return None


def parse_browser_authority_bool_arg(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    return parse_authority_bool(value, field_name=field_name)


def parse_browser_evidence_bool_arg(value: object, *, field_name: str, default: bool) -> bool:
    return parse_evidence_bool(value, field_name=field_name, default=default)
