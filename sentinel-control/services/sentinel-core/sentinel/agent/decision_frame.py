from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field

from sentinel.agent.evidence_ranker import EvidenceCard, sanitize_context_text
from sentinel.agent.prompt_budget import PromptBudgetAllocator
from sentinel.shared.models import SentinelModel, new_id


def _stable_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DecisionFrameHash(SentinelModel):
    value: str


class LLMDecisionFrame(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("llmframe"))
    mission_id: str
    mission_card: dict[str, Any]
    authority_card: dict[str, Any]
    progress_card: dict[str, Any]
    top_k_evidence: list[EvidenceCard]
    selected_tool_surface: list[str]
    current_blockers: list[str]
    next_decision_options: list[str]
    required_output_schema: dict[str, Any]
    receipt_refs: list[str]
    token_count: int = Field(ge=0)
    user_selected_model: str
    frame_hash: str
    raw_receipts_included: bool = False
    authority_expansion: bool = False
    prompt_budget_respected: bool = True
    deterministic_frame_hash: bool = True
    raw_secret_leakage: bool = False

    @classmethod
    def build(
        cls,
        *,
        mission_id: str,
        mission_card: dict[str, Any],
        authority_card: dict[str, Any],
        progress_card: dict[str, Any],
        evidence: list[EvidenceCard],
        selected_tool_surface: list[str],
        current_blockers: list[str],
        next_decision_options: list[str],
        required_output_schema: dict[str, Any],
        budget_allocator: PromptBudgetAllocator,
    ) -> LLMDecisionFrame:
        evidence_cards = [card.model_copy(update={"summary": sanitize_context_text(card.summary)}) for card in evidence]
        receipt_refs = sorted({card.receipt_id for card in evidence_cards})
        selected_tools = sorted(set(selected_tool_surface))
        payload = {
            "mission_id": mission_id,
            "mission_card": mission_card,
            "authority_card": authority_card,
            "progress_card": progress_card,
            "top_k_evidence": [card.model_dump(exclude={"id"}) for card in evidence_cards],
            "selected_tool_surface": selected_tools,
            "current_blockers": current_blockers,
            "next_decision_options": next_decision_options,
            "required_output_schema": required_output_schema,
            "receipt_refs": receipt_refs,
        }
        rendered = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        token_count = budget_allocator.estimate_frame_tokens(rendered)
        frame_hash = _stable_hash(payload)
        return cls(
            mission_id=mission_id,
            mission_card=mission_card,
            authority_card=authority_card,
            progress_card=progress_card,
            top_k_evidence=evidence_cards,
            selected_tool_surface=selected_tools,
            current_blockers=current_blockers,
            next_decision_options=next_decision_options,
            required_output_schema=required_output_schema,
            receipt_refs=receipt_refs,
            token_count=token_count,
            user_selected_model=budget_allocator.user_model.selected_model,
            frame_hash=frame_hash,
            prompt_budget_respected=budget_allocator.within_budget(token_count),
            deterministic_frame_hash=True,
            raw_secret_leakage="[REDACTED_SECRET]" not in rendered and "sk-" in rendered,
        )

    def all_evidence_refs(self) -> list[str]:
        refs: set[str] = set()
        for card in self.top_k_evidence:
            refs.update(card.evidence_refs)
        return sorted(refs)

    def render_prompt_text(self) -> str:
        payload = {
            "mission_card": self.mission_card,
            "authority_card": self.authority_card,
            "progress_card": self.progress_card,
            "top_k_evidence": [card.model_dump(exclude={"id", "token_count"}) for card in self.top_k_evidence],
            "selected_tool_surface": self.selected_tool_surface,
            "current_blockers": self.current_blockers,
            "next_decision_options": self.next_decision_options,
            "required_output_schema": self.required_output_schema,
            "receipt_refs": self.receipt_refs,
        }
        return sanitize_context_text(json.dumps(payload, sort_keys=True, ensure_ascii=True))


class DecisionFrameVerificationResult(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("dfverify"))
    passed: bool
    failures: list[str] = Field(default_factory=list)
    authority_preserved: bool
    critical_evidence_preserved: bool
    tool_surface_minimized: bool
    receipt_refs_resolvable: bool
    deterministic_frame_hash: bool
    prompt_budget_respected: bool
    raw_secret_leakage: bool
    authority_expansion: bool


class DecisionFrameVerifier:
    def __init__(self, *, required_evidence_refs: list[str] | None = None) -> None:
        self.required_evidence_refs = required_evidence_refs or []

    def verify(self, frame: LLMDecisionFrame) -> DecisionFrameVerificationResult:
        failures: list[str] = []
        evidence_refs = set(frame.all_evidence_refs())
        for ref in self.required_evidence_refs:
            if ref not in evidence_refs:
                failures.append(f"missing critical evidence ref: {ref}")
        if not frame.authority_card:
            failures.append("authority card missing")
        if frame.authority_expansion:
            failures.append("authority expansion detected")
        if frame.raw_secret_leakage:
            failures.append("raw secret leakage detected")
        if not frame.prompt_budget_respected:
            failures.append("prompt budget exceeded")
        return DecisionFrameVerificationResult(
            passed=not failures,
            failures=failures,
            authority_preserved=bool(frame.authority_card) and not frame.authority_expansion,
            critical_evidence_preserved=not any(failure.startswith("missing critical evidence ref") for failure in failures),
            tool_surface_minimized=len(frame.selected_tool_surface) <= 5,
            receipt_refs_resolvable=bool(frame.receipt_refs),
            deterministic_frame_hash=frame.deterministic_frame_hash and bool(frame.frame_hash),
            prompt_budget_respected=frame.prompt_budget_respected,
            raw_secret_leakage=frame.raw_secret_leakage,
            authority_expansion=frame.authority_expansion,
        )
