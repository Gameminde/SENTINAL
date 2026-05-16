from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlparse

from pydantic import Field

from sentinel.agent.artifact_capture import ArtifactCaptureKind, ArtifactCaptureSandbox  # noqa: E402 — agent-layer utility used cross-layer (Wave D documented exception)
from sentinel.organs.browser.accessibility_snapshot import BrowserAccessibilitySnapshotBuilder
from sentinel.organs.browser.interaction_dry_run import verify_browser_interaction_plan_hash
from sentinel.organs.browser.models import (
    BrowserAccessibilitySnapshot,
    BrowserInteractionPlan,
    BrowserRenderedPage,
)
from sentinel.organs.browser.observability import minimal_browser_network_ledger
from sentinel.organs.browser.screenshot import BrowserScreenshotNormalizer, BrowserScreenshotNormalizationError, normalize_browser_screenshot
from sentinel.organs.browser.v3_authority import (
    BrowserV3AuthorityClass,
    BrowserV3AuthorityGrant,
    BrowserV3Receipt,
    browser_v3_grant_allows_url,
)
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserFormSubmitRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bfsub"))
    mission_id: str
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    plan: BrowserInteractionPlan
    plan_trace_event_id: str
    before_snapshot_trace_event_id: str
    final_url: str
    form_ref_id: str
    submit_ref_id: str
    expected_effect: str
    submit_kind: str = "submit"
    flow_type: str = "generic"
    allow_cross_origin: bool = False
    capture_screenshot: bool = True
    max_chars: int = Field(default=100_000, ge=1, le=1_000_000)
    max_html_chars: int = Field(default=200_000, ge=1, le=2_000_000)
    max_screenshot_bytes: int = Field(default=2_000_000, ge=1, le=20_000_000)
    max_screenshot_side: int = Field(default=4_000, ge=1, le=20_000)
    max_ledger_records: int = Field(default=200, ge=1, le=2_000)
    timeout_ms: int = Field(default=15_000, ge=1, le=120_000)


class BrowserFormSubmitBackendResult(SentinelModel):
    before_snapshot: BrowserAccessibilitySnapshot
    after_page: BrowserRenderedPage | None = None
    final_url_before: str
    final_url_after: str
    submitted: bool = True
    backend_status_code: int | None = Field(default=None, ge=100, le=599)
    submitted_ref_ids: list[str] = Field(default_factory=list)


class BrowserFormSubmitReceipt(BrowserV3Receipt):
    authority_class: BrowserV3AuthorityClass = BrowserV3AuthorityClass.FORM_SUBMIT
    plan_id: str
    plan_sha256: str
    plan_trace_event_id: str
    before_snapshot_trace_event_id: str
    before_snapshot_sha256: str
    before_page_sha256: str
    after_snapshot_sha256: str
    after_page_sha256: str
    final_url_before: str
    final_url_after: str
    same_origin: bool = False
    cross_origin_authorized: bool = False
    form_ref_id: str
    submit_ref_id: str
    submit_kind: str
    expected_effect: str
    post_submit_snapshot_artifact_id: str | None = None
    post_submit_snapshot_artifact_sha256: str | None = None
    post_submit_screenshot_artifact_id: str | None = None
    post_submit_screenshot_artifact_sha256: str | None = None
    network_ledger_sha256: str | None = None
    browser_health: dict = Field(default_factory=dict)


class BrowserFormSubmitResult(SentinelModel):
    accepted: bool
    reason: str
    request_id: str
    receipt: BrowserFormSubmitReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


BrowserFormSubmitBackend = Callable[[BrowserFormSubmitRequest], BrowserFormSubmitBackendResult]


