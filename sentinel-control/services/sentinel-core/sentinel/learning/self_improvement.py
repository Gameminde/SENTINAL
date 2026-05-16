from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sentinel.learning.feedback import FeedbackRecord, summarize_feedback
from sentinel.shared.enums import RiskLevel
from sentinel.shared.models import new_id


ProposalStatus = Literal["draft", "needs_user_approval", "approved", "rejected"]


class ImprovementProposal(BaseModel):
    """Self-improvement proposal emitted by the learning loop.

    Task 14 / F-A3.7 — Approval Token contract. A proposal with
    ``status == "approved"`` MUST carry a non-empty
    ``approved_by_human_id`` string identifying the human reviewer who
    authorised the change. The runtime, memory layer, or any automated
    process is forbidden from marking a proposal approved without
    attaching a human id — the model's ``@model_validator`` enforces
    this at construction time, so the rule cannot be bypassed by a
    caller that round-trips through ``model_copy(update=...)`` either.

    All other statuses (``draft``, ``needs_user_approval``, ``rejected``)
    permit ``approved_by_human_id`` to be ``None``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("improve"))
    problem_observed: str
    evidence: list[str] = Field(default_factory=list)
    proposed_patch: str
    risk: RiskLevel
    tests_needed: list[str] = Field(default_factory=list)
    status: ProposalStatus = "needs_user_approval"
    approved_by_human_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _approval_requires_human_id(self) -> "ImprovementProposal":
        if self.status == "approved":
            token = self.approved_by_human_id
            if token is None or (isinstance(token, str) and not token.strip()):
                raise ValueError(
                    "ImprovementProposal with status='approved' requires a "
                    "non-empty approved_by_human_id. The runtime, memory "
                    "layer, or automated processes MUST NOT mark a "
                    "proposal approved without a human reviewer id."
                )
        return self


def propose_improvements(records: list[FeedbackRecord]) -> list[ImprovementProposal]:
    summary = summarize_feedback(records)
    proposals: list[ImprovementProposal] = []

    if summary.weak > 0:
        proposals.append(ImprovementProposal(
            problem_observed=f"{summary.weak} output(s) were marked weak by the user.",
            evidence=summary.weak_targets,
            proposed_patch="Revise the affected prompt/template and rerun evals before applying any production change.",
            risk=RiskLevel.MEDIUM,
            tests_needed=["test_evals.py", "test_gtm_pack.py"],
        ))

    if summary.rejected > 0:
        proposals.append(ImprovementProposal(
            problem_observed=f"{summary.rejected} action(s) were rejected by the user.",
            evidence=summary.weak_targets,
            proposed_patch="Tighten action proposal criteria and require clearer evidence references before proposing similar actions.",
            risk=RiskLevel.MEDIUM,
            tests_needed=["test_firewall.py", "test_execution.py"],
        ))

    return proposals
