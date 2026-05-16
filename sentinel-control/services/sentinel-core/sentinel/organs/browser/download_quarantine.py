from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import PurePosixPath
from urllib.parse import urlparse

from pydantic import Field

from sentinel.agent.artifact_capture import ArtifactCaptureKind, ArtifactCaptureSandbox  # noqa: E402 — agent-layer utility used cross-layer (Wave D documented exception)
from sentinel.organs.browser.models import PublicUrlDecision, PublicUrlDecisionStatus, PublicUrlPolicy
from sentinel.organs.browser.url_guard import DnsResolver, PublicUrlGuard
from sentinel.organs.browser.v3_authority import (
    BrowserV3AuthorityClass,
    BrowserV3AuthorityGrant,
    BrowserV3Receipt,
    browser_v3_grant_allows_url,
)
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserDownloadQuarantineRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bdlq"))
    mission_id: str
    authority_grant_id: str
    context_pack_id: str
    compiled_intent_trace_id: str
    source_url: str
    expected_effect: str = "file captured into quarantine"
    source_ref_id: str | None = None
    filename_hint: str | None = None
    allowed_mime_types: list[str] = Field(default_factory=list)
    max_bytes: int = Field(default=50_000_000, ge=1, le=500_000_000)
    quarantine_subdir: str = "browser/download_quarantine"
    require_https: bool = True
    require_dns_resolution: bool = False
    max_redirects: int = Field(default=3, ge=0, le=10)
    allow_cross_origin: bool = False
    flow_type: str = "file_transfer"
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)


class BrowserDownloadBackendResult(SentinelModel):
    final_url: str
    status_code: int = Field(ge=100, le=599)
    content_type: str = "application/octet-stream"
    data: bytes
    filename: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    redirect_chain: list[str] = Field(default_factory=list)
    compressed_bytes_read: int | None = Field(default=None, ge=0)
    uncompressed_bytes_read: int | None = Field(default=None, ge=0)


class BrowserDownloadQuarantineReceipt(BrowserV3Receipt):
    authority_class: BrowserV3AuthorityClass = BrowserV3AuthorityClass.DOWNLOAD_QUARANTINE
    source_url: str
    final_url: str
    url_policy_trace_id: str
    status_code: int
    content_type: str
    mime_type_allowed: bool = False
    size_bytes: int = Field(ge=0)
    max_bytes: int = Field(ge=1)
    download_sha256: str
    artifact_id: str
    artifact_sha256: str
    quarantine_relative_path: str
    filename_hash: str
    promoted: bool = False
    source_ref_id: str | None = None


class BrowserDownloadQuarantineResult(SentinelModel):
    accepted: bool
    reason: str
    request_id: str
    receipt: BrowserDownloadQuarantineReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


BrowserDownloadBackend = Callable[[BrowserDownloadQuarantineRequest], BrowserDownloadBackendResult]


