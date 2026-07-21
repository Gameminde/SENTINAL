from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_failure_policy import classify_action_execution_failure
from sentinel.operator.action_power_contract import ActionAliasNormalizer, ActionFailureClass
from sentinel.operator.action_power_contract import recoverable_action_observation
from sentinel.operator.browser_search_parameter_boundary import (
    typed_browser_search_scan_payload,
    typed_terminal_semantic_scan_payload,
)
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


FORBIDDEN_ACTION_PAYLOAD_MARKERS = (
    "raw_provider",
    "raw_prompt",
    "raw_response",
    "raw_visible_output",
    "raw_reasoning",
    "reasoning_content",
    "authorization",
    "bearer ",
    "cookie:",
    "session_token",
    "password",
    "private key",
    "credential",
    "secret=",
    "api_key=",
    "provider_native_tools",
    "provider-native tools",
    "fallback:auto",
)

TRUSTED_RUNTIME_CONTEXT_KEYS = frozenset(
    {
        "adapter_id",
        "authority",
        "backend_id",
        "decision_id",
        "execution_request_id",
        "kernel",
        "mission_id",
        "mission_workspace_manifest",
        "model_contract_ref",
        "organ_id",
        "parameter_hash",
        "product_task_resource_scope",
        "root_browser_runtime_lease",
        "simple_skill_id",
        "workspace_ref",
    }
)


class ActionKernelError(RuntimeError):
    pass


class ActionEnvelope(SentinelModel):
    action_id: str = Field(default_factory=lambda: new_id("action"))
    capability_id: str
    operation: str
    target_ref: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    authority_ref: str | None = None
    decision_ref: str | None = None
    expected_receipt_type: str | None = None
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _envelope_is_model_decision_not_authority(self) -> "ActionEnvelope":
        assert_data_not_authority(
            context="action_envelope",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        _reject_forbidden_material(self.safe_identity_payload(), context="action_envelope")
        _reject_forbidden_material(
            _params_for_forbidden_material_scan(self.capability_id, self.operation, self.params),
            context="action_envelope_params",
        )
        return self

    @property
    def action_hash(self) -> str:
        return stable_hash(
            {
                "capability_id": self.capability_id,
                "operation": self.operation,
                "target_ref": self.target_ref,
                "params": self.params,
            }
        )

    def safe_identity_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "capability_id": self.capability_id,
            "operation": self.operation,
            "target_ref": self.target_ref,
            "idempotency_key": self.idempotency_key,
            "authority_ref": self.authority_ref,
            "decision_ref": self.decision_ref,
            "expected_receipt_type": self.expected_receipt_type,
        }


