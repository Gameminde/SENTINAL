from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


def _round_usd(value: float) -> float:
    return round(max(0.0, value), 8)


class DecisionFrameCostProjection(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("dfcost"))
    model_name: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    retry_budget: int = Field(default=0, ge=0)
    input_cost_usd: float = Field(ge=0.0)
    output_cost_usd: float = Field(ge=0.0)
    cached_input_cost_usd: float = Field(default=0.0, ge=0.0)
    retry_cost_usd: float = Field(default=0.0, ge=0.0)
    cache_savings_usd: float = Field(default=0.0, ge=0.0)
    total_estimated_usd: float = Field(ge=0.0)


class ModelCostProfile(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("mcost"))
    model_name: str
    input_usd_per_1m: float = Field(ge=0.0)
    output_usd_per_1m: float = Field(ge=0.0)
    cached_input_usd_per_1m: float | None = Field(default=None, ge=0.0)
    context_window_tokens: int = Field(gt=0)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_cached_price(self) -> ModelCostProfile:
        if self.cached_input_usd_per_1m is not None and self.cached_input_usd_per_1m > self.input_usd_per_1m:
            raise ValueError("cached input price cannot exceed normal input price.")
        return self

    def project(
        self,
        *,
        input_tokens: int,
        output_tokens: int = 0,
        cached_input_tokens: int = 0,
        retry_budget: int = 0,
    ) -> DecisionFrameCostProjection:
        input_tokens = max(0, input_tokens)
        output_tokens = max(0, output_tokens)
        cached_input_tokens = min(max(0, cached_input_tokens), input_tokens)
        uncached_input_tokens = input_tokens - cached_input_tokens
        input_cost = uncached_input_tokens * self.input_usd_per_1m / 1_000_000
        cached_price = self.cached_input_usd_per_1m if self.cached_input_usd_per_1m is not None else self.input_usd_per_1m
        cached_cost = cached_input_tokens * cached_price / 1_000_000
        output_cost = output_tokens * self.output_usd_per_1m / 1_000_000
        single_call_cost = input_cost + cached_cost + output_cost
        retry_cost = single_call_cost * max(0, retry_budget)
        no_cache_cost = input_tokens * self.input_usd_per_1m / 1_000_000
        cache_savings = max(0.0, no_cache_cost - (input_cost + cached_cost))
        total = single_call_cost + retry_cost
        return DecisionFrameCostProjection(
            model_name=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            retry_budget=max(0, retry_budget),
            input_cost_usd=_round_usd(input_cost),
            output_cost_usd=_round_usd(output_cost),
            cached_input_cost_usd=_round_usd(cached_cost),
            retry_cost_usd=_round_usd(retry_cost),
            cache_savings_usd=_round_usd(cache_savings),
            total_estimated_usd=_round_usd(total),
        )
