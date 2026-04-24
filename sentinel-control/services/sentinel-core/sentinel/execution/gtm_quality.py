from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel.execution.gtm_pack import GTMPack

QualityStatus = Literal["draft", "needs_revision", "ready"]


MAJOR_SECTIONS = (
    "icp",
    "wtp",
    "competitor_gap",
    "positioning",
    "outreach",
    "landing",
    "roadmap",
)

GENERIC_TERMS = (
    "small businesses",
    "startups",
    "everyone",
    "anyone",
    "all companies",
    "businesses and startups",
)

SPAM_PATTERNS = (
    r"guaranteed\s+\d+x",
    r"scraped\s+your",
    r"know\s+you\s+need",
    r"keep\s+following\s+up",
    r"final\s+chance",
)

OPT_OUT_PATTERNS = (
    r"reply\s+stop",
    r"not\s+relevant",
    r"no\s+worries",
    r"not\s+the\s+right\s+person",
)


class GTMPackQualityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icp: str = ""
    wtp: str = ""
    competitor_gap: str = ""
    positioning: str = ""
    outreach: str = ""
    landing: str = ""
    roadmap: str = ""
    evidence_refs: dict[str, list[str]] = Field(default_factory=dict)
    evidence_gaps: dict[str, str] = Field(default_factory=dict)


class GTMSectionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    score: int = Field(ge=0, le=100)
    passed: bool
    message: str


class GTMPackQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    status: QualityStatus
    section_scores: list[GTMSectionScore] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _words(value: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9$%+-]+", value.lower())


def _has_specific_numbers(value: str) -> bool:
    return bool(re.search(r"\b\d+([%-]|\s*(clients|prospects|days|hours|minutes|monthly|mo|users|interviews))?\b", value.lower()))


def _has_evidence(name: str, pack: GTMPackQualityInput) -> bool:
    return bool(pack.evidence_refs.get(name)) or bool(pack.evidence_gaps.get(name))


def _score_text(name: str, value: str, pack: GTMPackQualityInput, min_words: int = 10) -> GTMSectionScore:
    words = _words(value)
    score = 35
    messages: list[str] = []

    if len(words) >= min_words:
        score += 25
    else:
        messages.append("too short")

    if _has_evidence(name, pack):
        score += 25
    else:
        messages.append("missing evidence_refs or evidence_gap")

    if _has_specific_numbers(value):
        score += 10

    if any(term in value.lower() for term in GENERIC_TERMS):
        score -= 30
        messages.append("generic wording")

    score = max(0, min(100, score))
    return GTMSectionScore(
        name=name,
        score=score,
        passed=score >= 70,
        message=", ".join(messages) or "specific and evidenced",
    )


def _score_icp(pack: GTMPackQualityInput) -> GTMSectionScore:
    score = _score_text("icp", pack.icp, pack, min_words=14)
    if not any(token in pack.icp.lower() for token in ("with", "who", "that", "spend", "managing", "running")):
        score.score = max(0, score.score - 18)
        score.message = f"{score.message}; lacks buyer constraints"
    score.passed = score.score >= 70
    return score


def _score_wtp(pack: GTMPackQualityInput) -> GTMSectionScore:
    value = pack.wtp.lower()
    score = _score_text("wtp", pack.wtp, pack, min_words=8)
    if not pack.wtp and not pack.evidence_gaps.get("wtp"):
        score.score = 0
        score.message = "missing WTP section and no explicit evidence_gap"
    elif any(token in value for token in ("would pay", "willingness", "budget", "pricing", "$", "/mo", "paid")):
        score.score = min(100, score.score + 15)
    elif pack.evidence_gaps.get("wtp"):
        score.score = max(score.score, 62)
        score.message = "WTP weakness is explicitly marked"
    else:
        score.score = max(0, score.score - 25)
        score.message = f"{score.message}; weak WTP language"
    score.passed = score.score >= 70
    return score


def _score_competitor_gap(pack: GTMPackQualityInput) -> GTMSectionScore:
    score = _score_text("competitor_gap", pack.competitor_gap, pack, min_words=10)
    value = pack.competitor_gap.lower()
    if any(phrase in value for phrase in ("bad", "better", "not good")) and not any(token in value for token in ("because", "miss", "lack", "without", "but")):
        score.score = max(0, score.score - 35)
        score.message = f"{score.message}; not actionable"
    if any(token in value for token in ("miss", "lack", "without", "but", "wedge", "gap")):
        score.score = min(100, score.score + 10)
    score.passed = score.score >= 70
    return score


def _score_positioning(pack: GTMPackQualityInput) -> GTMSectionScore:
    score = _score_text("positioning", pack.positioning, pack, min_words=8)
    value = pack.positioning.lower()
    if any(phrase in value for phrase in ("helpful tool", "makes work easier", "ai-powered platform", "all-in-one")):
        score.score = max(0, score.score - 35)
        score.message = f"{score.message}; generic positioning"
    if any(token in value for token in ("for ", "without", "who", "so they", "instead of")):
        score.score = min(100, score.score + 10)
    score.passed = score.score >= 70
    return score


