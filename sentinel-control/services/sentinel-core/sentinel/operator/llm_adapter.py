from __future__ import annotations

from typing import Any, Protocol

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.policy import (
    ModelExecutionBudgetPolicy,
    ModelRetryPolicy,
    ModelTimeoutPolicy,
)
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.llm_frame import OperatorConversationFrame
from sentinel.operator.models import OperatorLLMDecisionResult, OperatorMode
from sentinel.operator.prompt_renderer import OperatorPromptRenderer
from sentinel.operator.structured_output import (
    COCKPIT_MISSION_UNDERSTANDING_V2,
    OperatorStructuredOutputError,
    validate_operator_structured_output,
)


class OperatorLLMModeError(ValueError):
    """Raised when product LLM mode lacks an explicit model contract."""


class OperatorModelClient(Protocol):
    def complete(self, request: RealModelRequest) -> dict[str, Any]:
        ...


class OperatorLLMConversationAdapter:
    def __init__(
        self,
        *,
        mode: OperatorMode,
        user_model_contract: UserModelContract | None = None,
        model_client: OperatorModelClient | None = None,
        prompt_renderer: OperatorPromptRenderer | None = None,
        telemetry_sink: object | None = None,
        require_mission_understanding_v2: bool = False,
    ) -> None:
        if mode is OperatorMode.LLM_OPERATOR and user_model_contract is None:
            raise OperatorLLMModeError("llm_operator_mode requires explicit UserModelContract")
        self._mode = mode
        self._contract = user_model_contract
        self._client = model_client
        self._renderer = prompt_renderer or OperatorPromptRenderer()
        self._telemetry_sink = telemetry_sink
        self._required_protocol_version = (
            COCKPIT_MISSION_UNDERSTANDING_V2 if require_mission_understanding_v2 else None
        )

    def complete(self, frame: OperatorConversationFrame) -> OperatorLLMDecisionResult:
        if self._mode is not OperatorMode.LLM_OPERATOR:
            raise OperatorLLMModeError("OperatorLLMConversationAdapter only handles llm_operator_mode")
        if self._contract is None:
            raise OperatorLLMModeError("llm_operator_mode requires explicit UserModelContract")
        if self._client is None:
            self._record_model_completion(
                frame=frame,
                blocked_reason="missing_operator_model_client",
                schema_invalid=True,
                provider_response_hash=None,
                reasoning_hash=None,
            )
            return _fail_closed(
                mode=self._mode,
                contract=self._contract,
                reason="missing_operator_model_client",
                reply="I cannot run LLM operator mode because no explicit model client is configured.",
            )

        prompt = self._renderer.render(frame)
        request = _build_operator_model_request(frame=frame, prompt=prompt, contract=self._contract)
        self._record_model_start(request=request, frame=frame)
        raw_output = self._client.complete(request)
        try:
            result = validate_operator_structured_output(
                raw_output,
                mode=self._mode,
                provider_id=self._contract.selected_provider_id,
                backend_id=self._contract.selected_backend_id,
                model_id=self._contract.selected_model,
                required_protocol_version=self._required_protocol_version,
            )
            self._record_model_completion(
                frame=frame,
                request=request,
                decision=result,
                provider_response_hash=result.provider_response_hash,
                reasoning_hash=result.reasoning_hash,
                schema_invalid=False,
            )
            return result
        except OperatorStructuredOutputError as exc:
            self._record_model_completion(
                frame=frame,
                request=request,
                blocked_reason="invalid_structured_output",
                provider_response_hash=None,
                reasoning_hash=None,
                schema_invalid=True,
                diagnostics=exc.diagnostics,
            )
            return _fail_closed(
                mode=self._mode,
                contract=self._contract,
                reason="invalid_structured_output",
                reply="I could not validate the LLM operator output, so I will ask for a safer clarification instead.",
                diagnostics=exc.diagnostics,
            )

    def _record_model_start(self, *, request: RealModelRequest, frame: OperatorConversationFrame) -> None:
        if self._telemetry_sink is None or not hasattr(self._telemetry_sink, "record_model_call_started"):
            return
        self._telemetry_sink.record_model_call_started(
            request,
            session_id=frame.session_id,
            frame_hash=frame.prompt_hash,
        )

    def _record_model_completion(
        self,
        *,
        frame: OperatorConversationFrame,
        request: RealModelRequest | None = None,
        decision: OperatorLLMDecisionResult | None = None,
        blocked_reason: str | None = None,
        provider_response_hash: str | None = None,
        reasoning_hash: str | None = None,
        schema_invalid: bool,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        if self._telemetry_sink is None:
            return
        request = request or _build_operator_model_request(
            frame=frame,
            prompt=frame.safe_user_message,
            contract=self._contract,  # type: ignore[arg-type]
        )
        if hasattr(self._telemetry_sink, "record_model_call_completed"):
            self._telemetry_sink.record_model_call_completed(
                request,
                decision=decision,
                provider_response_hash=provider_response_hash,
                reasoning_hash=reasoning_hash,
                session_id=frame.session_id,
                blocked_reason=blocked_reason,
                schema_invalid=schema_invalid,
                diagnostics=diagnostics,
            )


def _build_operator_model_request(
    *,
    frame: OperatorConversationFrame,
    prompt: str,
    contract: UserModelContract,
) -> RealModelRequest:
    timeout_policy = ModelTimeoutPolicy(
        connect_timeout_seconds=2.0,
        read_timeout_seconds=10.0,
        total_timeout_seconds=12.0,
    )
    retry_policy = ModelRetryPolicy(max_attempts=1, retryable_outcomes=[])
    budget_policy = ModelExecutionBudgetPolicy(
        max_input_tokens=contract.context_budget_policy.max_decision_frame_tokens,
        max_output_tokens=contract.context_budget_policy.reserve_output_tokens,
        max_total_estimated_usd=max(contract.cost_profile.input_usd_per_1m, 0.0),
    )
    metadata = {
        "session_id": frame.session_id,
        "frame_id": frame.frame_id,
        "prompt_hash": text_hash(prompt),
        "frame_hash": frame.prompt_hash,
        "selected_provider_id": contract.selected_provider_id,
        "selected_backend_id": contract.selected_backend_id,
        "selected_model": contract.selected_model,
        "operator_mode": OperatorMode.LLM_OPERATOR.value,
        "routing_policy": "explicit_user_model_contract_only",
    }
    request_hash_payload = {
        "provider_id": contract.selected_provider_id,
        "backend_id": contract.selected_backend_id,
        "model_id": contract.selected_model,
        "prompt_hash": text_hash(prompt),
        "frame_hash": frame.prompt_hash,
        "user_model_contract_id": contract.id,
        "request_metadata": metadata,
    }
    return RealModelRequest(
        provider_id=contract.selected_provider_id,
        model_id=contract.selected_model,
        backend_id=contract.selected_backend_id,
        backend=contract.selected_backend_id,
        runtime="operator_llm_conversation",
        prompt_hash=text_hash(prompt),
        frame_hash=frame.prompt_hash,
        user_model_contract_id=contract.id,
        estimated_input_tokens=max(1, len(prompt) // 4),
        estimated_output_tokens=contract.context_budget_policy.reserve_output_tokens,
        prompt_text_in_memory_only=prompt,
        request_metadata=metadata,
        timeout_policy_id=timeout_policy.id,
        retry_policy_id=retry_policy.id,
        budget_policy_id=budget_policy.id,
        request_hash=stable_hash(request_hash_payload),
    )


def _fail_closed(
    *,
    mode: OperatorMode,
    contract: UserModelContract,
    reason: str,
    reply: str,
    diagnostics: dict[str, Any] | None = None,
) -> OperatorLLMDecisionResult:
    metadata: dict[str, Any] = {"blocked_reason": reason}
    if diagnostics:
        metadata["structured_output_diagnostics"] = diagnostics
    return OperatorLLMDecisionResult(
        mode=mode,
        reply=reply,
        metadata=metadata,
        provider_id=contract.selected_provider_id,
        backend_id=contract.selected_backend_id,
        model_id=contract.selected_model,
    )