class BrowserDownloadQuarantineExecutor:
    """Captures a public browser download into quarantine under a V3 authority grant."""

    def __init__(self, *, backend: BrowserDownloadBackend, url_guard: PublicUrlGuard | None = None) -> None:
        self.backend = backend
        self.url_guard = url_guard or PublicUrlGuard()

    def execute(
        self,
        request: BrowserDownloadQuarantineRequest,
        *,
        authority_grant: BrowserV3AuthorityGrant,
        event_bus: EventBus,
        artifact_capture: ArtifactCaptureSandbox,
        policy_trace_id: str | None = None,
        resolver: DnsResolver | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserDownloadQuarantineResult:
        if event_bus.mission_id != request.mission_id:
            raise ValueError("Browser download event bus mission_id must match request mission_id.")
        if artifact_capture.mission_id != request.mission_id:
            raise ValueError("Browser download artifact capture mission_id must match request mission_id.")

        errors = _validate_download_request(request, authority_grant)
        if errors:
            return self._rejected(request, "browser_download_quarantine_request_rejected", errors, event_bus, policy_trace_id, None, phase)

        decision, url_event_id = self._classify_url(request, event_bus=event_bus, resolver=resolver, phase=phase)
        if decision.status != PublicUrlDecisionStatus.ALLOWED or decision.final_url is None:
            return self._rejected(
                request,
                "browser_download_url_policy_blocked",
                [decision.reason, *decision.errors],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )

        try:
            backend_result = self.backend(request)
        except Exception as exc:
            return self._rejected(
                request,
                "browser_download_backend_failed",
                [f"{type(exc).__name__}:{str(exc)[:300]}"],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )

        if backend_result.redirect_chain:
            decision, url_event_id = self._classify_url(
                request,
                event_bus=event_bus,
                resolver=resolver,
                phase=phase,
                redirects=backend_result.redirect_chain,
            )
            if decision.status != PublicUrlDecisionStatus.ALLOWED or decision.final_url is None:
                return self._rejected(
                    request,
                    "browser_download_url_policy_blocked",
                    [decision.reason, *decision.errors],
                    event_bus,
                    policy_trace_id,
                    url_event_id,
                    phase,
                )

        if backend_result.final_url != decision.final_url:
            return self._rejected(
                request,
                "browser_download_final_url_policy_mismatch",
                [f"backend:{backend_result.final_url}", f"policy:{decision.final_url}"],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )
        if not browser_v3_grant_allows_url(authority_grant, backend_result.final_url):
            return self._rejected(
                request,
                "browser_download_final_url_outside_authority",
                [backend_result.final_url],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )
        same_origin = _same_origin(request.source_url, backend_result.final_url)
        cross_origin_authorized = authority_grant.allow_cross_origin or request.allow_cross_origin
        if not same_origin and not cross_origin_authorized:
            return self._rejected(
                request,
                "browser_download_cross_origin_result",
                [f"source:{request.source_url}", f"final:{backend_result.final_url}"],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )
        if not 200 <= backend_result.status_code <= 299:
            return self._rejected(
                request,
                "browser_download_status_not_success",
                [f"status_code:{backend_result.status_code}"],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )

        allowed_mime_types = request.allowed_mime_types or authority_grant.allowed_mime_types
        if not allowed_mime_types:
            return self._rejected(request, "browser_download_allowed_mime_missing", [], event_bus, policy_trace_id, url_event_id, phase)
        if not _mime_type_allowed(backend_result.content_type, allowed_mime_types):
            return self._rejected(
                request,
                "browser_download_mime_type_not_allowed",
                [f"content_type:{backend_result.content_type}"],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )

        data = backend_result.data
        max_bytes = min(request.max_bytes, authority_grant.max_bytes or request.max_bytes)
        if len(data) > max_bytes:
            return self._rejected(
                request,
                "browser_download_body_too_large",
                [f"bytes:{len(data)}", f"max_bytes:{max_bytes}"],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )

        filename = _safe_filename(backend_result.filename or request.filename_hint or _filename_from_url(backend_result.final_url))
        quarantine_subdir = _normalized_quarantine_subdir(authority_grant.quarantine_path or request.quarantine_subdir)
        relative_path = f"{quarantine_subdir}/{request.id}_{filename}"
        artifact = artifact_capture.capture_binary(
            relative_path=relative_path,
            data=data,
            artifact_type="browser_download_quarantine",
            kind=ArtifactCaptureKind.BINARY,
            content_type=backend_result.content_type,
            event_bus=event_bus,
            provenance_refs=[ref for ref in [policy_trace_id, request.compiled_intent_trace_id, url_event_id] if ref],
            phase=phase,
        )
        if not artifact.accepted or artifact.artifact is None:
            return self._rejected(
                request,
                f"browser_download_artifact_capture_failed:{artifact.reason}",
                [artifact.reason],
                event_bus,
                policy_trace_id,
                url_event_id,
                phase,
            )

        digest = hashlib.sha256(data).hexdigest()
        trace_refs = [
            ref
            for ref in [
                policy_trace_id,
                request.compiled_intent_trace_id,
                url_event_id,
                *artifact.artifact.trace_refs,
            ]
            if ref
        ]
        receipt = BrowserDownloadQuarantineReceipt(
            mission_id=request.mission_id,
            authority_grant_id=authority_grant.id,
            request_id=request.id,
            context_pack_id=request.context_pack_id,
            compiled_intent_trace_id=request.compiled_intent_trace_id,
            source_url=request.source_url,
            final_url=backend_result.final_url,
            url_policy_trace_id=url_event_id,
            status_code=backend_result.status_code,
            content_type=backend_result.content_type,
            mime_type_allowed=True,
            size_bytes=len(data),
            max_bytes=max_bytes,
            download_sha256=digest,
            artifact_id=artifact.artifact.id,
            artifact_sha256=artifact.artifact.sha256,
            quarantine_relative_path=artifact.artifact.relative_path,
            filename_hash=hashlib.sha256(filename.encode("utf-8")).hexdigest(),
            promoted=False,
            source_ref_id=request.source_ref_id,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_DOWNLOAD_QUARANTINED,
            "Browser V3 download captured into quarantine with explicit mission authority.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "receipt_id": receipt.id,
                "authority_class": BrowserV3AuthorityClass.DOWNLOAD_QUARANTINE.value,
                "authority_grant_id": authority_grant.id,
                "context_pack_id": request.context_pack_id,
                "compiled_intent_trace_id": request.compiled_intent_trace_id,
                "source_url": request.source_url,
                "final_url": backend_result.final_url,
                "url_policy_trace_id": url_event_id,
                "status_code": backend_result.status_code,
                "content_type": backend_result.content_type,
                "mime_type_allowed": True,
                "size_bytes": len(data),
                "max_bytes": max_bytes,
                "download_sha256": digest,
                "artifact_id": artifact.artifact.id,
                "artifact_sha256": artifact.artifact.sha256,
                "quarantine_relative_path": artifact.artifact.relative_path,
                "filename_hash": receipt.filename_hash,
                "promoted": False,
                "source_ref_id": request.source_ref_id,
                "policy_trace_id": policy_trace_id,
            },
            trace_refs=trace_refs,
        )
        receipt = receipt.model_copy(update={"trace_refs": [*trace_refs, event.id]})
        return BrowserDownloadQuarantineResult(
            accepted=True,
            reason="browser_download_quarantined",
            request_id=request.id,
            receipt=receipt,
            trace_event_id=event.id,
            artifact_ids=[artifact.artifact.id],
        )

    def _classify_url(
        self,
        request: BrowserDownloadQuarantineRequest,
        *,
        event_bus: EventBus,
        resolver: DnsResolver | None,
        phase: AgentPhase,
        redirects: list[str] | None = None,
    ) -> tuple[PublicUrlDecision, str]:
        policy = PublicUrlPolicy(
            allowed_schemes=["https"] if request.require_https else ["https", "http"],
            allowed_domains=[],
            max_redirects=request.max_redirects,
            require_dns_resolution=request.require_dns_resolution,
        )
        decision = self.url_guard.evaluate(request.source_url, policy=policy, resolver=resolver, redirects=redirects or [])
        event = event_bus.append(
            AgentEventType.BROWSER_URL_CLASSIFIED,
            "Browser V3 download URL classified before quarantine capture.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "status": decision.status,
                "reason": decision.reason,
                "original_url": decision.original_url,
                "normalized_url": decision.normalized_url,
                "final_url": decision.final_url,
                "host": decision.host,
                "resolved_addresses": decision.resolved_addresses,
                "redirect_chain": decision.redirect_chain,
                "errors": decision.errors,
            },
        )
        return decision, event.id

    @staticmethod
    def _rejected(
        request: BrowserDownloadQuarantineRequest,
        reason: str,
        errors: list[str],
        event_bus: EventBus,
        policy_trace_id: str | None,
        url_policy_trace_id: str | None,
        phase: AgentPhase,
    ) -> BrowserDownloadQuarantineResult:
        event = event_bus.append(
            AgentEventType.BROWSER_DOWNLOAD_REJECTED,
            "Browser V3 download quarantine rejected before artifact acceptance.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "request_id": request.id,
                "authority_class": BrowserV3AuthorityClass.DOWNLOAD_QUARANTINE.value,
                "authority_grant_id": request.authority_grant_id,
                "context_pack_id": request.context_pack_id,
                "compiled_intent_trace_id": request.compiled_intent_trace_id,
                "source_url": request.source_url,
                "url_policy_trace_id": url_policy_trace_id,
                "reason": reason,
                "errors": errors,
                "policy_trace_id": policy_trace_id,
            },
            trace_refs=[ref for ref in [policy_trace_id, request.compiled_intent_trace_id, url_policy_trace_id] if ref],
        )
        return BrowserDownloadQuarantineResult(
            accepted=False,
            reason=reason,
            request_id=request.id,
            trace_event_id=event.id,
            errors=errors,
        )


