from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

from sentinel.agent.events import AgentEventType
from sentinel.agent.phases import AgentPhase
from sentinel.shared.models import SentinelModel, new_id

if TYPE_CHECKING:
    from sentinel.agent.event_bus import EventBus
    from sentinel.agent.models import AgentContext, AgentEvent
    from sentinel.mission.models import MissionAuthorityEnvelope


CONTEXT_PACK_SCHEMA_VERSION = "1.0.0"
CONTEXT_PACK_ID_RE = re.compile(r"^cpk_[A-Za-z0-9_-]{8,96}$")
MAX_EVIDENCE_SUMMARY_CHARS = 800
MAX_CITATION_EXCERPT_CHARS = 1_200


def utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_context_pack_payload(payload: dict[str, Any]) -> str:
    stable_payload = dict(payload)
    stable_payload.pop("context_pack_sha256", None)
    return _canonical_hash(stable_payload)


_CONTEXT_SECRET_KEY_MARKERS = {
    "api_key",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "credential",
    "credential_value",
    "password",
    "secret",
    "session_token",
    "token",
}

_CONTEXT_SECRET_VALUE_RE = re.compile(
    r"(Bearer\s+[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9_\-]{8,}|gsk_[A-Za-z0-9_\-]{8,}|"
    r"[A-Z0-9_]*(API_KEY|TOKEN|SECRET|PASSWORD|COOKIE|SESSION)[A-Z0-9_]*\s*=\s*\S+)",
    re.IGNORECASE,
)


class ContextSecretSweepResult(SentinelModel):
    accepted: bool
    findings: list[str] = Field(default_factory=list)
    sanitized_payload: Any = None
    data_not_instruction: bool = True


def sweep_context_payload_for_secrets(payload: Any) -> ContextSecretSweepResult:
    sanitized, findings = _sweep_context_secret_value(payload, "$", secret_key=False)
    return ContextSecretSweepResult(
        accepted=not findings,
        findings=sorted(set(findings)),
        sanitized_payload=sanitized,
    )


def _sweep_context_secret_value(value: Any, path: str, *, secret_key: bool) -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        findings: list[str] = []
        for key, item in value.items():
            key_text = str(key).lower()
            child_secret_key = secret_key or key_text in _CONTEXT_SECRET_KEY_MARKERS
            child, child_findings = _sweep_context_secret_value(
                item,
                f"{path}.{key}" if path else str(key),
                secret_key=child_secret_key,
            )
            sanitized[key] = child
            findings.extend(child_findings)
        return sanitized, findings
    if isinstance(value, list):
        sanitized_items: list[Any] = []
        findings: list[str] = []
        for index, item in enumerate(value):
            child, child_findings = _sweep_context_secret_value(item, f"{path}[{index}]", secret_key=secret_key)
            sanitized_items.append(child)
            findings.extend(child_findings)
        return sanitized_items, findings
    if isinstance(value, tuple):
        child, findings = _sweep_context_secret_value(list(value), path, secret_key=secret_key)
        return tuple(child), findings
    if isinstance(value, str):
        if secret_key or _CONTEXT_SECRET_VALUE_RE.search(value):
            return "[REDACTED]", [path]
    return value, []


class ContextPackAutonomy(StrEnum):
    RECOMMEND = "recommend"
    EXECUTE = "execute"
    SUPERVISED = "supervised"


class ContextPackHypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_EVIDENCE = "needs_evidence"


class ContextPackSupportLevel(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    CONTEXT = "context"


class ContextPackInjectionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContextPackAuthorityBoundary(SentinelModel):
    autonomy: ContextPackAutonomy = ContextPackAutonomy.RECOMMEND
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    escalation_policy: dict[str, Any] = Field(default_factory=dict)


class ContextPackCurrentState(SentinelModel):
    phase: str = "unknown"
    last_action_intent_id: str | None = None
    unresolved_count: int = Field(default=0, ge=0)
    facts: dict[str, Any] = Field(default_factory=dict)


class ContextPackHypothesis(SentinelModel):
    id: str
    statement: str
    status: ContextPackHypothesisStatus = ContextPackHypothesisStatus.PROPOSED
    confidence: float = Field(ge=0.0, le=1.0)
    citation_ids: list[str] = Field(default_factory=list)
    contradiction_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ContextPackBrowserEvidenceSummary(SentinelModel):
    source_id: str
    summary: str = Field(max_length=MAX_EVIDENCE_SUMMARY_CHARS)
    summary_hash: str
    summary_method: str = "extractive"
    stable_ref_ids: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)


