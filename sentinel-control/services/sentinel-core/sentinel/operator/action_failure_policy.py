from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


_HARD_STOP_MARKERS = (
    "recipient_not_allowed",
    "workspace_escape",
    "outside_workspace",
    "out_of_scope",
    "authority",
    "mission_authority_inactive",
    "credential",
    "authorization",
    "secret",
    "network_arg",
    "network_blocked",
    "payment",
    "checkout",
    "provider_native",
    "provider-native",
    "fallback:auto",
)

_RECOVERABLE_MARKERS = (
    "timeout",
    "timed out",
    "locator",
    "stale",
    "hidden",
    "disabled",
    "not found",
    "not visible",
    "dynamic loading",
    "schema",
    "alias",
    "unknown ref",
    "candidate not found",
    "transport_missing",
    "channel_transport_missing",
)


class ActionExecutionFailureDecision(SentinelModel):
    recoverable: bool
    failure_class: ActionFailureClass
    failure_code: str
    safe_summary: str
    hard_stop_reason: str | None = None
    recommended_next_actions: tuple[str, ...] = Field(default_factory=tuple)
    refreshed_candidate_refs: tuple[str, ...] = Field(default_factory=tuple)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _decision_is_data_only(self) -> "ActionExecutionFailureDecision":
        assert_data_not_authority(
            context="action_execution_failure_decision",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


def classify_action_execution_failure(
    exc: BaseException,
    *,
    context: dict[str, Any],
) -> ActionExecutionFailureDecision:
    reason = str(exc) or exc.__class__.__name__
    lowered = reason.lower()
    if any(marker in lowered for marker in _HARD_STOP_MARKERS):
        return ActionExecutionFailureDecision(
            recoverable=False,
            failure_class=ActionFailureClass.HARD_STOP_OUT_OF_SCOPE_AUTHORITY,
            failure_code=reason,
            safe_summary="Executor reported a hard stop boundary.",
            hard_stop_reason=reason,
        )
    if isinstance(exc, TimeoutError) or any(marker in lowered for marker in _RECOVERABLE_MARKERS):
        return ActionExecutionFailureDecision(
            recoverable=True,
            failure_class=ActionFailureClass.RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE,
            failure_code=_recoverable_failure_code(exc, lowered),
            safe_summary="In-scope runtime action failed before material effect; recovery context is available.",
            recommended_next_actions=_recommended_actions(context),
            refreshed_candidate_refs=_candidate_refs(context),
        )
    return ActionExecutionFailureDecision(
        recoverable=False,
        failure_class=ActionFailureClass.SOURCE_BUG_OR_RUNTIME_INVARIANT,
        failure_code="EXECUTOR_UNCLASSIFIED_FAILURE",
        safe_summary="Executor failed with an unclassified runtime invariant.",
        hard_stop_reason=reason,
    )


def _recoverable_failure_code(exc: BaseException, lowered_reason: str) -> str:
    if isinstance(exc, TimeoutError) or "timeout" in lowered_reason or "timed out" in lowered_reason:
        return "EXECUTOR_TIMEOUT"
    if "locator" in lowered_reason or "unknown ref" in lowered_reason:
        return "EXECUTOR_REF_NOT_ACTIONABLE"
    if "hidden" in lowered_reason or "disabled" in lowered_reason or "not visible" in lowered_reason:
        return "EXECUTOR_ELEMENT_NOT_ACTIONABLE"
    if "stale" in lowered_reason or "dynamic loading" in lowered_reason:
        return "EXECUTOR_STATE_STALE"
    if "schema" in lowered_reason or "alias" in lowered_reason:
        return "EXECUTOR_ACTIONABILITY_CONTRACT_MISS"
    return "EXECUTOR_RECOVERABLE_RUNTIME_MISS"


def _recommended_actions(context: dict[str, Any]) -> tuple[str, ...]:
    for key in ("model_visible_next_recommended_actions", "next_recommended_actions", "available_actions"):
        value = context.get(key)
        if isinstance(value, list | tuple):
            return tuple(str(item) for item in value[:6])
    return ()


def _candidate_refs(context: dict[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for key in ("search_like_controls", "top_stable_refs", "top_link_candidates"):
        value = context.get(key)
        if not isinstance(value, list | tuple):
            continue
        for item in value[:8]:
            if isinstance(item, dict):
                ref = item.get("ref") or item.get("canonical_ref")
                if ref:
                    refs.append(str(ref))
            else:
                refs.append(str(item))
    return tuple(dict.fromkeys(refs))


__all__ = ["ActionExecutionFailureDecision", "classify_action_execution_failure"]
