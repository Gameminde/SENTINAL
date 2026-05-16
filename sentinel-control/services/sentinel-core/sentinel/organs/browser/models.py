from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from sentinel.shared.models import SentinelModel, new_id


class PublicUrlDecisionStatus(StrEnum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"


class PublicUrlPolicy(SentinelModel):
    """Read-only browser URL policy. This is not a fetch or navigation grant."""

    allowed_schemes: list[str] = Field(default_factory=lambda: ["https"])
    allowed_domains: list[str] = Field(default_factory=list)
    max_redirects: int = Field(default=3, ge=0, le=10)
    require_dns_resolution: bool = True


class PublicUrlDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("url"))
    status: PublicUrlDecisionStatus
    reason: str
    original_url: str
    normalized_url: str | None = None
    final_url: str | None = None
    host: str | None = None
    resolved_addresses: list[str] = Field(default_factory=list)
    redirect_chain: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.status == PublicUrlDecisionStatus.ALLOWED


class BrowserEvidenceFetchRequest(SentinelModel):
    """Contract for a future read-only evidence fetch. It performs no IO."""

    id: str = Field(default_factory=lambda: new_id("breq"))
    mission_id: str
    url: str
    purpose: str
    allowed_domains: list[str] = Field(default_factory=list)
    max_redirects: int = Field(default=3, ge=0, le=10)
    max_compressed_bytes: int = Field(default=1_000_000, ge=1, le=10_000_000)
    max_bytes: int = Field(default=1_000_000, ge=1, le=10_000_000)
    max_chars: int = Field(default=100_000, ge=1, le=1_000_000)
    allowed_mime_types: list[str] = Field(default_factory=lambda: ["text/html", "text/plain", "application/xhtml+xml"])
    require_https: bool = True
    require_connection_proof: bool = False
    trace_refs: list[str] = Field(default_factory=list)


class BrowserConnectionProof(SentinelModel):
    """Policy proof that a fetch was bound to the classified public URL decision."""

    host: str
    approved_addresses: list[str] = Field(default_factory=list)
    connected_address: str | None = None
    pinned: bool = False
    redirect_chain: list[str] = Field(default_factory=list)


class BrowserEvidenceFetchReceipt(SentinelModel):
    """Receipt contract for future browser evidence artifacts."""

    id: str = Field(default_factory=lambda: new_id("brec"))
    mission_id: str
    request_id: str
    original_url: str
    final_url: str
    url_policy_trace_id: str | None = None
    evidence_item_id: str | None = None
    artifact_id: str | None = None
    artifact_sha256: str | None = None
    content_sha256: str | None = None
    content_type: str | None = None
    mime_type_allowed: bool = False
    bytes_read: int = Field(default=0, ge=0)
    compressed_bytes_read: int = Field(default=0, ge=0)
    uncompressed_bytes_read: int = Field(default=0, ge=0)
    chars_extracted: int = Field(default=0, ge=0)
    raw_chars_extracted: int = Field(default=0, ge=0)
    extraction_strategy: str | None = None
    source_quality_flags: list[str] = Field(default_factory=list)
    truncated: bool = False
    citation_char_start: int | None = None
    citation_char_end: int | None = None
    connection_proof: dict[str, Any] = Field(default_factory=dict)
    prompt_injection_flags: list[str] = Field(default_factory=list)
    citation_refs: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserEvidenceAdapterStatus(StrEnum):
    COLLECTED = "collected"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class BrowserFetchedPage(SentinelModel):
    """Page payload returned by an injected read-only fetcher."""

    final_url: str
    status_code: int = Field(ge=100, le=599)
    content_type: str = "text/html; charset=utf-8"
    body: str
    headers: dict[str, str] = Field(default_factory=dict)
    compressed_bytes_read: int | None = Field(default=None, ge=0)
    uncompressed_bytes_read: int | None = Field(default=None, ge=0)
    connection_proof: BrowserConnectionProof | None = None