class ContextPackCitation(SentinelModel):
    id: str
    source_id: str
    stable_ref_id: str
    support_level: ContextPackSupportLevel = ContextPackSupportLevel.PARTIAL
    excerpt: str = Field(default="", max_length=MAX_CITATION_EXCERPT_CHARS)
    digest: str = ""
    trace_refs: list[str] = Field(default_factory=list)


class ContextPackSourceQualityFlag(SentinelModel):
    source_id: str
    flags: list[str] = Field(default_factory=list)
    derived_score: float = Field(ge=0.0, le=1.0)
    conflict_flag: bool = False


class ContextPackPromptInjectionFlag(SentinelModel):
    source_id: str
    risk: ContextPackInjectionRisk = ContextPackInjectionRisk.LOW
    indicators: list[str] = Field(default_factory=list)
    blocked: bool = False
    sanitized: bool = False


class ContextPackStableRef(SentinelModel):
    id: str
    kind: str = "browser_ref"
    source_id: str
    selector: str
    digest: str
    archive_ref: str | None = None
    page_sha256: str | None = None
    snapshot_sha256: str | None = None
    trace_refs: list[str] = Field(default_factory=list)


class ContextPackActionIntent(SentinelModel):
    id: str
    kind: str
    impact: str = "observation"
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    authorization_conditions: list[str] = Field(default_factory=list)


class ContextPackNetworkDiagnostics(SentinelModel):
    request_count: int = Field(default=0, ge=0)
    redirect_count: int = Field(default=0, ge=0)
    bytes_fetched: int = Field(default=0, ge=0)
    trace_root_hash: str | None = None
    capture_mode: str = "browser_v2"


class ContextPackOpenQuestion(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("cpq"))
    text: str
    blocking: bool = False
    suggested_next_action_intent_id: str | None = None


class ContextPackBudget(SentinelModel):
    token_budget: int = Field(default=8_000, ge=0)
    remaining_token_budget: int = Field(default=8_000, ge=0)
    max_browser_steps: int = Field(default=0, ge=0)
    max_wall_clock_ms: int = Field(default=0, ge=0)
    cost_ceiling_usd: float = Field(default=0.0, ge=0.0)


class ContextPack(SentinelModel):
    schema_version: str = CONTEXT_PACK_SCHEMA_VERSION
    context_pack_id: str = Field(default_factory=lambda: new_id("cpk"))
    context_pack_sha256: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    mission_id: str
    mission_goal: str
    authority_boundary: ContextPackAuthorityBoundary
    current_state: ContextPackCurrentState = Field(default_factory=ContextPackCurrentState)
    verified_hypotheses: list[ContextPackHypothesis] = Field(default_factory=list)
    browser_evidence_summaries: list[ContextPackBrowserEvidenceSummary] = Field(default_factory=list)
    citations: list[ContextPackCitation] = Field(default_factory=list)
    source_quality_flags: list[ContextPackSourceQualityFlag] = Field(default_factory=list)
    prompt_injection_flags: list[ContextPackPromptInjectionFlag] = Field(default_factory=list)
    browser_stable_refs: list[ContextPackStableRef] = Field(default_factory=list)
    available_action_intents: list[ContextPackActionIntent] = Field(default_factory=list)
    network_diagnostic_metadata: ContextPackNetworkDiagnostics = Field(default_factory=ContextPackNetworkDiagnostics)
    open_questions: list[ContextPackOpenQuestion] = Field(default_factory=list)
    budget_effort_constraints: ContextPackBudget = Field(default_factory=ContextPackBudget)
    cortex_interpretation_id: str | None = None
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def compute_or_validate_hash(self) -> "ContextPack":
        if not CONTEXT_PACK_ID_RE.match(self.context_pack_id):
            raise ValueError("invalid_context_pack_id")
        payload = self.model_dump(mode="json")
        sweep = sweep_context_payload_for_secrets(payload)
        if not sweep.accepted:
            raise ValueError("context_pack_secret_like_payload")
        expected_hash = hash_context_pack_payload(payload)
        if not self.context_pack_sha256:
            object.__setattr__(self, "context_pack_sha256", expected_hash)
        elif self.context_pack_sha256 != expected_hash:
            raise ValueError("invalid_context_pack_hash")
        return self


