from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.agent.model_cost import ModelCostProfile
from sentinel.shared.models import SentinelModel, new_id


class ModelCapabilityProfile(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("mcap"))
    model_name: str
    context_window_tokens: int = Field(gt=0)
    supports_tool_calling: bool = True
    supports_vision: bool = False
    supports_prompt_caching: bool = False
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ContextBudgetPolicy(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("cbudget"))
    max_decision_frame_tokens: int = Field(gt=0)
    max_tool_schema_tokens: int = Field(ge=0)
    max_evidence_tokens: int = Field(ge=0)
    reserve_output_tokens: int = Field(ge=0)


class QualityExpectationContract(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("qexp"))
    expected_quality: str
    minimum_evidence_refs: int = Field(ge=0)
    retry_budget: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list)


class UserModelContract(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("umodel"))
    selected_model: str
    cost_profile: ModelCostProfile
    capability_profile: ModelCapabilityProfile
    context_budget_policy: ContextBudgetPolicy
    quality_expectation: QualityExpectationContract
    user_selected: bool = True
    model_override_attempted: bool = False
    alternative_model_recommendations: list[dict[str, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_selected_model(self) -> UserModelContract:
        if self.cost_profile.model_name != self.selected_model:
            raise ValueError("cost profile model_name must match selected_model.")
        if self.capability_profile.model_name != self.selected_model:
            raise ValueError("capability profile model_name must match selected_model.")
        if not self.user_selected:
            raise ValueError("UserModelContract requires an explicit user-selected model.")
        return self

    def recommend_alternative(self, model: str, *, reason: str) -> UserModelContract:
        recommendations = [*self.alternative_model_recommendations, {"model": model, "reason": reason}]
        return self.model_copy(update={"alternative_model_recommendations": recommendations})

    def with_selected_model_override(self, model: str) -> UserModelContract:
        if model != self.selected_model:
            raise ValueError("Sentinel must not override the user-selected model.")
        return self
