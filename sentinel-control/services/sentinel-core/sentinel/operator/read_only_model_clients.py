from __future__ import annotations

import json
from typing import Any

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.policy import ModelExecutionBudgetPolicy, ModelRetryPolicy, ModelTimeoutPolicy
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.llm_adapter import OperatorModelClient
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyDecision,
    ReadOnlyFailureCode,
    ReadOnlyReportResult,
    ReadOnlySpineError,
)
from sentinel.operator.redaction import redact_operator_value, sanitize_operator_refs


_PROVIDER_MATERIAL_KEYS = frozenset(
    {
        "raw_provider_response",
        "raw_response",
        "raw_text",
        "raw_text_in_memory_only",
        "provider_wrapper",
        "provider_payload",
        "reasoning",
        "reasoning_content",
        "raw_reasoning",
        "chain_of_thought",
    }
)


class ReadOnlyProviderDecisionClient:
    """Provider-backed read-only exploration decisions using the explicit model contract."""

    def __init__(
        self,
        *,
        user_model_contract: UserModelContract,
        model_client: OperatorModelClient,
        max_output_tokens: int | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._contract = user_model_contract
        self._model_client = model_client
        self._max_output_tokens = max_output_tokens or user_model_contract.context_budget_policy.reserve_output_tokens
        self._timeout_seconds = timeout_seconds
        self.call_count = 0

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        self.call_count += 1
        prompt = _decision_prompt(context)
        request = _request(
            contract=self._contract,
            lane="exploration_decision",
            prompt=prompt,
            max_output_tokens=self._max_output_tokens,
            timeout_seconds=self._timeout_seconds,
            metadata={
                "mission_id": context.get("mission_id"),
                "status": context.get("status"),
                "observation_count": len(context.get("observations", [])),
                "legal_actions": list(context.get("legal_actions", [])),
            },
        )
        raw = self._model_client.complete(request)
        _raise_if_blocked(raw, phase="model_decision")
        try:
            return ReadOnlyDecision.model_validate(_typed_visible_content(raw))
        except Exception as exc:  # noqa: BLE001
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
                phase="model_decision",
                exception_class=exc.__class__.__name__,
                legacy_reason="read_only_decision_schema_invalid",
            ) from exc


class ReadOnlyProviderReportClient:
    """Separate provider-backed report lane for sanitized read-only reports."""

    def __init__(
        self,
        *,
        user_model_contract: UserModelContract,
        model_client: OperatorModelClient,
        max_output_tokens: int | None = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        self._contract = user_model_contract
        self._model_client = model_client
        reserve = user_model_contract.context_budget_policy.reserve_output_tokens
        self._max_output_tokens = max_output_tokens or max(reserve * 4, reserve + 500)
        self._timeout_seconds = timeout_seconds
        self.call_count = 0

    def complete(self, context: dict[str, Any]) -> ReadOnlyReportResult:
        self.call_count += 1
        evidence_refs = _context_evidence_refs(context)
        prompt = _report_prompt(context, evidence_refs=evidence_refs)
        request = _request(
            contract=self._contract,
            lane="final_report",
            prompt=prompt,
            max_output_tokens=self._max_output_tokens,
            timeout_seconds=self._timeout_seconds,
            metadata={
                "mission_id": context.get("mission_id"),
                "observation_count": len(context.get("observations", [])),
                "receipt_ref_count": len(context.get("receipt_refs", [])),
                "evidence_refs": evidence_refs,
            },
        )
        raw = self._model_client.complete(request)
        _raise_if_blocked(raw, phase="final_report")
        try:
            return ReadOnlyReportResult.model_validate(_typed_visible_content(raw))
        except Exception as exc:  # noqa: BLE001
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
                phase="final_report",
                exception_class=exc.__class__.__name__,
                legacy_reason="read_only_report_schema_invalid",
            ) from exc


