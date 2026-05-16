from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError

from sentinel.organs.browser.models import (
    BrowserAccessibilitySnapshot,
    BrowserInteractionDryRunProof,
    BrowserInteractionDryRunResult,
    BrowserInteractionDryRunStatus,
    BrowserInteractionImpact,
    BrowserInteractionIntent,
    BrowserInteractionPlan,
    BrowserInteractionStep,
    BrowserInteractionTarget,
    BrowserWaitPredicate,
)
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import new_id


P3G_FORBIDDEN_INTERACTION_NAMES = {
    "submit",
    "post",
    "send",
    "upload",
    "download",
    "evaluate",
    "javascript",
    "js",
    "file_chooser",
    "dialog",
    "close",
    "resize",
    "drag",
}

REF_REQUIRED_INTENTS = {
    BrowserInteractionIntent.CLICK_PLAN,
    BrowserInteractionIntent.TYPE_PLAN,
    BrowserInteractionIntent.FILL_PLAN,
    BrowserInteractionIntent.SELECT_PLAN,
    BrowserInteractionIntent.HOVER_PLAN,
}


class BrowserInteractionDryRunPlanner:
    """Builds proof-bound browser interaction plans without executing them."""

    def create_plan(
        self,
        *,
        mission_id: str,
        snapshot: BrowserAccessibilitySnapshot,
        steps: Sequence[BrowserInteractionStep | dict[str, Any]],
        event_bus: EventBus,
        final_url: str | None = None,
        expected_snapshot_sha256: str | None = None,
        expected_page_sha256: str | None = None,
        snapshot_trace_id: str | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserInteractionDryRunResult:
        if event_bus.mission_id != mission_id:
            raise ValueError("Browser interaction dry-run event bus mission_id must match request mission_id.")

        if expected_snapshot_sha256 and expected_snapshot_sha256 != snapshot.snapshot_sha256:
            return self._rejected(mission_id, "stale_snapshot_hash", [f"expected_snapshot:{expected_snapshot_sha256}"])
        if expected_page_sha256 and expected_page_sha256 != snapshot.page_sha256:
            return self._rejected(mission_id, "stale_page_hash", [f"expected_page:{expected_page_sha256}"])

        canonical_steps: list[BrowserInteractionStep] = []
        errors: list[str] = []
        for index, raw_step in enumerate(steps):
            step = self._parse_step(raw_step, index, errors)
            if step is None:
                continue
            resolved = self._validate_and_resolve_step(step, snapshot, index, errors)
            if resolved is not None:
                canonical_steps.append(resolved)

        if errors:
            return self._rejected(mission_id, "interaction_plan_rejected", errors)
        if not canonical_steps:
            return self._rejected(mission_id, "interaction_plan_empty", ["no_valid_steps"])

        required_ref_ids = sorted(
            {step.target.ref for step in canonical_steps if step.target.ref}
        )
        plan_payload = {
            "id": new_id("biplan"),
            "mission_id": mission_id,
            "final_url": final_url,
            "snapshot_sha256": snapshot.snapshot_sha256,
            "page_sha256": snapshot.page_sha256,
            "steps": [step.model_dump(mode="json") for step in canonical_steps],
            "dry_run_only": True,
            "required_ref_ids": required_ref_ids,
        }
        plan_sha256 = hash_browser_interaction_plan_payload(plan_payload)
        plan = BrowserInteractionPlan(**plan_payload, plan_sha256=plan_sha256)
        trace_refs = [snapshot_trace_id] if snapshot_trace_id else []
        proof = BrowserInteractionDryRunProof(
            mission_id=mission_id,
            plan_id=plan.id,
            plan_sha256=plan.plan_sha256,
            snapshot_sha256=plan.snapshot_sha256,
            page_sha256=plan.page_sha256,
            dry_run_only=True,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_INTERACTION_PLAN_CREATED,
            "Browser interaction dry-run plan created without browser state mutation.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "proof_id": proof.id,
                "plan_id": plan.id,
                "plan_sha256": plan.plan_sha256,
                "plan": plan.model_dump(mode="json"),
                "mission_id": mission_id,
                "final_url": final_url,
                "snapshot_sha256": plan.snapshot_sha256,
                "page_sha256": plan.page_sha256,
                "step_count": len(plan.steps),
                "required_ref_ids": required_ref_ids,
                "intents": [step.intent.value for step in plan.steps],
                "dry_run_only": True,
            },
            trace_refs=trace_refs,
        )
        proof = proof.model_copy(update={"trace_refs": [*trace_refs, event.id]})
        return BrowserInteractionDryRunResult(
            accepted=True,
            status=BrowserInteractionDryRunStatus.PLANNED,
            reason="interaction_plan_created",
            mission_id=mission_id,
            plan=plan,
            proof=proof,
            trace_event_id=event.id,
        )

    @staticmethod
    def _parse_step(
        raw_step: BrowserInteractionStep | dict[str, Any],
        index: int,
        errors: list[str],
    ) -> BrowserInteractionStep | None:
        if isinstance(raw_step, BrowserInteractionStep):
            candidate = raw_step
        else:
            intent_raw = str(raw_step.get("intent", "")).strip().lower() if isinstance(raw_step, dict) else ""
            if _contains_forbidden_intent_token(intent_raw):
                errors.append(f"forbidden_interaction_intent_{index}:{intent_raw}")
                return None
            try:
                candidate = BrowserInteractionStep(**raw_step)
            except (TypeError, ValidationError) as exc:
                errors.append(f"invalid_interaction_step_{index}:{_compact_error(exc)}")
                return None
        if _contains_forbidden_intent_token(candidate.intent.value):
            errors.append(f"forbidden_interaction_intent_{index}:{candidate.intent.value}")
            return None
        return candidate

    @staticmethod
    def _validate_and_resolve_step(
        step: BrowserInteractionStep,
        snapshot: BrowserAccessibilitySnapshot,
        index: int,
        errors: list[str],
    ) -> BrowserInteractionStep | None:
        target = step.target
        if step.intent in REF_REQUIRED_INTENTS:
            if not target.ref:
                errors.append(f"missing_ref_{index}")
                return None
            ref = snapshot.refs.get(target.ref)
            if ref is None:
                errors.append(f"unknown_ref_{index}:{target.ref}")
                return None
            target = BrowserInteractionTarget(
                ref=target.ref,
                role=ref.role,
                name=ref.name,
                nth=ref.nth,
                selector=target.selector,
                url=target.url,
            )
        if step.intent in {BrowserInteractionIntent.TYPE_PLAN, BrowserInteractionIntent.FILL_PLAN} and step.text is None:
            errors.append(f"missing_text_{index}")
            return None
        if step.intent == BrowserInteractionIntent.SELECT_PLAN and not step.values:
            errors.append(f"missing_values_{index}")
            return None
        if step.intent == BrowserInteractionIntent.PRESS_PLAN and not step.key:
            errors.append(f"missing_key_{index}")
            return None
        if step.intent == BrowserInteractionIntent.WAIT_FOR_TEXT_PLAN and not step.text:
            errors.append(f"missing_wait_text_{index}")
            return None
        if step.intent == BrowserInteractionIntent.WAIT_FOR_SELECTOR_PLAN and not target.selector:
            errors.append(f"missing_wait_selector_{index}")
            return None
        if step.intent == BrowserInteractionIntent.WAIT_FOR_URL_PLAN and not target.url:
            errors.append(f"missing_wait_url_{index}")
            return None
        return step.model_copy(update={"target": target, "impact": _impact_for_intent(step.intent)})

    @staticmethod
    def _rejected(mission_id: str, reason: str, errors: list[str]) -> BrowserInteractionDryRunResult:
        return BrowserInteractionDryRunResult(
            accepted=False,
            status=BrowserInteractionDryRunStatus.REJECTED,
            reason=reason,
            mission_id=mission_id,
            errors=errors,
        )


