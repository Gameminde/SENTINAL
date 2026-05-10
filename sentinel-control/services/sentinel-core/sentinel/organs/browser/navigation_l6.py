from __future__ import annotations

import hashlib
import html.parser
import ipaddress
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable, ClassVar
from urllib.parse import urljoin, urlsplit, urlunsplit

from pydantic import Field, model_validator

from sentinel.agent.evidence_ranker import sanitize_context_payload, sanitize_context_text
from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.browser.misuse_classifier import BrowserMisuseClassifier
from sentinel.organs.browser.power_governor import BrowserPowerGovernor, BrowserPowerLevel, BrowserPowerRequest
from sentinel.organs.reality_activation import RealityBrowserReader
from sentinel.shared.models import SentinelModel, new_id


REQUIRED_BROWSER_L6_BINDING_REFS = {
    "openclaw_browser_action_kernel",
    "cloakbrowser_power_classification",
    "jarvis_permission_lifecycle",
    "browser_use_action_registry_crosscheck",
    "cua_browser_tool_boundary_crosscheck",
    "chrome_devtools_mcp_cdp_shape_crosscheck",
    "hermes_browser_output_pruning",
    "sentinel_p6r_decision_frame",
}

NORMAL_BROWSER_L6_ACTION = "browser_controlled_navigation_l6"
PROPOSAL_ONLY_ACTIONS = {
    "login",
    "session_mutation",
    "form_submit",
    "file_upload",
    "file_download",
    "upload",
    "download",
    "post",
    "publish",
    "send",
    "payment",
    "checkout",
    "execute_javascript",
    "arbitrary_js_execution",
    "profile_takeover",
}
PROPOSAL_ONLY_SCHEMES = {"chrome", "devtools"}
QUARANTINE_SCHEMES = {"file", "javascript", "data"}


def _stable_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_host(host: str | None) -> str:
    if not host:
        return ""
    return host.rstrip(".").encode("idna").decode("ascii").lower()


def _normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    host = _normalize_host(parsed.hostname)
    netloc = host
    if parsed.port is not None:
        netloc = f"{host}:{parsed.port}"
    path = parsed.path or ("/" if scheme in {"http", "https"} else parsed.path)
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _host_is_local_or_private(host: str) -> bool:
    normalized = _normalize_host(host)
    if normalized in {"localhost", "127.0.0.1", "::1"} or normalized.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local or address.is_reserved


def _domain_matches(host: str, allowed_domain: str) -> bool:
    normalized_host = _normalize_host(host)
    normalized_allowed = _normalize_host(allowed_domain)
    return normalized_host == normalized_allowed or normalized_host.endswith(f".{normalized_allowed}")


def _domain_is_allowlisted(host: str, allowed_domains: list[str]) -> bool:
    return any(_domain_matches(host, allowed) for allowed in allowed_domains)


class BrowserRiskRoute(StrEnum):
    NORMAL_NAVIGATION = "normal_navigation"
    QUARANTINE_SANDBOX_INSPECTION = "quarantine_sandbox_inspection"
    PROPOSAL_ONLY = "proposal_only"
    BLACK_LANE_BLOCK = "black_lane_block"


class BrowserRiskDecision(SentinelModel):
    route: BrowserRiskRoute
    reason: str
    normalized_url: str
    scheme: str
    host: str = ""
    suspicious: bool = False
    blocked: bool = False


