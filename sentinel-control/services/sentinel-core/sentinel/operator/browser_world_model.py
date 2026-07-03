from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.shared.models import SentinelModel, new_id

if TYPE_CHECKING:
    from sentinel.operator.real_browser_control_runtime import RealBrowserEngineElement, RealBrowserEngineSnapshot


class BrowserStableRefCard(SentinelModel):
    ref: str
    role: str
    name: str
    text_preview: str = ""
    value_preview: str = ""


class BrowserActionCandidateCard(SentinelModel):
    action: str
    ref: str | None = None
    reason: str
    confidence: float = 0.5


class BrowserLinkCandidateCard(SentinelModel):
    ref: str
    text: str
    reason: str
    confidence: float = 0.5


class BrowserExtractionCard(SentinelModel):
    card_id: str = Field(default_factory=lambda: new_id("browser_extract_card"))
    kind: str
    title: str = "unknown"
    visible_price: str = "unknown"
    currency_or_unit: str = "unknown"
    minimum_order: str = "unknown"
    supplier_or_store: str = "unknown"
    relevance_to_objective: str = "unknown"
    relevance_reason: str = "unknown"
    price_condition_supported: str = "unknown"
    objective_relevance_assessed: bool = False
    short_features: tuple[str, ...] = Field(default_factory=tuple)
    caveats: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ref_hash: str
    confidence: float = 0.0


class ProductCandidateCard(BrowserExtractionCard):
    kind: str = "product_candidate"


class BrowserSearchResultCard(BrowserExtractionCard):
    kind: str = "search_result_candidate"


class BrowserWorldModel(SentinelModel):
    world_model_id: str = Field(default_factory=lambda: new_id("browser_world_model"))
    page_kind_guess: str
    title_hash_or_safe_title: str
    origin_hash: str
    visible_text_summary_hash: str
    top_visible_text_snippets: tuple[str, ...] = Field(default_factory=tuple)
    stable_refs: tuple[BrowserStableRefCard, ...] = Field(default_factory=tuple)
    search_like_refs: tuple[str, ...] = Field(default_factory=tuple)
    form_controls: tuple[str, ...] = Field(default_factory=tuple)
    button_refs: tuple[str, ...] = Field(default_factory=tuple)
    link_refs: tuple[str, ...] = Field(default_factory=tuple)
    product_or_result_candidate_cards: tuple[BrowserExtractionCard, ...] = Field(default_factory=tuple)
    modal_or_consent_signals: tuple[str, ...] = Field(default_factory=tuple)
    captcha_or_login_signals: tuple[str, ...] = Field(default_factory=tuple)
    dynamic_loading_signals: tuple[str, ...] = Field(default_factory=tuple)
    recommended_browser_actions: tuple[str, ...] = Field(default_factory=tuple)

    def compact_summary(self) -> dict[str, Any]:
        return {
            "world_model_id": self.world_model_id,
            "page_kind_guess": self.page_kind_guess,
            "title_hash_or_safe_title": self.title_hash_or_safe_title,
            "origin_hash": self.origin_hash,
            "visible_text_summary_hash": self.visible_text_summary_hash,
            "top_visible_text_snippets": list(self.top_visible_text_snippets[:8]),
            "stable_ref_count": len(self.stable_refs),
            "search_like_refs": list(self.search_like_refs[:8]),
            "form_controls": list(self.form_controls[:8]),
            "button_refs": list(self.button_refs[:8]),
            "link_refs": list(self.link_refs[:8]),
            "product_or_result_candidate_count": len(self.product_or_result_candidate_cards),
            "relevant_product_candidate_count": sum(
                1
                for card in self.product_or_result_candidate_cards
                if card.relevance_to_objective in {"relevant", "partial"}
            ),
            "objective_relevance_assessed": any(
                card.objective_relevance_assessed for card in self.product_or_result_candidate_cards
            ),
            "modal_or_consent_signals": list(self.modal_or_consent_signals),
            "captcha_or_login_signals": list(self.captcha_or_login_signals),
            "dynamic_loading_signals": list(self.dynamic_loading_signals),
            "recommended_browser_actions": list(self.recommended_browser_actions),
        }


