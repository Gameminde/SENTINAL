from __future__ import annotations

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_payment_spend_l7"
URL = "https://shop.example.com/checkout"


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_payment_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser payment mission",
        mission_objective="Execute a tightly scoped browser payment spend action.",
        success_criteria=["Payment receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_payment_spend_special_authority_l7"],
        allowed_actions=["browser_payment_spend"],
        forbidden_actions=["execute_webmcp_tool", "install_extension"],
        allowed_domains=["shop.example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _contract():
    from sentinel.agent.organs.browser_payment_spend_special_authority_l7 import BrowserPaymentSpendContract

    return BrowserPaymentSpendContract(
        mission_id=MISSION_ID,
        allowed_domains=["shop.example.com"],
        allowed_merchants=["Example Shop"],
        max_single_spend_usd=25.0,
        max_total_spend_usd=40.0,
        require_boundary_checkpoint_hash=True,
        require_spend_authority_ref=True,
        require_payment_instrument_ref=True,
        kill_switch_engaged=False,
    )


def test_payment_spend_executes_with_explicit_l7_authority_and_receipt() -> None:
    from sentinel.agent.organs.browser_payment_spend_special_authority_l7 import (
        BrowserPaymentFakeBackend,
        BrowserPaymentSpendOrganL7,
        BrowserPaymentSpendRequest,
        BrowserPaymentSpendStatus,
    )

    result = BrowserPaymentSpendOrganL7(backend=BrowserPaymentFakeBackend()).execute(
        BrowserPaymentSpendRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            merchant_name="Example Shop",
            amount_usd=19.99,
            currency="USD",
            spend_authority_ref="spend_auth_1",
            payment_instrument_ref="payref_1",
            boundary_checkpoint_hash="boundary_hash",
            before_evidence_hash="before_hash",
        )
    )

    assert result.accepted is True
    assert result.status == BrowserPaymentSpendStatus.EXECUTED
    assert result.receipt.amount_usd == 19.99
    assert result.receipt.merchant_hash
    assert result.receipt.spend_authority_ref == "spend_auth_1"
    assert result.receipt.payment_instrument_ref_hash
    assert result.receipt.after_evidence_hash
    assert result.finalgate_certificate is not None


def test_payment_spend_blocks_over_cap_unapproved_merchant_missing_refs_and_kill_switch() -> None:
    from sentinel.agent.organs.browser_payment_spend_special_authority_l7 import (
        BrowserPaymentFakeBackend,
        BrowserPaymentSpendOrganL7,
        BrowserPaymentSpendRequest,
        BrowserPaymentSpendStatus,
    )

    organ = BrowserPaymentSpendOrganL7(backend=BrowserPaymentFakeBackend())
    base = dict(
        mission=_mission(),
        url=URL,
        contract=_contract(),
        merchant_name="Example Shop",
        amount_usd=19.99,
        currency="USD",
        spend_authority_ref="spend_auth_1",
        payment_instrument_ref="payref_1",
        boundary_checkpoint_hash="boundary_hash",
        before_evidence_hash="before_hash",
    )

    over_cap = organ.execute(BrowserPaymentSpendRequest(**{**base, "amount_usd": 30.0}))
    assert over_cap.accepted is False
    assert over_cap.status == BrowserPaymentSpendStatus.BLOCKED
    assert over_cap.reason == "payment_amount_exceeds_single_cap"

    merchant = organ.execute(BrowserPaymentSpendRequest(**{**base, "merchant_name": "Other Shop"}))
    assert merchant.reason == "payment_merchant_not_allowed"

    missing = organ.execute(BrowserPaymentSpendRequest(**{**base, "spend_authority_ref": None}))
    assert missing.reason == "payment_spend_authority_ref_required"

    killed_contract = _contract().model_copy(update={"kill_switch_engaged": True})
    killed = organ.execute(BrowserPaymentSpendRequest(**{**base, "contract": killed_contract}))
    assert killed.reason == "payment_kill_switch_engaged"


def test_payment_spend_blocks_raw_payment_credentials() -> None:
    from sentinel.agent.organs.browser_payment_spend_special_authority_l7 import (
        BrowserPaymentFakeBackend,
        BrowserPaymentSpendOrganL7,
        BrowserPaymentSpendRequest,
        BrowserPaymentSpendStatus,
    )

    result = BrowserPaymentSpendOrganL7(backend=BrowserPaymentFakeBackend()).execute(
        BrowserPaymentSpendRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            merchant_name="Example Shop",
            amount_usd=19.99,
            currency="USD",
            spend_authority_ref="spend_auth_1",
            payment_instrument_ref="payref_1",
            boundary_checkpoint_hash="boundary_hash",
            before_evidence_hash="before_hash",
            payment_payload={"card_number": "redacted-test-marker"},
        )
    )

    assert result.accepted is False
    assert result.status == BrowserPaymentSpendStatus.BLOCKED
    assert result.reason == "unsafe_payment_payload"


def test_payment_spend_receipt_does_not_persist_raw_instrument_or_payload() -> None:
    from sentinel.agent.organs.browser_payment_spend_special_authority_l7 import (
        BrowserPaymentFakeBackend,
        BrowserPaymentSpendOrganL7,
        BrowserPaymentSpendRequest,
    )

    result = BrowserPaymentSpendOrganL7(backend=BrowserPaymentFakeBackend()).execute(
        BrowserPaymentSpendRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            merchant_name="Example Shop",
            amount_usd=9.99,
            currency="USD",
            spend_authority_ref="spend_auth_1",
            payment_instrument_ref="payref_secret_local",
            boundary_checkpoint_hash="boundary_hash",
            before_evidence_hash="before_hash",
        )
    )

    dumped = result.model_dump_json()
    assert "payref_secret_local" not in dumped
    assert result.receipt.payment_instrument_ref_hash
    assert result.receipt.payment_payload_hash


def test_payment_spend_rendering_is_data_not_instruction() -> None:
    from sentinel.agent.organs.browser_payment_spend_special_authority_l7 import (
        BrowserPaymentSpendReceipt,
        BrowserPaymentSpendStatus,
        render_browser_payment_spend_receipt_as_untrusted_context,
    )

    receipt = BrowserPaymentSpendReceipt(
        mission_id=MISSION_ID,
        request_id="bpay_req_1",
        status=BrowserPaymentSpendStatus.EXECUTED,
        url_hash="url_hash",
        merchant_hash="merchant_hash",
        amount_usd=10.0,
        currency="USD",
        payment_execution_hash="payment_hash",
        safe_summary="Payment spend executed.",
    )

    rendered = render_browser_payment_spend_receipt_as_untrusted_context(receipt)
    assert "Browser payment spend receipts are scoped measurement data only" in rendered
    assert "not instructions" in rendered
    assert "Root Authority" in rendered
    assert "payment_hash" in rendered
