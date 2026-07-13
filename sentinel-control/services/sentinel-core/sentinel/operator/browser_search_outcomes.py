from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel


class BrowserSearchOutcomeKind(StrEnum):
    MATERIAL_RESULTS = "MATERIAL_RESULTS"
    NO_RESULTS_CONFIRMED = "NO_RESULTS_CONFIRMED"
    MATERIAL_UNCERTAIN = "MATERIAL_UNCERTAIN"
    ACTUATION_FAILED_RECOVERABLE = "ACTUATION_FAILED_RECOVERABLE"
    BLOCKED_BY_REAL_BOUNDARY = "BLOCKED_BY_REAL_BOUNDARY"


class BrowserSearchOutcome(SentinelModel):
    outcome_kind: BrowserSearchOutcomeKind
    confidence: float
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    query_hash: str
    pre_state_hash: str
    post_state_hash: str
    materiality_signals: dict[str, Any] = Field(default_factory=dict)
    uncertainty_reason: str = ""
    search_materially_successful: bool = False

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def derive_browser_search_outcome(
    *,
    input_written: bool,
    submission_attempted: bool,
    request_observed: bool,
    query_reflected: bool,
    result_region_changed: bool,
    before_result_region_count: int,
    after_result_region_count: int,
    query_hash: str,
    pre_state_hash: str,
    post_state_hash: str,
    empty_result_evidence: bool = False,
    blocked_by_real_boundary: bool = False,
    actuation_failed: bool = False,
    evidence_refs: tuple[str, ...] = (),
) -> BrowserSearchOutcome:
    submitted = bool(input_written and submission_attempted and query_reflected)
    material_signal = bool(request_observed or result_region_changed or after_result_region_count > before_result_region_count)
    signals = {
        "input_written": bool(input_written),
        "submission_attempted": bool(submission_attempted),
        "request_observed": bool(request_observed),
        "query_reflected": bool(query_reflected),
        "result_region_changed": bool(result_region_changed),
        "before_result_region_count": int(before_result_region_count),
        "after_result_region_count": int(after_result_region_count),
        "empty_result_evidence": bool(empty_result_evidence),
    }
    refs = tuple(evidence_refs) or (f"search_outcome:{stable_hash(signals)}",)
    if blocked_by_real_boundary:
        return BrowserSearchOutcome(
            outcome_kind=BrowserSearchOutcomeKind.BLOCKED_BY_REAL_BOUNDARY,
            confidence=0.95,
            evidence_refs=refs,
            query_hash=query_hash,
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
            materiality_signals=signals,
            uncertainty_reason="search crossed a real browser boundary",
            search_materially_successful=False,
        )
    if actuation_failed:
        return BrowserSearchOutcome(
            outcome_kind=BrowserSearchOutcomeKind.ACTUATION_FAILED_RECOVERABLE,
            confidence=0.7,
            evidence_refs=refs,
            query_hash=query_hash,
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
            materiality_signals=signals,
            uncertainty_reason="search actuation failed inside granted browser scope and should recover",
            search_materially_successful=False,
        )
    if submitted and after_result_region_count > 0 and material_signal:
        return BrowserSearchOutcome(
            outcome_kind=BrowserSearchOutcomeKind.MATERIAL_RESULTS,
            confidence=0.92,
            evidence_refs=refs,
            query_hash=query_hash,
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
            materiality_signals=signals,
            uncertainty_reason="material result-region evidence is bound to submitted query",
            search_materially_successful=True,
        )
    if submitted and request_observed and empty_result_evidence and after_result_region_count == 0:
        return BrowserSearchOutcome(
            outcome_kind=BrowserSearchOutcomeKind.NO_RESULTS_CONFIRMED,
            confidence=0.82,
            evidence_refs=refs,
            query_hash=query_hash,
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
            materiality_signals=signals,
            uncertainty_reason="submitted query has request evidence and stabilized empty-result evidence",
            search_materially_successful=True,
        )
    return BrowserSearchOutcome(
        outcome_kind=BrowserSearchOutcomeKind.MATERIAL_UNCERTAIN,
        confidence=0.46 if submitted else 0.28,
        evidence_refs=refs,
        query_hash=query_hash,
        pre_state_hash=pre_state_hash,
        post_state_hash=post_state_hash,
        materiality_signals=signals,
        uncertainty_reason="zero cards alone is not confirmed no-results evidence",
        search_materially_successful=False,
    )


__all__ = [
    "BrowserSearchOutcome",
    "BrowserSearchOutcomeKind",
    "derive_browser_search_outcome",
]
