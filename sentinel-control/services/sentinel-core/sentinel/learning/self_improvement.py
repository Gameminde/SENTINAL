from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel.learning.feedback import FeedbackRecord, summarize_feedback
from sentinel.shared.enums import RiskLevel
from sentinel.shared.models import new_id


ProposalStatus = Literal["draft", "needs_user_approval", "approved", "rejected"]


class ImprovementProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("improve"))
    problem_observed: str
    evidence: list[str] = Field(default_factory=list)
    proposed_patch: str
    risk: RiskLevel
    tests_needed: list[str] = Field(default_factory=list)
    status: ProposalStatus = "needs_user_approval"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
