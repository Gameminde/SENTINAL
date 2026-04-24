import pytest

from sentinel.firewall import ApprovalRequiredError, FirewallBlockedError, assert_allowed, review_action
from sentinel.shared.enums import ApprovalStatus, RiskLevel
from sentinel.shared.models import AgentAction


def action(tool: str, risk_level: RiskLevel, input_payload: dict | None = None, requires_approval: bool = False) -> AgentAction:
    return AgentAction(
        tool=tool,
        intent=f"Use {tool}",
        input=input_payload or {},
        expected_output="A dry-run-safe result",
        risk_level=risk_level,
        requires_approval=requires_approval,
    )


def test_create_file_allowed_only_inside_generated_projects(tmp_path):
    allowed = action(
        "create_file",
        RiskLevel.LOW,
        {"path": "data/generated_projects/demo/00_VERDICT.md", "content": "hello"},
    )
    review = review_action(allowed, project_root=tmp_path)
    assert review.allowed is True
    assert review.blocked is False
    assert review.approval_status == ApprovalStatus.NOT_REQUIRED
    assert_allowed(review)

    blocked = action("create_file", RiskLevel.LOW, {"path": "secrets.txt", "content": "nope"})
    blocked_review = review_action(blocked, project_root=tmp_path)
    assert blocked_review.allowed is False
    assert blocked_review.blocked is True
    with pytest.raises(FirewallBlockedError):
        assert_allowed(blocked_review)


def test_prepare_email_draft_requires_approval():
    draft = action(
        "prepare_email_draft",
        RiskLevel.MEDIUM,
        {"subject": "Quick question", "body": "Can I ask about invoice follow-ups?"},
        requires_approval=True,
    )
    review = review_action(draft)
    assert review.requires_approval is True
    assert review.allowed is False
    assert review.approval_status == ApprovalStatus.PENDING
    with pytest.raises(ApprovalRequiredError):
        assert_allowed(review)

    approved = review_action(draft, approval_status=ApprovalStatus.APPROVED)
    assert approved.allowed is True
    assert_allowed(approved)


@pytest.mark.parametrize("tool,risk", [
    ("send_email", RiskLevel.HIGH),
    ("browser_submit_form", RiskLevel.HIGH),
    ("run_shell_command", RiskLevel.CRITICAL),
    ("modify_code", RiskLevel.CRITICAL),
])
def test_v1_disabled_actions_are_blocked_even_with_approval(tool, risk):
    dangerous = action(
        tool,
        risk,
        {"path": "data/generated_projects/demo/safe.md", "command": "echo safe", "to": "user@example.com"},
        requires_approval=True,
    )
    review = review_action(dangerous, approval_status=ApprovalStatus.APPROVED)
    assert review.blocked is True
    assert review.allowed is False
    assert review.risk_score == 100.0
    with pytest.raises(FirewallBlockedError):
        assert_allowed(review)

