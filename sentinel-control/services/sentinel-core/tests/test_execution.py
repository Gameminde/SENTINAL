import pytest

from sentinel.execution import ActionRunner
from sentinel.firewall import ApprovalRequiredError, FirewallBlockedError
from sentinel.shared.enums import ApprovalStatus, RiskLevel
from sentinel.shared.models import AgentAction


def action(tool: str, payload: dict, risk: RiskLevel = RiskLevel.LOW, requires_approval: bool = False) -> AgentAction:
    return AgentAction(
        tool=tool,
        intent=f"Run {tool}",
        input=payload,
        expected_output="safe output",
        risk_level=risk,
        requires_approval=requires_approval,
    )


def test_file_execution_is_limited_to_generated_projects(tmp_path):
    runner = ActionRunner(project_root=tmp_path)
    folder = action("create_folder", {"path": "data/generated_projects/demo"})
    file = action("create_file", {"path": "data/generated_projects/demo/00_VERDICT.md", "content": "ok"})

    _, folder_output = runner.run(folder)
    _, file_output = runner.run(file)

    assert folder_output["status"] == "created"
    assert file_output["status"] == "created"
    assert (tmp_path / "data/generated_projects/demo/00_VERDICT.md").read_text(encoding="utf-8") == "ok"

    outside = action("create_file", {"path": "outside.md", "content": "blocked"})
    with pytest.raises(FirewallBlockedError):
        runner.run(outside)


def test_email_draft_executor_requires_approval_and_never_sends(tmp_path):
    runner = ActionRunner(project_root=tmp_path)
    draft = action(
        "prepare_email_draft",
        {"subject": "Quick question", "body": "Draft only"},
        risk=RiskLevel.MEDIUM,
        requires_approval=True,
    )

    with pytest.raises(ApprovalRequiredError):
        runner.run(draft)

    _, output = runner.run(draft, approval_status=ApprovalStatus.APPROVED)
    assert output["status"] == "draft_created"
    assert output["sent"] == "false"

