from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.event_bus import EventBus
from sentinel.agent.events import AgentEventType
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.organs.contracts import ExternalOrganContract
from sentinel.shared.models import SentinelModel, new_id


class OrganAuthorityEnvelope(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("orgauth"))
    mission_id: str
    root_authority_id: str
    organ_id: str
    organ_name: str
    allowed_actions: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_accounts: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    max_actions: int = Field(ge=0)
    max_cost_usd: float = Field(default=0.0, ge=0.0)
    execution_authorized: bool = False
    dry_run_only: bool = True
    authority_expansion: bool = False
    errors: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> OrganAuthorityEnvelope:
        if self.authority_expansion:
            raise ValueError("OrganAuthorityEnvelope cannot expand root authority.")
        if self.execution_authorized and self.dry_run_only:
            raise ValueError("Execution-authorized organ authority cannot be dry-run-only.")
        return self


class OrganAuthorityEvaluator:
    BLACK_ZONE_ACTION_TERMS = {
        "payment",
        "spend",
        "trade",
        "trading",
        "credential",
        "account_create",
        "create_account",
        "send_email",
        "send_message",
    }
    BLACK_ZONE_TOOL_TERMS = {
        "stripe",
        "payment",
        "trading",
        "broker",
        "credential",
        "vault",
        "email_sender",
    }

    def evaluate(
        self,
        root: MissionAuthorityEnvelope,
        contract: ExternalOrganContract,
        *,
        requested_actions: list[str],
        requested_tools: list[str] | None = None,
        requested_domains: list[str] | None = None,
        requested_accounts: list[str] | None = None,
        context_signals: dict[str, Any] | None = None,
        workspace_context: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
        expected_profit: float | None = None,
        event_bus: EventBus | None = None,
    ) -> OrganAuthorityEnvelope:
        errors = []
        tools = requested_tools or []
        domains = requested_domains or []
        accounts = requested_accounts or []
        forbidden = {item.lower() for item in root.forbidden_actions}

        for action in requested_actions:
            if self._is_black_zone_action(action):
                errors.append(f"black_zone_action_blocked_by_default:{action}")
            if action not in root.allowed_actions:
                errors.append(f"action_outside_root_authority:{action}")
            if action not in contract.supported_actions:
                errors.append(f"action_not_supported_by_organ:{action}")
            if action.lower() in forbidden:
                errors.append(f"action_forbidden:{action}")
        for tool in tools:
            if self._is_black_zone_tool(tool):
                errors.append(f"black_zone_tool_blocked_by_default:{tool}")
            if tool not in root.allowed_tools:
                errors.append(f"tool_outside_root_authority:{tool}")
            if tool.lower() in forbidden:
                errors.append(f"tool_forbidden:{tool}")
        for domain in domains:
            if domain not in root.allowed_domains:
                errors.append(f"domain_outside_root_authority:{domain}")
        for account in accounts:
            if account not in root.allowed_accounts:
                errors.append(f"account_outside_root_authority:{account}")

        authority = OrganAuthorityEnvelope(
            mission_id=root.id,
            root_authority_id=root.id,
            organ_id=contract.id,
            organ_name=contract.organ_name,
            allowed_actions=[] if errors else list(dict.fromkeys(requested_actions)),
            allowed_tools=[] if errors else list(dict.fromkeys(tools)),
            allowed_domains=[] if errors else list(dict.fromkeys(domains)),
            allowed_accounts=[] if errors else list(dict.fromkeys(accounts)),
            allowed_paths=list(root.allowed_paths),
            max_actions=root.max_actions,
            max_cost_usd=root.max_cost_usd,
            dry_run_only=True,
            execution_authorized=False,
            errors=errors,
        )
        if event_bus is None:
            return authority
        event = event_bus.append(
            AgentEventType.ORGAN_AUTHORITY_EVALUATED,
            "External organ authority evaluated as subset of root mission authority.",
            payload={
                "organ_authority_id": authority.id,
                "organ_id": contract.id,
                "organ_name": contract.organ_name,
                "allowed": not errors,
                "errors": errors,
                "dry_run_only": True,
                "execution_authorized": False,
                "authority_expansion": False,
                "context_signals_ignored_for_authority": context_signals is not None,
                "workspace_context_ignored_for_authority": workspace_context is not None,
                "memory_context_ignored_for_authority": memory_context is not None,
                "expected_profit_ignored_for_authority": expected_profit is not None,
            },
        )
        return authority.model_copy(update={"trace_refs": [event.id]})

    @classmethod
    def _is_black_zone_action(cls, action: str) -> bool:
        normalized = action.lower()
        return any(term in normalized for term in cls.BLACK_ZONE_ACTION_TERMS)

    @classmethod
    def _is_black_zone_tool(cls, tool: str) -> bool:
        normalized = tool.lower()
        return any(term in normalized for term in cls.BLACK_ZONE_TOOL_TERMS)