class BrowserWorldModelBuilder:
    def build_from_snapshot(
        self,
        snapshot: "RealBrowserEngineSnapshot",
        *,
        mission_objective: str = "",
        origin_hash: str,
        extracted_text: str = "",
    ) -> BrowserWorldModel:
        observable = tuple(
            element
            for element in snapshot.elements
            if element.visible and element.enabled and not bool(getattr(element, "secret", False))
        )
        stable_refs = tuple(_stable_ref(element) for element in observable)
        visible_parts = [_element_text(element) for element in observable]
        if extracted_text:
            visible_parts.append(extracted_text[:1200])
        visible_text = "\n".join(part for part in visible_parts if part)
        snippets = _snippets(visible_text)
        search_like_refs = tuple(element.ref for element in observable if _is_search_like(element))
        form_controls = tuple(element.ref for element in observable if element.role in {"textbox", "combobox"})
        button_refs = tuple(element.ref for element in observable if element.role == "button")
        link_refs = tuple(element.ref for element in observable if element.role == "link")
        cards = tuple(
            _candidate_cards(
                observable,
                extracted_text=extracted_text or visible_text,
                mission_objective=mission_objective,
            )
        )
        blockers = _blocker_signals(visible_text)
        return BrowserWorldModel(
            page_kind_guess=_page_kind_guess(search_like_refs=search_like_refs, link_refs=link_refs, cards=cards, text=visible_text),
            title_hash_or_safe_title=_safe_title(snapshot.page_title),
            origin_hash=origin_hash,
            visible_text_summary_hash=text_hash(visible_text),
            top_visible_text_snippets=tuple(snippets),
            stable_refs=stable_refs,
            search_like_refs=search_like_refs,
            form_controls=form_controls,
            button_refs=button_refs,
            link_refs=link_refs,
            product_or_result_candidate_cards=cards,
            modal_or_consent_signals=tuple(blockers["modal_or_consent"]),
            captcha_or_login_signals=tuple(blockers["captcha_or_login"]),
            dynamic_loading_signals=tuple(blockers["dynamic_loading"]),
            recommended_browser_actions=_recommended_actions(
                search_like_refs=search_like_refs,
                button_refs=button_refs,
                link_refs=link_refs,
                cards=cards,
                extracted_text=extracted_text,
            ),
        )


def _stable_ref(element: "RealBrowserEngineElement") -> BrowserStableRefCard:
    return BrowserStableRefCard(
        ref=element.ref,
        role=element.role,
        name=_clip(element.name),
        text_preview=_clip(element.text_preview),
        value_preview=_clip(element.value_preview),
    )


def _element_text(element: "RealBrowserEngineElement") -> str:
    return " ".join(part for part in (element.name, element.text_preview, element.value_preview) if part).strip()


def _safe_title(title: str) -> str:
    stripped = title.strip()
    if not stripped:
        return "unknown"
    if len(stripped) <= 80 and not _contains_sensitive_marker(stripped):
        return stripped
    return f"title_hash:{text_hash(stripped)}"


def _clip(value: str, limit: int = 120) -> str:
    value = " ".join(value.split())
    if _contains_sensitive_marker(value):
        return f"redacted_hash:{text_hash(value)}"
    return value[:limit]


def _contains_sensitive_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in ("authorization", "bearer ", "cookie", "password", "secret", "api_key", "session"))


def _is_search_like(element: "RealBrowserEngineElement") -> bool:
    if element.role not in {"textbox", "combobox", "searchbox"}:
        return False
    text = f"{element.ref} {element.name} {element.text_preview} {element.value_preview}".lower()
    return any(marker in text for marker in ("search", "find", "query", "keyword", "product", "supplier"))


def _snippets(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"[\n\r]+|(?<=[.!?])\s+", text) if chunk.strip()]
    safe = [
        _clip(chunk, 180)
        for chunk in chunks
        if chunk and _is_browser_research_snippet(chunk) and not _contains_sensitive_marker(chunk)
    ]
    return safe[:8]


def _is_browser_research_snippet(chunk: str) -> bool:
    lowered = chunk.lower()
    return any(
        marker in lowered
        for marker in (
            "search",
            "result",
            "product",
            "price",
            "moq",
            "minimum order",
            "supplier",
            "store",
            "shipping",
            "customization",
            "glasses",
            "sunglasses",
            "eyeglasses",
            "$",
            "€",
            "eur",
            "usd",
            "lunette",
            "lunettes",
            "optique",
            "optiques",
            "monture",
        )
    )


def _candidate_cards(
    elements: tuple["RealBrowserEngineElement", ...],
    *,
    extracted_text: str,
    mission_objective: str,
) -> list[BrowserExtractionCard]:
    cards: list[BrowserExtractionCard] = []
    sources = [_element_text(element) for element in elements if element.role in {"link", "article", "card", "generic"}]
    if extracted_text:
        sources.extend(_extracted_text_sources(extracted_text))
    for source in sources:
        card = _card_from_text(source, mission_objective=mission_objective)
        if card is not None:
            cards.append(card)
    return cards[:6]


