from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import sanitize_metadata, stable_hash
from sentinel.shared.models import SentinelModel, new_id


class ModelExecutionOutcomeClass(str, Enum):
    SUCCESS_VALIDATED = "SUCCESS_VALIDATED"
    PROVIDER_REFUSAL = "PROVIDER_REFUSAL"
    MISSING_CREDENTIAL = "MISSING_CREDENTIAL"
    DISABLED_BACKEND = "DISABLED_BACKEND"
    UNKNOWN_PROVIDER = "UNKNOWN_PROVIDER"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    BUDGET_REJECTED = "BUDGET_REJECTED"
    INVALID_RESPONSE_SCHEMA = "INVALID_RESPONSE_SCHEMA"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    CREDENTIAL_REVOKED = "CREDENTIAL_REVOKED"
    AUTHORITY_EXPIRED = "AUTHORITY_EXPIRED"
    AUTHORITY_EXPANSION_REJECTED = "AUTHORITY_EXPANSION_REJECTED"
    MODEL_EXECUTION_DEFERRED = "MODEL_EXECUTION_DEFERRED"


class RealModelRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("model_request"))
    provider_id: str
    model_id: str
    backend_id: str | None = None
    backend: str
    runtime: str
    prompt_hash: str
    frame_hash: str
    user_model_contract_id: str
    estimated_input_tokens: int = Field(ge=0)
    estimated_output_tokens: int = Field(ge=0)
    prompt_text_in_memory_only: str | None = Field(default=None, exclude=True, repr=False)
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    timeout_policy_id: str
    retry_policy_id: str
    budget_policy_id: str
    request_hash: str

    @model_validator(mode="after")
    def _bind_backend_identity(self) -> RealModelRequest:
        backend_id = self.backend_id or self.backend
        if not self.provider_id.strip():
            raise ValueError("RealModelRequest.provider_id must be non-empty.")
        if not backend_id.strip():
            raise ValueError("RealModelRequest.backend_id must be non-empty.")
        object.__setattr__(self, "backend_id", backend_id)
        object.__setattr__(self, "backend", backend_id)
        return self

    def serializable_metadata(self) -> dict[str, Any]:
        return sanitize_metadata(
            {
                "id": self.id,
                "provider_id": self.provider_id,
                "model_id": self.model_id,
                "backend_id": self.backend_id,
                "backend": self.backend,
                "runtime": self.runtime,
                "prompt_hash": self.prompt_hash,
                "frame_hash": self.frame_hash,
                "user_model_contract_id": self.user_model_contract_id,
                "estimated_input_tokens": self.estimated_input_tokens,
                "estimated_output_tokens": self.estimated_output_tokens,
                "request_metadata": self.request_metadata,
                "timeout_policy_id": self.timeout_policy_id,
                "retry_policy_id": self.retry_policy_id,
                "budget_policy_id": self.budget_policy_id,
                "request_hash": self.request_hash,
            }
        )


class ProviderModelResponse(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("provider_response"))
    provider_id: str
    model_id: str
    response_id: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    refusal: bool = False
    error_class: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)

    @property
    def sanitized_response_hash(self) -> str:
        return stable_hash(sanitize_metadata(self.content))


class LLMDecisionResult(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("llm_result"))
    provider_id: str
    model_id: str
    decision: str | None = None
    rationale_summary: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    outcome_class: ModelExecutionOutcomeClass
    success: bool
    refusal: bool = False
    error_class: str | None = None
    authority_expansion: bool = False
    tool_execution_requested: bool = False
    organ_execution_requested: bool = False
    sanitized_response_hash: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)


class ModelExecutionOutcome(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("model_outcome"))
    outcome_class: ModelExecutionOutcomeClass
    success: bool
    result: LLMDecisionResult | None = None
    receipt: Any | None = None
    provider_called: bool = False
    budget_summary: dict[str, Any] | None = None
    message: str | None = None