class ContextPackValidationResult(SentinelModel):
    accepted: bool
    context_pack_id: str
    context_pack_sha256: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_event_id: str | None = None


class ContextPackAssembler:
    """Builds the LLM-facing context contract from brain and browser signals."""

    def assemble(
        self,
        context: AgentContext,
        trace: list[AgentEvent] | tuple[AgentEvent, ...],
        *,
        event_bus: EventBus | None = None,
        phase: AgentPhase = AgentPhase.CONTEXT_BUILDING,
        token_budget: int = 8_000,
    ) -> ContextPack:
        pack = ContextPack(
            mission_id=context.mission.id,
            mission_goal=context.mission.mission_objective,
            authority_boundary=ContextPackAuthorityBoundary(
                autonomy=ContextPackAutonomy.RECOMMEND,
                allowed_actions=list(context.mission.allowed_actions),
                forbidden_actions=list(context.mission.forbidden_actions),
                allowed_tools=list(context.mission.allowed_tools),
                allowed_domains=list(context.mission.allowed_domains),
                escalation_policy={"triggers": list(context.mission.escalation_triggers)},
            ),
            current_state=ContextPackCurrentState(
                phase=phase.value if hasattr(phase, "value") else str(phase),
                facts={key: value for key, value in context.user_input.items() if isinstance(key, str) and key != "tool_calls"},
            ),
            verified_hypotheses=self._hypotheses_from_input(context.user_input),
            browser_evidence_summaries=self._browser_evidence_summaries(trace),
            citations=self._citations(trace),
            source_quality_flags=self._source_quality_flags(trace),
            prompt_injection_flags=self._prompt_injection_flags(trace),
            browser_stable_refs=self._stable_refs(trace),
            available_action_intents=[
                ContextPackActionIntent(id=f"act_{index}", kind=action, parameter_schema={"type": "object"})
                for index, action in enumerate(context.mission.allowed_actions)
            ],
            network_diagnostic_metadata=self._network_diagnostics(trace),
            budget_effort_constraints=ContextPackBudget(
                token_budget=token_budget,
                remaining_token_budget=token_budget,
                max_browser_steps=context.mission.max_actions,
                max_wall_clock_ms=context.mission.max_duration_minutes * 60_000,
                cost_ceiling_usd=context.mission.max_cost_usd,
            ),
            trace_refs=[event.id for event in trace],
        )
        if event_bus is not None:
            event_bus.append(
                AgentEventType.CONTEXT_PACK_ASSEMBLED,
                "LLM ContextPack assembled from mission authority and browser evidence.",
                phase_before=phase,
                phase_after=phase,
                payload={
                    "context_pack_id": pack.context_pack_id,
                    "context_pack_sha256": pack.context_pack_sha256,
                    "summary_count": len(pack.browser_evidence_summaries),
                    "citation_count": len(pack.citations),
                    "stable_ref_count": len(pack.browser_stable_refs),
                    "available_action_intent_count": len(pack.available_action_intents),
                },
                trace_refs=pack.trace_refs,
            )
        return pack

    @staticmethod
    def _hypotheses_from_input(user_input: dict[str, Any]) -> list[ContextPackHypothesis]:
        hypotheses = user_input.get("verified_hypotheses", [])
        if not isinstance(hypotheses, list):
            return []
        result: list[ContextPackHypothesis] = []
        for index, item in enumerate(hypotheses[:64]):
            if not isinstance(item, dict):
                continue
            result.append(
                ContextPackHypothesis(
                    id=str(item.get("id") or f"hyp_{index}"),
                    statement=str(item.get("statement") or ""),
                    status=ContextPackHypothesisStatus(str(item.get("status") or "verified")),
                    confidence=float(item.get("confidence", 0.5)),
                    citation_ids=[str(value) for value in item.get("citation_ids", item.get("citationIds", []))],
                    contradiction_ids=[str(value) for value in item.get("contradiction_ids", [])],
                    evidence_refs=[str(value) for value in item.get("evidence_refs", [])],
                )
            )
        return result

    @staticmethod
    def _browser_evidence_summaries(trace: list[AgentEvent] | tuple[AgentEvent, ...]) -> list[ContextPackBrowserEvidenceSummary]:
        summaries: list[ContextPackBrowserEvidenceSummary] = []
        for index, event in enumerate(trace):
            if event.event_type not in {AgentEventType.BROWSER_EVIDENCE_COLLECTED, AgentEventType.BROWSER_SNAPSHOT_CAPTURED}:
                continue
            payload = event.payload
            source_id = str(payload.get("evidence_item_id") or payload.get("receipt_id") or event.id)
            text = str(payload.get("title") or payload.get("final_url") or event.summary)[:MAX_EVIDENCE_SUMMARY_CHARS]
            summaries.append(
                ContextPackBrowserEvidenceSummary(
                    source_id=source_id,
                    summary=text,
                    summary_hash=_canonical_hash({"source_id": source_id, "summary": text}),
                    summary_method=str(payload.get("extraction_strategy") or "event_summary"),
                    stable_ref_ids=[str(value) for value in payload.get("accessibility_ref_ids", [])],
                    trace_refs=[event.id],
                )
            )
        return summaries[:128]

    @staticmethod
    def _citations(trace: list[AgentEvent] | tuple[AgentEvent, ...]) -> list[ContextPackCitation]:
        citations: list[ContextPackCitation] = []
        for index, event in enumerate(trace):
            if event.event_type != AgentEventType.BROWSER_EVIDENCE_COLLECTED:
                continue
            payload = event.payload
            source_id = str(payload.get("evidence_item_id") or payload.get("receipt_id") or event.id)
            stable_ref_id = str(payload.get("stable_ref_id") or payload.get("receipt_id") or source_id)
            excerpt = str(payload.get("citation_excerpt") or payload.get("title") or payload.get("final_url") or "")[:MAX_CITATION_EXCERPT_CHARS]
            digest = str(payload.get("content_sha256") or _canonical_hash({"excerpt": excerpt, "source_id": source_id}))
            citations.append(
                ContextPackCitation(
                    id=str(payload.get("citation_id") or f"cit_{index}"),
                    source_id=source_id,
                    stable_ref_id=stable_ref_id,
                    support_level=ContextPackSupportLevel.PARTIAL,
                    excerpt=excerpt,
                    digest=digest,
                    trace_refs=[event.id],
                )
            )
        return citations[:256]

    @staticmethod
    def _source_quality_flags(trace: list[AgentEvent] | tuple[AgentEvent, ...]) -> list[ContextPackSourceQualityFlag]:
        flags: list[ContextPackSourceQualityFlag] = []
        for event in trace:
            if event.event_type not in {AgentEventType.BROWSER_EVIDENCE_COLLECTED, AgentEventType.BROWSER_SNAPSHOT_CAPTURED}:
                continue
            payload = event.payload
            source_id = str(payload.get("evidence_item_id") or payload.get("receipt_id") or event.id)
            local_flags = [str(value) for value in payload.get("source_quality_flags", [])]
            score = 0.45 if local_flags else 0.75
            flags.append(ContextPackSourceQualityFlag(source_id=source_id, flags=local_flags, derived_score=score))
        return flags[:256]

    @staticmethod
    def _prompt_injection_flags(trace: list[AgentEvent] | tuple[AgentEvent, ...]) -> list[ContextPackPromptInjectionFlag]:
        flags: list[ContextPackPromptInjectionFlag] = []
        for event in trace:
            if event.event_type not in {AgentEventType.BROWSER_EVIDENCE_COLLECTED, AgentEventType.BROWSER_SNAPSHOT_CAPTURED}:
                continue
            payload = event.payload
            indicators = [str(value) for value in payload.get("prompt_injection_flags", [])]
            if not indicators:
                continue
            source_id = str(payload.get("evidence_item_id") or payload.get("receipt_id") or event.id)
            flags.append(
                ContextPackPromptInjectionFlag(
                    source_id=source_id,
                    risk=ContextPackInjectionRisk.HIGH,
                    indicators=indicators,
                    blocked=True,
                    sanitized=True,
                )
            )
        return flags[:256]

    @staticmethod
    def _stable_refs(trace: list[AgentEvent] | tuple[AgentEvent, ...]) -> list[ContextPackStableRef]:
        refs: dict[str, ContextPackStableRef] = {}
        for event in trace:
            payload = event.payload
            source_id = str(payload.get("evidence_item_id") or payload.get("receipt_id") or event.id)
            for ref_id in payload.get("accessibility_ref_ids", []):
                ref_key = str(ref_id)
                refs[ref_key] = ContextPackStableRef(
                    id=ref_key,
                    source_id=source_id,
                    selector=f"accessibility_ref:{ref_key}",
                    digest=_canonical_hash(
                        {
                            "ref_id": ref_key,
                            "snapshot_sha256": payload.get("accessibility_snapshot_sha256"),
                            "page_sha256": payload.get("accessibility_page_sha256"),
                        }
                    ),
                    page_sha256=payload.get("accessibility_page_sha256"),
                    snapshot_sha256=payload.get("accessibility_snapshot_sha256"),
                    trace_refs=[event.id],
                )
        for citation in ContextPackAssembler._citations(trace):
            refs.setdefault(
                citation.stable_ref_id,
                ContextPackStableRef(
                    id=citation.stable_ref_id,
                    source_id=citation.source_id,
                    selector=f"citation:{citation.id}",
                    digest=citation.digest,
                    trace_refs=list(citation.trace_refs),
                ),
            )
        return list(refs.values())[:512]

    @staticmethod
    def _network_diagnostics(trace: list[AgentEvent] | tuple[AgentEvent, ...]) -> ContextPackNetworkDiagnostics:
        request_count = 0
        redirect_count = 0
        bytes_fetched = 0
        hashes: list[str] = []
        for event in trace:
            payload = event.payload
            request_count += int(payload.get("network_request_count") or 0)
            redirect_count += int(payload.get("redirect_count") or len(payload.get("redirect_chain", [])) or 0)
            bytes_fetched += int(payload.get("bytes_read") or payload.get("uncompressed_bytes_read") or 0)
            if payload.get("network_ledger_sha256"):
                hashes.append(str(payload["network_ledger_sha256"]))
        return ContextPackNetworkDiagnostics(
            request_count=request_count,
            redirect_count=redirect_count,
            bytes_fetched=bytes_fetched,
            trace_root_hash=_canonical_hash({"trace_hashes": hashes}) if hashes else None,
        )