def _request(
    *,
    contract: UserModelContract,
    lane: str,
    prompt: str,
    max_output_tokens: int,
    timeout_seconds: float,
    metadata: dict[str, Any],
) -> RealModelRequest:
    timeout_policy = ModelTimeoutPolicy(
        connect_timeout_seconds=2.0,
        read_timeout_seconds=timeout_seconds,
        total_timeout_seconds=timeout_seconds + 2.0,
    )
    retry_policy = ModelRetryPolicy(max_attempts=1, retryable_outcomes=[])
    budget_policy = ModelExecutionBudgetPolicy(
        max_input_tokens=contract.context_budget_policy.max_decision_frame_tokens
        + contract.context_budget_policy.max_evidence_tokens,
        max_output_tokens=max_output_tokens,
        max_total_estimated_usd=max(contract.cost_profile.input_usd_per_1m, contract.cost_profile.output_usd_per_1m, 0.0),
    )
    safe_metadata = {
        "read_only_lane": lane,
        "selected_provider_id": contract.selected_provider_id,
        "selected_backend_id": contract.selected_backend_id,
        "selected_model": contract.selected_model,
        "routing_policy": "explicit_user_model_contract_only",
        **redact_operator_value(metadata),
    }
    payload = {
        "provider_id": contract.selected_provider_id,
        "backend_id": contract.selected_backend_id,
        "model_id": contract.selected_model,
        "lane": lane,
        "prompt_hash": text_hash(prompt),
        "user_model_contract_id": contract.id,
        "request_metadata": safe_metadata,
    }
    return RealModelRequest(
        provider_id=contract.selected_provider_id,
        model_id=contract.selected_model,
        backend_id=contract.selected_backend_id,
        backend=contract.selected_backend_id,
        runtime="read_only_research_product",
        prompt_hash=text_hash(prompt),
        frame_hash=stable_hash({"lane": lane, "metadata": safe_metadata}),
        user_model_contract_id=contract.id,
        estimated_input_tokens=max(1, len(prompt) // 4),
        estimated_output_tokens=max_output_tokens,
        prompt_text_in_memory_only=prompt,
        request_metadata=safe_metadata,
        timeout_policy_id=timeout_policy.id,
        retry_policy_id=retry_policy.id,
        budget_policy_id=budget_policy.id,
        request_hash=stable_hash(payload),
    )


def _decision_prompt(context: dict[str, Any]) -> str:
    payload = {
        "task": "Return exactly one read-only exploration decision JSON object.",
        "allowed_actions": ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        "schema": {
            "action": "enum",
            "arguments": "object",
            "evidence_refs": "list[str]",
            "operator_message": "optional short display text",
        },
        "context": _safe_context(context),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _report_prompt(context: dict[str, Any], *, evidence_refs: list[str]) -> str:
    payload = {
        "task": "Return a sanitized evidence-linked read-only report JSON object.",
        "schema": {"report_text": "string", "evidence_refs": "list[str]"},
        "rules": [
            "Reference only provided evidence refs.",
            "Do not claim writes, external actions, credential access, or authority grants.",
        ],
        "evidence_refs": evidence_refs,
        "context": _safe_context(context),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _safe_context(context: dict[str, Any]) -> dict[str, Any]:
    return redact_operator_value(
        {
            "mission_id": context.get("mission_id"),
            "status": context.get("status"),
            "observations": context.get("observations", []),
            "receipt_refs": context.get("receipt_refs", []),
            "legal_actions": context.get("legal_actions", []),
        }
    )


def _context_evidence_refs(context: dict[str, Any]) -> list[str]:
    return sanitize_operator_refs(
        [
            str(item.get("evidence_ref"))
            for item in context.get("observations", [])
            if isinstance(item, dict) and item.get("evidence_ref")
        ]
    )


def _raise_if_blocked(raw: dict[str, Any], *, phase: str) -> None:
    blocked_reason = None
    if isinstance(raw.get("metadata"), dict):
        blocked_reason = raw["metadata"].get("blocked_reason")
    blocked_reason = blocked_reason or raw.get("blocked_reason")
    if blocked_reason:
        raise ReadOnlySpineError(
            ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
            phase=phase,
            legacy_reason=str(blocked_reason),
        )


def _typed_visible_content(raw: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in raw.items() if key not in _PROVIDER_MATERIAL_KEYS}


__all__ = [
    "ReadOnlyProviderDecisionClient",
    "ReadOnlyProviderReportClient",
]
