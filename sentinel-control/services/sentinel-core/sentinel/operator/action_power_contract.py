from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.shared.models import SentinelModel, new_id


class ActionFailureClass(StrEnum):
    HARD_STOP_REAL_DAMAGE = "HARD_STOP_REAL_DAMAGE"
    HARD_STOP_OUT_OF_SCOPE_AUTHORITY = "HARD_STOP_OUT_OF_SCOPE_AUTHORITY"
    RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE = "RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE"
    RECOVERABLE_MODEL_PROTOCOL_FAILURE = "RECOVERABLE_MODEL_PROTOCOL_FAILURE"
    RECOVERABLE_BROWSER_STATE_FAILURE = "RECOVERABLE_BROWSER_STATE_FAILURE"
    AUTHORITY_ALIAS_OR_MAPPING_BUG = "AUTHORITY_ALIAS_OR_MAPPING_BUG"
    ACTIONABILITY_CONTRACT_VIOLATION = "ACTIONABILITY_CONTRACT_VIOLATION"
    CONTEXT_TOO_THIN = "CONTEXT_TOO_THIN"
    BUDGET_TOO_STRICT = "BUDGET_TOO_STRICT"
    FALSE_SUCCESS_PREVENTION = "FALSE_SUCCESS_PREVENTION"
    SOURCE_BUG_OR_RUNTIME_INVARIANT = "SOURCE_BUG_OR_RUNTIME_INVARIANT"


class RecoverableActionObservation(SentinelModel):
    observation_id: str = Field(default_factory=lambda: new_id("recoverable_action_obs"))
    failure_class: ActionFailureClass
    failure_code: str
    attempted_action_hash: str
    safe_summary: str
    recommended_next_actions: tuple[str, ...] = Field(default_factory=tuple)
    refreshed_candidate_refs: tuple[str, ...] = Field(default_factory=tuple)
    recovery_budget_remaining: int | None = None
    material_effect: bool = False
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ActionabilityRef(SentinelModel):
    canonical_ref: str
    accepted_aliases: tuple[str, ...] = Field(default_factory=tuple)
    role: str
    safe_name: str = ""
    selector_hash: str = ""
    resolver_handle: str = ""
    visible: bool = True
    enabled: bool = True
    secret: bool = False
    state_hash: str = ""
    confidence: float = 0.5
    source: str = "runtime_snapshot"

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ActionabilityFrame(SentinelModel):
    frame_id: str = Field(default_factory=lambda: new_id("actionability_frame"))
    source_runtime: str
    state_hash: str
    epoch: int = 0
    canonical_action_id: str
    capability_id: str
    operation: str
    param_schema: dict[str, Any] = Field(default_factory=dict)
    executable_refs: tuple[str, ...] = Field(default_factory=tuple)
    accepted_aliases: tuple[str, ...] = Field(default_factory=tuple)
    blocked_refs: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    recovery_actions: tuple[str, ...] = Field(default_factory=tuple)
    proof_actions: tuple[str, ...] = Field(default_factory=tuple)
    finish_actions: tuple[str, ...] = ("sentinel_loop.finish",)

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class BrowserActionabilityRegistry(SentinelModel):
    registry_id: str = Field(default_factory=lambda: new_id("browser_actionability_registry"))
    browser_state_hash: str
    world_model_id: str
    decision_frame_id: str
    generated_at_turn: int = 0
    canonical_refs: tuple[ActionabilityRef, ...] = Field(default_factory=tuple)
    accepted_aliases: dict[str, str] = Field(default_factory=dict)
    candidate_actions: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    blocked_refs: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    recovery_actions: tuple[str, ...] = ("real_browser_control.real_browser.observe",)
    expires_on_navigation: bool = True

    def resolve_ref(self, ref: str) -> str | None:
        if any(item.canonical_ref == ref for item in self.canonical_refs):
            return ref
        return self.accepted_aliases.get(ref)

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ActionAliasNormalizer:
    def normalize(self, envelope: Any) -> Any:
        capability_id, operation = canonical_action_parts(
            str(getattr(envelope, "capability_id", "")),
            str(getattr(envelope, "operation", "")),
        )
        if capability_id == getattr(envelope, "capability_id", None) and operation == getattr(envelope, "operation", None):
            return envelope
        return envelope.model_copy(update={"capability_id": capability_id, "operation": operation})

    def normalize_action_name(self, action_name: str) -> str:
        capability_id, operation = action_name_parts(action_name)
        canonical_capability, canonical_operation = canonical_action_parts(capability_id, operation)
        return f"{canonical_capability}.{canonical_operation}"


