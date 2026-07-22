from __future__ import annotations

import re
from typing import Any

_TERMINAL_OBJECTIVE_SUPPORT_STATUSES = frozenset(
    {
        "supported",
        "satisfied",
        "complete",
        "completed",
        "confirmed",
        "grounded",
        "fully_supported",
        "materially_supported",
        "objective_satisfied",
    }
)


def browser_summary_supports_terminal_answer(summary: dict[str, Any]) -> bool:
    if not isinstance(summary, dict):
        return False
    if browser_summary_supports_terminal_blocker(summary):
        return False
    if summary.get("objective_answer_supported") is True or summary.get("objective_satisfied") is True:
        return True
    status = _support_status(summary)
    if status in _TERMINAL_OBJECTIVE_SUPPORT_STATUSES:
        return True
    return bool(
        summary.get("objective_relevance_assessed") is True
        and summary.get("has_relevant_product_evidence") is True
    )


def browser_summary_supports_terminal_blocker(
    summary: dict[str, Any],
    *,
    mission_objective: str = "",
) -> bool:
    if not isinstance(summary, dict):
        return False
    if summary.get("negative_result_confirmed") is True:
        return True
    if (
        summary.get("objective_relevance_assessed") is True
        and summary.get("has_relevant_product_evidence") is False
        and _negative_relevance_status(summary)
        and _objective_can_terminally_accept_product_relevance_gap(mission_objective)
    ):
        return True
    status = _support_status(summary)
    return status in {"no_results_confirmed", "negative_confirmed"}


def _support_status(summary: dict[str, Any]) -> str:
    return str(
        summary.get("objective_satisfaction_status")
        or summary.get("objective_support")
        or summary.get("objective_support_status")
        or ""
    ).strip().lower()


def _negative_relevance_status(summary: dict[str, Any]) -> bool:
    status = str(summary.get("under_price_condition_supported_by_visible_evidence") or "").strip().lower()
    return status in {
        "no_relevant_products",
        "no_relevant_evidence",
        "no_matching_entities",
        "irrelevant_results_confirmed",
        "negative_relevance_confirmed",
    }


def _objective_can_terminally_accept_product_relevance_gap(mission_objective: str) -> bool:
    objective = str(mission_objective or "").lower()
    if any(
        marker in objective
        for marker in (
            "product",
            "catalog",
            "price",
            "priced",
            "eur",
            "euro",
            "usd",
            "moq",
            "supplier",
            "store",
            "glasses",
            "sunglasses",
        )
    ):
        return True
    return bool(
        re.search(r"\b(under|below|less than|max(?:imum)?)\b", objective)
        and re.search(r"(?:\beur\b|\beuro\b|\busd\b|\bdollar\b|€|\\$)", objective)
    )