class BrowserFormSubmitExecutor:
    """Executes a governed Browser V3 form submit from a certified plan."""

    def __init__(self, *, backend: BrowserFormSubmitBackend, screenshot_normalizer: BrowserScreenshotNormalizer | None = None) -> None:
        self.backend = backend
        self.screenshot_normalizer = screenshot_normalizer

    def execute(
        self,
        request: BrowserFormSubmitRequest,
        *,
        authority_grant: BrowserV3AuthorityGrant,
        event_bus: EventBus,
        artifact_capture: ArtifactCaptureSandbox,
        policy_trace_id: str | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserFormSubmitResult:
        if event_bus.mission_id != request.mission_id:
            raise ValueError("Browser form submit event bus mission_id must match request mission_id.")
        if artifact_capture.mission_id != request.mission_id:
            raise ValueError("Browser form submit artifact capture mission_id must match request mission_id.")

        errors = _validate_form_submit_request(request, authority_grant)
        if errors:
            return self._rejected(request, "browser_form_submit_request_rejected", errors, event_bus, policy_trace_id, phase)

        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return self._rejected(
                request,
                "browser_form_submit_backend_failed",
                [f"{type(exc).__name__}:{str(exc)[:300]}"],
                event_bus,
                policy_trace_id,
                phase,
            )

        if backend_result.before_snapshot.snapshot_sha256 != request.plan.snapshot_sha256:
            return self._rejected(
                request,
                "browser_form_submit_stale_snapshot",
                [f"before_snapshot:{backend_result.before_snapshot.snapshot_sha256}"],
                event_bus,
                policy_trace_id,
                phase,
            )
        if backend_result.before_snapshot.page_sha256 != request.plan.page_sha256:
            return self._rejected(
                request,
                "browser_form_submit_stale_page",
                [f"before_page:{backend_result.before_snapshot.page_sha256}"],
                event_bus,
                policy_trace_id,
                phase,
            )
        if backend_result.after_page is None:
            return self._rejected(request, "browser_form_submit_post_snapshot_missing", [], event_bus, policy_trace_id, phase)
        if not backend_result.submitted:
            return self._rejected(request, "browser_form_submit_backend_did_not_submit", [], event_bus, policy_trace_id, phase)
        same_origin = _same_origin(backend_result.final_url_before, backend_result.final_url_after)
        cross_origin_authorized = authority_grant.allow_cross_origin or request.allow_cross_origin
        if not same_origin and not cross_origin_authorized:
            return self._rejected(
                request,
                "browser_form_submit_cross_origin_result",
                [f"before:{backend_result.final_url_before}", f"after:{backend_result.final_url_after}"],
                event_bus,
                policy_trace_id,
                phase,
            )

        after_page = backend_result.after_page
        text = _collapse(after_page.text)[: request.max_chars]
        html = after_page.html[: request.max_html_chars]
        if not text and not html:
            return self._rejected(request, "browser_form_submit_post_snapshot_missing", [], event_bus, policy_trace_id, phase)
        after_snapshot = after_page.accessibility_snapshot or BrowserAccessibilitySnapshotBuilder().build(html=html, text=text)
        network_ledger = after_page.network_ledger or minimal_browser_network_ledger(
            final_url=after_page.final_url,
            status_code=after_page.status_code,
            content_type=after_page.content_type,
            max_records=request.max_ledger_records,
        )
        screenshot_bytes = after_page.screenshot_png
        screenshot_meta = None
        if request.capture_screenshot and not screenshot_bytes:
            return self._rejected(request, "browser_form_submit_screenshot_missing", [], event_bus, policy_trace_id, phase)
        if screenshot_bytes:
            try:
                screenshot_bytes, screenshot_meta = normalize_browser_screenshot(
                    screenshot_bytes,
                    max_side=request.max_screenshot_side,
                    max_bytes=request.max_screenshot_bytes,
                    normalizer=self.screenshot_normalizer,
                )
            except BrowserScreenshotNormalizationError as exc:
                return self._rejected(request, "browser_form_submit_screenshot_invalid", [str(exc)], event_bus, policy_trace_id, phase)

        snapshot_artifact = artifact_capture.capture_json(
            relative_path=f"browser/form_submit/{request.id}_post_snapshot.json",
            payload={
                "request_id": request.id,
                "authority_grant_id": authority_grant.id,
                "plan_id": request.plan.id,
                "plan_sha256": request.plan.plan_sha256,
                "final_url_before": backend_result.final_url_before,
                "final_url_after": backend_result.final_url_after,
                "title": after_page.title,
                "text": text,
                "links": after_page.links,
                "html": html,
                "accessibility_snapshot": after_snapshot.model_dump(mode="json"),
                "network_ledger": network_ledger.model_dump(mode="json"),
                "screenshot_metadata": screenshot_meta.model_dump(mode="json") if screenshot_meta else {},
                "form_ref_id": request.form_ref_id,
                "submit_ref_id": request.submit_ref_id,
                "submit_kind": request.submit_kind,
                "expected_effect": request.expected_effect,
            },
            artifact_type="browser_form_submit_post_snapshot",
            event_bus=event_bus,
            provenance_refs=[request.compiled_intent_trace_id, request.plan_trace_event_id, request.before_snapshot_trace_event_id],
            phase=phase,
        )
        if not snapshot_artifact.accepted or snapshot_artifact.artifact is None:
            return self._rejected(
                request,
                f"browser_form_submit_snapshot_capture_failed:{snapshot_artifact.reason}",
                [snapshot_artifact.reason],
                event_bus,
                policy_trace_id,
                phase,
            )

        screenshot_artifact = None
        if screenshot_bytes:
            screenshot_artifact = artifact_capture.capture_binary(
                relative_path=f"browser/form_submit/{request.id}_post_screenshot.png",
                data=screenshot_bytes,
                artifact_type="browser_form_submit_screenshot",
                kind=ArtifactCaptureKind.IMAGE,
                content_type=screenshot_meta.content_type if screenshot_meta else "image/png",
                event_bus=event_bus,
                provenance_refs=[request.compiled_intent_trace_id, request.plan_trace_event_id, request.before_snapshot_trace_event_id, *snapshot_artifact.artifact.trace_refs],
                phase=phase,
            )
            if not screenshot_artifact.accepted or screenshot_artifact.artifact is None:
                return self._rejected(
                    request,
                    f"browser_form_submit_screenshot_capture_failed:{screenshot_artifact.reason}",
                    [screenshot_artifact.reason],
                    event_bus,
                    policy_trace_id,
                    phase,
                )

        screenshot_artifact_id = screenshot_artifact.artifact.id if screenshot_artifact and screenshot_artifact.artifact else None
        screenshot_artifact_sha256 = screenshot_artifact.artifact.sha256 if screenshot_artifact and screenshot_artifact.artifact else None
        trace_refs = [
            ref
            for ref in [
                policy_trace_id,
                request.compiled_intent_trace_id,
                request.plan_trace_event_id,
                request.before_snapshot_trace_event_id,
                *snapshot_artifact.artifact.trace_refs,
                *(screenshot_artifact.artifact.trace_refs if screenshot_artifact and screenshot_artifact.artifact else []),
            ]
            if ref
        ]
        receipt = BrowserFormSubmitReceipt(
            mission_id=request.mission_id,
            authority_grant_id=authority_grant.id,
            request_id=request.id,
            context_pack_id=request.context_pack_id,
            compiled_intent_trace_id=request.compiled_intent_trace_id,
            plan_id=request.plan.id,
            plan_sha256=request.plan.plan_sha256,
            plan_trace_event_id=request.plan_trace_event_id,
            before_snapshot_trace_event_id=request.before_snapshot_trace_event_id,
            before_snapshot_sha256=request.plan.snapshot_sha256,
            before_page_sha256=request.plan.page_sha256,
            after_snapshot_sha256=after_snapshot.snapshot_sha256,
            after_page_sha256=after_snapshot.page_sha256,
            final_url_before=backend_result.final_url_before,
            final_url_after=backend_result.final_url_after,
            same_origin=same_origin,
            cross_origin_authorized=cross_origin_authorized,
            form_ref_id=request.form_ref_id,
            submit_ref_id=request.submit_ref_id,
            submit_kind=request.submit_kind,
            expected_effect=request.expected_effect,
            post_submit_snapshot_artifact_id=snapshot_artifact.artifact.id,
            post_submit_snapshot_artifact_sha256=snapshot_artifact.artifact.sha256,
            post_submit_screenshot_artifact_id=screenshot_artifact_id,
            post_submit_screenshot_artifact_sha256=screenshot_artifact_sha256,
            network_ledger_sha256=network_ledger.ledger_sha256,
            browser_health=network_ledger.health.model_dump(mode="json"),
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED,
            "Browser V3 form submit executed through explicit mission authority and certified proof chain.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "receipt_id": receipt.id,
                "authority_class": BrowserV3AuthorityClass.FORM_SUBMIT.value,
                "authority_grant_id": authority_grant.id,
                "context_pack_id": request.context_pack_id,
                "compiled_intent_trace_id": request.compiled_intent_trace_id,
                "plan_id": request.plan.id,
                "plan_sha256": request.plan.plan_sha256,
                "plan": request.plan.model_dump(mode="json"),
                "plan_trace_event_id": request.plan_trace_event_id,
                "before_snapshot_trace_event_id": request.before_snapshot_trace_event_id,
                "before_snapshot_sha256": receipt.before_snapshot_sha256,
                "before_page_sha256": receipt.before_page_sha256,
                "after_snapshot_sha256": receipt.after_snapshot_sha256,
                "after_page_sha256": receipt.after_page_sha256,
                "final_url_before": receipt.final_url_before,
                "final_url_after": receipt.final_url_after,
                "same_origin": receipt.same_origin,
                "cross_origin_authorized": receipt.cross_origin_authorized,
                "form_ref_id": request.form_ref_id,
                "submit_ref_id": request.submit_ref_id,
                "submit_kind": request.submit_kind,
                "expected_effect": request.expected_effect,
                "post_submit_snapshot_artifact_id": receipt.post_submit_snapshot_artifact_id,
                "post_submit_snapshot_artifact_sha256": receipt.post_submit_snapshot_artifact_sha256,
                "post_submit_screenshot_artifact_id": receipt.post_submit_screenshot_artifact_id,
                "post_submit_screenshot_artifact_sha256": receipt.post_submit_screenshot_artifact_sha256,
                "network_ledger": network_ledger.model_dump(mode="json"),
                "network_ledger_sha256": network_ledger.ledger_sha256,
                "browser_health": receipt.browser_health,
                "policy_trace_id": policy_trace_id,
            },
            trace_refs=trace_refs,
        )
        receipt = receipt.model_copy(update={"trace_refs": [*trace_refs, event.id]})
        return BrowserFormSubmitResult(
            accepted=True,
            reason="browser_form_submit_executed",
            request_id=request.id,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[
                artifact_id
                for artifact_id in [receipt.post_submit_snapshot_artifact_id, receipt.post_submit_screenshot_artifact_id]
                if artifact_id
            ],
        )

    @staticmethod
    def _rejected(
        request: BrowserFormSubmitRequest,
        reason: str,
        errors: list[str],
        event_bus: EventBus,
        policy_trace_id: str | None,
        phase: AgentPhase,
    ) -> BrowserFormSubmitResult:
        event = event_bus.append(
            AgentEventType.BROWSER_FORM_SUBMIT_REJECTED,
            "Browser V3 form submit rejected before certified completion.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "authority_class": BrowserV3AuthorityClass.FORM_SUBMIT.value,
                "authority_grant_id": request.authority_grant_id,
                "context_pack_id": request.context_pack_id,
                "compiled_intent_trace_id": request.compiled_intent_trace_id,
                "plan_id": request.plan.id,
                "plan_sha256": request.plan.plan_sha256,
                "reason": reason,
                "errors": errors,
                "policy_trace_id": policy_trace_id,
            },
            trace_refs=[ref for ref in [policy_trace_id, request.compiled_intent_trace_id, request.plan_trace_event_id, request.before_snapshot_trace_event_id] if ref],
        )
        return BrowserFormSubmitResult(
            accepted=False,
            reason=reason,
            request_id=request.id,
            trace_event_id=event.id,
            errors=errors,
        )


