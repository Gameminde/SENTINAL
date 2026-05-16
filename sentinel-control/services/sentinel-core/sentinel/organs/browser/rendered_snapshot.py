from __future__ import annotations

import re
from collections.abc import Callable

from sentinel.agent.artifact_capture import ArtifactCaptureKind, ArtifactCaptureSandbox  # noqa: E402 — agent-layer utility used cross-layer (Wave D documented exception)
from sentinel.organs.browser.accessibility_snapshot import BrowserAccessibilitySnapshotBuilder
from sentinel.organs.browser.models import (
    BrowserCitation,
    BrowserElementScreenshotMetadata,
    BrowserRenderedPage,
    BrowserRenderedSnapshotReceipt,
    BrowserRenderedSnapshotRequest,
    BrowserRenderedSnapshotResult,
    BrowserSnapshotStatus,
    PublicUrlDecision,
    PublicUrlDecisionStatus,
    PublicUrlPolicy,
)
from sentinel.organs.browser.observability import minimal_browser_network_ledger
from sentinel.organs.browser.pdf import pdf_metadata
from sentinel.organs.browser.screenshot import (
    BrowserScreenshotNormalizer,
    BrowserScreenshotNormalizationError,
    normalize_browser_screenshot,
)
from sentinel.organs.browser.url_guard import DnsResolver, PublicUrlGuard
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus


BrowserRenderer = Callable[[BrowserRenderedSnapshotRequest, str], BrowserRenderedPage]

_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_previous_instructions", re.compile(r"\b(ignore|disregard)\b.{0,80}\b(previous|prior|above)\b.{0,40}\binstructions?\b", re.I | re.S)),
    ("system_prompt_request", re.compile(r"\b(system|developer)\s+(prompt|message|instructions?)\b", re.I)),
    ("tool_or_secret_instruction", re.compile(r"\b(call|invoke|use)\b.{0,40}\btool\b|\b(api[_ -]?key|token|password|credential)s?\b", re.I | re.S)),
    ("exfiltration_language", re.compile(r"\b(send|upload|post|submit)\b.{0,80}\b(secret|credential|token|cookie|session)\b", re.I | re.S)),
)


class BrowserRenderError(RuntimeError):
    pass


