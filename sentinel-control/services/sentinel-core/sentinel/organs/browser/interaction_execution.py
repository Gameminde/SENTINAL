from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlparse

from sentinel.agent.artifact_capture import ArtifactCaptureKind, ArtifactCaptureSandbox  # noqa: E402 — agent-layer utility used cross-layer (Wave D documented exception)
from sentinel.organs.browser.accessibility_snapshot import BrowserAccessibilitySnapshotBuilder
from sentinel.organs.browser.interaction_dry_run import (
    P3G_FORBIDDEN_INTERACTION_NAMES,
    verify_browser_interaction_plan_hash,
)
from sentinel.organs.browser.models import (
    BrowserInteractionBackendResult,
    BrowserInteractionExecutionReceipt,
    BrowserInteractionExecutionRequest,
    BrowserInteractionExecutionResult,
    BrowserInteractionExecutionStatus,
    BrowserInteractionIntent,
)
from sentinel.organs.browser.observability import minimal_browser_network_ledger
from sentinel.organs.browser.screenshot import (
    BrowserScreenshotNormalizer,
    BrowserScreenshotNormalizationError,
    normalize_browser_screenshot,
)
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus


BrowserInteractionBackend = Callable[[BrowserInteractionExecutionRequest], BrowserInteractionBackendResult]

P3H_ALLOWED_EXECUTION_INTENTS = frozenset(
    {
        BrowserInteractionIntent.CLICK_PLAN,
        BrowserInteractionIntent.TYPE_PLAN,
        BrowserInteractionIntent.FILL_PLAN,
        BrowserInteractionIntent.SELECT_PLAN,
        BrowserInteractionIntent.HOVER_PLAN,
        BrowserInteractionIntent.WAIT_FOR_TEXT_PLAN,
        BrowserInteractionIntent.WAIT_FOR_SELECTOR_PLAN,
        BrowserInteractionIntent.WAIT_FOR_URL_PLAN,
    }
)

P3H_FORBIDDEN_INTENT_TOKENS = frozenset(
    {
        *P3G_FORBIDDEN_INTERACTION_NAMES,
        "press",
        "enter",
        "return",
        "dialog",
        "file",
        "cookie",
        "storage",
        "login",
        "payment",
        "credential",
    }
)


