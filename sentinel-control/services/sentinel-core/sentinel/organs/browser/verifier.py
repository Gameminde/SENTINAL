from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from sentinel.organs.browser.models import BrowserInteractionExecutionReceipt, BrowserRenderedSnapshotResult
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserVerificationVerdict(StrEnum):
    ACCEPTED = "accepted"
    NEEDS_REPAIR = "needs_repair"
    INCONCLUSIVE = "inconclusive"


class BrowserVerificationResult(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bver"))
    mission_id: str
    verdict: BrowserVerificationVerdict
    reason: str
    checked_receipt_id: str | None = None
    before_snapshot_sha256: str | None = None
    after_snapshot_sha256: str | None = None
    expected_conditions: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserPostActionVerifier:
    """Checks post-action browser evidence against the certified interaction receipt."""

    def verify(
        self,
        *,
        mission_id: str,
        receipt: BrowserInteractionExecutionReceipt,
        after_snapshot: BrowserRenderedSnapshotResult,
        event_bus: EventBus,
        expected_text: str | None = None,
        expected_url: str | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserVerificationResult:
        if event_bus.mission_id != mission_id:
            raise ValueError("Browser verifier event bus mission_id must match mission_id.")
        findings: list[str] = []
        if receipt.mission_id != mission_id:
            findings.append("receipt_mission_mismatch")
        if after_snapshot.receipt is None:
            findings.append("after_snapshot_receipt_missing")
        elif after_snapshot.receipt.accessibility_snapshot_sha256 != receipt.after_snapshot_sha256:
            findings.append("after_snapshot_hash_mismatch")
        if expected_url and after_snapshot.receipt and after_snapshot.receipt.final_url != expected_url:
            findings.append("expected_url_not_observed")
        if expected_text and expected_text not in after_snapshot.extracted_text:
            findings.append("expected_text_not_observed")

        verdict = BrowserVerificationVerdict.ACCEPTED if not findings else BrowserVerificationVerdict.NEEDS_REPAIR
        reason = "browser_post_action_verified" if not findings else "browser_post_action_needs_repair"
        trace_refs = list(receipt.trace_refs)
        if after_snapshot.trace_event_id:
            trace_refs.append(after_snapshot.trace_event_id)
        result = BrowserVerificationResult(
            mission_id=mission_id,
            verdict=verdict,
            reason=reason,
            checked_receipt_id=receipt.id,
            before_snapshot_sha256=receipt.before_snapshot_sha256,
            after_snapshot_sha256=receipt.after_snapshot_sha256,
            expected_conditions=[item for item in [expected_url, expected_text] if item],
            findings=findings,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_VERIFICATION_COMPLETED,
            "Browser V2.5 verifier checked post-action evidence and receipt binding.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "verification_id": result.id,
                "verdict": result.verdict.value,
                "reason": result.reason,
                "checked_receipt_id": receipt.id,
                "before_snapshot_sha256": receipt.before_snapshot_sha256,
                "after_snapshot_sha256": receipt.after_snapshot_sha256,
                "expected_condition_count": len(result.expected_conditions),
                "findings": findings,
                "trace_ref_count": len(trace_refs),
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
            },
            trace_refs=trace_refs,
        )
        return result.model_copy(update={"trace_refs": [*trace_refs, event.id]})


class BrowserLoopDetectionResult(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bloop"))
    mission_id: str
    detected: bool
    reason: str
    repeated_count: int = Field(default=0, ge=0)
    loop_key: str | None = None
    trace_refs: list[str] = Field(default_factory=list)


class BrowserLoopDetector:
    """Detects repeated browser action/observation states before they waste budget."""

    def detect(
        self,
        *,
        mission_id: str,
        recent_state_keys: list[str],
        event_bus: EventBus | None = None,
        threshold: int = 3,
        trace_refs: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserLoopDetectionResult:
        if threshold < 2:
            raise ValueError("browser_loop_threshold_must_be_at_least_2")
        detected_key = None
        repeated_count = 0
        if recent_state_keys:
            current = recent_state_keys[-1]
            for value in reversed(recent_state_keys):
                if value != current:
                    break
                repeated_count += 1
            if repeated_count >= threshold:
                detected_key = current

        result = BrowserLoopDetectionResult(
            mission_id=mission_id,
            detected=detected_key is not None,
            reason="browser_loop_detected" if detected_key else "browser_loop_not_detected",
            repeated_count=repeated_count,
            loop_key=detected_key,
            trace_refs=list(trace_refs or []),
        )
        if event_bus is not None and result.detected:
            if event_bus.mission_id != mission_id:
                raise ValueError("Browser loop detector event bus mission_id must match mission_id.")
            event = event_bus.append(
                AgentEventType.BROWSER_LOOP_DETECTED,
                "Browser V2.5 loop detector found repeated browser state.",
                phase_before=phase,
                phase_after=phase,
                payload={
                    "loop_detection_id": result.id,
                    "reason": result.reason,
                    "repeated_count": result.repeated_count,
                    "loop_key": result.loop_key,
                    "threshold": threshold,
                    "stateless_public": True,
                    "cookies_enabled": False,
                    "storage_enabled": False,
                    "js_enabled": False,
                    "downloads_enabled": False,
                },
                trace_refs=list(trace_refs or []),
            )
            result = result.model_copy(update={"trace_refs": [*list(trace_refs or []), event.id]})
        return result
