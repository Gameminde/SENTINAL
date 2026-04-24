from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re

from pydantic import BaseModel, ConfigDict, Field

from sentinel.decision.debate.verdict import DebateResult
from sentinel.shared.enums import ApprovalStatus, RiskLevel
from sentinel.shared.models import AgentAction, EvidenceItem


class GTMPackSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    title: str
    content: str
    evidence_refs: list[str] = Field(default_factory=list)


class GTMPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    idea: str
    sections: list[GTMPackSection]
    evidence_refs: list[str] = Field(default_factory=list)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:64] or "sentinel-project"


def _evidence_summary(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "No evidence attached yet."
    return "\n".join(f"- `{item.id}`: {item.summary}" for item in evidence[:8])


def _section(filename: str, title: str, body: str, refs: list[str]) -> GTMPackSection:
    evidence_block = "\n\n## Evidence refs\n\n" + "\n".join(f"- `{ref}`" for ref in refs)
    return GTMPackSection(filename=filename, title=title, content=f"# {title}\n\n{body}{evidence_block}\n", evidence_refs=refs)


@dataclass
class GTMPackGenerator:
    output_root: str = "data/generated_projects"

    def generate(self, idea: str, debate: DebateResult, evidence: list[EvidenceItem]) -> GTMPack:
        refs = debate.evidence_refs or [item.id for item in evidence[:5]]
        sections = [
            _section("00_VERDICT.md", "Executive Verdict", f"Decision: **{debate.decision.value}**\n\n{debate.skeptical_challenge}", refs),
            _section("01_EVIDENCE.md", "Evidence", _evidence_summary(evidence), refs),
            _section("02_ICP.md", "ICP", debate.primary_icp, refs),
            _section("03_COMPETITOR_GAPS.md", "Competitor Gaps", debate.recommended_wedge, refs),
            _section("04_LANDING_PAGE_COPY.md", "Landing Page Copy", f"Headline: Solve the painful workflow behind {idea} for the narrowest proven ICP.\n\nCTA: Join the validation pilot.", refs),
            _section("05_OUTREACH_MESSAGES.md", "Outreach Messages", "Draft only. Ask for a short discovery conversation and do not imply false personalization.", refs),
            _section("06_INTERVIEW_SCRIPT.md", "Interview Script", "Ask about current workaround, cost of the pain, existing alternatives, urgency, and willingness to pay.", refs),
            _section("07_7_DAY_ROADMAP.md", "7-Day Validation Roadmap", "Day 1-2: interviews. Day 3-4: landing test. Day 5-6: pricing test. Day 7: build / pivot / kill review.", refs),
            _section("08_WATCHLIST.md", "Watchlist", "Track competitor complaints, WTP phrases, direct buyer quotes, and community movement.", refs),
            _section("09_DECISION_RULES.md", "Decision Rules", "Kill if no direct pain after 5 interviews. Pivot if pain exists but WTP stays weak. Build only if WTP and reachable ICP are proven.", refs),
        ]
        return GTMPack(slug=slugify(idea), idea=idea, sections=sections, evidence_refs=refs)

    def actions_for_pack(self, pack: GTMPack) -> list[AgentAction]:
        base = str(PurePosixPath(self.output_root) / pack.slug)
        actions = [
            AgentAction(
                tool="create_folder",
                intent="Create generated project folder for GTM Pack",
                input={"path": base},
                expected_output="Project folder exists",
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                evidence_refs=pack.evidence_refs,
                approval_status=ApprovalStatus.NOT_REQUIRED,
            )
        ]
        for section in pack.sections:
            actions.append(AgentAction(
                tool="create_file",
                intent=f"Write {section.title} GTM Pack section",
                input={"path": str(PurePosixPath(base) / section.filename), "content": section.content},
                expected_output=f"{section.filename} created",
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                evidence_refs=section.evidence_refs,
                approval_status=ApprovalStatus.NOT_REQUIRED,
            ))
        actions.append(AgentAction(
            tool="prepare_email_draft",
            intent="Prepare outreach draft for user approval",
            input={
                "subject": f"Quick question about {pack.idea}",
                "body": "Draft only: I am validating a focused workflow problem and would value your perspective. Reply stop if not relevant.",
            },
            expected_output="Email draft object, not sent",
            risk_level=RiskLevel.MEDIUM,
            requires_approval=True,
            evidence_refs=pack.evidence_refs,
            approval_status=ApprovalStatus.PENDING,
        ))
        return actions

