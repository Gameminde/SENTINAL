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
    "evaluate_verified_extraction_completion_attempt",
]