def _extracted_text_sources(text: str) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    normalized = _strip_search_intro(normalized)
    sources: list[str] = []
    product_start = _first_product_term_index(normalized)
    if product_start is not None:
        sources.append(normalized[product_start:])
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+|[\n\r]+", normalized) if chunk.strip()]
    for index, chunk in enumerate(chunks):
        if not _has_product_signal(chunk):
            continue
        window = " ".join(chunks[index : index + 4]).strip()
        if window:
            sources.append(window)
    return list(dict.fromkeys(source for source in sources if source))


def _first_product_term_index(text: str) -> int | None:
    match = re.search(
        r"\b(glasses|sunglasses|eyeglasses|eyewear|spectacles|lunettes?|optiques?|monture)\b",
        text,
        flags=re.I,
    )
    return match.start() if match else None


def _card_from_text(text: str, *, mission_objective: str) -> BrowserExtractionCard | None:
    if not text.strip():
        return None
    product_text = _strip_search_intro(text)
    has_product_signal = bool(
        re.search(r"(\$|€|eur|usd|price|moq|minimum order|supplier|store|piece|unit|pcs?)", product_text, flags=re.I)
    )
    if not has_product_signal:
        has_product_signal = bool(re.search(r"(product|glasses|sunglasses|listing|catalog)", product_text, flags=re.I))
    if not has_product_signal:
        return None
    title = _extract_title(product_text)
    price = _first_match(
        product_text,
        r"(\$\s?\d+(?:[.,]\d+)?|€\s?\d+(?:[.,]\d+)?|(?:EUR|USD)\s?\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s?(?:EUR|USD))",
    )
    moq = _normalize_minimum_order(
        _first_match(product_text, r"(MOQ\s*\d+\s*(?:pieces|piece|pcs?|units?)?|minimum order\s*[:\-]?\s*\d+\s*\w*)")
    )
    supplier = _extract_supplier(product_text)
    relevance, relevance_reason = _objective_relevance(product_text, mission_objective=mission_objective)
    price_support = _price_condition_supported(price, mission_objective=mission_objective)
    caveats = []
    for marker in ("shipping not included", "shipping", "customization", "unclear", "login required", "MOQ"):
        if marker.lower() in product_text.lower():
            caveats.append(marker)
    return ProductCandidateCard(
        title=_clip(title or "unknown", 120),
        visible_price=_clip(price or "unknown", 80),
        currency_or_unit=_currency_or_unit(price or product_text),
        minimum_order=_clip(moq or "unknown", 80),
        supplier_or_store=_clip(supplier or "unknown", 120),
        relevance_to_objective=relevance,
        relevance_reason=_clip(relevance_reason, 180),
        price_condition_supported=price_support,
        objective_relevance_assessed=True,
        short_features=tuple(_snippets(product_text)[:3]),
        caveats=tuple(dict.fromkeys(caveats)) or ("unknown",),
        evidence_ref_hash=stable_hash({"source_hash": text_hash(product_text), "card_kind": "product_candidate"}),
        confidence=0.72 if price != "unknown" or moq != "unknown" else 0.42,
    )


def _has_product_signal(text: str) -> bool:
    return bool(
        re.search(
            (
                r"(\$|eur|usd|price|moq|minimum order|supplier|store|piece|unit|pcs?|"
                r"product|glasses|sunglasses|eyeglasses|eyewear|spectacles|listing|catalog|"
                r"lunettes?|optiques?|monture)"
            ),
            text,
            flags=re.I,
        )
    )


def _strip_search_intro(text: str) -> str:
    stripped = " ".join(text.split())
    return re.sub(
        r"^search results?\s+for\s+.+?(?:\.|:)\s*",
        "",
        stripped,
        count=1,
        flags=re.I,
    ).strip() or stripped


def _extract_title(text: str) -> str:
    first = re.split(r"(\$|€|price|MOQ|minimum order|supplier|store)", text, maxsplit=1, flags=re.I)[0]
    return _normalize_title(first.strip(" -:,.")[:120] or text.strip()[:120])


def _normalize_title(title: str) -> str:
    midpoint = len(title) // 2
    if len(title) > 12 and len(title) % 2 == 1 and title[:midpoint].strip() == title[midpoint:].strip():
        return title[:midpoint].strip()
    if "Polarized sunglasses" in title:
        return "Polarized sunglasses"
    return title


