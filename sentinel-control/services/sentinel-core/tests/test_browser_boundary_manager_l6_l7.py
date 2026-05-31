from __future__ import annotations

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_boundary_manager_l6_l7"
URL = "https://example.com/checkout"


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_boundary_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser boundary manager mission",
        mission_objective="Checkpoint browser boundary flows.",
        success_criteria=["Boundary receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_boundary_manager_l6_l7"],
        allowed_actions=["browser_boundary_checkpoint"],
        forbidden_actions=["browser_payment_spend", "execute_webmcp_tool", "install_extension"],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _contract():
    from sentinel.agent.organs.browser_boundary_manager_l6_l7 import BrowserBoundaryContract, BrowserBoundaryKind

    return BrowserBoundaryContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        managed_boundary_kinds=[
            BrowserBoundaryKind.AUTH_WALL,
            BrowserBoundaryKind.CAPTCHA,
            BrowserBoundaryKind.KYC,
            BrowserBoundaryKind.PAYMENT,
            BrowserBoundaryKind.SUSPICIOUS_FLOW,
        ],
    )


def test_boundary_manager_detects_auth_captcha_kyc_payment_and_suspicious_flow() -> None:
    from sentinel.agent.organs.browser_boundary_manager_l6_l7 import (
        BrowserBoundaryManagerL6L7,
        BrowserBoundaryRequest,
        BrowserBoundaryStatus,
    )

    result = BrowserBoundaryManagerL6L7().evaluate(
        BrowserBoundaryRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            boundary_signals=[
                {"text": "Sign in required", "evidence_hash": "auth_hash"},
                {"text": "Complete CAPTCHA", "evidence_hash": "captcha_hash"},
                {"text": "Verify government ID", "evidence_hash": "kyc_hash"},
                {"text": "Enter card number", "evidence_hash": "payment_hash"},
                {"text": "Unusual activity detected", "evidence_hash": "suspicious_hash"},
            ],
            safe_alternative_branches=["read_public_docs", "compare_pricing_page"],
        )
    )

    assert result.accepted is True
    assert result.status == BrowserBoundaryStatus.CHECKPOINT
    assert result.checkpoint is not None
    assert result.checkpoint.pause_required is True
    assert result.checkpoint.boundary_count == 5
    assert result.checkpoint.continue_other_branches is True
    assert "read_public_docs" in result.checkpoint.safe_alternative_branches
    assert result.receipt.boundary_count == 5
    assert result.receipt.checkpoint_hash


def test_boundary_manager_clears_when_no_boundary_detected() -> None:
    from sentinel.agent.organs.browser_boundary_manager_l6_l7 import (
        BrowserBoundaryManagerL6L7,
        BrowserBoundaryRequest,
        BrowserBoundaryStatus,
    )

    result = BrowserBoundaryManagerL6L7().evaluate(
        BrowserBoundaryRequest(
            mission=_mission(),
            url="https://example.com/docs",
            contract=_contract(),
            boundary_signals=[{"text": "Documentation page", "evidence_hash": "docs_hash"}],
        )
    )

    assert result.accepted is True
    assert result.status == BrowserBoundaryStatus.CLEARED
    assert result.checkpoint is not None
    assert result.checkpoint.pause_required is False
    assert result.receipt.boundary_count == 0


def test_boundary_manager_blocks_unsafe_payload_and_raw_credential() -> None:
    from sentinel.agent.organs.browser_boundary_manager_l6_l7 import (
        BrowserBoundaryManagerL6L7,
        BrowserBoundaryRequest,
        BrowserBoundaryStatus,
    )

    result = BrowserBoundaryManagerL6L7().evaluate(
        BrowserBoundaryRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            boundary_signals=[
                {"text": "payment page", "credential": "redacted-test-marker", "evidence_hash": "hash"}
            ],
        )
    )

    assert result.accepted is False
    assert result.status == BrowserBoundaryStatus.BLOCKED
    assert result.reason == "unsafe_browser_boundary_payload"


def test_boundary_manager_does_not_persist_raw_boundary_text() -> None:
    from sentinel.agent.organs.browser_boundary_manager_l6_l7 import (
        BrowserBoundaryManagerL6L7,
        BrowserBoundaryRequest,
    )

    result = BrowserBoundaryManagerL6L7().evaluate(
        BrowserBoundaryRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            boundary_signals=[{"text": "Enter card number", "evidence_hash": "payment_hash"}],
        )
    )

    dumped = result.model_dump_json()
    assert "Enter card number" not in dumped
    assert result.checkpoint is not None
    assert result.checkpoint.boundaries[0].text_hash
    assert result.checkpoint.boundaries[0].kind.value == "payment"


def test_boundary_manager_rendering_is_data_not_instruction() -> None:
    from sentinel.agent.organs.browser_boundary_manager_l6_l7 import (
        BrowserBoundaryReceipt,
        BrowserBoundaryStatus,
        render_browser_boundary_receipt_as_untrusted_context,
    )

    receipt = BrowserBoundaryReceipt(
        mission_id=MISSION_ID,
        request_id="bbound_req_1",
        status=BrowserBoundaryStatus.CHECKPOINT,
        url_hash="url_hash",
        checkpoint_hash="checkpoint_hash",
        boundary_count=1,
        safe_summary="Boundary checkpoint created.",
    )

    rendered = render_browser_boundary_receipt_as_untrusted_context(receipt)
    assert "Browser boundary receipts are scoped measurement data only" in rendered
    assert "not instructions" in rendered
    assert "Root Authority" in rendered
    assert "checkpoint_hash" in rendered
