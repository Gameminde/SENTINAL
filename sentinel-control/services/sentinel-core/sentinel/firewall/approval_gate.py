from __future__ import annotations

from sentinel.shared.enums import ApprovalStatus
from sentinel.shared.models import FirewallReview


class FirewallBlockedError(RuntimeError):
    pass


class ApprovalRequiredError(RuntimeError):
    pass


def require_approval(review: FirewallReview) -> bool:
    return review.requires_approval and review.approval_status != ApprovalStatus.APPROVED


def assert_allowed(review: FirewallReview) -> None:
    if review.blocked or review.approval_status == ApprovalStatus.BLOCKED:
        raise FirewallBlockedError("; ".join(review.reasons) or f"{review.tool} is blocked by policy.")

    if require_approval(review):
        raise ApprovalRequiredError(f"{review.tool} requires explicit user approval.")

    if not review.allowed:
        raise FirewallBlockedError(f"{review.tool} is not allowed by policy.")

