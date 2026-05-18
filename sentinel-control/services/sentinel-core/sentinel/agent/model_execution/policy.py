from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class ModelTimeoutPolicy(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("model_timeout"))
    connect_timeout_seconds: float = Field(gt=0.0)
    read_timeout_seconds: float = Field(gt=0.0)
    total_timeout_seconds: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_total_timeout(self) -> ModelTimeoutPolicy:
        if self.total_timeout_seconds < self.connect_timeout_seconds:
            raise ValueError("total timeout must be at least connect timeout.")
        if self.total_timeout_seconds < self.read_timeout_seconds:
            raise ValueError("total timeout must be at least read timeout.")
        return self


class ModelRetryPolicy(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("model_retry"))
    max_attempts: int = Field(default=1, ge=1, le=3)
    retryable_outcomes: list[str] = Field(default_factory=list)


class ModelExecutionBudgetPolicy(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("model_budget"))
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(ge=0)
    max_total_estimated_usd: float = Field(ge=0.0)