class ActionResult(SentinelModel):
    action_id: str
    capability_id: str
    operation: str
    status: str
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    finalgate_refs: tuple[str, ...] = Field(default_factory=tuple)
    certificate_refs: tuple[str, ...] = Field(default_factory=tuple)
    material_action: bool = False
    observation_summary: str = ""
    blocked_reason: str | None = None
    failure_class: ActionFailureClass | None = None
    failure_code: str | None = None
    recoverable: bool = False
    recovery_observation: dict[str, Any] = Field(default_factory=dict)
    recommended_next_actions: tuple[str, ...] = Field(default_factory=tuple)
    result_hash: str = ""
    context_cards: dict[str, Any] = Field(default_factory=dict)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _result_is_evidence_not_authority(self) -> "ActionResult":
        assert_data_not_authority(
            context="action_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.result_hash:
            self.result_hash = stable_hash(self.safe_summary())
        return self

    def safe_summary(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "capability_id": self.capability_id,
            "operation": self.operation,
            "status": self.status,
            "receipt_refs": list(self.receipt_refs),
            "evidence_refs": list(self.evidence_refs),
            "finalgate_refs": list(self.finalgate_refs),
            "certificate_refs": list(self.certificate_refs),
            "material_action": self.material_action,
            "observation_summary": self.observation_summary[:500],
            "blocked_reason": self.blocked_reason,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "failure_code": self.failure_code,
            "recoverable": self.recoverable,
            "recovery_observation_hash": stable_hash(self.recovery_observation) if self.recovery_observation else None,
            "recommended_next_actions": list(self.recommended_next_actions),
            "result_hash": self.result_hash,
            "context_card_names": sorted(self.context_cards),
            "context_card_hashes": {
                key: stable_hash(value)
                for key, value in sorted(self.context_cards.items())
            },
        }


ActionExecutor = Callable[[ActionEnvelope, dict[str, Any]], ActionResult]


class ActionKernel:
    def __init__(self, executors: dict[str, ActionExecutor] | None = None) -> None:
        self._executors = dict(executors or {})
        self._normalizer = ActionAliasNormalizer()

    def register(self, capability_id: str, executor: ActionExecutor) -> None:
        if not capability_id.strip():
            raise ActionKernelError("capability id required")
        self._executors[capability_id] = executor

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        if authority.revoked_at is not None:
            raise ActionKernelError("mission_authority_inactive")
        envelope = self._normalizer.normalize(envelope)
        context = _effective_context_with_loop_context(context)
        if envelope.capability_id == "sentinel_loop" and envelope.operation == "finish":
            return ActionResult(
                action_id=envelope.action_id,
                capability_id=envelope.capability_id,
                operation=envelope.operation,
                status="completed",
                material_action=False,
                observation_summary=str(envelope.params.get("safe_summary") or "Task loop finished."),
            )
        if envelope.capability_id == "sentinel_loop" and envelope.operation == "summarize_evidence":
            return _summarize_evidence(envelope, context=context)
        executor = self._executors.get(envelope.capability_id)
        if executor is None:
            raise ActionKernelError(f"action_executor_missing:{envelope.capability_id}")
        try:
            return executor(envelope, context)
        except ActionKernelError as exc:
            failure = classify_action_execution_failure(exc, context=context)
            if failure.recoverable:
                return _recoverable_executor_result(envelope, failure=failure)
            raise
        except Exception as exc:  # noqa: BLE001
            failure = classify_action_execution_failure(exc, context=context)
            if failure.recoverable:
                return _recoverable_executor_result(envelope, failure=failure)
            raise ActionKernelError(failure.hard_stop_reason or failure.failure_code) from exc


def _effective_context_with_loop_context(context: dict[str, Any]) -> dict[str, Any]:
    loop_context = context.get("loop_context")
    if not isinstance(loop_context, dict):
        return context
    model_evidence = {
        str(key): value
        for key, value in loop_context.items()
        if str(key) not in TRUSTED_RUNTIME_CONTEXT_KEYS
    }
    merged = dict(context)
    merged.update(model_evidence)
    merged["model_evidence"] = model_evidence
    return merged


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered_key = str(key).lower()
            if any(marker in lowered_key for marker in FORBIDDEN_ACTION_PAYLOAD_MARKERS):
                if "provider_native" in lowered_key or "provider-native" in lowered_key:
                    raise ValueError(f"{context}: provider-native tools are forbidden")
                if "raw_provider" in lowered_key or lowered_key in {"raw_prompt", "raw_response", "raw_reasoning"}:
                    raise ValueError(f"{context}: raw provider material is forbidden")
                raise ValueError(f"{context}: credential or secret material is forbidden")
            _reject_forbidden_material(child, context=context)
        return
    if isinstance(value, list | tuple | set):
        for child in value:
            _reject_forbidden_material(child, context=context)
        return
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in FORBIDDEN_ACTION_PAYLOAD_MARKERS):
            if "provider_native" in lowered or "provider-native" in lowered:
                raise ValueError(f"{context}: provider-native tools are forbidden")
            if "raw_provider" in lowered or "raw prompt" in lowered or "raw response" in lowered:
                raise ValueError(f"{context}: raw provider material is forbidden")
            raise ValueError(f"{context}: credential or secret material is forbidden")


def _params_for_forbidden_material_scan(capability_id: str, operation: str, params: dict[str, Any]) -> dict[str, Any]:
    if capability_id != "real_browser_control" or operation != "real_browser.search":
        if capability_id == "sentinel_loop" and operation in {"finish", "summarize_evidence"}:
            return typed_terminal_semantic_scan_payload(params, context="action_envelope_params")
        return params
    return typed_browser_search_scan_payload(params, context="action_envelope_params")


def _recoverable_executor_result(envelope: ActionEnvelope, *, failure: Any) -> ActionResult:
    observation = recoverable_action_observation(
        failure_class=failure.failure_class,
        failure_code=failure.failure_code,
        attempted_action_hash=envelope.action_hash,
        safe_summary=failure.safe_summary,
        recommended_next_actions=failure.recommended_next_actions,
        refreshed_candidate_refs=failure.refreshed_candidate_refs,
    )
    return ActionResult(
        action_id=envelope.action_id,
        capability_id=envelope.capability_id,
        operation=envelope.operation,
        status="recoverable_failed",
        material_action=False,
        blocked_reason=failure.failure_code,
        failure_class=failure.failure_class,
        failure_code=failure.failure_code,
        recoverable=True,
        recovery_observation=observation.safe_model_dump(),
        recommended_next_actions=failure.recommended_next_actions,
        observation_summary=f"recoverable executor miss: {failure.failure_code}",
    )


def _summarize_evidence(envelope: ActionEnvelope, *, context: dict[str, Any]) -> ActionResult:
    summary = _grounded_evidence_summary(context)
    summary_hash = stable_hash(summary)
    return ActionResult(
        action_id=envelope.action_id,
        capability_id=envelope.capability_id,
        operation=envelope.operation,
        status="completed",
        material_action=False,
        observation_summary=(
            f"grounded browser evidence summary card_count={summary['card_count']} "
            f"summary_hash={summary_hash}."
        ),
        context_cards={"grounded_evidence_summary": summary},
    )


