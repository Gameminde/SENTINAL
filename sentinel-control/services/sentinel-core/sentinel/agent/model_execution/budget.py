from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.models import ModelExecutionOutcomeClass, ProviderModelResponse, RealModelRequest
from sentinel.agent.model_execution.redaction import sanitize_metadata, stable_hash
from sentinel.shared.models import SentinelModel


class ModelExecutionBudgetDecision(SentinelModel):
    allowed: bool
    decision: str
    provider_called: bool = False
    projected_input_tokens: int = Field(default=0, ge=0)
    projected_output_tokens: int = Field(default=0, ge=0)
    projected_total_tokens: int = Field(default=0, ge=0)
    projected_retry_attempts: int = Field(default=0, ge=0)
    projected_provider_time_seconds: float = Field(default=0.0, ge=0.0)


class ModelExecutionBudgetEntry(SentinelModel):
    id: str
    mission_id: str
    request_hash: str
    provider_id: str
    backend_id: str
    model_id: str
    action_id: str
    outcome_class: str
    decision: str
    compliant: bool
    provider_called: bool
    estimated_input_tokens: int = Field(default=0, ge=0)
    estimated_output_tokens: int = Field(default=0, ge=0)
    actual_input_tokens: int = Field(default=0, ge=0)
    actual_output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    retry_attempts: int = Field(default=0, ge=0)
    provider_time_seconds: float = Field(default=0.0, ge=0.0)
    entry_hash: str

    @classmethod
    def build(
        cls,
        *,
        mission_id: str,
        request: RealModelRequest,
        outcome_class: ModelExecutionOutcomeClass,
        decision: str,
        compliant: bool,
        provider_called: bool,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
        reasoning_tokens: int = 0,
        retry_attempts: int = 0,
        provider_time_seconds: float = 0.0,
    ) -> ModelExecutionBudgetEntry:
        action_id = str(request.request_metadata.get("action_id") or request.id)
        payload = sanitize_metadata(
            {
                "mission_id": mission_id,
                "request_hash": request.request_hash,
                "provider_id": request.provider_id,
                "backend_id": request.backend_id,
                "model_id": request.model_id,
                "action_id": action_id,
                "outcome_class": outcome_class.value,
                "decision": decision,
                "compliant": compliant,
                "provider_called": provider_called,
                "estimated_input_tokens": request.estimated_input_tokens,
                "estimated_output_tokens": request.estimated_output_tokens,
                "actual_input_tokens": actual_input_tokens,
                "actual_output_tokens": actual_output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "retry_attempts": retry_attempts,
                "provider_time_seconds": provider_time_seconds,
            }
        )
        entry_hash = stable_hash(payload)
        return cls(id=f"model_budget_entry_{entry_hash[:16]}", entry_hash=entry_hash, **payload)