def _validate_form_submit_request(request: BrowserFormSubmitRequest, grant: BrowserV3AuthorityGrant) -> list[str]:
    errors: list[str] = []
    if grant.authority_class != BrowserV3AuthorityClass.FORM_SUBMIT:
        errors.append("authority_grant_class_mismatch")
    if grant.id != request.authority_grant_id:
        errors.append("authority_grant_id_mismatch")
    if not browser_v3_grant_allows_url(grant, request.final_url):
        errors.append("form_submit_url_outside_authority")
    if request.flow_type.lower() in {item.lower() for item in grant.blocked_flow_types}:
        errors.append(f"form_submit_flow_type_not_delegated:{request.flow_type}")
    if request.submit_kind.lower() not in {"submit", "post", "send", "publish"}:
        errors.append(f"form_submit_kind_not_supported:{request.submit_kind}")
    if not request.context_pack_id:
        errors.append("missing_context_pack_id")
    if not request.compiled_intent_trace_id:
        errors.append("missing_compiled_intent_trace_id")
    if not request.plan_trace_event_id:
        errors.append("missing_plan_trace_event_id")
    if not request.before_snapshot_trace_event_id:
        errors.append("missing_before_snapshot_trace_event_id")
    if not verify_browser_interaction_plan_hash(request.plan.model_dump(mode="json"), request.plan.plan_sha256):
        errors.append("plan_hash_invalid")
    ref_ids = {request.form_ref_id, request.submit_ref_id}
    plan_ref_ids = set(request.plan.required_ref_ids)
    plan_ref_ids.update(step.target.ref for step in request.plan.steps if step.target.ref)
    missing = sorted(ref_id for ref_id in ref_ids if ref_id not in plan_ref_ids)
    if missing:
        errors.append(f"form_submit_refs_not_in_certified_plan:{','.join(missing)}")
    if request.plan.final_url and _normalize_origin(request.plan.final_url) != _normalize_origin(request.final_url):
        errors.append("request_final_url_origin_mismatch")
    return errors


def _same_origin(left: str, right: str) -> bool:
    return _normalize_origin(left) == _normalize_origin(right)


def _normalize_origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlparse(value)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