def _grounded_evidence_summary(context: dict[str, Any]) -> dict[str, Any]:
    cards = _browser_product_cards(context)
    if cards and not any(_card_value(card, "kind") == "product_candidate" for card in cards):
        return _grounded_open_world_evidence_summary(cards)
    safe_cards: list[dict[str, Any]] = []
    for card in cards[:5]:
        safe_cards.append(
            {
                "title": _card_value(card, "title"),
                "visible_price": _card_value(card, "visible_price"),
                "currency_or_unit": _card_value(card, "currency_or_unit"),
                "minimum_order": _card_value(card, "minimum_order"),
                "supplier_or_store": _card_value(card, "supplier_or_store"),
                "relevance_to_objective": _card_value(card, "relevance_to_objective"),
                "relevance_reason": _card_value(card, "relevance_reason"),
                "price_condition_supported": _card_value(card, "price_condition_supported"),
                "objective_relevance_assessed": _card_bool(card, "objective_relevance_assessed"),
                "caveats": _card_list(card, "caveats"),
                "short_features": _card_list(card, "short_features"),
                "evidence_ref_hash": _card_value(card, "evidence_ref_hash"),
                "confidence": _card_float(card, "confidence"),
            }
        )
    if not safe_cards and _has_confirmed_no_results_search(context):
        materiality = context.get("browser_search_materiality") if isinstance(context, dict) else {}
        outcome = materiality.get("typed_search_outcome") if isinstance(materiality, dict) else {}
        evidence_refs = outcome.get("evidence_refs") if isinstance(outcome, dict) else ()
        return {
            "summary_kind": "grounded_browser_negative_search_summary",
            "card_count": 0,
            "cards": [],
            "matched_products": [],
            "uncertain_products": [],
            "objective_relevance_assessed": True,
            "has_relevant_product_evidence": False,
            "under_price_condition_supported_by_visible_evidence": "not_supported",
            "summary_text": (
                "The bounded browser search completed with material request/query evidence, "
                "but the stabilized page showed no matching product result region."
            ),
            "negative_result_confirmed": True,
            "search_outcome_kind": "NO_RESULTS_CONFIRMED",
            "evidence_refs": tuple(str(ref) for ref in evidence_refs) if isinstance(evidence_refs, (list, tuple)) else (),
            "unknown_policy": "no_product_fields_invented_for_negative_search_result",
            "source": "browser_search_materiality_and_receipts",
            "data_not_authority": True,
            "authority_effect": "none",
            "can_execute": False,
        }
    matched = [
        card
        for card in safe_cards
        if card["relevance_to_objective"] in {"relevant", "partial"}
    ]
    uncertain = [
        card
        for card in matched
        if card["price_condition_supported"] in {"unknown", "not_supported"}
    ]
    price_support = _under_price_support(matched)
    relevance_assessed = bool(safe_cards) and all(bool(card["objective_relevance_assessed"]) for card in safe_cards)
    return {
        "summary_kind": "grounded_browser_evidence_summary",
        "card_count": len(safe_cards),
        "cards": safe_cards,
        "matched_products": [
            {
                "title": card["title"],
                "visible_price": card["visible_price"],
                "minimum_order": card["minimum_order"],
                "supplier_or_store": card["supplier_or_store"],
                "price_condition_supported": card["price_condition_supported"],
            }
            for card in matched
        ],
        "uncertain_products": [
            {
                "title": card["title"],
                "visible_price": card["visible_price"],
                "caveats": card["caveats"],
                "reason": "under-5-EUR condition is not directly supported by visible EUR evidence",
            }
            for card in uncertain
        ],
        "objective_relevance_assessed": relevance_assessed,
        "has_relevant_product_evidence": bool(matched),
        "under_price_condition_supported_by_visible_evidence": price_support,
        "summary_text": _grounded_summary_text(
            matched_count=len(matched),
            uncertain_count=len(uncertain),
            price_support=price_support,
        ),
        "unknown_policy": "unknown_fields_preserved_no_hallucinated_price_moq_supplier",
        "source": "browser_extraction_cards_and_receipts",
        "data_not_authority": True,
        "authority_effect": "none",
        "can_execute": False,
    }


