"""AgentOps Firewall public API."""

from sentinel.firewall.approval_gate import ApprovalRequiredError, FirewallBlockedError, assert_allowed, require_approval
from sentinel.firewall.dry_run import build_dry_run
from sentinel.firewall.policy import POLICIES, get_policy, review_action
from sentinel.firewall.risk_scorer import score_action

__all__ = [
    "ApprovalRequiredError",
    "FirewallBlockedError",
    "POLICIES",
    "assert_allowed",
    "build_dry_run",
    "get_policy",
    "require_approval",
    "review_action",
    "score_action",
]