class BrowserEvidenceAdapterResult(SentinelModel):
    accepted: bool
    status: BrowserEvidenceAdapterStatus
    reason: str
    request_id: str
    url_decision: PublicUrlDecision
    title: str | None = None
    extracted_text: str = ""
    links: list[str] = Field(default_factory=list)
    prompt_injection_flags: list[str] = Field(default_factory=list)
    source_quality_flags: list[str] = Field(default_factory=list)
    extraction_strategy: str | None = None
    truncated: bool = False
    citation_char_start: int | None = None
    citation_char_end: int | None = None
    evidence_item_id: str | None = None
    receipt: BrowserEvidenceFetchReceipt | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserSnapshotStatus(StrEnum):
    CAPTURED = "captured"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class BrowserRenderedSnapshotRequest(SentinelModel):
    """Request contract for a future rendered read-only browser snapshot."""

    id: str = Field(default_factory=lambda: new_id("bsreq"))
    mission_id: str
    url: str
    purpose: str
    allowed_domains: list[str] = Field(default_factory=list)
    max_redirects: int = Field(default=3, ge=0, le=10)
    max_chars: int = Field(default=100_000, ge=1, le=1_000_000)
    max_html_chars: int = Field(default=200_000, ge=1, le=2_000_000)
    max_screenshot_bytes: int = Field(default=2_000_000, ge=1, le=20_000_000)
    max_screenshot_side: int = Field(default=4_000, ge=1, le=20_000)
    max_ledger_records: int = Field(default=200, ge=1, le=2_000)
    capture_pdf: bool = False
    max_pdf_bytes: int = Field(default=10_000_000, ge=1, le=50_000_000)
    capture_element_screenshots: bool = False
    element_screenshot_ref_ids: list[str] = Field(default_factory=list)
    max_element_screenshots: int = Field(default=8, ge=0, le=32)
    max_element_screenshot_bytes: int = Field(default=1_000_000, ge=1, le=10_000_000)
    max_element_screenshot_side: int = Field(default=2_000, ge=1, le=10_000)
    require_https: bool = True
    capture_screenshot: bool = True
    trace_refs: list[str] = Field(default_factory=list)


class BrowserRoleRef(SentinelModel):
    role: str
    name: str | None = None
    nth: int | None = Field(default=None, ge=0)


class BrowserRoleSnapshotStats(SentinelModel):
    lines: int = Field(default=0, ge=0)
    chars: int = Field(default=0, ge=0)
    refs: int = Field(default=0, ge=0)
    interactive: int = Field(default=0, ge=0)


class BrowserAccessibilitySnapshot(SentinelModel):
    snapshot: str
    refs: dict[str, BrowserRoleRef] = Field(default_factory=dict)
    stats: BrowserRoleSnapshotStats
    snapshot_sha256: str
    page_sha256: str


class BrowserScreenshotMetadata(SentinelModel):
    content_type: str
    format: str
    bytes: int = Field(ge=0)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    max_side: int = Field(ge=1)
    max_bytes: int = Field(ge=1)
    normalized: bool = False
    original_bytes: int | None = Field(default=None, ge=0)
    original_width: int | None = Field(default=None, ge=0)
    original_height: int | None = Field(default=None, ge=0)
    normalization_strategy: str = "none"
    warnings: list[str] = Field(default_factory=list)


class BrowserPdfMetadata(SentinelModel):
    content_type: str = "application/pdf"
    bytes: int = Field(ge=0)
    max_bytes: int = Field(ge=1)
    page_count_estimate: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)


class BrowserElementScreenshotMetadata(SentinelModel):
    ref_id: str
    role: str | None = None
    name: str | None = None
    bbox: dict[str, float] = Field(default_factory=dict)
    artifact_id: str | None = None
    artifact_sha256: str | None = None
    screenshot_metadata: BrowserScreenshotMetadata


class BrowserRenderedElementScreenshot(SentinelModel):
    ref_id: str
    png: bytes
    role: str | None = None
    name: str | None = None
    bbox: dict[str, float] = Field(default_factory=dict)


class BrowserRequestRecord(SentinelModel):
    id: str
    method: str
    url: str
    resource_type: str | None = None
    timestamp: str | None = None


class BrowserResponseRecord(SentinelModel):
    request_id: str
    url: str
    status: int | None = Field(default=None, ge=100, le=599)
    ok: bool | None = None
    content_type: str | None = None
    timestamp: str | None = None


class BrowserRequestFailureRecord(SentinelModel):
    request_id: str
    url: str
    error_text: str
    resource_type: str | None = None
    timestamp: str | None = None


class BrowserConsoleRecord(SentinelModel):
    type: str
    text: str
    timestamp: str | None = None
    location: dict[str, Any] = Field(default_factory=dict)


class BrowserPageErrorRecord(SentinelModel):
    message: str
    name: str | None = None
    stack: str | None = None
    timestamp: str | None = None


