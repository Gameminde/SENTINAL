from __future__ import annotations

from pydantic import Field

from sentinel.agent.model_execution.credentials import ProviderCredentialHandle
from sentinel.agent.model_execution.models import LLMDecisionResult, ModelExecutionOutcomeClass, RealModelRequest
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel, new_id


class ModelExecutionReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("model_receipt"))
    request_hash: str
    prompt_hash: str
    response_hash: str | None = None
    provider_id: str
    model_id: str
    backend_id: str | None = None
    backend: str
    outcome_class: ModelExecutionOutcomeClass
    validation_status: str
    refusal: bool = False
    error_class: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    attempts: int = Field(default=0, ge=0)
    credential_source_type: str | None = None
    credential_source_ref_hash: str | None = None
    credential_scopes: list[str] = Field(default_factory=list)
    receipt_hash: str


def build_model_execution_receipt(
    *,
    request: RealModelRequest,
    outcome_class: ModelExecutionOutcomeClass,
    result: LLMDecisionResult | None,
    credential: ProviderCredentialHandle | None,
    attempts: int,
) -> ModelExecutionReceipt:
    payload = {
        "request_hash": request.request_hash,
        "prompt_hash": request.prompt_hash,
        "response_hash": result.sanitized_response_hash if result else None,
        "provider_id": request.provider_id,
        "model_id": request.model_id,
        "backend_id": request.backend_id,
        "backend": request.backend,
        "outcome_class": outcome_class.value,
        "validation_status": result.outcome_class.value if result else outcome_class.value,
        "refusal": bool(result.refusal) if result else False,
        "error_class": result.error_class if result else None,
        "input_tokens": result.input_tokens if result else 0,
        "output_tokens": result.output_tokens if result else 0,
        "cost_usd": result.cost_usd if result else 0.0,
        "attempts": attempts,
        "credential_source_type": credential.source_type.value if credential else None,
        "credential_source_ref_hash": credential.source_ref_hash if credential else None,
        "credential_scopes": credential.scopes if credential else [],
    }
    return ModelExecutionReceipt(receipt_hash=stable_hash(payload), **payload)
