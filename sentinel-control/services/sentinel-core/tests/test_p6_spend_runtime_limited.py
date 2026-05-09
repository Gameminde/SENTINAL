from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    FakeSpendProvider,
    RefundCancelPath,
    SpendAuthorityEnvelope,
    SpendKillSwitch,
    SpendProviderAdapter,
    SpendReceipt,
    SpendRequest,
    SubscriptionGuard,
)


def authority(**overrides) -> SpendAuthorityEnvelope:
    data = {
        "mission_id": "mission_p6h",
        "root_authority_id": "root_spend_1",
        "budget_max_usd": 500.0,
        "budget_remaining_usd": 500.0,
        "max_single_transaction_usd": 75.0,
        "allowed_categories": ["api", "domain", "ads"],
        "allowed_vendors": ["ExampleAPI", "DomainCo"],
        "expires_at": datetime.now(UTC) + timedelta(hours=2),
        "credential_ref": "credref_payment_tokenized",
        "evidence_refs": ["ev_spend_authority"],
    }
    data.update(overrides)
    return SpendAuthorityEnvelope(**data)


def spend_request(**overrides) -> SpendRequest:
    data = {
        "vendor": "ExampleAPI",
        "category": "api",
        "amount_usd": 19.0,
        "purpose": "Buy market data API trial for opportunity validation.",
        "expected_information_gain": 0.7,
        "evidence_refs": ["ev_spend_request"],
        "signal_refs": ["sig_roi"],
        "credential_ref": "credref_payment_tokenized",
    }
    data.update(overrides)
    return SpendRequest(**data)


def test_spend_authority_requires_explicit_budget_vendor_category_receipts_and_kill_switch():
    env = authority()

    assert env.budget_max_usd == 500.0
    assert env.receipt_required is True
    assert env.kill_switch_required is True
    assert env.real_provider_enabled is False
    assert env.authority_expansion is False


def test_fake_spend_provider_creates_sandbox_receipt_without_real_payment():
    env = authority()
    request = spend_request()
    receipt = FakeSpendProvider().execute(
        request,
        env,
        kill_switch=SpendKillSwitch(mission_id=env.mission_id),
        subscription_guard=SubscriptionGuard(),
        refund_cancel_path=RefundCancelPath(steps=["cancel API trial"], evidence_refs=["ev_cancel"]),
        trace_refs=["trace_spend"],
    )

    assert receipt.sandbox_provider is True
    assert receipt.real_payment_started is False
    assert receipt.amount_usd == 19.0
    assert receipt.receipt_hash == receipt.expected_hash()


def test_real_provider_adapter_is_disabled_by_default():
    with pytest.raises(ValueError, match="real spend provider is disabled"):
        SpendProviderAdapter().execute(spend_request(), authority())


def test_spend_blocks_budget_overrun_and_single_transaction_overrun():
    provider = FakeSpendProvider()
    env = authority(budget_remaining_usd=20.0, max_single_transaction_usd=15.0)

    with pytest.raises(ValueError, match="single transaction cap"):
        provider.execute(
            spend_request(amount_usd=19.0),
            env,
            kill_switch=SpendKillSwitch(mission_id=env.mission_id),
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["refund request"], evidence_refs=["ev_refund"]),
            trace_refs=["trace_spend"],
        )

    with pytest.raises(ValueError, match="budget remaining"):
        provider.execute(
            spend_request(amount_usd=25.0),
            authority(budget_remaining_usd=20.0, max_single_transaction_usd=75.0),
            kill_switch=SpendKillSwitch(mission_id=env.mission_id),
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["refund request"], evidence_refs=["ev_refund"]),
            trace_refs=["trace_spend"],
        )