class BrowserRenderedSnapshotAdapter:
    """Captures rendered-page output through an injected read-only renderer."""

    def __init__(
        self,
        *,
        renderer: BrowserRenderer,
        url_guard: PublicUrlGuard | None = None,
        screenshot_normalizer: BrowserScreenshotNormalizer | None = None,
    ) -> None:
        self.renderer = renderer
        self.url_guard = url_guard or PublicUrlGuard()
        self.screenshot_normalizer = screenshot_normalizer

    def capture(
        self,
        request: BrowserRenderedSnapshotRequest,
        *,
        event_bus: EventBus,
        artifact_capture: ArtifactCaptureSandbox,
        resolver: DnsResolver | None = None,
        redirects: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserRenderedSnapshotResult:
        if event_bus.mission_id != request.mission_id:
            raise ValueError("Browser snapshot event bus mission_id must match request mission_id.")
        if artifact_capture.mission_id != request.mission_id:
            raise ValueError("Browser snapshot artifact capture mission_id must match request mission_id.")

        policy = PublicUrlPolicy(
            allowed_schemes=["https"] if request.require_https else ["https", "http"],
            allowed_domains=request.allowed_domains,
            max_redirects=request.max_redirects,
            require_dns_resolution=True,
        )
        decision = self.url_guard.evaluate(request.url, policy=policy, resolver=resolver, redirects=redirects)
        url_event = self._emit_url_decision(event_bus, decision, phase)
        if decision.status != PublicUrlDecisionStatus.ALLOWED or decision.final_url is None:
            status = BrowserSnapshotStatus.BLOCKED
            if decision.status == PublicUrlDecisionStatus.UNAVAILABLE:
                status = BrowserSnapshotStatus.UNAVAILABLE
            return self._rejected(
                request=request,
                decision=decision,
                reason=decision.reason,
                status=status,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
            )

        try:
            page = self.renderer(request, decision.final_url)
        except BrowserRenderError as exc:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_render_failed",
                status=BrowserSnapshotStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[str(exc)],
            )

        if page.final_url != decision.final_url:
            return self._rejected(
                request=request,
                decision=decision,
                reason="rendered_final_url_changed_without_policy",
                status=BrowserSnapshotStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[f"rendered_final_url:{page.final_url}"],
            )
        if not 200 <= page.status_code <= 299:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_render_status_not_successful",
                status=BrowserSnapshotStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[f"status_code:{page.status_code}"],
            )
        if request.capture_screenshot and not page.screenshot_png:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_screenshot_missing",
                status=BrowserSnapshotStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
            )
        screenshot_bytes = page.screenshot_png
        screenshot_meta = None
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
                reason = "browser_screenshot_normalization_failed"
                if "bytes_exceed_max" in message and "dimensions_exceed_max_side" not in message:
                    reason = "browser_screenshot_too_large"
                elif "dimensions_exceed_max_side" in message:
                    reason = "browser_screenshot_dimensions_too_large"
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason=reason,
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=[message],
                )

        text = _collapse(page.text)[: request.max_chars]
        html = page.html[: request.max_html_chars]
        flags = _detect_prompt_injection(text, html)
        citations = _extract_citations(page.final_url, page.title, text)
        accessibility_snapshot = page.accessibility_snapshot or BrowserAccessibilitySnapshotBuilder().build(html=html, text=text)
        network_ledger = page.network_ledger or minimal_browser_network_ledger(
            final_url=page.final_url,
            status_code=page.status_code,
            content_type=page.content_type,
            max_records=request.max_ledger_records,
        )
        snapshot_artifact = artifact_capture.capture_json(
            relative_path=f"browser/rendered/{request.id}_snapshot.json",
            payload={
                "request_id": request.id,
                "original_url": request.url,
                "final_url": page.final_url,
                "title": page.title,
                "text": text,
                "links": page.links,
                "citations": [citation.model_dump(mode="json") for citation in citations],
                "html": html,
                "accessibility_snapshot": accessibility_snapshot.model_dump(mode="json"),
                "screenshot_metadata": screenshot_meta.model_dump(mode="json") if screenshot_meta else {},
                "network_ledger": network_ledger.model_dump(mode="json"),
                "prompt_injection_flags": flags,
                "content_type": page.content_type,
                "status_code": page.status_code,
            },
            artifact_type="browser_rendered_snapshot",
            event_bus=event_bus,
            provenance_refs=[url_event.id],
            phase=phase,
        )
        if not snapshot_artifact.accepted or snapshot_artifact.artifact is None:
            return self._rejected(
                request=request,
                decision=decision,
                reason=f"snapshot_artifact_capture_failed:{snapshot_artifact.reason}",
                status=BrowserSnapshotStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[snapshot_artifact.reason],
            )

        screenshot_artifact = None
        if screenshot_bytes:
            screenshot_artifact = artifact_capture.capture_binary(
                relative_path=f"browser/rendered/{request.id}_screenshot.png",
                data=screenshot_bytes,
                artifact_type="browser_screenshot",
                kind=ArtifactCaptureKind.IMAGE,
                content_type=screenshot_meta.content_type if screenshot_meta else "image/png",
                event_bus=event_bus,
                provenance_refs=[url_event.id, *snapshot_artifact.artifact.trace_refs],
                phase=phase,
            )
            if not screenshot_artifact.accepted or screenshot_artifact.artifact is None:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason=f"screenshot_artifact_capture_failed:{screenshot_artifact.reason}",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=[screenshot_artifact.reason],
                )

        pdf_artifact = None
        pdf_meta = None
        if request.capture_pdf:
            if not page.pdf_bytes:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason="browser_pdf_missing",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                )
            pdf_meta = pdf_metadata(page.pdf_bytes, max_bytes=request.max_pdf_bytes)
            if pdf_meta.warnings:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason="browser_pdf_invalid",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=pdf_meta.warnings,
                )
            pdf_artifact = artifact_capture.capture_binary(
                relative_path=f"browser/rendered/{request.id}.pdf",
                data=page.pdf_bytes,
                artifact_type="browser_pdf",
                kind=ArtifactCaptureKind.BINARY,
                content_type="application/pdf",
                event_bus=event_bus,
                provenance_refs=[url_event.id, *snapshot_artifact.artifact.trace_refs],
                phase=phase,
            )
            if not pdf_artifact.accepted or pdf_artifact.artifact is None:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason=f"pdf_artifact_capture_failed:{pdf_artifact.reason}",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=[pdf_artifact.reason],
                )

        element_screenshot_artifacts: list[BrowserElementScreenshotMetadata] = []
        element_screenshot_trace_refs: list[str] = []
        if request.capture_element_screenshots:
            requested_refs = [str(ref_id) for ref_id in request.element_screenshot_ref_ids]
            if len(requested_refs) > request.max_element_screenshots:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason="browser_element_screenshot_request_limit_exceeded",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=[f"requested:{len(requested_refs)}", f"max:{request.max_element_screenshots}"],
                )
            if not page.element_screenshots:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason="browser_element_screenshot_missing",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                )
            if len(page.element_screenshots) > request.max_element_screenshots:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason="browser_element_screenshot_count_exceeded",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=[f"count:{len(page.element_screenshots)}", f"max:{request.max_element_screenshots}"],
                )
            seen_refs: set[str] = set()
            snapshot_refs = set(accessibility_snapshot.refs)
            for element in page.element_screenshots:
                if requested_refs and element.ref_id not in requested_refs:
                    return self._rejected(
                        request=request,
                        decision=decision,
                        reason="browser_element_screenshot_unrequested_ref",
                        status=BrowserSnapshotStatus.REJECTED,
                        event_bus=event_bus,
                        phase=phase,
                        url_event_id=url_event.id,
                        errors=[element.ref_id],
                    )
                if element.ref_id not in snapshot_refs:
                    return self._rejected(
                        request=request,
                        decision=decision,
                        reason="browser_element_screenshot_unknown_ref",
                        status=BrowserSnapshotStatus.REJECTED,
                        event_bus=event_bus,
                        phase=phase,
                        url_event_id=url_event.id,
                        errors=[element.ref_id],
                    )
                if element.ref_id in seen_refs:
                    return self._rejected(
                        request=request,
                        decision=decision,
                        reason="browser_element_screenshot_duplicate_ref",
                        status=BrowserSnapshotStatus.REJECTED,
                        event_bus=event_bus,
                        phase=phase,
                        url_event_id=url_event.id,
                        errors=[element.ref_id],
                    )
                seen_refs.add(element.ref_id)
                try:
                    element_bytes, element_meta = normalize_browser_screenshot(
                        element.png,
                        max_side=request.max_element_screenshot_side,
                        max_bytes=request.max_element_screenshot_bytes,
                        normalizer=self.screenshot_normalizer,
                    )
                except BrowserScreenshotNormalizationError as exc:
                    return self._rejected(
                        request=request,
                        decision=decision,
                        reason="browser_element_screenshot_normalization_failed",
                        status=BrowserSnapshotStatus.REJECTED,
                        event_bus=event_bus,
                        phase=phase,
                        url_event_id=url_event.id,
                        errors=[element.ref_id, str(exc)],
                    )
                artifact = artifact_capture.capture_binary(
                    relative_path=f"browser/rendered/{request.id}_element_{_safe_ref_filename(element.ref_id)}.png",
                    data=element_bytes,
                    artifact_type="browser_element_screenshot",
                    kind=ArtifactCaptureKind.IMAGE,
                    content_type=element_meta.content_type,
                    event_bus=event_bus,
                    provenance_refs=[url_event.id, *snapshot_artifact.artifact.trace_refs],
                    phase=phase,
                )
                if not artifact.accepted or artifact.artifact is None:
                    return self._rejected(
                        request=request,
                        decision=decision,
                        reason=f"element_screenshot_artifact_capture_failed:{artifact.reason}",
                        status=BrowserSnapshotStatus.REJECTED,
                        event_bus=event_bus,
                        phase=phase,
                        url_event_id=url_event.id,
                        errors=[element.ref_id, artifact.reason],
                    )
                element_screenshot_trace_refs.extend(artifact.artifact.trace_refs)
                element_screenshot_artifacts.append(
                    BrowserElementScreenshotMetadata(
                        ref_id=element.ref_id,
                        role=element.role or accessibility_snapshot.refs[element.ref_id].role,
                        name=element.name or accessibility_snapshot.refs[element.ref_id].name,
                        bbox=element.bbox,
                        artifact_id=artifact.artifact.id,
                        artifact_sha256=artifact.artifact.sha256,
                        screenshot_metadata=element_meta,
                    )
                )
            if requested_refs and set(requested_refs) != seen_refs:
                missing = sorted(set(requested_refs) - seen_refs)
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason="browser_element_screenshot_requested_ref_missing",
                    status=BrowserSnapshotStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=missing,
                )

        screenshot_artifact_id = screenshot_artifact.artifact.id if screenshot_artifact and screenshot_artifact.artifact else None
        screenshot_sha256 = screenshot_artifact.artifact.sha256 if screenshot_artifact and screenshot_artifact.artifact else None
        pdf_artifact_id = pdf_artifact.artifact.id if pdf_artifact and pdf_artifact.artifact else None
        pdf_artifact_sha256 = pdf_artifact.artifact.sha256 if pdf_artifact and pdf_artifact.artifact else None
        trace_refs = [url_event.id, *snapshot_artifact.artifact.trace_refs]
        if screenshot_artifact and screenshot_artifact.artifact:
            trace_refs.extend(screenshot_artifact.artifact.trace_refs)
        if pdf_artifact and pdf_artifact.artifact:
            trace_refs.extend(pdf_artifact.artifact.trace_refs)
        trace_refs.extend(element_screenshot_trace_refs)
        receipt = BrowserRenderedSnapshotReceipt(
            mission_id=request.mission_id,
            request_id=request.id,
            original_url=request.url,
            final_url=page.final_url,
            url_policy_trace_id=url_event.id,
            snapshot_artifact_id=snapshot_artifact.artifact.id,
            snapshot_artifact_sha256=snapshot_artifact.artifact.sha256,
            screenshot_artifact_id=screenshot_artifact_id,
            screenshot_artifact_sha256=screenshot_sha256,
            accessibility_snapshot_sha256=accessibility_snapshot.snapshot_sha256,
            accessibility_ref_count=accessibility_snapshot.stats.refs,
            accessibility_interactive_count=accessibility_snapshot.stats.interactive,
            screenshot_metadata=screenshot_meta.model_dump(mode="json") if screenshot_meta else {},
            pdf_artifact_id=pdf_artifact_id,
            pdf_artifact_sha256=pdf_artifact_sha256,
            pdf_metadata=pdf_meta.model_dump(mode="json") if pdf_meta else {},
            element_screenshot_artifacts=[
                item.model_dump(mode="json") for item in element_screenshot_artifacts
            ],
            network_ledger_sha256=network_ledger.ledger_sha256,
            network_request_count=len(network_ledger.requests),
            network_response_count=len(network_ledger.responses),
            network_failure_count=len(network_ledger.failures),
            console_message_count=len(network_ledger.console),
            page_error_count=len(network_ledger.page_errors),
            network_ledger_truncated=network_ledger.truncated,
            browser_health=network_ledger.health.model_dump(mode="json"),
            chars_extracted=len(text),
            html_chars=len(html),
            prompt_injection_flags=flags,
            citation_refs=[citation.id for citation in citations],
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_SNAPSHOT_CAPTURED,
            "Rendered browser snapshot captured through injected read-only renderer.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "receipt_id": receipt.id,
                "final_url": page.final_url,
                "title": page.title,
                "snapshot_artifact_id": snapshot_artifact.artifact.id,
                "snapshot_artifact_sha256": snapshot_artifact.artifact.sha256,
                "screenshot_artifact_id": screenshot_artifact_id,
                "screenshot_artifact_sha256": screenshot_sha256,
                "pdf_artifact_id": pdf_artifact_id,
                "pdf_artifact_sha256": pdf_artifact_sha256,
                "pdf_metadata": pdf_meta.model_dump(mode="json") if pdf_meta else {},
                "element_screenshot_artifacts": [
                    item.model_dump(mode="json") for item in element_screenshot_artifacts
                ],
                "link_count": len(page.links),
                "citation_count": len(citations),
                "accessibility_snapshot_sha256": accessibility_snapshot.snapshot_sha256,
                "accessibility_page_sha256": accessibility_snapshot.page_sha256,
                "accessibility_ref_count": accessibility_snapshot.stats.refs,
                "accessibility_interactive_count": accessibility_snapshot.stats.interactive,
                "accessibility_ref_ids": sorted(accessibility_snapshot.refs),
                "screenshot_metadata": screenshot_meta.model_dump(mode="json") if screenshot_meta else {},
                "network_ledger": network_ledger.model_dump(mode="json"),
                "network_ledger_sha256": network_ledger.ledger_sha256,
                "network_request_count": len(network_ledger.requests),
                "network_response_count": len(network_ledger.responses),
                "network_failure_count": len(network_ledger.failures),
                "console_message_count": len(network_ledger.console),
                "page_error_count": len(network_ledger.page_errors),
                "network_ledger_truncated": network_ledger.truncated,
                "browser_health": network_ledger.health.model_dump(mode="json"),
                "prompt_injection_flags": flags,
                "url_policy_trace_id": url_event.id,
            },
            trace_refs=trace_refs,
        )
        receipt = receipt.model_copy(update={"trace_refs": [*trace_refs, event.id]})
        return BrowserRenderedSnapshotResult(
            accepted=True,
            status=BrowserSnapshotStatus.CAPTURED,
            reason="browser_snapshot_captured",
            request_id=request.id,
            url_decision=decision,
            title=page.title,
            extracted_text=text,
            links=page.links,
            citations=citations,
            accessibility_snapshot=accessibility_snapshot,
            screenshot_metadata=screenshot_meta,
            pdf_metadata=pdf_meta,
            element_screenshot_artifacts=element_screenshot_artifacts,
            network_ledger=network_ledger,
            prompt_injection_flags=flags,
            receipt=receipt,
            trace_event_id=event.id,
        )

    @staticmethod
    def _emit_url_decision(event_bus: EventBus, decision: PublicUrlDecision, phase: AgentPhase):
        return event_bus.append(
            AgentEventType.BROWSER_URL_CLASSIFIED,
            "Browser URL classified before rendered snapshot capture.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "url_decision_id": decision.id,
                "status": decision.status,
                "reason": decision.reason,
                "original_url": decision.original_url,
                "final_url": decision.final_url,
                "host": decision.host,
                "resolved_addresses": decision.resolved_addresses,
                "redirect_chain": decision.redirect_chain,
                "errors": decision.errors,
            },
        )

    @staticmethod
    def _rejected(
        *,
        request: BrowserRenderedSnapshotRequest,
        decision: PublicUrlDecision,
        reason: str,
        status: BrowserSnapshotStatus,
        event_bus: EventBus,
        phase: AgentPhase,
        url_event_id: str,
        errors: list[str] | None = None,
    ) -> BrowserRenderedSnapshotResult:
        event = event_bus.append(
            AgentEventType.BROWSER_SNAPSHOT_REJECTED,
            "Rendered browser snapshot rejected before certified artifact creation.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "reason": reason,
                "url_decision_id": decision.id,
                "url_policy_trace_id": url_event_id,
                "status": status,
                "errors": errors or [],
            },
            trace_refs=[url_event_id],
        )
        return BrowserRenderedSnapshotResult(
            accepted=False,
            status=status,
            reason=reason,
            request_id=request.id,
            url_decision=decision,
            trace_event_id=event.id,
            errors=errors or [],
        )


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _detect_prompt_injection(visible_text: str, html: str) -> list[str]:
    target = f"{visible_text}\n{html}"
    flags: list[str] = []
    for name, pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(target):
            flags.append(name)
    return sorted(set(flags))


def _extract_citations(url: str, title: str | None, text: str, *, limit: int = 3) -> list[BrowserCitation]:
    cleaned = _collapse(text)
    if not cleaned:
        return []
    sentences = [match.group(0).strip() for match in re.finditer(r"[^.!?]+[.!?]?", cleaned)]
    citations: list[BrowserCitation] = []
    cursor = 0
    for sentence in sentences:
        if len(citations) >= limit:
            break
        quote = sentence.strip()
        if len(quote) < 24:
            cursor += len(sentence)
            continue
        quote = quote[:500]
        start = cleaned.find(sentence, cursor)
        if start < 0:
            start = cursor
        end = min(start + len(quote), len(cleaned))
        citations.append(
            BrowserCitation(
                url=url,
                title=title,
                quote=quote,
                char_start=start,
                char_end=end,
            )
        )
        cursor = end
    if citations:
        return citations
    quote = cleaned[:500]
    return [BrowserCitation(url=url, title=title, quote=quote, char_start=0, char_end=len(quote))]


def _safe_ref_filename(ref_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", ref_id)[:80] or "ref"