class BrowserHealthMetadata(SentinelModel):
    renderer: str = "unknown"
    status: str = "unknown"
    duration_ms: int | None = Field(default=None, ge=0)
    page_url: str | None = None
    notes: list[str] = Field(default_factory=list)


class BrowserNetworkLedger(SentinelModel):
    requests: list[BrowserRequestRecord] = Field(default_factory=list)
    responses: list[BrowserResponseRecord] = Field(default_factory=list)
    failures: list[BrowserRequestFailureRecord] = Field(default_factory=list)
    console: list[BrowserConsoleRecord] = Field(default_factory=list)
    page_errors: list[BrowserPageErrorRecord] = Field(default_factory=list)
    health: BrowserHealthMetadata = Field(default_factory=BrowserHealthMetadata)
    max_records: int = Field(default=200, ge=1)
    truncated: bool = False
    original_counts: dict[str, int] = Field(default_factory=dict)
    ledger_sha256: str


class BrowserInteractionIntent(StrEnum):
    CLICK_PLAN = "click_plan"
    TYPE_PLAN = "type_plan"
    FILL_PLAN = "fill_plan"
    SELECT_PLAN = "select_plan"
    PRESS_PLAN = "press_plan"
    HOVER_PLAN = "hover_plan"
    WAIT_FOR_TEXT_PLAN = "wait_for_text_plan"
    WAIT_FOR_SELECTOR_PLAN = "wait_for_selector_plan"
    WAIT_FOR_URL_PLAN = "wait_for_url_plan"


class BrowserInteractionImpact(StrEnum):
    OBSERVATION_ONLY = "observation_only"
    LOCAL_PAGE_STATE = "local_page_state"
    LOCAL_FORM_STATE = "local_form_state"
    NAVIGATION_WAIT = "navigation_wait"


class BrowserWaitPredicate(StrEnum):
    TEXT = "text"
    SELECTOR = "selector"
    URL = "url"


class BrowserInteractionTarget(SentinelModel):
    ref: str | None = None
    role: str | None = None
    name: str | None = None
    nth: int | None = Field(default=None, ge=0)
    selector: str | None = None
    url: str | None = None


class BrowserInteractionStep(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bistep"))
    intent: BrowserInteractionIntent
    target: BrowserInteractionTarget = Field(default_factory=BrowserInteractionTarget)
    text: str | None = None
    key: str | None = None
    values: list[str] = Field(default_factory=list)
    wait_predicate: BrowserWaitPredicate | None = None
    timeout_ms: int | None = Field(default=None, ge=0, le=120_000)
    impact: BrowserInteractionImpact = BrowserInteractionImpact.OBSERVATION_ONLY
    reason: str = ""


class BrowserInteractionPlan(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("biplan"))
    mission_id: str
    final_url: str | None = None
    snapshot_sha256: str
    page_sha256: str
    steps: list[BrowserInteractionStep] = Field(default_factory=list)
    dry_run_only: bool = True
    required_ref_ids: list[str] = Field(default_factory=list)
    plan_sha256: str


class BrowserInteractionDryRunProof(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("biproof"))
    mission_id: str
    plan_id: str
    plan_sha256: str
    snapshot_sha256: str
    page_sha256: str
    dry_run_only: bool = True
    trace_refs: list[str] = Field(default_factory=list)


class BrowserInteractionDryRunStatus(StrEnum):
    PLANNED = "planned"
    REJECTED = "rejected"


class BrowserInteractionDryRunResult(SentinelModel):
    accepted: bool
    status: BrowserInteractionDryRunStatus
    reason: str
    mission_id: str
    plan: BrowserInteractionPlan | None = None
    proof: BrowserInteractionDryRunProof | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserInteractionExecutionStatus(StrEnum):
    EXECUTED = "executed"
    REJECTED = "rejected"


class BrowserInteractionExecutionRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("biexec"))
    mission_id: str
    plan: BrowserInteractionPlan
    plan_trace_event_id: str
    before_snapshot_trace_event_id: str
    final_url: str
    allowed_domains: list[str] = Field(default_factory=list)
    capture_screenshot: bool = True
    max_chars: int = Field(default=100_000, ge=1, le=1_000_000)
    max_html_chars: int = Field(default=200_000, ge=1, le=2_000_000)
    max_screenshot_bytes: int = Field(default=2_000_000, ge=1, le=20_000_000)
    max_screenshot_side: int = Field(default=4_000, ge=1, le=20_000)
    max_ledger_records: int = Field(default=200, ge=1, le=2_000)
    timeout_ms: int = Field(default=15_000, ge=1, le=120_000)


