from __future__ import annotations

from pydantic import Field

from sentinel.shared.models import SentinelModel


class VerifiedExtractionCompletionAttemptMetrics(SentinelModel):
    extract_product_cards_count: int = 0
    verify_extraction_count: int = 0
    summarize_evidence_count: int = 0
    summary_present: bool = False
    finish_present: bool = False
    mission_status: str = ""
    replay_no_react: bool = False
    high_risk_scan_clean: bool = False
    search_or_navigation_evidence: bool = False


class AttemptEvaluationVerdict(SentinelModel):
    verdict: str
    accepted: bool
    required_fields: tuple[str, ...] = Field(default_factory=tuple)
    failed_fields: tuple[str, ...] = Field(default_factory=tuple)
    ignored_legacy_fields: tuple[str, ...] = Field(default_factory=tuple)


def browser_receipts_backend_match(
    receipts: tuple[dict[str, object], ...] | list[dict[str, object]],
    *,
    expected_backend_id: str,
    expected_session_backend_kind: str = "cloakbrowser",
) -> bool:
    """Evaluate backend truth from receipts that actually carry backend fields.

    Open/world-model receipts can predate backend truth fields; they should not
    be counted as Cloak failures when later material browser action receipts
    prove selected/actual backend agreement.
    """

    material_backend_receipts = [
        receipt
        for receipt in receipts
        if receipt.get("selected_backend_id") is not None or receipt.get("actual_backend_id") is not None
    ]
    if not material_backend_receipts:
        return False
    return all(
        receipt.get("selected_backend_id") == expected_backend_id
        and receipt.get("actual_backend_id") == expected_backend_id
        and str(receipt.get("session_backend_kind") or "").lower() == expected_session_backend_kind.lower()
        for receipt in material_backend_receipts
    )


def evaluate_verified_extraction_completion_attempt(
    metrics: VerifiedExtractionCompletionAttemptMetrics,
) -> AttemptEvaluationVerdict:
    """Evaluate 5H-style completion-lane proof without stale search criteria."""

    required = (
        "extract_product_cards_count",
        "verify_extraction_count",
        "summarize_evidence_count_or_summary_present",
        "finish_present",
        "mission_status_completed",
        "replay_no_react",
        "high_risk_scan_clean",
    )
    failed: list[str] = []
    if metrics.extract_product_cards_count < 1:
        failed.append("extract_product_cards_count")
    if metrics.verify_extraction_count < 1:
        failed.append("verify_extraction_count")
    if metrics.summarize_evidence_count < 1 and not metrics.summary_present:
        failed.append("summarize_evidence_count_or_summary_present")
    if not metrics.finish_present:
        failed.append("finish_present")
    if metrics.mission_status != "completed":
        failed.append("mission_status_completed")
    if not metrics.replay_no_react:
        failed.append("replay_no_react")
    if not metrics.high_risk_scan_clean:
        failed.append("high_risk_scan_clean")
    accepted = not failed
    return AttemptEvaluationVerdict(
        verdict="VALID_SUCCESS" if accepted else "VALID_FAILED",
        accepted=accepted,
        required_fields=required,
        failed_fields=tuple(failed),
        ignored_legacy_fields=("search_or_navigation_evidence",),
    )


__all__ = [
    "AttemptEvaluationVerdict",
    "VerifiedExtractionCompletionAttemptMetrics",
    "browser_receipts_backend_match",
    "evaluate_verified_extraction_completion_attempt",
]