def action_name_parts(action_name: str) -> tuple[str, str]:
    if action_name == "finish":
        return "finish", "finish"
    if "." not in action_name:
        return action_name, action_name
    capability_id, operation = action_name.split(".", 1)
    return capability_id, operation


def canonical_action_parts(capability_id: str, operation: str) -> tuple[str, str]:
    capability_id = capability_id.strip()
    operation = operation.strip()
    if capability_id in {"finish", "sentinel_finish"} or operation == "finish":
        return "sentinel_loop", "finish"
    if capability_id == "read_only":
        return "read_only_research", operation
    if capability_id == "real_browser":
        return "real_browser_control", _prefix_operation(operation, "real_browser")
    if capability_id == "real_browser_control":
        return capability_id, _prefix_operation(operation, "real_browser")
    if capability_id == "browser":
        return "browser_control", _prefix_operation(operation, "browser")
    if capability_id == "browser_control":
        return capability_id, _prefix_operation(operation, "browser")
    if capability_id == "channel_transport" and operation == "send_message":
        return "bounded_channel", "send_message"
    if capability_id == "channel":
        return "bounded_channel", operation
    return capability_id, operation


def _prefix_operation(operation: str, prefix: str) -> str:
    if not operation:
        return operation
    if operation.startswith(f"{prefix}."):
        return operation
    return f"{prefix}.{operation}"


def build_browser_actionability_registry(
    *,
    browser_state_hash: str,
    world_model: Any,
    decision_frame: Any,
    generated_at_turn: int = 0,
) -> BrowserActionabilityRegistry:
    canonical_refs = tuple(_actionability_ref(ref) for ref in getattr(world_model, "stable_refs", ()))
    product_cards = tuple(getattr(world_model, "product_or_result_candidate_cards", ()) or ())
    alias_map: dict[str, str] = {}
    for item in canonical_refs:
        for alias in item.accepted_aliases:
            alias_map.setdefault(alias, item.canonical_ref)
    candidate_actions = tuple(_candidate_action(action, alias_map=alias_map) for action in getattr(decision_frame, "candidate_actions", ()))
    return BrowserActionabilityRegistry(
        browser_state_hash=browser_state_hash,
        world_model_id=str(getattr(world_model, "world_model_id", "")),
        decision_frame_id=str(getattr(decision_frame, "frame_id", "")),
        generated_at_turn=generated_at_turn,
        canonical_refs=canonical_refs,
        accepted_aliases=alias_map,
        candidate_actions=candidate_actions,
        blocked_refs=tuple(_blocked_ref(ref) for ref in getattr(world_model, "stable_refs", ()) if getattr(ref, "secret", False)),
        recovery_actions=_browser_recovery_actions(product_cards_present=_has_actionable_browser_cards(product_cards)),
    )


def build_browser_actionability_frame(
    *,
    browser_state_hash: str,
    registry: BrowserActionabilityRegistry,
    decision_frame: Any,
) -> ActionabilityFrame:
    executable_refs = tuple(dict.fromkeys([ref.canonical_ref for ref in registry.canonical_refs] + sorted(registry.accepted_aliases)))
    accepted_action_aliases = tuple(
        dict.fromkeys(
            [
                "real_browser.observe",
                "real_browser.search",
                "real_browser.inspect_result",
                "real_browser.open_result",
                "real_browser.extract_evidence",
                "real_browser.extract_entities",
                "real_browser.extract_product_cards",
                "real_browser.verify_extraction",
                "real_browser_control.real_browser.observe",
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.inspect_result",
                "real_browser_control.real_browser.open_result",
                "real_browser_control.real_browser.extract_evidence",
                "real_browser_control.real_browser.extract_entities",
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.verify_extraction",
            ]
        )
    )
    candidate_actions = tuple(getattr(decision_frame, "candidate_actions", ()))
    first_action = candidate_actions[0] if candidate_actions else {}
    operation = str(first_action.get("action") or "real_browser.observe") if isinstance(first_action, dict) else "real_browser.observe"
    return ActionabilityFrame(
        source_runtime="real_browser_control",
        state_hash=browser_state_hash,
        canonical_action_id=f"real_browser_control.{operation}",
        capability_id="real_browser_control",
        operation=operation,
        param_schema={
            "capability_id": "real_browser_control",
            "operation": "real_browser.<operation>",
            "params": {"ref": "stable ref or accepted alias when action needs a ref"},
        },
        executable_refs=executable_refs,
        accepted_aliases=accepted_action_aliases,
        blocked_refs=registry.blocked_refs,
        recovery_actions=registry.recovery_actions,
        proof_actions=(
            "real_browser_control.real_browser.verify_extraction",
            "real_browser_control.real_browser.extract_evidence",
            "real_browser_control.real_browser.extract_entities",
            "real_browser_control.real_browser.extract_product_cards",
        ),
        finish_actions=("sentinel_loop.finish",),
    )