class ContextPackValidator:
    """Validates ContextPack schema, provenance, authority, and injection rules."""

    def validate(
        self,
        pack: ContextPack,
        envelope: MissionAuthorityEnvelope,
        *,
        event_bus: EventBus | None = None,
        phase: AgentPhase = AgentPhase.CONTEXT_BUILDING,
    ) -> ContextPackValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if pack.schema_version != CONTEXT_PACK_SCHEMA_VERSION:
            errors.append("unsupported_context_pack_schema_version")
        if pack.mission_id != envelope.id:
            errors.append("context_pack_mission_id_mismatch")
        if pack.mission_goal != envelope.mission_objective:
            errors.append("context_pack_mission_goal_mismatch")
        if pack.authority_boundary.allowed_actions != list(envelope.allowed_actions):
            errors.append("context_pack_allowed_actions_mismatch")
        if pack.authority_boundary.allowed_tools != list(envelope.allowed_tools):
            errors.append("context_pack_allowed_tools_mismatch")
        if pack.budget_effort_constraints.remaining_token_budget < 0:
            errors.append("context_pack_negative_token_budget")

        action_kinds = {intent.kind for intent in pack.available_action_intents}
        allowed_actions = set(envelope.allowed_actions)
        forbidden_actions = set(envelope.forbidden_actions)
        outside = sorted(action_kinds - allowed_actions)
        forbidden = sorted(action_kinds & forbidden_actions)
        if outside:
            errors.append(f"context_pack_action_intents_outside_authority:{','.join(outside)}")
        if forbidden:
            errors.append(f"context_pack_action_intents_forbidden:{','.join(forbidden)}")

        citation_by_id = {citation.id: citation for citation in pack.citations}
        ref_by_id = {ref.id: ref for ref in pack.browser_stable_refs}
        source_quality_ids = {flag.source_id for flag in pack.source_quality_flags}
        high_injection_sources = {
            flag.source_id
            for flag in pack.prompt_injection_flags
            if flag.risk == ContextPackInjectionRisk.HIGH or str(flag.risk) == ContextPackInjectionRisk.HIGH.value
        }

        for summary in pack.browser_evidence_summaries:
            if summary.source_id not in source_quality_ids:
                errors.append(f"context_pack_summary_missing_source_quality:{summary.source_id}")
            for ref_id in summary.stable_ref_ids:
                if ref_id not in ref_by_id:
                    errors.append(f"context_pack_summary_unknown_stable_ref:{ref_id}")

        for citation in pack.citations:
            if citation.stable_ref_id not in ref_by_id:
                errors.append(f"context_pack_citation_unknown_stable_ref:{citation.id}:{citation.stable_ref_id}")
            if citation.support_level == ContextPackSupportLevel.FULL and (not citation.excerpt or not citation.digest):
                errors.append(f"context_pack_full_citation_missing_proof:{citation.id}")

        for hypothesis in pack.verified_hypotheses:
            if hypothesis.status != ContextPackHypothesisStatus.VERIFIED:
                continue
            if not hypothesis.citation_ids:
                errors.append(f"context_pack_verified_hypothesis_missing_citation:{hypothesis.id}")
                continue
            for citation_id in hypothesis.citation_ids:
                citation = citation_by_id.get(citation_id)
                if citation is None:
                    errors.append(f"context_pack_verified_hypothesis_unknown_citation:{hypothesis.id}:{citation_id}")
                    continue
                if citation.source_id in high_injection_sources:
                    errors.append(f"context_pack_verified_hypothesis_uses_prompt_injection_source:{hypothesis.id}:{citation.source_id}")

        for flag in pack.prompt_injection_flags:
            if flag.risk == ContextPackInjectionRisk.HIGH and (not flag.blocked or not flag.sanitized):
                errors.append(f"context_pack_high_injection_source_not_isolated:{flag.source_id}")

        expected_hash = hash_context_pack_payload(pack.model_dump(mode="json"))
        if pack.context_pack_sha256 != expected_hash:
            errors.append("context_pack_hash_mismatch")

        result = ContextPackValidationResult(
            accepted=not errors,
            context_pack_id=pack.context_pack_id,
            context_pack_sha256=pack.context_pack_sha256,
            errors=errors,
            warnings=warnings,
        )
        if event_bus is None:
            return result
        event = event_bus.append(
            AgentEventType.CONTEXT_PACK_VALIDATED if result.accepted else AgentEventType.CONTEXT_PACK_REJECTED,
            "LLM ContextPack validated." if result.accepted else "LLM ContextPack rejected.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "accepted": result.accepted,
                "context_pack_id": pack.context_pack_id,
                "context_pack_sha256": pack.context_pack_sha256,
                "errors": errors,
                "warnings": warnings,
            },
            trace_refs=pack.trace_refs,
        )
        return result.model_copy(update={"trace_event_id": event.id})