def _score_outreach(pack: GTMPackQualityInput) -> GTMSectionScore:
    score = _score_text("outreach", pack.outreach, pack, min_words=14)
    value = pack.outreach.lower()
    spam_hits = [pattern for pattern in SPAM_PATTERNS if re.search(pattern, value)]
    has_opt_out = any(re.search(pattern, value) for pattern in OPT_OUT_PATTERNS)
    if spam_hits:
        score.score = 0
        score.message = f"spam patterns: {', '.join(spam_hits)}"
    elif not has_opt_out:
        score.score = max(0, score.score - 20)
        score.message = f"{score.message}; missing opt-out language"
    if any(token in value for token in ("i saw", "discussing", "testing", "feedback")):
        score.score = min(100, score.score + 10)
    score.passed = score.score >= 70
    return score


def _score_landing(pack: GTMPackQualityInput) -> GTMSectionScore:
    score = _score_text("landing", pack.landing, pack, min_words=8)
    value = pack.landing.lower()
    if any(phrase in value for phrase in ("grow faster", "save time", "get insights", "ai-powered")) and not any(token in value for token in ("without", "for ", "because", "specific")):
        score.score = max(0, score.score - 35)
        score.message = f"{score.message}; generic landing copy"
    if any(token in value for token in ("without", "for ", "find why", "collect", "stop")):
        score.score = min(100, score.score + 10)
    score.passed = score.score >= 70
    return score


def _score_roadmap(pack: GTMPackQualityInput) -> GTMSectionScore:
    score = _score_text("roadmap", pack.roadmap, pack, min_words=22)
    value = pack.roadmap.lower()
    measurable_hits = len(re.findall(r"\b(day|interview|prospect|price|pricing|reply|landing|decide|build|pivot|kill|\d+)\b", value))
    if measurable_hits >= 6:
        score.score = min(100, score.score + 15)
    if any(phrase in value for phrase in ("complete saas", "100 customers", "expand globally", "launch paid ads")) and "interview" not in value:
        score.score = max(0, score.score - 45)
        score.message = f"{score.message}; unrealistic validation plan"
    score.passed = score.score >= 70
    return score


def evaluate_gtm_pack_quality(pack: GTMPackQualityInput) -> GTMPackQualityReport:
    section_scores = [
        _score_icp(pack),
        _score_wtp(pack),
        _score_competitor_gap(pack),
        _score_positioning(pack),
        _score_outreach(pack),
        _score_landing(pack),
        _score_roadmap(pack),
    ]
    blockers = [
        f"{section.name}: {section.message}"
        for section in section_scores
        if not section.passed
    ]
    missing_evidence = [
        name
        for name in MAJOR_SECTIONS
        if not _has_evidence(name, pack)
    ]
    if missing_evidence:
        blockers.append(f"missing evidence_refs or evidence_gap for: {', '.join(missing_evidence)}")

    score = round(sum(section.score for section in section_scores) / len(section_scores))
    if blockers:
        score = min(score, 79)
    status: QualityStatus = "ready" if score >= 80 and not blockers else "needs_revision"
    if not any(section.score > 0 for section in section_scores):
        status = "draft"

    warnings = [
        f"{section.name}: {section.message}"
        for section in section_scores
        if section.passed and section.score < 82
    ]
    return GTMPackQualityReport(
        score=score,
        status=status,
        section_scores=section_scores,
        blockers=blockers,
        warnings=warnings,
    )


def input_from_gtm_pack(pack: GTMPack) -> GTMPackQualityInput:
    by_filename = {section.filename: section for section in pack.sections}

    def content(filename: str) -> str:
        section = by_filename.get(filename)
        return section.content if section else ""

    def refs(filename: str) -> list[str]:
        section = by_filename.get(filename)
        return section.evidence_refs if section else []

    return GTMPackQualityInput(
        icp=content("02_ICP.md"),
        wtp=content("09_DECISION_RULES.md"),
        competitor_gap=content("03_COMPETITOR_GAPS.md"),
        positioning=content("04_LANDING_PAGE_COPY.md"),
        outreach=content("05_OUTREACH_MESSAGES.md"),
        landing=content("04_LANDING_PAGE_COPY.md"),
        roadmap=content("07_7_DAY_ROADMAP.md"),
        evidence_refs={
            "icp": refs("02_ICP.md"),
            "wtp": refs("09_DECISION_RULES.md"),
            "competitor_gap": refs("03_COMPETITOR_GAPS.md"),
            "positioning": refs("04_LANDING_PAGE_COPY.md"),
            "outreach": refs("05_OUTREACH_MESSAGES.md"),
            "landing": refs("04_LANDING_PAGE_COPY.md"),
            "roadmap": refs("07_7_DAY_ROADMAP.md"),
        },
    )