class BrowserNavigationAuthority(SentinelModel):
    mission_id: str
    root_authority_id: str
    allowed_domains: list[str]
    allowed_schemes: list[str]
    allowed_operation_classes: list[str]
    timeout_seconds: float = Field(gt=0.0)
    max_page_bytes: int = Field(gt=0)
    max_extracted_text_bytes: int = Field(gt=0)
    max_links_extracted: int = Field(ge=0)
    expires_at: datetime
    evidence_refs: list[str]
    trace_refs: list[str]
    source_binding_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> BrowserNavigationAuthority:
        missing = sorted(REQUIRED_BROWSER_L6_BINDING_REFS - set(self.source_binding_refs))
        if missing:
            raise ValueError(f"BrowserNavigationAuthority requires P6T-A source binding refs:{missing}")
        if not self.root_authority_id:
            raise ValueError("BrowserNavigationAuthority requires root authority id.")
        if not self.allowed_domains:
            raise ValueError("BrowserNavigationAuthority requires allowed domains.")
        if not set(self.allowed_schemes).issubset({"http", "https"}):
            raise ValueError("BrowserNavigationAuthority normal lane only supports http/https schemes.")
        if NORMAL_BROWSER_L6_ACTION not in self.allowed_operation_classes:
            raise ValueError("BrowserNavigationAuthority requires browser_controlled_navigation_l6 operation class.")
        if not self.evidence_refs:
            raise ValueError("BrowserNavigationAuthority requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("BrowserNavigationAuthority requires trace refs.")
        if self.expires_at <= datetime.now(UTC):
            raise ValueError("BrowserNavigationAuthority is expired.")
        if self.authority_expansion:
            raise ValueError("BrowserNavigationAuthority cannot expand authority.")
        self.allowed_domains = sorted({_normalize_host(domain) for domain in self.allowed_domains})
        self.allowed_schemes = sorted({scheme.lower() for scheme in self.allowed_schemes})
        self.source_binding_refs = list(self.source_binding_refs)
        return self

    def domain_allowed(self, host: str) -> bool:
        return _domain_is_allowlisted(host, self.allowed_domains)


class BrowserNavigationBudget(SentinelModel):
    max_pages: int = Field(default=1, gt=0)
    timeout_seconds: float = Field(default=10.0, gt=0.0)
    max_page_bytes: int = Field(default=250_000, gt=0)
    max_extracted_text_bytes: int = Field(default=4_000, gt=0)
    max_links_extracted: int = Field(default=20, ge=0)


class BrowserNavigationTimeoutPolicy(SentinelModel):
    timeout_seconds: float = Field(default=10.0, gt=0.0)
    fail_closed_on_timeout: bool = True


class BrowserNavigationKillSwitch(SentinelModel):
    mission_id: str
    triggered: bool = False
    reason: str | None = None

    def trigger(self, *, reason: str) -> BrowserNavigationKillSwitch:
        return self.model_copy(update={"triggered": True, "reason": reason})


class BrowserSchemeClassifier:
    def classify(self, url: str) -> BrowserRiskDecision:
        normalized_url = _normalize_url(url)
        parsed = urlsplit(normalized_url)
        scheme = parsed.scheme.lower()
        host = _normalize_host(parsed.hostname)
        if scheme in PROPOSAL_ONLY_SCHEMES:
            return BrowserRiskDecision(
                route=BrowserRiskRoute.PROPOSAL_ONLY,
                reason=f"{scheme}_scheme_requires_proposal",
                normalized_url=normalized_url,
                scheme=scheme,
                host=host,
                suspicious=True,
            )
        if scheme in QUARANTINE_SCHEMES:
            return BrowserRiskDecision(
                route=BrowserRiskRoute.QUARANTINE_SANDBOX_INSPECTION,
                reason=f"{scheme}_scheme_requires_quarantine",
                normalized_url=normalized_url,
                scheme=scheme,
                host=host,
                suspicious=True,
            )
        if scheme in {"http", "https"} and _host_is_local_or_private(host):
            return BrowserRiskDecision(
                route=BrowserRiskRoute.QUARANTINE_SANDBOX_INSPECTION,
                reason="local_or_private_network_requires_sandbox_authority",
                normalized_url=normalized_url,
                scheme=scheme,
                host=host,
                suspicious=True,
            )
        if scheme in {"http", "https"}:
            return BrowserRiskDecision(
                route=BrowserRiskRoute.NORMAL_NAVIGATION,
                reason="http_https_normal_navigation_candidate",
                normalized_url=normalized_url,
                scheme=scheme,
                host=host,
            )
        return BrowserRiskDecision(
            route=BrowserRiskRoute.QUARANTINE_SANDBOX_INSPECTION,
            reason="unknown_scheme_requires_quarantine",
            normalized_url=normalized_url,
            scheme=scheme,
            host=host,
            suspicious=True,
        )


class BrowserRiskRouter:
    def __init__(self, *, scheme_classifier: BrowserSchemeClassifier | None = None) -> None:
        self.scheme_classifier = scheme_classifier or BrowserSchemeClassifier()
        self.misuse_classifier = BrowserMisuseClassifier()

    def route(
        self,
        *,
        url: str,
        authority: BrowserNavigationAuthority,
        action_type: str = NORMAL_BROWSER_L6_ACTION,
        objective_tags: list[str] | None = None,
        redirect_chain: list[str] | None = None,
    ) -> BrowserRiskDecision:
        misuse = self.misuse_classifier.classify(objective_tags=objective_tags or [], objective_text=action_type)
        if misuse.blocked:
            return BrowserRiskDecision(
                route=BrowserRiskRoute.BLACK_LANE_BLOCK,
                reason="black_lane_browser_misuse_objective",
                normalized_url=_normalize_url(url),
                scheme=urlsplit(url).scheme.lower(),
                host=_normalize_host(urlsplit(url).hostname),
                suspicious=True,
                blocked=True,
            )
        if action_type != NORMAL_BROWSER_L6_ACTION:
            return BrowserRiskDecision(
                route=BrowserRiskRoute.PROPOSAL_ONLY,
                reason=f"{action_type}_requires_future_browser_promotion",
                normalized_url=_normalize_url(url),
                scheme=urlsplit(url).scheme.lower(),
                host=_normalize_host(urlsplit(url).hostname),
                suspicious=True,
            )
        decision = self.scheme_classifier.classify(url)
        if decision.route != BrowserRiskRoute.NORMAL_NAVIGATION:
            return decision
        if decision.scheme not in authority.allowed_schemes:
            return decision.model_copy(
                update={"route": BrowserRiskRoute.QUARANTINE_SANDBOX_INSPECTION, "reason": "scheme_not_authorized_for_normal_navigation"}
            )
        if not authority.domain_allowed(decision.host):
            return decision.model_copy(update={"route": BrowserRiskRoute.QUARANTINE_SANDBOX_INSPECTION, "reason": "domain_not_allowlisted"})
        for target in redirect_chain or []:
            target_decision = self.scheme_classifier.classify(target)
            if target_decision.route != BrowserRiskRoute.NORMAL_NAVIGATION or not authority.domain_allowed(target_decision.host):
                return target_decision.model_copy(
                    update={
                        "route": BrowserRiskRoute.QUARANTINE_SANDBOX_INSPECTION,
                        "reason": "redirect_target_requires_quarantine",
                    }
                )
        return decision


class BrowserQuarantineSandboxPolicy(SentinelModel):
    disposable_profile: bool = True
    personal_profile_allowed: bool = False
    saved_cookies_allowed: bool = False
    saved_credentials_allowed: bool = False
    credential_store_allowed: bool = False
    clipboard_allowed: bool = False
    camera_allowed: bool = False
    microphone_allowed: bool = False
    host_filesystem_mount_allowed: bool = False
    downloads_allowed: bool = True
    download_target: str = "quarantine_artifact_store"
    arbitrary_host_js_allowed: bool = False

    @classmethod
    def default(cls) -> BrowserQuarantineSandboxPolicy:
        return cls()


class BrowserSandboxNetworkPolicy(SentinelModel):
    local_network_allowed: bool = False
    allowed_targets: list[str] = Field(default_factory=list)


class BrowserSandboxArtifactStore(SentinelModel):
    store_name: str = "quarantine_artifact_store"
    host_filesystem_mount_allowed: bool = False
    artifact_refs: list[str] = Field(default_factory=list)


class BrowserSandboxEscapeGuard(SentinelModel):
    host_filesystem_mount_allowed: bool = False
    personal_profile_allowed: bool = False
    credential_store_allowed: bool = False


class BrowserSandboxAuthority(SentinelModel):
    mission_id: str
    root_authority_id: str
    allowed_sandbox_targets: list[str]
    local_network_allowed: bool = False
    expires_at: datetime
    evidence_refs: list[str]
    trace_refs: list[str]
    source_binding_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> BrowserSandboxAuthority:
        missing = sorted(REQUIRED_BROWSER_L6_BINDING_REFS - set(self.source_binding_refs))
        if missing:
            raise ValueError(f"BrowserSandboxAuthority requires P6T-A source binding refs:{missing}")
        if self.expires_at <= datetime.now(UTC):
            raise ValueError("BrowserSandboxAuthority is expired.")
        if self.authority_expansion:
            raise ValueError("BrowserSandboxAuthority cannot expand authority.")
        self.allowed_sandbox_targets = sorted({_normalize_host(target) for target in self.allowed_sandbox_targets})
        return self

    def allows_local_target(self, target: str) -> bool:
        return self.local_network_allowed and _normalize_host(target) in set(self.allowed_sandbox_targets)


class SuspiciousUrlEvidenceCard(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bsus"))
    suspicious_url_hash: str
    reason: str
    raw_payload_included: bool = False
    untrusted_context: bool = True


class BrowserSandboxInspectionReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bsandbox"))
    mission_id: str
    suspicious_url_hash: str
    route: BrowserRiskRoute = BrowserRiskRoute.QUARANTINE_SANDBOX_INSPECTION
    sandbox_policy: BrowserQuarantineSandboxPolicy = Field(default_factory=BrowserQuarantineSandboxPolicy.default)
    evidence_refs: list[str]
    trace_refs: list[str]
    source_binding_refs: list[str]
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _validate(self) -> BrowserSandboxInspectionReceipt:
        if not self.evidence_refs:
            raise ValueError("BrowserSandboxInspectionReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("BrowserSandboxInspectionReceipt requires trace refs.")
        if not self.receipt_hash:
            self.receipt_hash = self.expected_hash()
        elif self.receipt_hash != self.expected_hash():
            raise ValueError("BrowserSandboxInspectionReceipt hash mismatch.")
        return self

    def expected_hash(self) -> str:
        return _stable_hash(
            {
                "mission_id": self.mission_id,
                "suspicious_url_hash": self.suspicious_url_hash,
                "route": self.route,
                "sandbox_policy": self.sandbox_policy.model_dump(),
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
                "source_binding_refs": self.source_binding_refs,
            }
        )


class BrowserLinkCandidateRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("blink"))
    target_url: str
    target_url_hash: str
    text_summary: str
    route: BrowserRiskRoute

    @classmethod
    def from_link(cls, *, href: str, base_url: str, text: str, authority: BrowserNavigationAuthority) -> BrowserLinkCandidateRef:
        target = _normalize_url(urljoin(base_url, href))
        route = BrowserRiskRouter().route(url=target, authority=authority).route
        return cls(
            target_url=target,
            target_url_hash=_hash_text(target),
            text_summary=sanitize_context_text(text)[:120],
            route=route,
        )


class _PreviewOnlyDescriptor:
    def __get__(self, instance: BrowserActionCandidateRef | None, owner: type[BrowserActionCandidateRef]) -> bool | Callable[..., BrowserActionCandidateRef]:
        if instance is not None:
            return instance.preview_only_flag

        def factory(*, action_type: str, target_url: str, reason: str) -> BrowserActionCandidateRef:
            return owner(
                action_type=action_type,
                target_url_hash=_hash_text(_normalize_url(target_url)),
                reason=reason,
                preview_only_flag=True,
            )

        return factory


class BrowserActionCandidateRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("baction"))
    action_type: str
    target_url_hash: str
    reason: str
    preview_only_flag: bool = True
    preview_only: ClassVar[_PreviewOnlyDescriptor] = _PreviewOnlyDescriptor()


class BrowserNavigationCostTrace(SentinelModel):
    page_count: int = Field(ge=0)
    bytes_read: int = Field(ge=0)
    extracted_text_bytes: int = Field(ge=0)
    link_count: int = Field(ge=0)
    timeout_seconds: float = Field(gt=0.0)


class BrowserNavigationReceipt(SentinelModel):
    id: str = ""
    mission_id: str
    requested_url: str
    final_url: str
    redirect_chain: list[str]
    domain_allowlist_proof: bool
    scheme_proof: bool
    action_type: str
    authority_ref: str
    allowed_domains: list[str]
    allowed_schemes: list[str]
    source_binding_refs: list[str]
    timeout_cost_trace: BrowserNavigationCostTrace
    compact_summary: dict[str, Any]
    page_content_hash: str
    extracted_link_candidate_refs: list[str]
    evidence_refs: list[str]
    trace_refs: list[str]
    normal_navigation_allowed: bool = True
    sandbox_inspection_allowed: bool = False
    proposal_only: bool = False
    black_lane_blocked: bool = False
    raw_page_included: bool = False
    untrusted_page_instructions_included: bool = False
    secrets_included: bool = False
    kill_switch_triggered: bool = False
    authority_expansion: bool = False
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _validate(self) -> BrowserNavigationReceipt:
        missing = sorted(REQUIRED_BROWSER_L6_BINDING_REFS - set(self.source_binding_refs))
        if missing:
            raise ValueError(f"BrowserNavigationReceipt missing source binding refs:{missing}")
        if not self.evidence_refs:
            raise ValueError("BrowserNavigationReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("BrowserNavigationReceipt requires trace refs.")
        if self.authority_expansion:
            raise ValueError("BrowserNavigationReceipt cannot expand authority.")
        if self.raw_page_included:
            raise ValueError("BrowserNavigationReceipt cannot include raw page dump.")
        if self.untrusted_page_instructions_included:
            raise ValueError("BrowserNavigationReceipt cannot include untrusted page instructions.")
        if self.secrets_included:
            raise ValueError("BrowserNavigationReceipt cannot include secrets.")
        if not self.receipt_hash:
            self.receipt_hash = self.expected_hash()
        elif self.receipt_hash != self.expected_hash():
            raise ValueError("BrowserNavigationReceipt hash mismatch.")
        if not self.id:
            self.id = f"bnav_{self.receipt_hash[:24]}"
        return self

    def expected_hash(self) -> str:
        return _stable_hash(
            {
                "mission_id": self.mission_id,
                "requested_url": self.requested_url,
                "final_url": self.final_url,
                "redirect_chain": self.redirect_chain,
                "domain_allowlist_proof": self.domain_allowlist_proof,
                "scheme_proof": self.scheme_proof,
                "action_type": self.action_type,
                "authority_ref": self.authority_ref,
                "allowed_domains": self.allowed_domains,
                "allowed_schemes": self.allowed_schemes,
                "source_binding_refs": self.source_binding_refs,
                "timeout_cost_trace": self.timeout_cost_trace.model_dump(),
                "compact_summary": self.compact_summary,
                "page_content_hash": self.page_content_hash,
                "extracted_link_candidate_refs": self.extracted_link_candidate_refs,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
                "normal_navigation_allowed": self.normal_navigation_allowed,
            }
        )


class BrowserPageEvidenceCard(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bpage"))
    requested_url_hash: str
    final_url_hash: str
    title: str
    text_summary: str
    text_summary_hash: str
    link_candidate_refs: list[str]
    receipt_ref: str
    source_binding_refs: list[str]
    untrusted_context: bool = True
    raw_page_included: bool = False
    risk_flags: list[str] = Field(default_factory=lambda: ["page_content_is_untrusted"])


class BrowserNavigationDiffSummary(SentinelModel):
    requested_url_hash: str
    final_url_hash: str
    title: str
    text_length: int = Field(ge=0)
    link_count: int = Field(ge=0)


class BrowserNavigationResult(SentinelModel):
    requested_url: str
    final_url: str
    redirect_chain: list[str]
    raw_html: str
    text_summary: str
    evidence_card: BrowserPageEvidenceCard
    link_candidate_refs: list[BrowserLinkCandidateRef]
    action_candidate_refs: list[BrowserActionCandidateRef]
    receipt: BrowserNavigationReceipt
    risk_decision: BrowserRiskDecision


class BrowserFailureReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bnavfail"))
    mission_id: str
    requested_url: str
    reason: str
    route: BrowserRiskRoute
    evidence_refs: list[str]
    trace_refs: list[str]


class BrowserNavigationDecisionFrameSlice(SentinelModel):
    mission_id: str
    authority_card: dict[str, Any]
    page_evidence_card: BrowserPageEvidenceCard
    selected_tool_surface: list[str]
    link_candidate_refs: list[str]
    action_candidate_refs: list[str]
    current_blockers: list[str] = Field(default_factory=list)
    next_decision_options: list[str]
    receipt_refs: list[str]
    required_output_schema: dict[str, Any]
    raw_page_included: bool = False
    full_dom_included: bool = False
    all_links_dump_included: bool = False
    authority_expansion: bool = False

    @classmethod
    def from_result(
        cls,
        *,
        authority: BrowserNavigationAuthority,
        result: BrowserNavigationResult,
        blockers: list[str] | None = None,
    ) -> BrowserNavigationDecisionFrameSlice:
        return cls(
            mission_id=authority.mission_id,
            authority_card={
                "root_authority_id": authority.root_authority_id,
                "allowed_domains": authority.allowed_domains,
                "allowed_schemes": authority.allowed_schemes,
                "allowed_operation_classes": authority.allowed_operation_classes,
                "authority_expansion": False,
            },
            page_evidence_card=result.evidence_card,
            selected_tool_surface=[NORMAL_BROWSER_L6_ACTION],
            link_candidate_refs=[ref.id for ref in result.link_candidate_refs],
            action_candidate_refs=[ref.id for ref in result.action_candidate_refs],
            current_blockers=blockers or [],
            next_decision_options=["navigate_candidate_link", "stop_for_review", "request_authority_extension"],
            receipt_refs=[result.receipt.id],
            required_output_schema={"decision": "navigate_candidate_link|stop_for_review|request_authority_extension"},
            raw_page_included=False,
            full_dom_included=False,
            all_links_dump_included=False,
            authority_expansion=False,
        )


class BrowserSandboxDecisionFrameSlice(SentinelModel):
    mission_id: str
    suspicious_evidence_card: SuspiciousUrlEvidenceCard
    selected_tool_surface: list[str]
    receipt_refs: list[str]
    current_blockers: list[str]
    raw_payload_included: bool = False

    @classmethod
    def from_suspicious_url(
        cls,
        *,
        mission_id: str,
        suspicious_url: str,
        reason: str,
        receipt_refs: list[str],
    ) -> BrowserSandboxDecisionFrameSlice:
        return cls(
            mission_id=mission_id,
            suspicious_evidence_card=SuspiciousUrlEvidenceCard(suspicious_url_hash=_hash_text(suspicious_url), reason=reason),
            selected_tool_surface=["browser_quarantine_sandbox_inspection"],
            receipt_refs=receipt_refs,
            current_blockers=["sandbox inspection required", reason],
            raw_payload_included=False,
        )


class BrowserNavigationFinalGateDecision(SentinelModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)
    normal_navigation_allowed: bool = False
    sandbox_inspection_allowed: bool = False
    proposal_only: bool = False
    black_lane_blocked: bool = False


class BrowserNavigationFinalGate:
    def verify(self, receipt: BrowserNavigationReceipt | None) -> BrowserNavigationFinalGateDecision:
        if receipt is None:
            return BrowserNavigationFinalGateDecision(passed=False, failures=["missing receipt"])
        failures: list[str] = []
        if receipt.authority_expansion:
            failures.append("authority expansion detected")
        if not receipt.domain_allowlist_proof:
            failures.append("missing allowlisted domain proof")
        if not receipt.scheme_proof:
            failures.append("forbidden scheme")
        if not receipt.source_binding_refs or set(REQUIRED_BROWSER_L6_BINDING_REFS) - set(receipt.source_binding_refs):
            failures.append("missing source-binding refs")
        if not receipt.timeout_cost_trace or receipt.timeout_cost_trace.timeout_seconds <= 0:
            failures.append("missing timeout budget")
        if receipt.kill_switch_triggered:
            failures.append("kill switch triggered")
        if receipt.action_type != NORMAL_BROWSER_L6_ACTION:
            failures.append("forbidden browser action")
        final_decision = BrowserSchemeClassifier().classify(receipt.final_url)
        if final_decision.route != BrowserRiskRoute.NORMAL_NAVIGATION or not _domain_is_allowlisted(
            final_decision.host, receipt.allowed_domains
        ):
            failures.append("final_url outside allowlist")
        for redirect_target in receipt.redirect_chain:
            redirect_decision = BrowserSchemeClassifier().classify(redirect_target)
            if redirect_decision.route != BrowserRiskRoute.NORMAL_NAVIGATION or not _domain_is_allowlisted(
                redirect_decision.host, receipt.allowed_domains
            ):
                failures.append("redirect outside allowlist")
                break
        if receipt.proposal_only:
            failures.append("proposal only")
        if receipt.black_lane_blocked:
            failures.append("black lane blocked")
        if receipt.raw_page_included or receipt.untrusted_page_instructions_included or receipt.secrets_included:
            failures.append("unsafe receipt summary")
        if not receipt.receipt_hash or receipt.receipt_hash != receipt.expected_hash():
            failures.append("receipt hash mismatch")
        return BrowserNavigationFinalGateDecision(
            passed=not failures,
            failures=failures,
            normal_navigation_allowed=receipt.normal_navigation_allowed and not failures,
            sandbox_inspection_allowed=receipt.sandbox_inspection_allowed,
            proposal_only=receipt.proposal_only,
            black_lane_blocked=receipt.black_lane_blocked,
        )


class BrowserNavigationCapabilityScanner(SentinelModel):
    normal_navigation_surfaces: list[str] = Field(default_factory=lambda: [NORMAL_BROWSER_L6_ACTION])
    quarantine_surfaces: list[str] = Field(
        default_factory=lambda: ["file", "javascript", "data", "localhost", "private_ip", "suspicious_redirect"]
    )
    proposal_only_surfaces: list[str] = Field(
        default_factory=lambda: ["chrome", "devtools", "login", "form_submit", "upload", "download", "execute_javascript"]
    )
    black_lane_surfaces: list[str] = Field(
        default_factory=lambda: ["credential_theft", "fake_identity", "kyc_bypass", "captcha_bypass", "fraud"]
    )


class BrowserNavigationReceiptAdapter(SentinelModel):
    adapter_name: str = "browser_navigation_l6_receipt_adapter"
    required_receipt_fields: list[str] = Field(
        default_factory=lambda: [
            "requested_url",
            "final_url",
            "redirect_chain",
            "domain_allowlist_proof",
            "scheme_proof",
            "receipt_hash",
        ]
    )


class BrowserNavigationActionKernel(SentinelModel):
    allowed_operations: list[str]
    source_binding_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> BrowserNavigationActionKernel:
        missing = sorted(REQUIRED_BROWSER_L6_BINDING_REFS - set(self.source_binding_refs))
        if missing:
            raise ValueError(f"BrowserNavigationActionKernel missing source binding refs:{missing}")
        if set(self.allowed_operations) - {NORMAL_BROWSER_L6_ACTION, "browser_quarantine_sandbox_inspection"}:
            raise ValueError("BrowserNavigationActionKernel contains unsupported browser operation.")
        return self


class BrowserNavigationPreview(SentinelModel):
    requested_url_hash: str
    route: BrowserRiskRoute
    action_type: str
    preview_only: bool = True
    reason: str


class _BrowserPageParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._in_title = False
        self._ignored_depth = 0
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style", "noscript"}:
            self._ignored_depth += 1
            return
        if normalized == "title":
            self._in_title = True
        if normalized == "a":
            for key, value in attrs:
                if key.lower() == "href" and value:
                    self._current_href = value
                    self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if normalized == "title":
            self._in_title = False
        if normalized == "a" and self._current_href:
            self.links.append((self._current_href, " ".join(self._current_text).strip()))
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        stripped = data.strip()
        if not stripped:
            return
        if self._in_title:
            self.title_parts.append(stripped)
        else:
            self.text_parts.append(stripped)
        if self._current_href:
            self._current_text.append(stripped)


class BrowserNavigationAdapter:
    def __init__(
        self,
        *,
        authority: BrowserNavigationAuthority,
        budget: BrowserNavigationBudget,
        fetcher: Callable[[str], dict[str, Any] | str] | None = None,
        kill_switch: BrowserNavigationKillSwitch | None = None,
        risk_router: BrowserRiskRouter | None = None,
    ) -> None:
        self.authority = authority
        self.budget = budget
        self.fetcher = fetcher
        self.kill_switch = kill_switch
        self.risk_router = risk_router or BrowserRiskRouter()

    def navigate(
        self,
        requested_url: str,
        *,
        action_type: str = NORMAL_BROWSER_L6_ACTION,
        objective_tags: list[str] | None = None,
    ) -> BrowserNavigationResult:
        if self.kill_switch is not None and self.kill_switch.triggered:
            raise ValueError(f"browser navigation blocked by kill switch:{self.kill_switch.reason}")
        route = self.risk_router.route(url=requested_url, authority=self.authority, action_type=action_type, objective_tags=objective_tags)
        if route.route == BrowserRiskRoute.BLACK_LANE_BLOCK:
            raise ValueError(f"black lane browser objective blocked:{route.reason}")
        if route.route == BrowserRiskRoute.PROPOSAL_ONLY:
            raise ValueError(f"proposal only browser action:{route.reason}")
        if route.route != BrowserRiskRoute.NORMAL_NAVIGATION:
            if route.reason == "domain_not_allowlisted":
                raise ValueError(f"domain not allowlisted:{route.host}")
            raise ValueError(f"not normal navigation:{route.reason}")
        if not self.authority.domain_allowed(route.host):
            raise ValueError(f"domain not allowlisted:{route.host}")
        power_trace = self._verify_p0_power()
        response = self._fetch(route.normalized_url)
        final_url = _normalize_url(str(response.get("final_url") or route.normalized_url))
        redirect_chain = [_normalize_url(str(item)) for item in response.get("redirect_chain", [route.normalized_url, final_url])]
        if final_url not in redirect_chain:
            redirect_chain.append(final_url)
        self._verify_redirect_chain(redirect_chain)
        html_text = str(response.get("html", ""))
        byte_count = len(html_text.encode("utf-8"))
        max_bytes = min(self.budget.max_page_bytes, self.authority.max_page_bytes)
        if byte_count > max_bytes:
            raise ValueError("page byte budget exceeded")
        parser = _BrowserPageParser()
        parser.feed(html_text)
        extracted_text = " ".join(parser.text_parts)
        max_text_bytes = min(self.budget.max_extracted_text_bytes, self.authority.max_extracted_text_bytes)
        text_summary = sanitize_context_text(extracted_text[:max_text_bytes])
        link_limit = min(self.budget.max_links_extracted, self.authority.max_links_extracted)
        link_refs = [
            BrowserLinkCandidateRef.from_link(href=href, base_url=final_url, text=text or href, authority=self.authority)
            for href, text in parser.links[:link_limit]
        ]
        title = sanitize_context_text(" ".join(parser.title_parts))[:160]
        compact_summary = sanitize_context_payload(
            {
                "title": title,
                "text_summary_hash": _hash_text(text_summary),
                "text_length": len(text_summary),
                "link_candidate_count": len(link_refs),
                "untrusted_context": True,
            }
        )
        receipt = BrowserNavigationReceipt(
            mission_id=self.authority.mission_id,
            requested_url=route.normalized_url,
            final_url=final_url,
            redirect_chain=redirect_chain,
            domain_allowlist_proof=True,
            scheme_proof=True,
            action_type=NORMAL_BROWSER_L6_ACTION,
            authority_ref=self.authority.root_authority_id,
            allowed_domains=self.authority.allowed_domains,
            allowed_schemes=self.authority.allowed_schemes,
            source_binding_refs=self.authority.source_binding_refs,
            timeout_cost_trace=BrowserNavigationCostTrace(
                page_count=1,
                bytes_read=byte_count,
                extracted_text_bytes=len(text_summary.encode("utf-8")),
                link_count=len(link_refs),
                timeout_seconds=min(self.budget.timeout_seconds, self.authority.timeout_seconds),
            ),
            compact_summary=compact_summary,
            page_content_hash=_hash_text(html_text),
            extracted_link_candidate_refs=[ref.id for ref in link_refs],
            evidence_refs=self.authority.evidence_refs,
            trace_refs=[*self.authority.trace_refs, power_trace, "browser_navigation_l6_receipt_created"],
        )
        evidence_card = BrowserPageEvidenceCard(
            requested_url_hash=_hash_text(route.normalized_url),
            final_url_hash=_hash_text(final_url),
            title=title,
            text_summary=text_summary,
            text_summary_hash=_hash_text(text_summary),
            link_candidate_refs=[ref.id for ref in link_refs],
            receipt_ref=receipt.id,
            source_binding_refs=self.authority.source_binding_refs,
        )
        return BrowserNavigationResult(
            requested_url=route.normalized_url,
            final_url=final_url,
            redirect_chain=redirect_chain,
            raw_html=html_text,
            text_summary=text_summary,
            evidence_card=evidence_card,
            link_candidate_refs=link_refs,
            action_candidate_refs=[],
            receipt=receipt,
            risk_decision=route,
        )

    def _fetch(self, normalized_url: str) -> dict[str, Any]:
        if self.fetcher is not None:
            response = self.fetcher(normalized_url)
            if isinstance(response, str):
                return {"requested_url": normalized_url, "final_url": normalized_url, "redirect_chain": [normalized_url], "html": response}
            return response
        reader = RealityBrowserReader(
            allowed_domains=self.authority.allowed_domains,
            timeout_seconds=min(self.budget.timeout_seconds, self.authority.timeout_seconds),
        )
        html_text = reader._fetch(normalized_url)  # Reuse the locked P6M public read fetch path without exposing mutation.
        return {"requested_url": normalized_url, "final_url": normalized_url, "redirect_chain": [normalized_url], "html": html_text}

    def _verify_redirect_chain(self, redirect_chain: list[str]) -> None:
        for target in redirect_chain:
            decision = self.risk_router.route(url=target, authority=self.authority)
            if decision.route != BrowserRiskRoute.NORMAL_NAVIGATION or not self.authority.domain_allowed(decision.host):
                raise ValueError(f"redirect outside allowlist:{target}")

    def _verify_p0_power(self) -> str:
        organ_authority = OrganAuthorityEnvelope(
            mission_id=self.authority.mission_id,
            root_authority_id=self.authority.root_authority_id,
            organ_id="browser_navigation_l6",
            organ_name="browser_power_governor",
            allowed_actions=["browser_read_public_page"],
            allowed_domains=self.authority.allowed_domains,
            max_actions=1,
            execution_authorized=True,
            dry_run_only=False,
            trace_refs=self.authority.trace_refs,
        )
        decision = BrowserPowerGovernor().govern(
            BrowserPowerRequest(
                action="browser_read_public_page",
                requested_power=BrowserPowerLevel.P0_NORMAL_RELIABILITY,
                evidence_refs=self.authority.evidence_refs,
                trace_refs=self.authority.trace_refs,
            ),
            organ_authority,
        )
        if not decision.allowed:
            raise ValueError(f"browser power governor rejected navigation:{decision.reasons}")
        return "browser_power_governor_allowed_p0"
