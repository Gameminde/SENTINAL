from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_power_contract import ActionAliasNormalizer, ActionFailureClass
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
        _reject_forbidden_material(self.params, context="action_envelope_params")
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
        if envelope.capability_id == "sentinel_loop" and envelope.operation == "finish":
            return ActionResult(
                action_id=envelope.action_id,
                capability_id=envelope.capability_id,
                operation=envelope.operation,
                status="completed",
                material_action=False,
                observation_summary=str(envelope.params.get("safe_summary") or "Task loop finished."),
            )
        executor = self._executors.get(envelope.capability_id)
        if executor is None:
            raise ActionKernelError(f"action_executor_missing:{envelope.capability_id}")
        try:
            return executor(envelope, context)
        except ActionKernelError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ActionKernelError(str(exc) or exc.__class__.__name__) from exc


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


__all__ = ["ActionEnvelope", "ActionKernel", "ActionKernelError", "ActionResult", "ActionExecutor"]