class ModelExecutionBudgetLedger(SentinelModel):
    mission_id: str
    max_mission_input_tokens: int | None = Field(default=None, ge=0)
    max_mission_output_tokens: int | None = Field(default=None, ge=0)
    max_mission_total_tokens: int | None = Field(default=None, ge=0)
    max_mission_reasoning_tokens: int | None = Field(default=None, ge=0)
    max_mission_retry_attempts: int | None = Field(default=None, ge=0)
    max_mission_provider_time_seconds: float | None = Field(default=None, ge=0.0)
    entries: list[ModelExecutionBudgetEntry] = Field(default_factory=list)

    def preflight(self, request: RealModelRequest) -> ModelExecutionBudgetDecision:
        budget = _dict_metadata(request, "budget_policy")
        retry = _dict_metadata(request, "retry_policy")
        timeout = _dict_metadata(request, "timeout_policy")
        planned_retry_attempts = _safe_int(retry.get("max_attempts"), default=1)
        planned_provider_time = _safe_float(timeout.get("total_timeout_seconds"))
        estimated_input = request.estimated_input_tokens
        estimated_output = request.estimated_output_tokens
        estimated_total = estimated_input + estimated_output

        action_checks = [
            ("action_input_tokens_exceeded", estimated_input, budget.get("max_input_tokens")),
            ("action_output_tokens_exceeded", estimated_output, budget.get("max_output_tokens")),
            ("action_total_tokens_exceeded", estimated_total, budget.get("max_total_tokens")),
            (
                "action_retry_attempts_exceeded",
                planned_retry_attempts,
                budget.get("max_retry_attempts_per_action"),
            ),
            (
                "action_provider_time_budget_exceeded",
                planned_provider_time,
                budget.get("max_provider_time_seconds_per_action"),
            ),
        ]
        for decision, value, limit in action_checks:
            if _limit_exceeded(value, limit):
                return self._blocked(
                    decision=decision,
                    projected_input_tokens=estimated_input,
                    projected_output_tokens=estimated_output,
                    projected_retry_attempts=planned_retry_attempts,
                    projected_provider_time_seconds=planned_provider_time,
                )

        mission_checks = [
            (
                "mission_input_tokens_exhausted",
                self.used_input_tokens + estimated_input,
                self.max_mission_input_tokens,
            ),
            (
                "mission_output_tokens_exhausted",
                self.used_output_tokens + estimated_output,
                self.max_mission_output_tokens,
            ),
            (
                "mission_total_tokens_exhausted",
                self.used_total_tokens + estimated_total,
                self.max_mission_total_tokens,
            ),
            (
                "mission_retry_attempts_exhausted",
                self.used_retry_attempts + planned_retry_attempts,
                self.max_mission_retry_attempts,
            ),
            (
                "mission_provider_time_exhausted",
                self.used_provider_time_seconds + planned_provider_time,
                self.max_mission_provider_time_seconds,
            ),
        ]
        for decision, value, limit in mission_checks:
            if _limit_exceeded(value, limit):
                return self._blocked(
                    decision=decision,
                    projected_input_tokens=estimated_input,
                    projected_output_tokens=estimated_output,
                    projected_retry_attempts=planned_retry_attempts,
                    projected_provider_time_seconds=planned_provider_time,
                )

        return ModelExecutionBudgetDecision(
            allowed=True,
            decision="within_budget",
            projected_input_tokens=estimated_input,
            projected_output_tokens=estimated_output,
            projected_total_tokens=estimated_total,
            projected_retry_attempts=planned_retry_attempts,
            projected_provider_time_seconds=planned_provider_time,
        )

    def record_rejection(
        self,
        *,
        request: RealModelRequest,
        decision: ModelExecutionBudgetDecision,
    ) -> dict[str, Any]:
        self.entries.append(
            ModelExecutionBudgetEntry.build(
                mission_id=self.mission_id,
                request=request,
                outcome_class=ModelExecutionOutcomeClass.BUDGET_REJECTED,
                decision=decision.decision,
                compliant=False,
                provider_called=False,
                retry_attempts=0,
                provider_time_seconds=0.0,
            )
        )
        summary = self.safe_summary(decision=decision.decision, compliant=False)
        budget = _dict_metadata(request, "budget_policy")
        timeout = _dict_metadata(request, "timeout_policy")
        summary.update(
            sanitize_metadata(
                {
                    "input_token_budget": budget.get("max_input_tokens"),
                    "output_token_budget": budget.get("max_output_tokens"),
                    "total_token_budget": budget.get("max_total_tokens"),
                    "retry_attempt_budget": budget.get("max_retry_attempts_per_action"),
                    "provider_time_budget_seconds": budget.get("max_provider_time_seconds_per_action"),
                    "provider_time_reserved_seconds": timeout.get("total_timeout_seconds"),
                }
            )
        )
        return summary

    def record_response(
        self,
        *,
        request: RealModelRequest,
        response: ProviderModelResponse,
        outcome_class: ModelExecutionOutcomeClass,
        attempts: int,
        provider_time_seconds: float,
    ) -> dict[str, Any]:
        reasoning_tokens = _safe_int(response.content.get("reasoning_token_count"), default=0)
        actual_input_tokens = response.input_tokens
        actual_output_tokens = response.output_tokens
        self.entries.append(
            ModelExecutionBudgetEntry.build(
                mission_id=self.mission_id,
                request=request,
                outcome_class=outcome_class,
                decision=outcome_class.value,
                compliant=True,
                provider_called=True,
                actual_input_tokens=actual_input_tokens,
                actual_output_tokens=actual_output_tokens,
                reasoning_tokens=reasoning_tokens,
                retry_attempts=attempts,
                provider_time_seconds=provider_time_seconds,
            )
        )
        decision, compliant = self._post_response_compliance(
            request=request,
            actual_input_tokens=actual_input_tokens,
            actual_output_tokens=actual_output_tokens,
            reasoning_tokens=reasoning_tokens,
        )
        return self.safe_summary(decision=decision, compliant=compliant)

    @property
    def used_input_tokens(self) -> int:
        return sum(entry.actual_input_tokens for entry in self.entries)

    @property
    def used_output_tokens(self) -> int:
        return sum(entry.actual_output_tokens for entry in self.entries)

    @property
    def used_reasoning_tokens(self) -> int:
        return sum(entry.reasoning_tokens for entry in self.entries)

    @property
    def used_total_tokens(self) -> int:
        return self.used_input_tokens + self.used_output_tokens + self.used_reasoning_tokens

    @property
    def used_retry_attempts(self) -> int:
        return sum(entry.retry_attempts for entry in self.entries)

    @property
    def used_provider_time_seconds(self) -> float:
        return sum(entry.provider_time_seconds for entry in self.entries)

    def _post_response_compliance(
        self,
        *,
        request: RealModelRequest,
        actual_input_tokens: int,
        actual_output_tokens: int,
        reasoning_tokens: int,
    ) -> tuple[str, bool]:
        budget = _dict_metadata(request, "budget_policy")
        actual_total_tokens = actual_input_tokens + actual_output_tokens + reasoning_tokens
        action_checks = [
            ("actual_action_input_tokens_exceeded", actual_input_tokens, budget.get("max_input_tokens")),
            ("actual_action_output_tokens_exceeded", actual_output_tokens, budget.get("max_output_tokens")),
            ("actual_action_total_tokens_exceeded", actual_total_tokens, budget.get("max_total_tokens")),
        ]
        mission_checks = [
            ("actual_mission_input_tokens_exceeded", self.used_input_tokens, self.max_mission_input_tokens),
            ("actual_mission_output_tokens_exceeded", self.used_output_tokens, self.max_mission_output_tokens),
            ("actual_mission_reasoning_tokens_exceeded", self.used_reasoning_tokens, self.max_mission_reasoning_tokens),
            ("actual_mission_total_tokens_exceeded", self.used_total_tokens, self.max_mission_total_tokens),
            ("actual_mission_retry_attempts_exceeded", self.used_retry_attempts, self.max_mission_retry_attempts),
            (
                "actual_mission_provider_time_exceeded",
                self.used_provider_time_seconds,
                self.max_mission_provider_time_seconds,
            ),
        ]
        for decision, value, limit in action_checks + mission_checks:
            if _limit_exceeded(value, limit):
                return decision, False
        return "within_budget", True

    def safe_summary(self, *, decision: str = "within_budget", compliant: bool = True) -> dict[str, Any]:
        return sanitize_metadata(
            {
                "mission_id": self.mission_id,
                "compliant": compliant,
                "decision": decision,
                "used_input_tokens": self.used_input_tokens,
                "used_output_tokens": self.used_output_tokens,
                "used_reasoning_tokens": self.used_reasoning_tokens,
                "used_total_tokens": self.used_total_tokens,
                "used_retry_attempts": self.used_retry_attempts,
                "used_provider_time_seconds": self.used_provider_time_seconds,
                "max_mission_input_tokens": self.max_mission_input_tokens,
                "max_mission_output_tokens": self.max_mission_output_tokens,
                "max_mission_total_tokens": self.max_mission_total_tokens,
                "max_mission_reasoning_tokens": self.max_mission_reasoning_tokens,
                "max_mission_retry_attempts": self.max_mission_retry_attempts,
                "max_mission_provider_time_seconds": self.max_mission_provider_time_seconds,
                "entry_hashes": [entry.entry_hash for entry in self.entries],
            }
        )

    def _blocked(
        self,
        *,
        decision: str,
        projected_input_tokens: int,
        projected_output_tokens: int,
        projected_retry_attempts: int,
        projected_provider_time_seconds: float,
    ) -> ModelExecutionBudgetDecision:
        return ModelExecutionBudgetDecision(
            allowed=False,
            decision=decision,
            projected_input_tokens=projected_input_tokens,
            projected_output_tokens=projected_output_tokens,
            projected_total_tokens=projected_input_tokens + projected_output_tokens,
            projected_retry_attempts=projected_retry_attempts,
            projected_provider_time_seconds=projected_provider_time_seconds,
        )


def _dict_metadata(request: RealModelRequest, key: str) -> dict[str, Any]:
    value = request.request_metadata.get(key)
    return value if isinstance(value, dict) else {}


def _limit_exceeded(value: int | float, limit: Any) -> bool:
    if limit is None:
        return False
    try:
        parsed_limit = float(limit)
    except (TypeError, ValueError):
        return False
    return float(value) > parsed_limit


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _safe_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, parsed)