class BrowserInteractionBackendResult(SentinelModel):
    before_snapshot: BrowserAccessibilitySnapshot
    after_page: "BrowserRenderedPage"
    final_url_before: str
    final_url_after: str
    executed_step_ids: list[str] = Field(default_factory=list)


class BrowserInteractionExecutionReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bierec"))
    mission_id: str
    request_id: str
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
    executed_step_ids: list[str] = Field(default_factory=list)
    executed_intents: list[str] = Field(default_factory=list)
    executed_ref_ids: list[str] = Field(default_factory=list)
    after_snapshot_artifact_id: str | None = None
    after_snapshot_artifact_sha256: str | None = None
    after_screenshot_artifact_id: str | None = None
    after_screenshot_artifact_sha256: str | None = None
    network_ledger_sha256: str | None = None
    browser_health: dict[str, Any] = Field(default_factory=dict)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserInteractionExecutionResult(SentinelModel):
    accepted: bool
    status: BrowserInteractionExecutionStatus
    reason: str
    request_id: str
    plan_id: str | None = None
    plan_sha256: str | None = None
    receipt: BrowserInteractionExecutionReceipt | None = None
    trace_event_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BrowserPublicLifecycleStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    REJECTED = "rejected"


class BrowserPublicSession(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bpsess"))
    mission_id: str
    purpose: str
    stateless_public: bool = True
    cookies_enabled: bool = False
    storage_enabled: bool = False
    max_tabs: int = Field(default=8, ge=1, le=32)
    status: BrowserPublicLifecycleStatus = BrowserPublicLifecycleStatus.ACTIVE
    trace_refs: list[str] = Field(default_factory=list)


class BrowserPublicTab(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bptab"))
    session_id: str
    mission_id: str
    current_url: str
    opener_trace_id: str | None = None
    current_url_policy_trace_id: str | None = None
    status: BrowserPublicLifecycleStatus = BrowserPublicLifecycleStatus.ACTIVE
    navigation_count: int = Field(default=0, ge=0)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserPublicLifecycleReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bplrec"))
    mission_id: str
    action: str
    session_id: str | None = None
    tab_id: str | None = None
    final_url: str | None = None
    url_policy_trace_id: str | None = None
    stateless_public: bool = True
    cookies_enabled: bool = False
    storage_enabled: bool = False
    trace_refs: list[str] = Field(default_factory=list)


class BrowserPublicLifecycleResult(SentinelModel):
    accepted: bool
    status: BrowserPublicLifecycleStatus
    reason: str
    action: str
    mission_id: str
    session: BrowserPublicSession | None = None
    tab: BrowserPublicTab | None = None
    receipt: BrowserPublicLifecycleReceipt | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserPoolLeaseStatus(StrEnum):
    LEASED = "leased"
    RELEASED = "released"
    REJECTED = "rejected"


class BrowserHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class BrowserOperationStatus(StrEnum):
    COMPLETED = "completed"
    RETRYING = "retrying"
    FAILED = "failed"
    REJECTED = "rejected"


class BrowserPoolLease(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bpleas"))
    mission_id: str
    purpose: str
    backend_kind: str = "playwright_public"
    stateless_public: bool = True
    cookies_enabled: bool = False
    storage_enabled: bool = False
    js_enabled: bool = False
    downloads_enabled: bool = False
    max_operations: int = Field(default=10, ge=1, le=100)
    operation_count: int = Field(default=0, ge=0)
    status: BrowserPoolLeaseStatus = BrowserPoolLeaseStatus.LEASED
    trace_refs: list[str] = Field(default_factory=list)


class BrowserPoolLeaseReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bplrec"))
    mission_id: str
    lease_id: str
    action: str
    backend_kind: str = "playwright_public"
    stateless_public: bool = True
    cookies_enabled: bool = False
    storage_enabled: bool = False
    js_enabled: bool = False
    downloads_enabled: bool = False
    trace_refs: list[str] = Field(default_factory=list)


class BrowserPoolLeaseResult(SentinelModel):
    accepted: bool
    status: BrowserPoolLeaseStatus
    reason: str
    mission_id: str
    lease: BrowserPoolLease | None = None
    receipt: BrowserPoolLeaseReceipt | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserHealthCheck(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bhchk"))
    mission_id: str
    lease_id: str | None = None
    status: BrowserHealthStatus
    backend_kind: str = "playwright_public"
    latency_ms: int | None = Field(default=None, ge=0)
    consecutive_failures: int = Field(default=0, ge=0)
    notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserRetryPolicy(SentinelModel):
    max_attempts: int = Field(default=2, ge=1, le=5)
    retryable_reasons: list[str] = Field(
        default_factory=lambda: [
            "browser_render_timeout",
            "browser_transient_error",
            "browser_backend_unavailable",
            "browser_interaction_timeout",
            "browser_render_failed",
        ]
    )


class BrowserOperationAttempt(SentinelModel):
    attempt_number: int = Field(ge=1)
    reason: str
    retryable: bool = False
    trace_event_id: str | None = None


class BrowserSupervisedOperationResult(SentinelModel):
    accepted: bool
    status: BrowserOperationStatus
    mission_id: str
    operation_name: str
    reason: str = ""
    lease_id: str | None = None
    attempts: list[BrowserOperationAttempt] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserRenderedPage(SentinelModel):
    """Rendered page payload returned by an injected renderer."""

    final_url: str
    status_code: int = Field(ge=100, le=599)
    title: str | None = None
    text: str = ""
    links: list[str] = Field(default_factory=list)
    html: str = ""
    screenshot_png: bytes | None = None
    pdf_bytes: bytes | None = None
    element_screenshots: list[BrowserRenderedElementScreenshot] = Field(default_factory=list)
    content_type: str = "text/html; charset=utf-8"
    accessibility_snapshot: BrowserAccessibilitySnapshot | None = None
    network_ledger: BrowserNetworkLedger | None = None


class BrowserRenderedSnapshotReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bsrec"))
    mission_id: str
    request_id: str
    original_url: str
    final_url: str
    url_policy_trace_id: str | None = None
    snapshot_artifact_id: str | None = None
    snapshot_artifact_sha256: str | None = None
    screenshot_artifact_id: str | None = None
    screenshot_artifact_sha256: str | None = None
    accessibility_snapshot_sha256: str | None = None
    accessibility_ref_count: int = Field(default=0, ge=0)
    accessibility_interactive_count: int = Field(default=0, ge=0)
    screenshot_metadata: dict[str, Any] = Field(default_factory=dict)
    pdf_artifact_id: str | None = None
    pdf_artifact_sha256: str | None = None
    pdf_metadata: dict[str, Any] = Field(default_factory=dict)
    element_screenshot_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    network_ledger_sha256: str | None = None
    network_request_count: int = Field(default=0, ge=0)
    network_response_count: int = Field(default=0, ge=0)
    network_failure_count: int = Field(default=0, ge=0)
    console_message_count: int = Field(default=0, ge=0)
    page_error_count: int = Field(default=0, ge=0)
    network_ledger_truncated: bool = False
    browser_health: dict[str, Any] = Field(default_factory=dict)
    chars_extracted: int = Field(default=0, ge=0)
    html_chars: int = Field(default=0, ge=0)
    prompt_injection_flags: list[str] = Field(default_factory=list)
    citation_refs: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserCitation(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bcit"))
    url: str
    title: str | None = None
    quote: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class BrowserRenderedSnapshotResult(SentinelModel):
    accepted: bool
    status: BrowserSnapshotStatus
    reason: str
    request_id: str
    url_decision: PublicUrlDecision
    title: str | None = None
    extracted_text: str = ""
    links: list[str] = Field(default_factory=list)
    citations: list[BrowserCitation] = Field(default_factory=list)
    accessibility_snapshot: BrowserAccessibilitySnapshot | None = None
    screenshot_metadata: BrowserScreenshotMetadata | None = None
    pdf_metadata: BrowserPdfMetadata | None = None
    element_screenshot_artifacts: list[BrowserElementScreenshotMetadata] = Field(default_factory=list)
    network_ledger: BrowserNetworkLedger | None = None
    prompt_injection_flags: list[str] = Field(default_factory=list)
    receipt: BrowserRenderedSnapshotReceipt | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserControlledCapabilityStatus(StrEnum):
    EXECUTED = "executed"
    REJECTED = "rejected"


class BrowserControlledCapabilityResult(SentinelModel):
    accepted: bool
    status: BrowserControlledCapabilityStatus
    tool_id: str
    action: str
    reason: str
    policy_status: str | None = None
    policy_trace_id: str | None = None
    browser_trace_event_id: str | None = None
    trace_event_id: str | None = None
    receipt_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