def recoverable_action_observation(
    *,
    failure_class: ActionFailureClass,
    failure_code: str,
    attempted_action_hash: str,
    safe_summary: str,
    recommended_next_actions: tuple[str, ...] = (),
    refreshed_candidate_refs: tuple[str, ...] = (),
    recovery_budget_remaining: int | None = None,
) -> RecoverableActionObservation:
    return RecoverableActionObservation(
        failure_class=failure_class,
        failure_code=failure_code,
        attempted_action_hash=attempted_action_hash,
        safe_summary=safe_summary,
        recommended_next_actions=recommended_next_actions,
        refreshed_candidate_refs=refreshed_candidate_refs,
        recovery_budget_remaining=recovery_budget_remaining,
    )


def _browser_recovery_actions(*, product_cards_present: bool) -> tuple[str, ...]:
    if product_cards_present:
        return (
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "real_browser_control.real_browser.observe",
        )
    return (
            "real_browser_control.real_browser.observe",
            "real_browser_control.real_browser.extract_evidence",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.extract_product_cards",
        )


def _has_actionable_browser_cards(cards: tuple[Any, ...]) -> bool:
    for card in cards:
        if float(getattr(card, "confidence", 0.0) or 0.0) >= 0.5:
            return True
        for field in ("visible_price", "minimum_order", "supplier_or_store"):
            value = str(getattr(card, field, "") or "").strip().lower()
            if value and value != "unknown":
                return True
    return False


def _actionability_ref(ref: Any) -> ActionabilityRef:
    canonical_ref = str(getattr(ref, "ref", ""))
    role = str(getattr(ref, "role", "element"))
    name = str(getattr(ref, "name", ""))
    aliases = _accepted_ref_aliases(canonical_ref=canonical_ref, role=role, name=name)
    return ActionabilityRef(
        canonical_ref=canonical_ref,
        accepted_aliases=aliases,
        role=role,
        safe_name=name[:120],
        selector_hash=text_hash(canonical_ref),
        resolver_handle=f"browser_ref:{text_hash(canonical_ref)}",
        visible=bool(getattr(ref, "visible", True)),
        enabled=bool(getattr(ref, "enabled", True)),
        secret=bool(getattr(ref, "secret", False)),
        state_hash=stable_hash({"ref": canonical_ref, "role": role, "name": name}),
        confidence=0.86 if aliases else 0.65,
        source="browser_world_model",
    )


def _accepted_ref_aliases(*, canonical_ref: str, role: str, name: str) -> tuple[str, ...]:
    aliases = [canonical_ref]
    lowered = f"{canonical_ref} {role} {name}".lower()
    if role in {"textbox", "searchbox", "combobox"} and any(marker in lowered for marker in ("search", "query", "product")):
        aliases.extend(["search_box", "search_input", "primary_search_control"])
    if role == "textbox":
        aliases.append("textbox")
    if role == "button":
        aliases.append(_safe_alias(name, suffix="button"))
    if role == "link":
        aliases.extend(["first_result_link", _safe_alias(name, suffix="link")])
    return tuple(alias for alias in dict.fromkeys(aliases) if alias)


def _safe_alias(name: str, *, suffix: str) -> str:
    cleaned = "_".join(part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in name).split()[:4])
    if not cleaned:
        return ""
    return f"{cleaned}_{suffix}"


def _candidate_action(action: Any, *, alias_map: dict[str, str]) -> dict[str, Any]:
    payload = dict(action) if isinstance(action, dict) else {}
    action_name = str(payload.get("action") or "")
    canonical_action_id = f"real_browser_control.{action_name}" if action_name.startswith("real_browser.") else action_name
    ref = payload.get("ref")
    if isinstance(ref, str) and ref in alias_map:
        payload["canonical_ref"] = alias_map[ref]
    payload["canonical_action_id"] = canonical_action_id
    return payload


def _blocked_ref(ref: Any) -> dict[str, Any]:
    return {
        "ref_hash": text_hash(str(getattr(ref, "ref", ""))),
        "role": str(getattr(ref, "role", "element")),
        "reason": "secret_or_non_executable",
    }


__all__ = [
    "ActionAliasNormalizer",
    "ActionFailureClass",
    "ActionabilityFrame",
    "ActionabilityRef",
    "BrowserActionabilityRegistry",
    "RecoverableActionObservation",
    "build_browser_actionability_frame",
    "build_browser_actionability_registry",
    "recoverable_action_observation",
]
