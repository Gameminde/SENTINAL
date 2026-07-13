from __future__ import annotations

import unicodedata
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel


class SearchControlCandidate(SentinelModel):
    control_ref: str
    semantic_role: str = "search_control"
    confidence: float = 0.0
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    freshness: str = "current_snapshot"
    frame_identity: str = "main"
    tab_identity: str = "active"
    submission_mechanisms: tuple[str, ...] = Field(default_factory=tuple)
    uncertainty_reason: str = ""

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


_SEARCH_LEXICAL_MARKERS = {
    "search",
    "find",
    "query",
    "keyword",
    "product",
    "supplier",
    "catalog",
    "catalogue",
    "recherche",
    "rechercher",
    "chercher",
    "buscar",
    "busca",
    "suche",
    "suchen",
    "procurar",
    "pesquisar",
    "cerca",
    "ricerca",
    "zoeken",
    "zoek",
    "ara",
    "arama",
    "sok",
    "søk",
    "検索",
    "搜尋",
    "搜索",
    "بحث",
}


def classify_search_controls(
    elements: tuple[Any, ...] | list[Any],
    *,
    mission_objective: str = "",
    frame_id: str = "main",
    tab_id: str = "active",
) -> tuple[SearchControlCandidate, ...]:
    candidates: list[SearchControlCandidate] = []
    visible_buttons = tuple(_element_ref(element) for element in elements if _is_safe_button(element))
    for element in elements:
        if not _is_candidate_control(element):
            continue
        score, evidence = _score_control(element, mission_objective=mission_objective)
        if visible_buttons:
            score += 0.05
            evidence.append(f"nearby_submit_controls:{stable_hash(visible_buttons)}")
        if score < 0.45:
            continue
        mechanisms = ["press_enter"]
        if visible_buttons:
            mechanisms.append("safe_submit_control")
        candidates.append(
            SearchControlCandidate(
                control_ref=_element_ref(element),
                confidence=round(min(score, 0.98), 3),
                evidence_refs=tuple(dict.fromkeys(evidence)),
                frame_identity=frame_id,
                tab_identity=tab_id,
                submission_mechanisms=tuple(mechanisms),
                uncertainty_reason=_uncertainty_reason(score, evidence),
            )
        )
    return tuple(sorted(candidates, key=lambda item: (-item.confidence, item.control_ref)))


def is_search_like_control(element: Any, *, mission_objective: str = "") -> bool:
    return bool(classify_search_controls((element,), mission_objective=mission_objective))


def ranked_search_control_refs(
    elements: tuple[Any, ...] | list[Any],
    *,
    mission_objective: str = "",
) -> tuple[str, ...]:
    return tuple(candidate.control_ref for candidate in classify_search_controls(elements, mission_objective=mission_objective))


def _is_candidate_control(element: Any) -> bool:
    if not bool(getattr(element, "visible", True)) or not bool(getattr(element, "enabled", True)):
        return False
    if bool(getattr(element, "secret", False)):
        return False
    role = _norm(getattr(element, "role", ""))
    return role in {"searchbox", "textbox", "combobox", "input"}


def _is_safe_button(element: Any) -> bool:
    if not bool(getattr(element, "visible", True)) or not bool(getattr(element, "enabled", True)):
        return False
    if bool(getattr(element, "secret", False)):
        return False
    return _norm(getattr(element, "role", "")) == "button"


def _score_control(element: Any, *, mission_objective: str) -> tuple[float, list[str]]:
    role = _norm(getattr(element, "role", ""))
    text = _norm(
        " ".join(
            str(value or "")
            for value in (
                getattr(element, "ref", ""),
                getattr(element, "name", ""),
                getattr(element, "text_preview", ""),
                getattr(element, "value_preview", ""),
            )
        )
    )
    objective = _norm(mission_objective)
    score = 0.0
    evidence: list[str] = []
    if role == "searchbox":
        score += 0.72
        evidence.append("accessibility_role:searchbox")
    elif role in {"textbox", "combobox", "input"}:
        score += 0.28
        evidence.append(f"accessibility_role:{role}")
    lexical_hits = _lexical_hits(text)
    if lexical_hits:
        score += 0.22
        evidence.extend(f"lexical_search_marker:{marker}" for marker in lexical_hits[:4])
    if any(marker in objective for marker in ("find", "search", "trouver", "buscar", "product", "produit", "catalog")):
        score += 0.04
        evidence.append("objective_search_intent")
    if "input" in text or "query" in text:
        score += 0.03
        evidence.append("structural_input_ref")
    return score, evidence


def _lexical_hits(text: str) -> list[str]:
    return [marker for marker in sorted(_SEARCH_LEXICAL_MARKERS, key=len, reverse=True) if marker in text]


def _uncertainty_reason(score: float, evidence: list[str]) -> str:
    if score >= 0.85:
        return "high confidence search control from structural and semantic signals"
    if any(item.startswith("accessibility_role:searchbox") for item in evidence):
        return "searchbox role provides primary evidence; submit behavior still requires runtime proof"
    return "heuristic search control classification requires material search outcome verification"


def _element_ref(element: Any) -> str:
    return str(getattr(element, "ref", "") or "")


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    stripped = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    return " ".join(stripped.split())


__all__ = [
    "SearchControlCandidate",
    "classify_search_controls",
    "is_search_like_control",
    "ranked_search_control_refs",
]
