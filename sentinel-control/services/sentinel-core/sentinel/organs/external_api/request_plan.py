from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


RAW_CREDENTIAL_TERMS = {
    "authorization",
    "api-key",
    "apikey",
    "x-api-key",
    "token",
    "bearer",
    "sk-",
    "secret",
    "password",
}


class APIRequestPlan(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("apiplan"))
    vendor: str
    domain: str
    method: str
    path: str
    action: str
    query_params: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body_summary: dict[str, str] = Field(default_factory=dict)
    data_categories: list[str] = Field(default_factory=list)
    credential_ref: str | None = None
    estimated_unit_cost_usd: float = Field(default=0.0, ge=0.0)
    expected_calls: int = Field(default=1, ge=1)
    paid_api: bool = False
    account_affecting: bool = False
    mutation: bool = False
    live_execution_requested: bool = False
    execution_started: bool = False
    raw_secret_present: bool = False
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> APIRequestPlan:
        if not self.evidence_refs:
            raise ValueError("APIRequestPlan requires evidence refs.")
        self.method = self.method.upper()
        if self.execution_started:
            raise ValueError("APIRequestPlan cannot start execution.")
        if self.live_execution_requested:
            raise ValueError("APIRequestPlan cannot request live execution in P6D.")
        if self._contains_raw_credential():
            self.raw_secret_present = True
            raise ValueError("APIRequestPlan cannot contain raw credential material; use CredentialRef placeholder.")
        if self.method not in {"GET", "HEAD", "OPTIONS"}:
            self.mutation = True
        if self.estimated_unit_cost_usd > 0:
            self.paid_api = True
        return self

    @property
    def lane(self) -> AutonomyRiskLane:
        if self.account_affecting:
            return AutonomyRiskLane.RED
        if self.paid_api or self.mutation or self.method not in {"GET", "HEAD", "OPTIONS"}:
            return AutonomyRiskLane.ORANGE
        return AutonomyRiskLane.BLUE

    def _contains_raw_credential(self) -> bool:
        serialized = " ".join([*self.headers.keys(), *self.headers.values()]).lower()
        return any(term in serialized for term in RAW_CREDENTIAL_TERMS)
