from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.organs.contracts import ExternalOrganContract, OrganType
from sentinel.shared.models import SentinelModel


class ExternalOrganRegistry(SentinelModel):
    contracts: list[ExternalOrganContract] = Field(default_factory=list)

    def register(self, contract: ExternalOrganContract, *, event_bus: EventBus | None = None) -> ExternalOrganRegistry:
        if any(item.id == contract.id or item.organ_name == contract.organ_name for item in self.contracts):
            raise ValueError("ExternalOrganRegistry cannot register duplicate organ contracts.")
        next_registry = self.model_copy(update={"contracts": [*self.contracts, contract]})
        if event_bus is None:
            return next_registry
        event_bus.append(
            AgentEventType.ORGAN_CONTRACT_REGISTERED,
            "External organ contract registered without enabling execution.",
            payload={
                "organ_id": contract.id,
                "organ_name": contract.organ_name,
                "organ_type": contract.organ_type.value,
                "promotion_level": contract.promotion_level.value,
                "execution_enabled": contract.execution_enabled,
                "authority_expansion": False,
            },
        )
        return next_registry

    def get(self, organ_name: str) -> ExternalOrganContract:
        for contract in self.contracts:
            if contract.organ_name == organ_name or contract.id == organ_name:
                return contract
        raise ValueError("Unknown external organ contract.")

    def by_type(self, organ_type: OrganType) -> list[ExternalOrganContract]:
        return [contract for contract in self.contracts if contract.organ_type == organ_type]


def runtime_organ_spec_safe_export() -> list[dict[str, Any]]:
    """Expose runtime organ specs as inert metadata for inventories and frames."""
    from sentinel.agent.organs.organ_spec_registry import default_organ_spec_registry

    return default_organ_spec_registry().safe_export()
