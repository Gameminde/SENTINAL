from __future__ import annotations

import hashlib
import inspect
import re
from collections.abc import Callable
from urllib.parse import urljoin

from sentinel.agent.artifact_capture import ArtifactCaptureSandbox  # noqa: E402 — agent-layer utility used cross-layer (Wave D documented exception)
from sentinel.organs.browser.extraction import ReadablePageExtractor
from sentinel.organs.browser.models import (
    BrowserEvidenceAdapterResult,
    BrowserEvidenceAdapterStatus,
    BrowserEvidenceFetchReceipt,
    BrowserEvidenceFetchRequest,
    BrowserFetchedPage,
    PublicUrlDecision,
    PublicUrlDecisionStatus,
    PublicUrlPolicy,
)
from sentinel.organs.browser.url_guard import DnsResolver, PublicUrlGuard
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.enums import EvidenceType
from sentinel.shared.models import EvidenceItem


BrowserFetcher = Callable[..., BrowserFetchedPage]


class BrowserFetchError(RuntimeError):
    pass

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}

_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_previous_instructions", re.compile(r"\b(ignore|disregard)\b.{0,80}\b(previous|prior|above)\b.{0,40}\binstructions?\b", re.I | re.S)),
    ("system_prompt_request", re.compile(r"\b(system|developer)\s+(prompt|message|instructions?)\b", re.I)),
    ("tool_or_secret_instruction", re.compile(r"\b(call|invoke|use)\b.{0,40}\btool\b|\b(api[_ -]?key|token|password|credential)s?\b", re.I | re.S)),
    ("exfiltration_language", re.compile(r"\b(send|upload|post|submit)\b.{0,80}\b(secret|credential|token|cookie|session)\b", re.I | re.S)),
)


