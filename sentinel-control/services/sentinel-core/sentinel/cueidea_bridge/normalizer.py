from __future__ import annotations

from typing import Any

from sentinel.cueidea_bridge.evidence_mapper import map_cueidea_evidence
from sentinel.cueidea_bridge.schemas import Competitor, TrendSignal, ValidationResult, Watchlist
from sentinel.shared.enums import EvidenceType
from sentinel.shared.models import EvidenceItem


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_record(*values: Any) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def _confidence(value: Any, default: float = 0.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    if score > 1:
        score = score / 100
    return max(0.0, min(1.0, score))


def _collect_evidence_entries(report: dict[str, Any]) -> list[dict[str, Any]]:
    market = _record(report.get("market_analysis"))
    entries = [
        *_list(market.get("evidence")),
        *_list(market.get("pain_quotes")),
        *_list(report.get("debate_evidence")),
        *_list(report.get("evidence")),
        *_list(report.get("wtp_evidence")),
        *_list(report.get("competitor_complaints")),
    ]
    return [entry for entry in entries if isinstance(entry, dict)]


def _extract_report(payload: dict[str, Any]) -> dict[str, Any]:
    return _first_record(payload.get("report"), payload.get("result"), payload.get("data"), payload)


def _summary(report: dict[str, Any]) -> str:
    return str(
        report.get("executive_summary")
        or report.get("summary")
        or _record(report.get("market_analysis")).get("pain_description")
        or "CueIdea validation normalized without an executive summary."
    )


def normalize_competitors_response(payload: dict[str, Any]) -> list[Competitor]:
    report = _extract_report(payload)
    landscape = _record(report.get("competition_landscape") or payload.get("competition_landscape"))
    raw_competitors = (
        _list(landscape.get("direct_competitors"))
        or _list(payload.get("competitors"))
        or _list(report.get("competitors"))
    )
    competitors: list[Competitor] = []

    for item in raw_competitors:
        if isinstance(item, str):
            competitors.append(Competitor(name=item, raw={"name": item}))
            continue
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("competitor") or "").strip()
        if not name:
            continue
        evidence_refs = [str(ref) for ref in _list(item.get("evidence_refs"))]
        competitors.append(Competitor(
            name=name,
            url=str(item.get("url") or "") or None,
            gap=str(item.get("gap") or item.get("weakness") or item.get("why_they_fail") or "") or None,
            threat_level=str(item.get("threat_level") or item.get("threat") or "") or None,
            evidence_refs=evidence_refs,
            raw=item,
        ))

    return competitors


def normalize_trends_response(payload: dict[str, Any]) -> list[TrendSignal]:
    report = _extract_report(payload)
    trends = _record(report.get("trends_data") or payload.get("trends_data") or payload.get("trends"))
    raw_signals = _list(trends.get("signals")) or _list(trends.get("keywords")) or _list(payload.get("trend_signals"))

    if not raw_signals and trends:
        keyword = str(trends.get("keyword") or trends.get("query") or "market trend")
        direction = str(trends.get("overall_trend") or trends.get("direction") or "unknown")
        summary = str(trends.get("summary") or f"{keyword} trend direction: {direction}")
        return [TrendSignal(
            keyword=keyword,
            direction=direction,
            summary=summary,
            confidence=_confidence(trends.get("confidence"), 0.5),
            raw=trends,
        )]

    result: list[TrendSignal] = []
    for item in raw_signals:
        if isinstance(item, str):
            result.append(TrendSignal(keyword=item, direction="unknown", summary=item, confidence=0.5, raw={"keyword": item}))
            continue
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword") or item.get("query") or item.get("label") or "").strip()
        if not keyword:
            continue
        result.append(TrendSignal(
            keyword=keyword,
            direction=str(item.get("direction") or item.get("trend") or "unknown"),
            summary=str(item.get("summary") or item.get("reason") or keyword),
            confidence=_confidence(item.get("confidence"), 0.5),
            evidence_refs=[str(ref) for ref in _list(item.get("evidence_refs"))],
            raw=item,
        ))
    return result


def normalize_wtp_response(payload: dict[str, Any]) -> list[EvidenceItem]:
    report = _extract_report(payload)
    entries = [
        *_list(report.get("wtp_evidence")),
        *_list(report.get("willingness_to_pay_evidence")),
        *_list(_record(report.get("ideal_customer_profile")).get("willingness_to_pay_evidence")),
        *_list(_record(report.get("pricing_strategy")).get("evidence")),
        *_list(payload.get("wtp_signals")),
    ]
    mapped = [map_cueidea_evidence(entry, index=index, validation_id=str(report.get("id") or "wtp")) for index, entry in enumerate(entries) if isinstance(entry, dict)]
    return [item for item in mapped if item.evidence_type in {EvidenceType.WTP, EvidenceType.PRICING}]


def normalize_watchlist_response(payload: dict[str, Any], idea: str, competitors: list[str]) -> Watchlist:
    row = _extract_report(payload)
    return Watchlist(
        id=str(row.get("id") or row.get("watchlist_id") or "") or None,
        idea=str(row.get("idea") or row.get("idea_text") or idea),
        competitors=[str(item) for item in _list(row.get("competitors"))] or competitors,
        status=str(row.get("status") or "created"),
        raw=payload,
    )


def normalize_validation_response(payload: dict[str, Any], idea: str) -> ValidationResult:
    report = _extract_report(payload)
    validation_id = str(payload.get("id") or payload.get("validation_id") or report.get("id") or "") or None
    evidence = [
        map_cueidea_evidence(entry, index=index, validation_id=validation_id)
        for index, entry in enumerate(_collect_evidence_entries(report))
    ]
    direct_count = sum(1 for item in evidence if item.metadata.get("proof_tier") == "direct")
    adjacent_count = sum(1 for item in evidence if item.metadata.get("proof_tier") == "adjacent")
    wtp_count = sum(1 for item in evidence if item.evidence_type in {EvidenceType.WTP, EvidenceType.PRICING})

    return ValidationResult(
        idea=idea,
        validation_id=validation_id,
        verdict=str(report.get("verdict") or payload.get("verdict") or "") or None,
        confidence=_confidence(report.get("confidence") or payload.get("confidence"), 0.0),
        summary=_summary(report),
        evidence=evidence,
        competitors=normalize_competitors_response(report),
        trends=normalize_trends_response(report),
        direct_evidence_count=direct_count,
        adjacent_evidence_count=adjacent_count,
        wtp_signal_count=wtp_count,
        raw=payload,
    )