def _grounded_open_world_evidence_summary(cards: list[Any]) -> dict[str, Any]:
    safe_entities: list[dict[str, Any]] = []
    for card in cards[:8]:
        safe_entities.append(
            {
                "kind": _card_value(card, "kind"),
                "entity_family": _card_value(card, "entity_family"),
                "entity_kind": _card_value(card, "entity_kind"),
                "title": _card_value(card, "title"),
                "relevance_to_objective": _card_value(card, "relevance_to_objective"),
                "relevance_reason": _card_value(card, "relevance_reason"),
                "objective_relevance_assessed": _card_bool(card, "objective_relevance_assessed"),
                "short_features": _card_list(card, "short_features"),
                "evidence_ref_hash": _card_value(card, "evidence_ref_hash"),
                "evidence_refs": _card_list(card, "evidence_refs"),
                "confidence": _card_float(card, "confidence"),
            }
        )
    assessed = bool(safe_entities) and all(entity["objective_relevance_assessed"] for entity in safe_entities)
    relevant = [entity for entity in safe_entities if entity["relevance_to_objective"] in {"relevant", "partial"}]
    status = "supported" if any(entity["relevance_to_objective"] == "relevant" for entity in relevant) else "partial" if relevant else "uncertain"
    return {
        "summary_kind": "grounded_browser_open_world_evidence_summary",
        "card_count": len(safe_entities),
        "entities": safe_entities,
        "cards": safe_entities,
        "objective_relevance_assessed": assessed,
        "objective_satisfaction_status": status,
        "has_relevant_product_evidence": False,
        "unsupported_claims": 0,
        "summary_text": _open_world_summary_text(entity_count=len(safe_entities), status=status),
        "unknown_policy": "unknown_fields_preserved_no_closed_ontology_forced",
        "source": "browser_open_world_extraction_cards_and_receipts",
        "data_not_authority": True,
        "authority_effect": "none",
        "can_execute": False,
    }


def _open_world_summary_text(*, entity_count: int, status: str) -> str:
    return (
        f"Open-world browser evidence entities: {entity_count}. "
        f"Objective support: {status}. "
        "Entity kinds remain extensible; unknown fields stay unknown and no product, price, MOQ, or supplier claim is inferred."
    )


def _browser_product_cards(context: dict[str, Any]) -> list[Any]:
    cards = _cards_from_context_obj(context.get("browser_world_model"))
    if cards:
        return cards
    frame = context.get("browser_decision_frame")
    if isinstance(frame, dict):
        candidates = frame.get("candidate_extractions")
        if isinstance(candidates, list):
            return candidates
    summary = context.get("browser_world_model_summary")
    if isinstance(summary, dict) and int(summary.get("product_or_result_candidate_count") or 0) > 0:
        return []
    return []


def _has_confirmed_no_results_search(context: dict[str, Any]) -> bool:
    materiality = context.get("browser_search_materiality") if isinstance(context, dict) else None
    if not isinstance(materiality, dict):
        return False
    outcome = materiality.get("typed_search_outcome")
    if not isinstance(outcome, dict):
        return False
    return bool(
        outcome.get("outcome_kind") == "NO_RESULTS_CONFIRMED"
        and outcome.get("search_materially_successful") is True
    )


def _cards_from_context_obj(value: Any) -> list[Any]:
    if isinstance(value, dict):
        cards = value.get("product_or_result_candidate_cards")
        return list(cards) if isinstance(cards, list) else []
    cards = getattr(value, "product_or_result_candidate_cards", None)
    if cards is not None:
        return list(cards)
    return []


def _card_value(card: Any, key: str) -> str:
    value = card.get(key) if isinstance(card, dict) else getattr(card, key, None)
    rendered = str(value).strip() if value is not None else ""
    return rendered[:240] if rendered else "unknown"


def _card_list(card: Any, key: str) -> list[str]:
    value = card.get(key) if isinstance(card, dict) else getattr(card, key, None)
    if isinstance(value, str):
        return [value[:240]] if value.strip() else ["unknown"]
    if isinstance(value, list | tuple):
        rendered = [str(item).strip()[:240] for item in value if str(item).strip()]
        return rendered or ["unknown"]
    return ["unknown"]


def _card_float(card: Any, key: str) -> float:
    value = card.get(key) if isinstance(card, dict) else getattr(card, key, None)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _card_bool(card: Any, key: str) -> bool:
    value = card.get(key) if isinstance(card, dict) else getattr(card, key, None)
    return bool(value)


def _under_price_support(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return "no_relevant_products"
    values = {str(card.get("price_condition_supported") or "unknown") for card in cards}
    if "supported" in values:
        return "supported"
    if values == {"not_supported"}:
        return "not_supported"
    return "unknown"


def _grounded_summary_text(*, matched_count: int, uncertain_count: int, price_support: str) -> str:
    return (
        f"Matching products: {matched_count}. "
        f"Uncertain products: {uncertain_count}. "
        f"Under-5-EUR visible evidence: {price_support}. "
        "Unknown fields remain unknown; no landed-cost, shipping, MOQ, supplier, or currency claim is inferred."
    )


__all__ = ["ActionEnvelope", "ActionKernel", "ActionKernelError", "ActionResult", "ActionExecutor"]