class BrowserEvidenceAdapter:
    """Collects browser evidence through an injected fetcher.

    This adapter does not open a browser and does not perform network IO by
    itself. The fetcher is injected so fake evals can prove the evidence,
    receipt, and trace contract before live web access exists.
    """

    def __init__(self, *, fetcher: BrowserFetcher, url_guard: PublicUrlGuard | None = None) -> None:
        self.fetcher = fetcher
        self.url_guard = url_guard or PublicUrlGuard()

    def collect(
        self,
        request: BrowserEvidenceFetchRequest,
        *,
        event_bus: EventBus,
        artifact_capture: ArtifactCaptureSandbox,
        resolver: DnsResolver | None = None,
        redirects: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserEvidenceAdapterResult:
        if event_bus.mission_id != request.mission_id:
            raise ValueError("Browser evidence event bus mission_id must match request mission_id.")
        if artifact_capture.mission_id != request.mission_id:
            raise ValueError("Browser evidence artifact capture mission_id must match request mission_id.")

        policy = PublicUrlPolicy(
            allowed_schemes=["https"] if request.require_https else ["https", "http"],
            allowed_domains=request.allowed_domains,
            max_redirects=request.max_redirects,
            require_dns_resolution=True,
        )
        redirect_chain = list(redirects or [])
        decision, url_event = self._classify_url(
            request=request,
            policy=policy,
            resolver=resolver,
            redirects=redirect_chain,
            event_bus=event_bus,
            phase=phase,
        )
        if decision.status != PublicUrlDecisionStatus.ALLOWED or decision.final_url is None:
            status = BrowserEvidenceAdapterStatus.BLOCKED
            if decision.status == PublicUrlDecisionStatus.UNAVAILABLE:
                status = BrowserEvidenceAdapterStatus.UNAVAILABLE
            return self._rejected(
                request=request,
                decision=decision,
                reason=decision.reason,
                status=status,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
            )

        while True:
            try:
                page = self._fetch_page(request, decision.final_url, decision)
            except BrowserFetchError as exc:
                return self._rejected(
                    request=request,
                    decision=decision,
                    reason="browser_fetch_failed",
                    status=BrowserEvidenceAdapterStatus.REJECTED,
                    event_bus=event_bus,
                    phase=phase,
                    url_event_id=url_event.id,
                    errors=[str(exc)],
                )

            if page.status_code in _REDIRECT_STATUSES:
                location = _header_value(page.headers, "location")
                if not location:
                    return self._rejected(
                        request=request,
                        decision=decision,
                        reason="browser_redirect_missing_location",
                        status=BrowserEvidenceAdapterStatus.REJECTED,
                        event_bus=event_bus,
                        phase=phase,
                        url_event_id=url_event.id,
                        errors=[f"status_code:{page.status_code}"],
                    )
                redirect_chain.append(urljoin(decision.final_url, location))
                decision, url_event = self._classify_url(
                    request=request,
                    policy=policy,
                    resolver=resolver,
                    redirects=redirect_chain,
                    event_bus=event_bus,
                    phase=phase,
                )
                if decision.status != PublicUrlDecisionStatus.ALLOWED or decision.final_url is None:
                    status = BrowserEvidenceAdapterStatus.BLOCKED
                    if decision.status == PublicUrlDecisionStatus.UNAVAILABLE:
                        status = BrowserEvidenceAdapterStatus.UNAVAILABLE
                    return self._rejected(
                        request=request,
                        decision=decision,
                        reason=decision.reason,
                        status=status,
                        event_bus=event_bus,
                        phase=phase,
                        url_event_id=url_event.id,
                    )
                continue
            break

        if page.final_url != decision.final_url:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_final_url_policy_mismatch",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[f"page_final_url:{page.final_url}", f"policy_final_url:{decision.final_url}"],
            )

        body_bytes = page.body.encode("utf-8")
        compressed_bytes = page.compressed_bytes_read if page.compressed_bytes_read is not None else len(body_bytes)
        uncompressed_bytes = page.uncompressed_bytes_read if page.uncompressed_bytes_read is not None else len(body_bytes)
        if compressed_bytes > request.max_compressed_bytes:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_compressed_body_too_large",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[f"compressed_bytes:{compressed_bytes}"],
            )
        if uncompressed_bytes > request.max_bytes:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_body_too_large",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[f"bytes:{uncompressed_bytes}"],
            )
        if not 200 <= page.status_code <= 299:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_status_not_successful",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[f"status_code:{page.status_code}"],
            )
        if not _mime_type_allowed(page.content_type, request.allowed_mime_types):
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_mime_type_not_allowed",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[f"content_type:{page.content_type}"],
            )
        proof_error = _connection_proof_error(page, decision, require_proof=request.require_connection_proof)
        if proof_error is not None:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_connection_not_pinned",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[proof_error],
            )

        extraction = ReadablePageExtractor().extract(
            final_url=page.final_url,
            content_type=page.content_type,
            body=page.body,
            max_chars=request.max_chars,
        )
        text = extraction.text
        flags = _detect_prompt_injection(page.body, text)
        quality_flags = extraction.source_quality_flags
        if flags:
            quality_flags = sorted({*quality_flags, "prompt_injection_detected"})
        if "empty_extraction" in quality_flags:
            return self._rejected(
                request=request,
                decision=decision,
                reason="browser_evidence_gap",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=quality_flags,
            )
        content_hash = hashlib.sha256(body_bytes).hexdigest()
        summary = _summary(text, fallback=request.purpose)
        quote = extraction.citation_quote
        confidence = _source_confidence(prompt_flags=flags, quality_flags=quality_flags)
        evidence_item = EvidenceItem(
            source="browser_readonly",
            url=page.final_url,
            quote=quote,
            summary=summary,
            confidence=confidence,
            freshness_score=0.5,
            relevance_score=0.75,
            evidence_type=EvidenceType.DIRECT_PROOF,
            metadata={
                "title": extraction.title,
                "request_id": request.id,
                "content_sha256": content_hash,
                "prompt_injection_flags": flags,
                "source_quality_flags": quality_flags,
                "extraction_strategy": extraction.strategy,
                "truncated": extraction.truncated,
                "citation_char_start": extraction.citation_char_start,
                "citation_char_end": extraction.citation_char_end,
            },
        )

        artifact_payload = {
            "request_id": request.id,
            "original_url": request.url,
            "final_url": page.final_url,
            "title": extraction.title,
            "summary": summary,
            "text": text,
            "links": extraction.links,
            "prompt_injection_flags": flags,
            "source_quality_flags": quality_flags,
            "extraction_strategy": extraction.strategy,
            "truncated": extraction.truncated,
            "raw_chars_extracted": extraction.raw_chars_extracted,
            "citation_char_start": extraction.citation_char_start,
            "citation_char_end": extraction.citation_char_end,
            "content_sha256": content_hash,
            "content_type": page.content_type,
            "status_code": page.status_code,
            "compressed_bytes_read": compressed_bytes,
            "uncompressed_bytes_read": uncompressed_bytes,
            "connection_proof": page.connection_proof.model_dump(mode="json") if page.connection_proof else {},
        }
        artifact = artifact_capture.capture_json(
            relative_path=f"browser/{request.id}.json",
            payload=artifact_payload,
            artifact_type="browser_evidence",
            event_bus=event_bus,
            evidence_refs=[evidence_item.id],
            provenance_refs=[url_event.id],
            phase=phase,
        )
        if not artifact.accepted or artifact.artifact is None:
            return self._rejected(
                request=request,
                decision=decision,
                reason=f"artifact_capture_failed:{artifact.reason}",
                status=BrowserEvidenceAdapterStatus.REJECTED,
                event_bus=event_bus,
                phase=phase,
                url_event_id=url_event.id,
                errors=[artifact.reason],
            )

        receipt = BrowserEvidenceFetchReceipt(
            mission_id=request.mission_id,
            request_id=request.id,
            original_url=request.url,
            final_url=page.final_url,
            url_policy_trace_id=url_event.id,
            evidence_item_id=evidence_item.id,
            artifact_id=artifact.artifact.id,
            artifact_sha256=artifact.artifact.sha256,
            content_sha256=content_hash,
            content_type=page.content_type,
            mime_type_allowed=True,
            bytes_read=uncompressed_bytes,
            compressed_bytes_read=compressed_bytes,
            uncompressed_bytes_read=uncompressed_bytes,
            chars_extracted=len(text),
            raw_chars_extracted=extraction.raw_chars_extracted,
            extraction_strategy=extraction.strategy,
            source_quality_flags=quality_flags,
            truncated=extraction.truncated,
            citation_char_start=extraction.citation_char_start,
            citation_char_end=extraction.citation_char_end,
            connection_proof=page.connection_proof.model_dump(mode="json") if page.connection_proof else {},
            prompt_injection_flags=flags,
            citation_refs=[evidence_item.id],
            trace_refs=[url_event.id, *(artifact.artifact.trace_refs or [])],
        )
        event = event_bus.append(
            AgentEventType.BROWSER_EVIDENCE_COLLECTED,
            "Browser evidence collected through injected read-only adapter.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "receipt_id": receipt.id,
                "evidence_item_id": evidence_item.id,
                "artifact_id": artifact.artifact.id,
                "artifact_sha256": artifact.artifact.sha256,
                "content_sha256": content_hash,
                "final_url": page.final_url,
                "title": extraction.title,
                "link_count": len(extraction.links),
                "prompt_injection_flags": flags,
                "source_quality_flags": quality_flags,
                "extraction_strategy": extraction.strategy,
                "truncated": extraction.truncated,
                "citation_char_start": extraction.citation_char_start,
                "citation_char_end": extraction.citation_char_end,
                "url_policy_trace_id": url_event.id,
                "compressed_bytes_read": compressed_bytes,
                "uncompressed_bytes_read": uncompressed_bytes,
                "mime_type_allowed": True,
                "connection_proof": page.connection_proof.model_dump(mode="json") if page.connection_proof else {},
            },
            trace_refs=[url_event.id, *(artifact.artifact.trace_refs or [])],
        )
        receipt = receipt.model_copy(update={"trace_refs": [*receipt.trace_refs, event.id]})
        return BrowserEvidenceAdapterResult(
            accepted=True,
            status=BrowserEvidenceAdapterStatus.COLLECTED,
            reason="browser_evidence_collected",
            request_id=request.id,
            url_decision=decision,
            title=extraction.title,
            extracted_text=text,
            links=extraction.links,
            prompt_injection_flags=flags,
            source_quality_flags=quality_flags,
            extraction_strategy=extraction.strategy,
            truncated=extraction.truncated,
            citation_char_start=extraction.citation_char_start,
            citation_char_end=extraction.citation_char_end,
            evidence_item_id=evidence_item.id,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def _classify_url(
        self,
        *,
        request: BrowserEvidenceFetchRequest,
        policy: PublicUrlPolicy,
        resolver: DnsResolver | None,
        redirects: list[str],
        event_bus: EventBus,
        phase: AgentPhase,
    ):
        decision = self.url_guard.evaluate(request.url, policy=policy, resolver=resolver, redirects=redirects)
        return decision, self._emit_url_decision(event_bus, decision, phase)

    def _fetch_page(
        self,
        request: BrowserEvidenceFetchRequest,
        final_url: str,
        decision: PublicUrlDecision,
    ) -> BrowserFetchedPage:
        if _callable_accepts_decision(self.fetcher):
            return self.fetcher(request, final_url, decision)
        return self.fetcher(request, final_url)

    @staticmethod
    def _emit_url_decision(event_bus: EventBus, decision: PublicUrlDecision, phase: AgentPhase):
        return event_bus.append(
            AgentEventType.BROWSER_URL_CLASSIFIED,
            "Browser URL classified before any evidence collection.",
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
        request: BrowserEvidenceFetchRequest,
        decision: PublicUrlDecision,
        reason: str,
        status: BrowserEvidenceAdapterStatus,
        event_bus: EventBus,
        phase: AgentPhase,
        url_event_id: str,
        errors: list[str] | None = None,
    ) -> BrowserEvidenceAdapterResult:
        event = event_bus.append(
            AgentEventType.BROWSER_EVIDENCE_REJECTED,
            "Browser evidence collection rejected before certified evidence was created.",
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
        return BrowserEvidenceAdapterResult(
            accepted=False,
            status=status,
            reason=reason,
            request_id=request.id,
            url_decision=decision,
            trace_event_id=event.id,
            errors=errors or [],
        )


def _summary(text: str, *, fallback: str) -> str:
    if text:
        return text[:280]
    return fallback[:280]


def _detect_prompt_injection(raw_body: str, visible_text: str) -> list[str]:
    target = f"{visible_text}\n{raw_body}"
    flags: list[str] = []
    for name, pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(target):
            flags.append(name)
    return sorted(set(flags))


def _source_confidence(*, prompt_flags: list[str], quality_flags: list[str]) -> float:
    confidence = 0.88
    if prompt_flags:
        confidence -= 0.14
    if "thin_content" in quality_flags:
        confidence -= 0.12
    if "boilerplate_heavy" in quality_flags:
        confidence -= 0.1
    if "fallback_text_extraction" in quality_flags:
        confidence -= 0.08
    if "truncated" in quality_flags:
        confidence -= 0.04
    return max(0.25, round(confidence, 2))


def _callable_accepts_decision(fetcher: BrowserFetcher) -> bool:
    try:
        signature = inspect.signature(fetcher)
    except (TypeError, ValueError):
        return False
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in {parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD}
    ]
    accepts_varargs = any(parameter.kind == parameter.VAR_POSITIONAL for parameter in signature.parameters.values())
    return accepts_varargs or len(positional) >= 3


def _header_value(headers: dict[str, str], name: str) -> str | None:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def _mime_type_allowed(content_type: str, allowed_mime_types: list[str]) -> bool:
    mime = content_type.split(";", 1)[0].strip().lower()
    allowed = {value.split(";", 1)[0].strip().lower() for value in allowed_mime_types if value.strip()}
    return bool(mime and mime in allowed)


def _connection_proof_error(
    page: BrowserFetchedPage,
    decision: PublicUrlDecision,
    *,
    require_proof: bool,
) -> str | None:
    proof = page.connection_proof
    if proof is None:
        if require_proof:
            return "connection_proof_missing"
        return None
    if proof.host != decision.host:
        return f"connection_host_mismatch:{proof.host}:{decision.host}"
    approved = set(decision.resolved_addresses)
    if require_proof and not proof.approved_addresses:
        return "approved_addresses_missing"
    if proof.approved_addresses and set(proof.approved_addresses) != approved:
        return "connection_approved_addresses_mismatch"
    if require_proof and not proof.connected_address:
        return "connected_address_missing"
    if proof.connected_address and proof.connected_address not in approved:
        return f"connected_address_not_approved:{proof.connected_address}"
    if require_proof and not proof.pinned:
        return "connection_not_pinned"
    return None
