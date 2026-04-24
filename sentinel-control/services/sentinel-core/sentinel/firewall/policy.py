from __future__ import annotations

from pathlib import Path

from sentinel.firewall.dry_run import build_dry_run
from sentinel.firewall.risk_scorer import is_path_allowed, score_action
from sentinel.shared.enums import ApprovalStatus, RiskLevel
from sentinel.shared.models import AgentAction, EvidenceItem, FirewallPolicy, FirewallReview


POLICIES: dict[str, dict[str, object]] = {
    "create_folder": {
        "risk": "low",
        "auto_allowed": True,
        "allowed_paths": ["./data/generated_projects"],
    },
    "create_file": {
        "risk": "low",
        "auto_allowed": True,
        "allowed_paths": ["./data/generated_projects"],
    },
    "prepare_email_draft": {
        "risk": "medium",
        "auto_allowed": False,
        "requires_user_approval": True,
    },
    "send_email": {
        "risk": "high",
        "auto_allowed": False,
        "requires_user_approval": True,
        "v1_disabled": True,
    },
    "browser_submit_form": {
        "risk": "high",
        "auto_allowed": False,
        "requires_user_approval": True,
        "v1_disabled": True,
    },
    "run_shell_command": {
        "risk": "critical",
        "auto_allowed": False,
        "v1_disabled": True,
    },
    "modify_code": {
        "risk": "critical",
        "auto_allowed": False,
        "v1_disabled": True,
    },
}


_RISK_ORDER = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


def _max_risk(left: RiskLevel, right: RiskLevel) -> RiskLevel:
    return left if _RISK_ORDER[left] >= _RISK_ORDER[right] else right


def _requires_approval(risk: RiskLevel, policy: FirewallPolicy) -> bool:
    return policy.requires_user_approval or risk in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}


def get_policy(tool_name: str) -> FirewallPolicy:
    raw = POLICIES.get(tool_name)
    if raw is None:
        return FirewallPolicy(
            tool_name=tool_name,
            risk_level=RiskLevel.CRITICAL,
            auto_allowed=False,
            requires_user_approval=True,
            v1_disabled=True,
            policy_json={"reason": "Unknown tools default to critical risk and are blocked."},
        )

    return FirewallPolicy(
        tool_name=tool_name,
        risk_level=RiskLevel(str(raw["risk"])),
        auto_allowed=bool(raw.get("auto_allowed", False)),
        requires_user_approval=bool(raw.get("requires_user_approval", False)),
        v1_disabled=bool(raw.get("v1_disabled", False)),
        allowed_paths=[str(path) for path in raw.get("allowed_paths", [])],
        policy_json={key: value for key, value in raw.items() if key not in {"risk", "auto_allowed", "requires_user_approval", "v1_disabled", "allowed_paths"}},
    )


def review_action(
    action: AgentAction,
    evidence: list[EvidenceItem] | None = None,
    approval_status: ApprovalStatus | None = None,
    project_root: str | Path | None = None,
) -> FirewallReview:
    policy = get_policy(action.tool)
    effective_risk = _max_risk(action.risk_level, policy.risk_level)
    requires_approval = action.requires_approval or _requires_approval(effective_risk, policy)
    normalized_action = action.model_copy(update={
        "risk_level": effective_risk,
        "requires_approval": requires_approval,
    })

    reasons: list[str] = []
    blocked = False

    if policy.v1_disabled:
        blocked = True
        reasons.append(f"{action.tool} is disabled in v1.")

    if policy.allowed_paths and not is_path_allowed(normalized_action, policy, project_root=project_root):
        blocked = True
        reasons.append(f"{action.tool} path is outside allowed directories.")

    risk_score = score_action(normalized_action, policy=policy, project_root=project_root)

    if blocked:
        status = ApprovalStatus.BLOCKED
    elif approval_status is not None:
        status = approval_status
    elif requires_approval:
        status = ApprovalStatus.PENDING
    else:
        status = ApprovalStatus.NOT_REQUIRED

    allowed = not blocked and (not requires_approval or status == ApprovalStatus.APPROVED)
    if not requires_approval and not policy.auto_allowed:
        allowed = False
        reasons.append(f"{action.tool} is not auto-allowed by policy.")

    return FirewallReview(
        action_id=action.id,
        tool=action.tool,
        risk_level=effective_risk,
        risk_score=risk_score,
        requires_approval=requires_approval,
        approval_status=status,
        allowed=allowed,
        blocked=blocked,
        reasons=reasons,
        policy=policy.model_dump(mode="json"),
        dry_run=build_dry_run(normalized_action, evidence=evidence),
    )

