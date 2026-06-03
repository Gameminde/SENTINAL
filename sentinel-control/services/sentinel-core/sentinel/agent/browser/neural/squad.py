from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger
from sentinel.agent.browser.neural.models import NeuronKind
from sentinel.agent.browser.neural.risk import _BOUNDARY_KEYWORDS
from sentinel.shared.models import SentinelModel, new_id


class BrowserSquadRoleKind(StrEnum):
    SCOUT = "scout"
    PLANNER = "planner"
    OPERATOR = "operator"
    VERIFIER = "verifier"
    RECOVERY = "recovery"
    BOUNDARY = "boundary"
    EVIDENCE_AUDITOR = "evidence_auditor"


class BrowserSquadRole(SentinelModel):
    role_id: str = Field(default_factory=lambda: new_id("bsrole"))
    mission_id: str
    authority_envelope_id: str
    role_kind: BrowserSquadRoleKind
    allowed_neuron_kinds: list[NeuronKind] = Field(default_factory=list)
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_execute: bool = False
    can_call_organ_directly: bool = False
    can_call_runtime_execution: bool = False
    can_access_credentials: bool = False
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False

    @model_validator(mode="after")
    def _role_is_view_only(self) -> "BrowserSquadRole":
        if not self.data_not_instruction:
            raise ValueError("browser_squad_role_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("browser_squad_role_cannot_enable_execution_or_authority")
        if any(
            (
                self.can_execute,
                self.can_call_organ_directly,
                self.can_call_runtime_execution,
                self.can_access_credentials,
                self.can_grant_authority,
                self.can_approve_future_execution,
            )
        ):
            raise ValueError("browser_squad_role_cannot_enable_execution_or_authority")
        return self


class BrowserSquadRoleOutput(SentinelModel):
    output_id: str = Field(default_factory=lambda: new_id("bsout"))
    mission_id: str
    authority_envelope_id: str
    role_kind: BrowserSquadRoleKind
    source_signal_refs: list[str] = Field(default_factory=list)
    proposal_artifact_refs: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    summary: str
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_execute: bool = False
    can_call_organ_directly: bool = False
    can_call_runtime_execution: bool = False
    can_access_credentials: bool = False
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False

    @model_validator(mode="after")
    def _output_is_context_only(self) -> "BrowserSquadRoleOutput":
        if not self.data_not_instruction:
            raise ValueError("browser_squad_output_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("browser_squad_output_cannot_enable_execution_or_authority")
        if any(
            (
                self.can_execute,
                self.can_call_organ_directly,
                self.can_call_runtime_execution,
                self.can_access_credentials,
                self.can_grant_authority,
                self.can_approve_future_execution,
            )
        ):
            raise ValueError("browser_squad_output_cannot_enable_execution_or_authority")
        return self


class BrowserNeuralOperatorSquad(SentinelModel):
    mission_id: str
    authority_envelope_id: str
    roles: list[BrowserSquadRole]
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"

    @model_validator(mode="after")
    def _squad_is_context_only(self) -> "BrowserNeuralOperatorSquad":
        if not self.data_not_instruction:
            raise ValueError("browser_squad_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("browser_squad_cannot_enable_execution_or_authority")
        return self

    @classmethod
    def default(cls, *, mission_id: str, authority_envelope_id: str) -> "BrowserNeuralOperatorSquad":
        mapping = {
            BrowserSquadRoleKind.SCOUT: [NeuronKind.BROWSER_OBSERVATION, NeuronKind.PAGE_STATE],
            BrowserSquadRoleKind.PLANNER: [NeuronKind.INTENT, NeuronKind.ACTION_PLANNER],
            BrowserSquadRoleKind.OPERATOR: [NeuronKind.MOTOR_PROPOSAL],
            BrowserSquadRoleKind.VERIFIER: [NeuronKind.VERIFIER],
            BrowserSquadRoleKind.RECOVERY: [NeuronKind.FAILURE_RECOVERY],
            BrowserSquadRoleKind.BOUNDARY: [NeuronKind.RISK_BOUNDARY],
            BrowserSquadRoleKind.EVIDENCE_AUDITOR: [NeuronKind.EVIDENCE_AUDITOR],
        }
        return cls(
            mission_id=mission_id,
            authority_envelope_id=authority_envelope_id,
            roles=[
                BrowserSquadRole(
                    mission_id=mission_id,
                    authority_envelope_id=authority_envelope_id,
                    role_kind=kind,
                    allowed_neuron_kinds=neurons,
                )
                for kind, neurons in mapping.items()
            ],
        )

    def role(self, role_kind: BrowserSquadRoleKind) -> BrowserSquadRole:
        for role in self.roles:
            if role.role_kind is role_kind:
                return role
        raise KeyError(role_kind)

    def role_output(
        self,
        role_kind: BrowserSquadRoleKind,
        *,
        source_signal_refs: list[str],
        summary: str,
        proposal_artifact_refs: list[str] | None = None,
        risk_flags: list[str] | None = None,
    ) -> BrowserSquadRoleOutput:
        self.role(role_kind)
        return BrowserSquadRoleOutput(
            mission_id=self.mission_id,
            authority_envelope_id=self.authority_envelope_id,
            role_kind=role_kind,
            source_signal_refs=list(source_signal_refs),
            proposal_artifact_refs=list(proposal_artifact_refs or []),
            risk_flags=sorted(set(risk_flags or [])),
            summary=summary,
        )

    def boundary_check(self, text: str, *, source_signal_refs: list[str]) -> BrowserSquadRoleOutput:
        lowered = text.lower()
        flags = sorted({flag for flag, keywords in _BOUNDARY_KEYWORDS.items() if any(keyword in lowered for keyword in keywords)})
        return self.role_output(BrowserSquadRoleKind.BOUNDARY, source_signal_refs=source_signal_refs, summary="boundary check", risk_flags=flags)

    def record_output(
        self,
        ledger: BrowserNeuralReceiptLedger,
        *,
        workflow_id: str,
        run_id: str,
        output: BrowserSquadRoleOutput,
    ) -> None:
        ledger.append(
            workflow_id=workflow_id,
            run_id=run_id,
            event_type="browser_squad_role_output",
            actor_or_neuron_id=output.role_kind.value,
            refs={
                "role_output_id": output.output_id,
                "authority_envelope_id": self.authority_envelope_id,
            },
            state={
                "summary": output.summary,
                "source_signal_refs": output.source_signal_refs,
                "proposal_artifact_refs": output.proposal_artifact_refs,
                "risk_flags": output.risk_flags,
            },
        )
