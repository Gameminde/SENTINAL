from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from sentinel.shared.enums import EvidenceType
from sentinel.shared.models import EvidenceItem


def _text(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).strip()


def _lower(*values: Any) -> str:
    return _text(*values).lower()


def _confidence(value: Any, default: float = 0.65) -> float:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"high", "strong", "confirmed"}:
            return 0.9
        if normalized in {"medium", "moderate", "solid"}:
            return 0.65
        if normalized in {"low", "weak", "early"}:
            return 0.35

    try:
        score = float(value)
    except (TypeError, ValueError):
        return default

    if score > 1:
        score = score / 100
    return max(0.0, min(1.0, score))


def _freshness_score(value: Any) -> float:
    if not value:
        return 0.5

    try:
        observed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0.5

    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)

    age_hours = max(0.0, (datetime.now(UTC) - observed).total_seconds() / 3600)
    if age_hours <= 24:
        return 1.0
    if age_hours <= 72:
        return 0.75
    if age_hours <= 24 * 14:
        return 0.5
    return 0.25


def _proof_tier(entry: dict[str, Any]) -> str:
    tier_text = _lower(
        entry.get("proof_tier"),
        entry.get("directness_tier"),
        entry.get("evidence_taxonomy"),
        entry.get("directness"),
        entry.get("relevance"),
    )
    if "direct" in tier_text:
        return "direct"
    if "adjacent" in tier_text:
        return "adjacent"
    return "supporting"


def _evidence_type(entry: dict[str, Any], proof_tier: str) -> EvidenceType:
    signal_text = _lower(
        entry.get("evidence_type"),
        entry.get("signal_kind"),
        entry.get("what_it_proves"),
        entry.get("summary"),
        entry.get("title"),
        entry.get("body"),
    )

    if (
        "wtp" in signal_text
        or "willingness to pay" in signal_text
        or "budget" in signal_text
        or re.search(r"\b(would|will|willing to|ready to|happy to)\s+pay\b", signal_text)
        or re.search(r"\bpaid\b", signal_text)
    ):
        return EvidenceType.WTP
    if any(token in signal_text for token in ("price", "pricing", "expensive", "cheap", "cost")):
        return EvidenceType.PRICING
    if any(token in signal_text for token in ("competitor", "alternative", "complaint", "switching")):
        return EvidenceType.COMPETITOR_COMPLAINT
    if any(token in signal_text for token in ("trend", "growing", "momentum", "search volume")):
        return EvidenceType.TREND
    if any(token in signal_text for token in ("community", "subreddit", "forum", "discord", "slack")):
        return EvidenceType.COMMUNITY_SIGNAL
    if any(token in signal_text for token in ("pain", "problem", "struggling", "frustrated", "manual", "broken")):
        return EvidenceType.PAIN
    if proof_tier == "direct":
        return EvidenceType.DIRECT_PROOF
    return EvidenceType.ADJACENT_PROOF


def _relevance_score(entry: dict[str, Any], proof_tier: str) -> float:
    direct_bonus = {"direct": 0.85, "adjacent": 0.6, "supporting": 0.45}[proof_tier]
    return _confidence(entry.get("relevance_score") or entry.get("relevance"), direct_bonus)


def map_cueidea_evidence(entry: dict[str, Any], index: int = 0, validation_id: str | None = None) -> EvidenceItem:
    proof_tier = _proof_tier(entry)
    evidence_type = _evidence_type(entry, proof_tier)
    title = _text(entry.get("post_title"), entry.get("title"), entry.get("keyword")) or f"CueIdea evidence {index + 1}"
    summary = (
        _text(entry.get("summary"))
        or _text(entry.get("what_it_proves"))
        or _text(entry.get("insight"))
        or _text(entry.get("body"))
        or title
    )

    return EvidenceItem(
        id=str(entry.get("id") or f"cue_ev_{validation_id or 'pending'}_{index}"),
        source=str(entry.get("source") or entry.get("platform") or "cueidea"),
        url=str(entry.get("url") or entry.get("permalink") or "") or None,
        quote=str(entry.get("quote") or entry.get("pain_quote") or "") or None,
        summary=summary,
        confidence=_confidence(entry.get("confidence") or entry.get("score")),
        freshness_score=_freshness_score(entry.get("created_at") or entry.get("observed_at") or entry.get("scraped_at")),
        relevance_score=_relevance_score(entry, proof_tier),
        evidence_type=evidence_type,
        metadata={
            "title": title,
            "proof_tier": proof_tier,
            "subreddit": entry.get("subreddit"),
            "platform": entry.get("platform") or entry.get("source"),
            "what_it_proves": entry.get("what_it_proves"),
            "raw": entry,
        },
    )