class BrowserLimitedInteractionExecutor:
    """Executes a certified browser interaction plan through a bounded backend."""

    def __init__(self, *, backend: BrowserInteractionBackend, screenshot_normalizer: BrowserScreenshotNormalizer | None = None) -> None:
        self.backend = backend
        self.screenshot_normalizer = screenshot_normalizer

    def execute(
        self,
        request: BrowserInteractionExecutionRequest,
        *,
        event_bus: EventBus,
        artifact_capture: ArtifactCaptureSandbox,
        policy_trace_id: str | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserInteractionExecutionResult:
        if event_bus.mission_id != request.mission_id:
            raise ValueError("Browser interaction event bus mission_id must match request mission_id.")
        if artifact_capture.mission_id != request.mission_id:
            raise ValueError("Browser interaction artifact capture mission_id must match request mission_id.")

        validation_errors = _validate_execution_request(request)
        if validation_errors:
            return self._rejected(
                request,
                reason="browser_interaction_request_rejected",
                errors=validation_errors,
                event_bus=event_bus,
                policy_trace_id=policy_trace_id,
                phase=phase,
            )

        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return self._rejected(
                request,
                reason="browser_interaction_backend_failed",
                errors=[f"{type(exc).__name__}:{str(exc)[:300]}"],
                event_bus=event_bus,
                policy_trace_id=policy_trace_id,
                phase=phase,
            )

        if backend_result.before_snapshot.snapshot_sha256 != request.plan.snapshot_sha256:
            return self._rejected(
                request,
                reason="browser_interaction_stale_snapshot",
                errors=[f"before_snapshot:{backend_result.before_snapshot.snapshot_sha256}"],
                event_bus=event_bus,
                policy_trace_id=policy_trace_id,
                phase=phase,
            )
        if backend_result.before_snapshot.page_sha256 != request.plan.page_sha256:
            return self._rejected(
                request,
                reason="browser_interaction_stale_page",
                errors=[f"before_page:{backend_result.before_snapshot.page_sha256}"],
                event_bus=event_bus,
                policy_trace_id=policy_trace_id,
                phase=phase,
            )
        if not _same_origin(backend_result.final_url_before, backend_result.final_url_after):
            return self._rejected(
                request,
                reason="browser_interaction_cross_origin_result",
                errors=[f"before:{backend_result.final_url_before}", f"after:{backend_result.final_url_after}"],
                event_bus=event_bus,
                policy_trace_id=policy_trace_id,
                phase=phase,
            )

        after_page = backend_result.after_page
        text = _collapse(after_page.text)[: request.max_chars]
        html = after_page.html[: request.max_html_chars]
        after_snapshot = after_page.accessibility_snapshot or BrowserAccessibilitySnapshotBuilder().build(html=html, text=text)
        network_ledger = after_page.network_ledger or minimal_browser_network_ledger(
            final_url=after_page.final_url,
            status_code=after_page.status_code,
            content_type=after_page.content_type,
            max_records=request.max_ledger_records,
        )
        screenshot_bytes = after_page.screenshot_png
        screenshot_meta = None
        if request.capture_screenshot and not after_page.screenshot_png:
            return self._rejected(
                request,
                reason="browser_interaction_screenshot_missing",
                errors=[],
                event_bus=event_bus,
                policy_trace_id=policy_trace_id,
                phase=phase,
            )
        if screenshot_bytes:
            try:
                screenshot_bytes, screenshot_meta = normalize_browser_screenshot(
                    screenshot_bytes,
                    max_side=request.max_screenshot_side,
                    max_bytes=request.max_screenshot_bytes,
                    normalizer=self.screenshot_normalizer,
                )
            except BrowserScreenshotNormalizationError as exc:
                message = str(exc)
                reason = "browser_interaction_screenshot_normalization_failed"
                if "bytes_exceed_max" in message and "dimensions_exceed_max_side" not in message:
                    reason = "browser_interaction_screenshot_too_large"
                elif "dimensions_exceed_max_side" in message:
                    reason = "browser_interaction_screenshot_dimensions_too_large"
                return self._rejected(
                    request,
                    reason=reason,
                    errors=[message],
                    event_bus=event_bus,
                    policy_trace_id=policy_trace_id,
                    phase=phase,
                )

        snapshot_artifact = artifact_capture.capture_json(
            relative_path=f"browser/interactions/{request.id}_after_snapshot.json",
            payload={
                "request_id": request.id,
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
                "executed_step_ids": backend_result.executed_step_ids,
            },
            artifact_type="browser_interaction_after_snapshot",
            event_bus=event_bus,
            provenance_refs=[request.plan_trace_event_id, request.before_snapshot_trace_event_id],
            phase=phase,
        )
        if not snapshot_artifact.accepted or snapshot_artifact.artifact is None:
            return self._rejected(
                request,
                reason=f"browser_interaction_snapshot_capture_failed:{snapshot_artifact.reason}",
                errors=[snapshot_artifact.reason],
                event_bus=event_bus,
                policy_trace_id=policy_trace_id,
                phase=phase,
            )

        screenshot_artifact = None
        if screenshot_bytes:
            screenshot_artifact = artifact_capture.capture_binary(
                relative_path=f"browser/interactions/{request.id}_after_screenshot.png",
                data=screenshot_bytes,
                artifact_type="browser_interaction_screenshot",
                kind=ArtifactCaptureKind.IMAGE,
                content_type=screenshot_meta.content_type if screenshot_meta else "image/png",
                event_bus=event_bus,
                provenance_refs=[request.plan_trace_event_id, request.before_snapshot_trace_event_id, *snapshot_artifact.artifact.trace_refs],
                phase=phase,
            )
            if not screenshot_artifact.accepted or screenshot_artifact.artifact is None:
                return self._rejected(
                    request,
                    reason=f"browser_interaction_screenshot_capture_failed:{screenshot_artifact.reason}",
                    errors=[screenshot_artifact.reason],
                    event_bus=event_bus,
                    policy_trace_id=policy_trace_id,
                    phase=phase,
                )

        executed_steps = [
            step
            for step in request.plan.steps
            if not backend_result.executed_step_ids or step.id in set(backend_result.executed_step_ids)
        ]
        screenshot_artifact_id = screenshot_artifact.artifact.id if screenshot_artifact and screenshot_artifact.artifact else None
        screenshot_artifact_sha256 = screenshot_artifact.artifact.sha256 if screenshot_artifact and screenshot_artifact.artifact else None
        trace_refs = [
            ref
            for ref in [
                policy_trace_id,
                request.plan_trace_event_id,
                request.before_snapshot_trace_event_id,
                *snapshot_artifact.artifact.trace_refs,
                *(screenshot_artifact.artifact.trace_refs if screenshot_artifact and screenshot_artifact.artifact else []),
            ]
            if ref
        ]
        receipt = BrowserInteractionExecutionReceipt(
            mission_id=request.mission_id,
            request_id=request.id,
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
            same_origin=True,
            executed_step_ids=[step.id for step in executed_steps],
            executed_intents=[step.intent.value for step in executed_steps],
            executed_ref_ids=sorted({step.target.ref for step in executed_steps if step.target.ref}),
            after_snapshot_artifact_id=snapshot_artifact.artifact.id,
            after_snapshot_artifact_sha256=snapshot_artifact.artifact.sha256,
            after_screenshot_artifact_id=screenshot_artifact_id,
            after_screenshot_artifact_sha256=screenshot_artifact_sha256,
            network_ledger_sha256=network_ledger.ledger_sha256,
            browser_health=network_ledger.health.model_dump(mode="json"),
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_INTERACTION_EXECUTED,
            "Limited browser interaction executed from a certified dry-run plan and recaptured after action.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "receipt_id": receipt.id,
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
                "same_origin": True,
                "executed_step_ids": receipt.executed_step_ids,
                "executed_intents": receipt.executed_intents,
                "executed_ref_ids": receipt.executed_ref_ids,
                "after_snapshot_artifact_id": receipt.after_snapshot_artifact_id,
                "after_snapshot_artifact_sha256": receipt.after_snapshot_artifact_sha256,
                "after_screenshot_artifact_id": receipt.after_screenshot_artifact_id,
                "after_screenshot_artifact_sha256": receipt.after_screenshot_artifact_sha256,
                "network_ledger": network_ledger.model_dump(mode="json"),
                "network_ledger_sha256": network_ledger.ledger_sha256,
                "browser_health": receipt.browser_health,
                "policy_trace_id": policy_trace_id,
            },
            trace_refs=trace_refs,
        )
        receipt = receipt.model_copy(update={"trace_refs": [*trace_refs, event.id]})
        artifact_ids = [receipt.after_snapshot_artifact_id, receipt.after_screenshot_artifact_id]
        return BrowserInteractionExecutionResult(
            accepted=True,
            status=BrowserInteractionExecutionStatus.EXECUTED,
            reason="browser_interaction_executed",
            request_id=request.id,
            plan_id=request.plan.id,
            plan_sha256=request.plan.plan_sha256,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[artifact_id for artifact_id in artifact_ids if artifact_id],
        )

    @staticmethod
    def _rejected(
        request: BrowserInteractionExecutionRequest,
        *,
        reason: str,
        errors: list[str],
        event_bus: EventBus,
        policy_trace_id: str | None,
        phase: AgentPhase,
    ) -> BrowserInteractionExecutionResult:
        event = event_bus.append(
            AgentEventType.BROWSER_INTERACTION_REJECTED,
            "Limited browser interaction rejected before certified completion.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "plan_id": request.plan.id,
                "plan_sha256": request.plan.plan_sha256,
                "reason": reason,
                "errors": errors,
                "policy_trace_id": policy_trace_id,
            },
            trace_refs=[ref for ref in [policy_trace_id, request.plan_trace_event_id, request.before_snapshot_trace_event_id] if ref],
        )
        return BrowserInteractionExecutionResult(
            accepted=False,
            status=BrowserInteractionExecutionStatus.REJECTED,
            reason=reason,
            request_id=request.id,
            plan_id=request.plan.id,
            plan_sha256=request.plan.plan_sha256,
            trace_event_id=event.id,
            errors=errors,
        )