def _validate_download_request(request: BrowserDownloadQuarantineRequest, grant: BrowserV3AuthorityGrant) -> list[str]:
    errors: list[str] = []
    if grant.authority_class != BrowserV3AuthorityClass.DOWNLOAD_QUARANTINE:
        errors.append("authority_grant_class_mismatch")
    if grant.id != request.authority_grant_id:
        errors.append("authority_grant_id_mismatch")
    if not browser_v3_grant_allows_url(grant, request.source_url):
        errors.append("browser_download_url_outside_authority")
    if request.flow_type.lower() in {item.lower() for item in grant.blocked_flow_types}:
        errors.append(f"browser_download_flow_type_not_delegated:{request.flow_type}")
    if not request.context_pack_id:
        errors.append("missing_context_pack_id")
    if not request.compiled_intent_trace_id:
        errors.append("missing_compiled_intent_trace_id")
    if not _normalized_quarantine_subdir(authority_path := (grant.quarantine_path or request.quarantine_subdir)):
        errors.append(f"quarantine_path_invalid:{authority_path}")
    if grant.max_bytes is not None and request.max_bytes > grant.max_bytes:
        errors.append("request_max_bytes_exceeds_authority")
    return errors


def _mime_type_allowed(content_type: str, allowed_mime_types: list[str]) -> bool:
    mime = content_type.split(";", 1)[0].strip().lower()
    allowed = {value.split(";", 1)[0].strip().lower() for value in allowed_mime_types if value.strip()}
    return bool(mime and mime in allowed)


def _normalized_quarantine_subdir(path: str) -> str:
    pure = PurePosixPath(str(path or "").replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        return ""
    return pure.as_posix().strip("/")


def _filename_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    name = path.rsplit("/", 1)[-1] if path else ""
    return name or "download.bin"


def _safe_filename(filename: str) -> str:
    name = PurePosixPath(str(filename or "download.bin").replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:120] or "download.bin"


def _same_origin(left: str, right: str) -> bool:
    return _normalize_origin(left) == _normalize_origin(right)


def _normalize_origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlparse(value)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port