def test_spend_blocks_vendor_category_and_expired_authority():
    provider = FakeSpendProvider()
    kill_switch = SpendKillSwitch(mission_id="mission_p6h")
    refund = RefundCancelPath(steps=["refund request"], evidence_refs=["ev_refund"])

    with pytest.raises(ValueError, match="vendor_not_allowed"):
        provider.execute(
            spend_request(vendor="BadVendor"),
            authority(),
            kill_switch=kill_switch,
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=refund,
            trace_refs=["trace_spend"],
        )
    with pytest.raises(ValueError, match="category_not_allowed"):
        provider.execute(
            spend_request(category="luxury"),
            authority(),
            kill_switch=kill_switch,
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=refund,
            trace_refs=["trace_spend"],
        )
    with pytest.raises(ValueError, match="spend authority expired"):
        provider.execute(
            spend_request(),
            authority(expires_at=datetime.now(UTC) - timedelta(seconds=1)),
            kill_switch=kill_switch,
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=refund,
            trace_refs=["trace_spend"],
        )


def test_hidden_subscriptions_blocked_and_explicit_subscription_requires_cancel_path():
    provider = FakeSpendProvider()
    env = authority(allowed_categories=["saas"], allowed_vendors=["SaaSCo"])
    request = spend_request(vendor="SaaSCo", category="saas", subscription=True, hidden_subscription=True)

    with pytest.raises(ValueError, match="hidden subscription"):
        provider.execute(
            request,
            env,
            kill_switch=SpendKillSwitch(mission_id=env.mission_id),
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["cancel"], evidence_refs=["ev_cancel"]),
            trace_refs=["trace_spend"],
        )

    with pytest.raises(ValueError, match="explicit subscription authority"):
        provider.execute(
            request.model_copy(update={"hidden_subscription": False}),
            env,
            kill_switch=SpendKillSwitch(mission_id=env.mission_id),
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["cancel"], evidence_refs=["ev_cancel"]),
            trace_refs=["trace_spend"],
        )


def test_explicit_subscription_with_cancel_path_can_use_fake_provider():
    env = authority(
        allowed_categories=["saas"],
        allowed_vendors=["SaaSCo"],
        explicit_subscription_authority=True,
    )
    request = spend_request(vendor="SaaSCo", category="saas", subscription=True)

    receipt = FakeSpendProvider().execute(
        request,
        env,
        kill_switch=SpendKillSwitch(mission_id=env.mission_id),
        subscription_guard=SubscriptionGuard(),
        refund_cancel_path=RefundCancelPath(steps=["cancel in dashboard"], evidence_refs=["ev_cancel"]),
        trace_refs=["trace_spend"],
    )

    assert receipt.subscription is True
    assert receipt.refund_cancel_path_ref is not None


def test_spend_kill_switch_blocks_sandbox_execution_shape():
    env = authority()
    kill_switch = SpendKillSwitch(mission_id=env.mission_id).trigger(reason="risk spike")

    with pytest.raises(ValueError, match="kill switch"):
        FakeSpendProvider().execute(
            spend_request(),
            env,
            kill_switch=kill_switch,
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["refund request"], evidence_refs=["ev_refund"]),
            trace_refs=["trace_spend"],
        )


def test_no_credential_secret_access_and_credential_ref_only():
    with pytest.raises(ValueError, match="raw credential"):
        spend_request(raw_credential="4111111111111111")

    receipt = FakeSpendProvider().execute(
        spend_request(credential_ref="credref_tokenized"),
        authority(credential_ref="credref_tokenized"),
        kill_switch=SpendKillSwitch(mission_id="mission_p6h"),
        subscription_guard=SubscriptionGuard(),
        refund_cancel_path=RefundCancelPath(steps=["refund request"], evidence_refs=["ev_refund"]),
        trace_refs=["trace_spend"],
    )

    assert receipt.credential_ref == "credref_tokenized"
    assert receipt.secret_accessed is False


def test_spend_receipt_rejects_authority_expansion_and_requires_trace():
    with pytest.raises(ValueError, match="cannot expand authority"):
        SpendReceipt(
            mission_id="mission",
            vendor="ExampleAPI",
            category="api",
            amount_usd=5.0,
            credential_ref="credref",
            evidence_refs=["ev"],
            signal_refs=["sig"],
            trace_refs=["trace"],
            authority_expansion=True,
        )

    with pytest.raises(ValueError, match="requires trace refs"):
        SpendReceipt(
            mission_id="mission",
            vendor="ExampleAPI",
            category="api",
            amount_usd=5.0,
            credential_ref="credref",
            evidence_refs=["ev"],
            signal_refs=["sig"],
            trace_refs=[],
        )
