from __future__ import annotations

import hashlib
import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from sentinel.power.runtime import PowerStepResult, PowerStepStatus
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized


class ExternalAPIStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class ExternalAPIRequest(SentinelModel):
    mission_id: str
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: bytes | None = None
    credential_ref_id: str | None = None
    mutation_authority_ref: str | None = None
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @field_validator("method")
    @classmethod
    def _method_upper(cls, value: str) -> str:
        method = value.strip().upper()
        if not method:
            raise ValueError("method is required")
        return method

    @field_validator("url")
    @classmethod
    def _url_must_be_http(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("external API URL must be http(s) with a host")
        return value

    @model_validator(mode="after")
    def _request_is_safe_metadata(self) -> ExternalAPIRequest:
        if self.authority_effect != "none":
            raise ValueError("external API request cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("external API request must remain data-not-instruction")
        scan = scan_forbidden_payload_categorized(
            {
                "headers": self.headers,
                "credential_ref_id": self.credential_ref_id,
                "mutation_authority_ref": self.mutation_authority_ref,
            },
            path="$",
        )
        rejected = [
            *scan[OrganSafetyScanCategory.SECRET.value],
            *scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value],
            *scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value],
            *scan[OrganSafetyScanCategory.UNSAFE_PAYLOAD.value],
            *scan[OrganSafetyScanCategory.CREDENTIAL_DANGEROUS.value],
        ]
        if rejected:
            raise ValueError("external API request contains forbidden credential/provider metadata")
        return self

    @property
    def host(self) -> str:
        return str(urlparse(self.url).hostname or "").lower()


class ExternalAPIContract(SentinelModel):
    allowed_domains: list[str]
    allowed_methods: list[str] = Field(default_factory=lambda: ["GET", "HEAD"])
    mutation_authorized: bool = False
    max_requests_per_domain: int = Field(default=10, ge=1)
    allow_response_body_quarantine: bool = False
    max_response_body_bytes: int = Field(default=262_144, ge=0)
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @field_validator("allowed_methods")
    @classmethod
    def _methods_upper(cls, value: list[str]) -> list[str]:
        return [method.strip().upper() for method in value]

    @field_validator("allowed_domains")
    @classmethod
    def _domains_lower(cls, value: list[str]) -> list[str]:
        return [domain.strip().lower() for domain in value if domain.strip()]

    @model_validator(mode="after")
    def _contract_is_not_authority(self) -> ExternalAPIContract:
        if self.authority_effect != "none":
            raise ValueError("external API contract cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("external API contract must remain data-not-instruction")
        if not self.allowed_domains:
            raise ValueError("external API contract requires allowed_domains")
        return self


class ExternalAPITransportRequest(SentinelModel):
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: bytes | None = None
    timeout_seconds: int = 30


class ExternalAPITransportResponse(SentinelModel):
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: bytes = b""


class ExternalAPIRateLimitLedger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, str], int] = {}

    def consume(self, *, mission_id: str, domain: str, limit: int) -> bool:
        key = (mission_id, domain.lower())
        with self._lock:
            current = self._counts.get(key, 0)
            if current >= limit:
                return False
            self._counts[key] = current + 1
            return True


class ExternalAPIReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("api_receipt"))
    mission_id: str
    method: str
    host: str
    url_hash: str
    request_hash: str
    status_code: int | None = None
    response_header_hash: str | None = None
    response_body_sha256: str | None = None
    response_body_bytes: int = Field(default=0, ge=0)
    response_body_quarantine_ref: str | None = None
    mutation_authority_ref: str | None = None
    credential_ref_id: str | None = None
    started_at: datetime
    ended_at: datetime
    authority_effect: str = "none"
    execution_effect: str = "external_api_request"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _receipt_is_not_authority(self) -> ExternalAPIReceipt:
        if self.authority_effect != "none":
            raise ValueError("external API receipt cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("external API receipt must remain data-not-instruction")
        return self


class ExternalAPIFinalGateCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("api_finalgate"))
    mission_id: str
    passed: bool
    status: ExternalAPIStatus
    receipt_ref: str | None = None
    failures: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_instruction: bool = True