def hash_browser_interaction_plan_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_browser_interaction_plan_hash(plan: dict[str, Any], expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    payload = {key: value for key, value in plan.items() if key != "plan_sha256"}
    return hash_browser_interaction_plan_payload(payload) == expected_hash


def _impact_for_intent(intent: BrowserInteractionIntent) -> BrowserInteractionImpact:
    if intent in {BrowserInteractionIntent.TYPE_PLAN, BrowserInteractionIntent.FILL_PLAN, BrowserInteractionIntent.SELECT_PLAN}:
        return BrowserInteractionImpact.LOCAL_FORM_STATE
    if intent in {BrowserInteractionIntent.CLICK_PLAN, BrowserInteractionIntent.PRESS_PLAN, BrowserInteractionIntent.HOVER_PLAN}:
        return BrowserInteractionImpact.LOCAL_PAGE_STATE
    if intent == BrowserInteractionIntent.WAIT_FOR_URL_PLAN:
        return BrowserInteractionImpact.NAVIGATION_WAIT
    return BrowserInteractionImpact.OBSERVATION_ONLY


def _compact_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:300]


def _contains_forbidden_intent_token(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in P3G_FORBIDDEN_INTERACTION_NAMES or any(
        token in normalized for token in P3G_FORBIDDEN_INTERACTION_NAMES
    )
