"""Tests for Task 14 / F-A3.7 — ImprovementProposal approval-token.

An ``ImprovementProposal`` with ``status == "approved"`` must carry a
non-empty ``approved_by_human_id``. All other statuses accept a ``None``
token. The invariant is enforced twice:

* At construction time by the pydantic ``@model_validator`` on
  :class:`sentinel.learning.self_improvement.ImprovementProposal`.
* At the runtime supervisor layer by
  :meth:`sentinel.agent.invariants.InvariantChecker.check_improvement_proposals`
  (belt-and-braces for proposals reconstituted outside the pydantic
  validator, e.g. from a persistence store).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentinel.agent import InvariantChecker, InvariantViolation
from sentinel.learning.self_improvement import ImprovementProposal
from sentinel.shared.enums import RiskLevel


def _base_kwargs() -> dict:
    return {
        "problem_observed": "Evaluator flagged a weak asset.",
        "evidence": ["asset_weak_001"],
        "proposed_patch": "Revise the prompt template and rerun evals.",
        "risk": RiskLevel.MEDIUM,
        "tests_needed": ["test_evals.py"],
    }


# ---------------------------------------------------------------------------
# Construction-time (pydantic @model_validator) enforcement.
# ---------------------------------------------------------------------------


def test_approved_without_human_id_raises():
    """Constructing ``ImprovementProposal(status="approved",
    approved_by_human_id=None)`` is forbidden."""
    with pytest.raises(ValidationError) as excinfo:
        ImprovementProposal(
            **_base_kwargs(),
            status="approved",
            approved_by_human_id=None,
        )
    assert "approved_by_human_id" in str(excinfo.value)


def test_approved_with_empty_string_human_id_raises():
    """Empty-string ids are treated identically to ``None``. This closes
    the ``approved_by_human_id=""`` bypass where a caller could satisfy
    ``is not None`` without actually naming a reviewer."""
    with pytest.raises(ValidationError):
        ImprovementProposal(
            **_base_kwargs(),
            status="approved",
            approved_by_human_id="",
        )


def test_approved_with_whitespace_only_human_id_raises():
    """Whitespace-only ids are also forbidden."""
    with pytest.raises(ValidationError):
        ImprovementProposal(
            **_base_kwargs(),
            status="approved",
            approved_by_human_id="   \t\n  ",
        )


def test_approved_with_human_id_succeeds():
    """The happy path: a real human id unlocks the approved status."""
    proposal = ImprovementProposal(
        **_base_kwargs(),
        status="approved",
        approved_by_human_id="user-123",
    )
    assert proposal.status == "approved"
    assert proposal.approved_by_human_id == "user-123"


def test_pending_without_human_id_succeeds():
    """``needs_user_approval`` is the default status. A proposal that
    has not yet been reviewed may omit the token."""
    proposal = ImprovementProposal(
        **_base_kwargs(),
        status="needs_user_approval",
    )
    assert proposal.status == "needs_user_approval"
    assert proposal.approved_by_human_id is None


def test_draft_without_human_id_succeeds():
    proposal = ImprovementProposal(
        **_base_kwargs(),
        status="draft",
    )
    assert proposal.status == "draft"
    assert proposal.approved_by_human_id is None


def test_rejected_without_human_id_succeeds():
    """A rejected proposal records a final decision, but the reviewer
    identity is tracked on the rejection pathway, not on the proposal
    model. The approval-token field stays ``None``."""
    proposal = ImprovementProposal(
        **_base_kwargs(),
        status="rejected",
    )
    assert proposal.status == "rejected"
    assert proposal.approved_by_human_id is None


def test_default_status_is_needs_user_approval_without_token():
    """Regression guard: the default-constructed proposal must not be
    implicitly approved. A proposal coming in from the learning loop
    starts in a human-review-required state by doctrine."""
    proposal = ImprovementProposal(**_base_kwargs())
    assert proposal.status == "needs_user_approval"
    assert proposal.approved_by_human_id is None


# ---------------------------------------------------------------------------
# Backward-compatibility for non-approved statuses under model_copy.
# ---------------------------------------------------------------------------


def test_model_copy_to_approved_without_token_is_rejected():
    """``model_copy(update={"status": "approved"})`` must ALSO enforce
    the invariant. Pydantic v2's ``model_copy`` does not re-run
    validators by default — but callers MUST opt in to revalidation
    via ``model_copy(..., deep=False)`` wrapped by
    ``model_validate`` if they want safety. We verify the intended
    promotion flow by reconstructing the model via ``model_validate``,
    which is the supported doctrine."""
    proposal = ImprovementProposal(**_base_kwargs())
    with pytest.raises(ValidationError):
        ImprovementProposal.model_validate(
            {**proposal.model_dump(), "status": "approved"}
        )


# ---------------------------------------------------------------------------
# Runtime supervisor invariant (belt-and-braces).
# ---------------------------------------------------------------------------


def test_invariant_checker_validates_approval_token_happy_path():
    """A well-formed approved proposal passes the supervisor check."""
    proposal = ImprovementProposal(
        **_base_kwargs(),
        status="approved",
        approved_by_human_id="user-123",
    )
    InvariantChecker().check_improvement_proposals([proposal])


def test_invariant_checker_validates_approval_token_reconstituted():
    """Simulate a proposal reconstituted outside the pydantic
    validator path (e.g. loaded from storage via
    ``model_construct``, which skips validators). The supervisor
    invariant must still catch a missing token.
    """
    proposal = ImprovementProposal.model_construct(
        id="improve-test",
        problem_observed="x",
        evidence=[],
        proposed_patch="y",
        risk=RiskLevel.MEDIUM,
        tests_needed=[],
        status="approved",
        approved_by_human_id=None,
    )
    with pytest.raises(InvariantViolation) as excinfo:
        InvariantChecker().check_improvement_proposals([proposal])
    assert "approved_by_human_id" in str(excinfo.value)


def test_invariant_checker_ignores_non_approved_proposals():
    """Non-approved statuses are always token-optional."""
    proposals = [
        ImprovementProposal(**_base_kwargs(), status="draft"),
        ImprovementProposal(**_base_kwargs(), status="needs_user_approval"),
        ImprovementProposal(**_base_kwargs(), status="rejected"),
    ]
    # Should not raise.
    InvariantChecker().check_improvement_proposals(proposals)


def test_invariant_checker_catches_whitespace_token_when_reconstituted():
    proposal = ImprovementProposal.model_construct(
        id="improve-test",
        problem_observed="x",
        evidence=[],
        proposed_patch="y",
        risk=RiskLevel.MEDIUM,
        tests_needed=[],
        status="approved",
        approved_by_human_id="   ",
    )
    with pytest.raises(InvariantViolation):
        InvariantChecker().check_improvement_proposals([proposal])