class ExternalAPIResult(SentinelModel):
    mission_id: str
    status: ExternalAPIStatus
    receipt: ExternalAPIReceipt | None = None
    finalgate_certificate: ExternalAPIFinalGateCertificate | None = None
    blocked_reason: str | None = None
    safe_summary: str = ""
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _result_is_not_authority(self) -> ExternalAPIResult:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("external API result cannot grant authority or execute more")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("external API result cannot approve future execution")
        if self.data_not_instruction is not True:
            raise ValueError("external API result must remain data-not-instruction")
        return self


ExternalAPITransport = Callable[[ExternalAPITransportRequest], ExternalAPITransportResponse]


class ExternalAPIFinalGate:
    def certify(self, result: ExternalAPIResult) -> ExternalAPIFinalGateCertificate:
        failures: list[str] = []
        if result.status in {ExternalAPIStatus.SUCCEEDED, ExternalAPIStatus.FAILED} and result.receipt is None:
            failures.append("missing_api_receipt")
        if result.receipt is not None:
            if not result.receipt.request_hash:
                failures.append("missing_request_hash")
            if result.receipt.response_body_bytes and not result.receipt.response_body_sha256:
                failures.append("missing_response_body_hash")
        return ExternalAPIFinalGateCertificate(
            mission_id=result.mission_id,
            passed=not failures,
            status=result.status,
            receipt_ref=result.receipt.receipt_id if result.receipt else None,
            failures=failures,
        )


class ExternalAPIOrganV1:
    organ_kind = "external_api"

    def __init__(
        self,
        *,
        transport: ExternalAPITransport | None = None,
        rate_ledger: ExternalAPIRateLimitLedger | None = None,
    ) -> None:
        self._transport = transport or _urllib_transport
        self._rate_ledger = rate_ledger or ExternalAPIRateLimitLedger()

    def execute(self, request: ExternalAPIRequest, *, contract: ExternalAPIContract) -> ExternalAPIResult:
        block_reason = self._block_reason(request, contract)
        if block_reason:
            return self._blocked(request, block_reason)

        if not self._rate_ledger.consume(
            mission_id=request.mission_id,
            domain=request.host,
            limit=contract.max_requests_per_domain,
        ):
            return self._blocked(request, "rate_limit_exhausted")

        started_at = _utc_now()
        try:
            response = self._transport(
                ExternalAPITransportRequest(
                    method=request.method,
                    url=request.url,
                    headers=_safe_non_auth_headers(request.headers),
                    body=request.body,
                )
            )
            status = ExternalAPIStatus.SUCCEEDED if 200 <= response.status_code < 400 else ExternalAPIStatus.FAILED
            receipt = _build_receipt(request, response, contract, started_at=started_at, ended_at=_utc_now())
        except Exception as exc:  # pragma: no cover - transport specific.
            status = ExternalAPIStatus.FAILED
            receipt = _build_receipt(
                request,
                ExternalAPITransportResponse(status_code=0, headers={"transport_error": exc.__class__.__name__}, body=b""),
                contract,
                started_at=started_at,
                ended_at=_utc_now(),
            )

        result = ExternalAPIResult(
            mission_id=request.mission_id,
            status=status,
            receipt=receipt,
            safe_summary=f"External API request finished with status {status.value}.",
        )
        return result.model_copy(update={"finalgate_certificate": ExternalAPIFinalGate().certify(result)})

    def _block_reason(self, request: ExternalAPIRequest, contract: ExternalAPIContract) -> str | None:
        if not _domain_allowed(request.host, contract.allowed_domains):
            return "domain_not_allowed"
        if request.method not in contract.allowed_methods:
            return "method_not_allowed"
        if request.method not in {"GET", "HEAD"} and (not contract.mutation_authorized or not request.mutation_authority_ref):
            return "mutation_authority_missing"
        return None

    @staticmethod
    def _blocked(request: ExternalAPIRequest, reason: str) -> ExternalAPIResult:
        result = ExternalAPIResult(
            mission_id=request.mission_id,
            status=ExternalAPIStatus.BLOCKED,
            blocked_reason=reason,
            safe_summary=f"External API request blocked: {reason}.",
        )
        return result.model_copy(update={"finalgate_certificate": ExternalAPIFinalGate().certify(result)})