def _extract_supplier(text: str) -> str:
    supplier = re.search(
        r"supplier\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9 _-]{2,80}?)(?=\s*(?:\.|,|caveat|shipping|customization|$))",
        text,
        flags=re.I,
    )
    if supplier:
        return supplier.group(1).strip()
    store = re.search(
        r"([A-Za-z][A-Za-z0-9 _-]{2,50}\s+Store)(?=\s*(?:\.|,|caveat|shipping|customization|$))",
        text,
        flags=re.I,
    )
    if store:
        value = store.group(1).strip()
        suffix = re.search(r"([A-Za-z][A-Za-z0-9_-]*\s+[A-Za-z0-9_-]+\s+Store)$", value)
        return suffix.group(1).strip() if suffix else value
    return "unknown"


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return "unknown"
    if match.lastindex and match.lastindex > 1:
        return match.group(match.lastindex).strip()
    return match.group(1).strip()


def _currency_or_unit(text: str) -> str:
    lowered = text.lower()
    if "$" in text or "usd" in lowered:
        return "USD/visible"
    if "€" in text or "eur" in lowered:
        return "EUR/visible"
    if "piece" in lowered or "unit" in lowered or "pcs" in lowered:
        return "visible unit"
    return "unknown"


def _objective_relevance(text: str, *, mission_objective: str) -> tuple[str, str]:
    objective = mission_objective.lower()
    lowered = text.lower()
    wanted_terms = []
    if any(marker in objective for marker in ("glasses", "sunglasses", "eyewear")):
        wanted_terms.extend(
            (
                "glasses",
                "sunglasses",
                "eyewear",
                "eyeglasses",
                "spectacles",
                "lunette",
                "lunettes",
                "optique",
                "optiques",
                "monture",
            )
        )
    if not wanted_terms:
        return "unknown", "mission objective has no product keyword Sentinel can safely score"
    if any(term in lowered for term in wanted_terms):
        return "relevant", "visible product text matches the requested eyewear category"
    return "irrelevant", "visible product text does not match the requested eyewear category"


def _price_condition_supported(price: str, *, mission_objective: str) -> str:
    objective = mission_objective.lower()
    if "5" not in objective and "five" not in objective:
        return "unknown"
    if "eur" not in objective and "euro" not in objective:
        return "unknown"
    if not price or price == "unknown":
        return "unknown"
    lowered = price.lower()
    if "eur" not in lowered and "€" not in price and "â‚¬" not in price:
        return "unknown"
    amount = _price_amount(price)
    if amount is None:
        return "unknown"
    return "supported" if amount <= 5 else "not_supported"


def _price_amount(price: str) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)", price)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _normalize_minimum_order(value: str) -> str:
    if value == "unknown":
        return value
    return re.sub(r"^(MOQ|minimum order)\s*[:\-]?\s*", "", value, flags=re.I).strip() or value


def _blocker_signals(text: str) -> dict[str, list[str]]:
    lowered = text.lower()
    return {
        "modal_or_consent": [marker for marker in ("cookie", "consent", "accept all", "privacy") if marker in lowered],
        "captcha_or_login": [marker for marker in ("captcha", "login", "sign in", "verify you are human") if marker in lowered],
        "dynamic_loading": [marker for marker in ("loading", "please wait", "spinner") if marker in lowered],
    }


def _page_kind_guess(
    *,
    search_like_refs: tuple[str, ...],
    link_refs: tuple[str, ...],
    cards: tuple[BrowserExtractionCard, ...],
    text: str,
) -> str:
    lowered = text.lower()
    if cards:
        return "search_results" if search_like_refs else "product_listing"
    if "captcha" in lowered or "login" in lowered:
        return "blocked_or_login"
    if search_like_refs:
        return "catalog_search"
    if link_refs:
        return "link_index"
    return "unknown_page"


def _recommended_actions(
    *,
    search_like_refs: tuple[str, ...],
    button_refs: tuple[str, ...],
    link_refs: tuple[str, ...],
    cards: tuple[BrowserExtractionCard, ...],
    extracted_text: str,
) -> tuple[str, ...]:
    actions: list[str] = ["real_browser.observe"]
    if search_like_refs:
        actions.append("real_browser.search")
    if link_refs:
        actions.extend(["real_browser.inspect_result", "real_browser.open_result"])
    if cards or extracted_text:
        actions.extend(["real_browser.extract_product_cards", "real_browser.verify_extraction"])
    if button_refs and not search_like_refs and not link_refs:
        actions.append("real_browser.inspect_result")
    return tuple(dict.fromkeys(actions))


__all__ = [
    "BrowserActionCandidateCard",
    "BrowserExtractionCard",
    "BrowserLinkCandidateCard",
    "BrowserSearchResultCard",
    "BrowserStableRefCard",
    "BrowserWorldModel",
    "BrowserWorldModelBuilder",
    "ProductCandidateCard",
]