def _validate_execution_request(request: BrowserInteractionExecutionRequest) -> list[str]:
    errors: list[str] = []
    plan = request.plan
    if not plan.dry_run_only:
        errors.append("plan_not_created_as_dry_run")
    if not verify_browser_interaction_plan_hash(plan.model_dump(mode="json"), plan.plan_sha256):
        errors.append("plan_hash_invalid")
    if plan.snapshot_sha256 == "" or plan.page_sha256 == "":
        errors.append("plan_missing_snapshot_binding")
    if not request.plan_trace_event_id:
        errors.append("missing_plan_trace_event_id")
    if not request.before_snapshot_trace_event_id:
        errors.append("missing_before_snapshot_trace_event_id")
    if plan.final_url and _normalize_origin(plan.final_url) != _normalize_origin(request.final_url):
        errors.append("request_final_url_origin_mismatch")
    if not plan.steps:
        errors.append("plan_has_no_steps")
    for index, step in enumerate(plan.steps):
        intent = step.intent
        intent_value = intent.value.lower()
        if intent not in P3H_ALLOWED_EXECUTION_INTENTS:
            errors.append(f"intent_not_delegated_for_limited_execution_{index}:{intent_value}")
        if _contains_forbidden_execution_token(intent_value):
            errors.append(f"forbidden_execution_intent_{index}:{intent_value}")
        if intent in {
            BrowserInteractionIntent.CLICK_PLAN,
            BrowserInteractionIntent.TYPE_PLAN,
            BrowserInteractionIntent.FILL_PLAN,
            BrowserInteractionIntent.SELECT_PLAN,
            BrowserInteractionIntent.HOVER_PLAN,
        } and not step.target.ref:
            errors.append(f"missing_ref_for_execution_{index}")
        if intent in {BrowserInteractionIntent.TYPE_PLAN, BrowserInteractionIntent.FILL_PLAN} and step.text is None:
            errors.append(f"missing_text_for_execution_{index}")
        if intent == BrowserInteractionIntent.SELECT_PLAN and not step.values:
            errors.append(f"missing_values_for_execution_{index}")
        if intent == BrowserInteractionIntent.WAIT_FOR_URL_PLAN and step.target.url:
            if not _same_origin(request.final_url, step.target.url):
                errors.append(f"wait_url_cross_origin_{index}")
    return errors


def _contains_forbidden_execution_token(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in P3H_FORBIDDEN_INTENT_TOKENS or any(token in normalized for token in P3H_FORBIDDEN_INTENT_TOKENS)


def _same_origin(left: str, right: str) -> bool:
    return _normalize_origin(left) == _normalize_origin(right)


def _normalize_origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    return scheme, host, parsed.port


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