def build_external_api_power_executor(
    *,
    contract: ExternalAPIContract,
    transport: ExternalAPITransport | None = None,
    rate_ledger: ExternalAPIRateLimitLedger | None = None,
) -> Any:
    organ = ExternalAPIOrganV1(transport=transport, rate_ledger=rate_ledger)

    def _executor(step: Any, context: dict[str, Any]) -> PowerStepResult:
        request_payload = dict(getattr(step, "request", {}) or {})
        request = ExternalAPIRequest(
            mission_id=str(context.get("mission_id") or "mission_unknown"),
            method=str(request_payload.get("method") or "GET"),
            url=str(request_payload.get("url") or ""),
            headers=dict(request_payload.get("headers") or {}),
            body=request_payload.get("body"),
            credential_ref_id=request_payload.get("credential_ref_id"),
            mutation_authority_ref=request_payload.get("mutation_authority_ref"),
        )
        result = organ.execute(request, contract=contract)
        status = PowerStepStatus.SUCCEEDED if result.status is ExternalAPIStatus.SUCCEEDED else PowerStepStatus.FAILED
        if result.status is ExternalAPIStatus.BLOCKED:
            status = PowerStepStatus.BLOCKED
        return PowerStepResult(
            step_id=step.step_id,
            status=status,
            receipt_refs=[result.receipt.receipt_id] if result.receipt else [],
            finalgate_certificate_refs=[result.finalgate_certificate.certificate_id] if result.finalgate_certificate else [],
            blocked_reason=result.blocked_reason,
            safe_summary=result.safe_summary,
        )

    return _executor


def _build_receipt(
    request: ExternalAPIRequest,
    response: ExternalAPITransportResponse,
    contract: ExternalAPIContract,
    *,
    started_at: datetime,
    ended_at: datetime,
) -> ExternalAPIReceipt:
    body = response.body[: contract.max_response_body_bytes]
    body_hash = _sha256_bytes(body) if body else None
    quarantine_ref = f"api_body_quarantine:{body_hash}" if body_hash and contract.allow_response_body_quarantine else None
    return ExternalAPIReceipt(
        mission_id=request.mission_id,
        method=request.method,
        host=request.host,
        url_hash=_stable_hash({"url": request.url}),
        request_hash=_stable_hash(
            {
                "method": request.method,
                "url_hash": _stable_hash({"url": request.url}),
                "headers_hash": _stable_hash(_safe_non_auth_headers(request.headers)),
                "body_sha256": _sha256_bytes(request.body) if request.body else None,
            }
        ),
        status_code=response.status_code,
        response_header_hash=_stable_hash(response.headers),
        response_body_sha256=body_hash,
        response_body_bytes=len(body),
        response_body_quarantine_ref=quarantine_ref,
        mutation_authority_ref=request.mutation_authority_ref,
        credential_ref_id=request.credential_ref_id,
        started_at=started_at,
        ended_at=ended_at,
    )


def _safe_non_auth_headers(headers: dict[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in headers.items():
        normalized = key.strip().lower()
        if normalized in {"authorization", "cookie", "x-api-key", "api-key"}:
            continue
        safe[str(key)] = str(value)
    return safe


def _domain_allowed(host: str, allowed_domains: list[str]) -> bool:
    normalized = host.lower()
    for domain in allowed_domains:
        allowed = domain.lower()
        if normalized == allowed or normalized.endswith("." + allowed):
            return True
    return False


def _urllib_transport(request: ExternalAPITransportRequest) -> ExternalAPITransportResponse:
    req = urllib.request.Request(
        request.url,
        data=request.body,
        headers=request.headers,
        method=request.method,
    )
    try:
        with urllib.request.urlopen(req, timeout=request.timeout_seconds) as response:  # noqa: S310 - gated by contract before call.
            return ExternalAPITransportResponse(
                status_code=int(response.status),
                headers={str(key): str(value) for key, value in response.headers.items()},
                body=response.read(),
            )
    except urllib.error.HTTPError as exc:
        return ExternalAPITransportResponse(
            status_code=int(exc.code),
            headers={str(key): str(value) for key, value in exc.headers.items()},
            body=exc.read(),
        )


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes | None) -> str:
    return hashlib.sha256(value or b"").hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)
