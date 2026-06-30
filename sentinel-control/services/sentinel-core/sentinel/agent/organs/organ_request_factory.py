from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.organs.organ_spec_registry import OrganSpecRegistry, default_organ_spec_registry
from sentinel.shared.models import SentinelModel


class OrganRequestBuildContext(SentinelModel):
    raw_candidate: dict[str, Any]
    bridged_candidate: Any
    gate_result: Any = None
    mission_id: str
    organ_contracts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    prior_candidate_results: list[Any] = Field(default_factory=list)
    authority_envelope: Any = None
    source_readonly_receipts: list[Any] = Field(default_factory=list)
    data_not_instruction: bool = True
    authority_granting: bool = False
    can_grant_authority: bool = False
    registry_can_execute: bool = False

    @model_validator(mode="after")
    def _keep_context_data_only(self) -> OrganRequestBuildContext:
        if self.data_not_instruction is not True:
            raise ValueError("Organ request build context is data, not instruction.")
        if self.authority_granting or self.can_grant_authority or self.registry_can_execute:
            raise ValueError("Organ request build context cannot grant authority or execute.")
        return self


class OrganRequestBuildResult(SentinelModel):
    accepted: bool
    organ_id: str | None = None
    request_field: str | None = None
    request_model: str | None = None
    runtime_handler: str | None = None
    skill_binding: str | None = None
    sub_request: Any = None
    blocked_reason: str | None = None
    data_not_instruction: bool = True
    authority_granting: bool = False
    can_grant_authority: bool = False
    registry_can_execute: bool = False

    @model_validator(mode="after")
    def _keep_result_data_only(self) -> OrganRequestBuildResult:
        if self.data_not_instruction is not True:
            raise ValueError("Organ request build result is data, not instruction.")
        if self.authority_granting or self.can_grant_authority or self.registry_can_execute:
            raise ValueError("Organ request build result cannot grant authority or execute.")
        if self.accepted and (not self.organ_id or not self.request_field or self.sub_request is None):
            raise ValueError("Accepted organ request build results require an organ id, request field, and sub-request.")
        if not self.accepted and not self.blocked_reason:
            raise ValueError("Rejected organ request build results require a blocked reason.")
        return self

    def runtime_request_kwargs(self) -> dict[str, Any]:
        if not self.accepted or not self.request_field or self.sub_request is None:
            return {}
        return {self.request_field: self.sub_request}


OrganRequestBuilder = Callable[[OrganRequestBuildContext], Any | None]


class OrganRequestFactory:
    def __init__(
        self,
        *,
        registry: OrganSpecRegistry | None = None,
        builders: dict[str, OrganRequestBuilder] | None = None,
    ) -> None:
        self._registry = registry or default_organ_spec_registry()
        self._builders = builders or {}

    def build(self, organ_id_or_alias: str, context: OrganRequestBuildContext) -> OrganRequestBuildResult:
        spec = self._registry.get(organ_id_or_alias)
        if spec is None:
            return OrganRequestBuildResult(accepted=False, blocked_reason="unknown_organ_not_registered")

        if not spec.request_field:
            return OrganRequestBuildResult(
                accepted=False,
                organ_id=spec.organ_id,
                request_model=spec.request_model,
                runtime_handler=spec.runtime_handler,
                skill_binding=spec.skill_binding,
                blocked_reason="organ_request_field_missing",
            )

        builder = self._builders.get(spec.organ_id)
        if builder is None:
            return OrganRequestBuildResult(
                accepted=False,
                organ_id=spec.organ_id,
                request_field=spec.request_field,
                request_model=spec.request_model,
                runtime_handler=spec.runtime_handler,
                skill_binding=spec.skill_binding,
                blocked_reason="organ_request_builder_missing",
            )

        sub_request = builder(context)
        if sub_request is None:
            return OrganRequestBuildResult(
                accepted=False,
                organ_id=spec.organ_id,
                request_field=spec.request_field,
                request_model=spec.request_model,
                runtime_handler=spec.runtime_handler,
                skill_binding=spec.skill_binding,
                blocked_reason="organ_sub_request_build_failed",
            )

        return OrganRequestBuildResult(
            accepted=True,
            organ_id=spec.organ_id,
            request_field=spec.request_field,
            request_model=spec.request_model,
            runtime_handler=spec.runtime_handler,
            skill_binding=spec.skill_binding,
            sub_request=sub_request,
        )
