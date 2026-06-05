from __future__ import annotations


def test_channel_draft_creates_receipt_without_sender_call() -> None:
    from sentinel.agent.organs.channel_draft_send_organ_v1 import (
        ChannelDraftSendContract,
        ChannelDraftSendOrganV1,
        ChannelDraftSendRequest,
        ChannelDraftSendStatus,
    )

    called = False

    def sender(_request):
        nonlocal called
        called = True
        raise AssertionError("sender must not be called for draft")

    result = ChannelDraftSendOrganV1(sender=sender).execute(
        ChannelDraftSendRequest(
            mission_id="mission_channel_draft",
            mode="draft",
            channel="email",
            subject="Hello",
            body="Draft body",
            recipients=["founder@example.com"],
            evidence_refs=["ev_channel"],
        ),
        contract=ChannelDraftSendContract(allowed_channels=["email"]),
    )

    assert result.status is ChannelDraftSendStatus.DRAFT_CREATED
    assert called is False
    assert result.receipt is not None
    assert result.receipt.send_attempted is False
    assert result.receipt.body_sha256
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True


def test_channel_send_requires_explicit_authority_and_sender() -> None:
    from sentinel.agent.organs.channel_draft_send_organ_v1 import (
        ChannelDraftSendContract,
        ChannelDraftSendOrganV1,
        ChannelDraftSendRequest,
        ChannelDraftSendStatus,
    )

    request = ChannelDraftSendRequest(
        mission_id="mission_channel_send_block",
        mode="send",
        channel="email",
        subject="Hello",
        body="Body",
        recipients=["founder@example.com"],
        recipient_provenance={"founder@example.com": "user_supplied_contact"},
        evidence_refs=["ev_channel"],
    )

    no_auth = ChannelDraftSendOrganV1(sender=lambda _request: "delivery").execute(
        request,
        contract=ChannelDraftSendContract(allowed_channels=["email"], send_authorized=False),
    )
    assert no_auth.status is ChannelDraftSendStatus.BLOCKED
    assert no_auth.blocked_reason == "send_authority_missing"

    no_sender = ChannelDraftSendOrganV1().execute(
        request.model_copy(update={"send_authority_ref": "auth_channel_send_1"}),
        contract=ChannelDraftSendContract(allowed_channels=["email"], send_authorized=True),
    )
    assert no_sender.status is ChannelDraftSendStatus.BLOCKED
    assert no_sender.blocked_reason == "channel_sender_missing"


def test_channel_rejects_receipt_or_memory_as_send_authority_ref() -> None:
    import pytest

    from sentinel.agent.organs.channel_draft_send_organ_v1 import ChannelDraftSendRequest

    for ref in ["receipt:abc", "finalgate:abc", "memory:abc", "replan:abc"]:
        with pytest.raises(ValueError):
            ChannelDraftSendRequest(
                mission_id="mission_channel_bad_auth_ref",
                mode="send",
                channel="email",
                subject="Hello",
                body="Body",
                recipients=["founder@example.com"],
                recipient_provenance={"founder@example.com": "user_supplied_contact"},
                send_authority_ref=ref,
                evidence_refs=["ev_channel"],
            )


def test_channel_send_with_authority_calls_injected_sender_and_hashes_recipients() -> None:
    from sentinel.agent.organs.channel_draft_send_organ_v1 import (
        ChannelDraftSendContract,
        ChannelDraftSendOrganV1,
        ChannelDraftSendRequest,
        ChannelDraftSendStatus,
        ChannelSendTransportReceipt,
    )

    sent_to: list[list[str]] = []

    def sender(request):
        sent_to.append(list(request.recipients))
        return ChannelSendTransportReceipt(delivery_ref="fixture_delivery_1")

    result = ChannelDraftSendOrganV1(sender=sender).execute(
        ChannelDraftSendRequest(
            mission_id="mission_channel_send",
            mode="send",
            channel="email",
            subject="Hello",
            body="Body",
            recipients=["founder@example.com"],
            recipient_provenance={"founder@example.com": "user_supplied_contact"},
            send_authority_ref="auth_channel_send_1",
            evidence_refs=["ev_channel"],
        ),
        contract=ChannelDraftSendContract(allowed_channels=["email"], send_authorized=True),
    )

    assert result.status is ChannelDraftSendStatus.SENT
    assert sent_to == [["founder@example.com"]]
    assert result.receipt is not None
    assert result.receipt.send_attempted is True
    assert result.receipt.delivery_ref == "fixture_delivery_1"
    assert result.receipt.recipient_hashes
    assert "founder@example.com" not in str(result.model_dump(mode="json"))


def test_channel_compliance_and_rate_limit_block_send() -> None:
    from sentinel.agent.organs.channel_draft_send_organ_v1 import (
        ChannelDraftSendContract,
        ChannelDraftSendOrganV1,
        ChannelDraftSendRequest,
        ChannelDraftSendStatus,
        ChannelRateLimitLedger,
        ChannelSendTransportReceipt,
    )

    organ = ChannelDraftSendOrganV1(
        sender=lambda _request: ChannelSendTransportReceipt(delivery_ref="delivery"),
        rate_ledger=ChannelRateLimitLedger(),
    )
    contract = ChannelDraftSendContract(allowed_channels=["email"], send_authorized=True, max_recipients_per_window=1)

    compliance = organ.execute(
        ChannelDraftSendRequest(
            mission_id="mission_channel_compliance",
            mode="send",
            channel="email",
            subject="Credential capture",
            body="Please send api_key now",
            recipients=["a@example.com"],
            recipient_provenance={"a@example.com": "user_supplied_contact"},
            send_authority_ref="auth_channel_send_1",
            evidence_refs=["ev_channel"],
        ),
        contract=contract,
    )
    assert compliance.status is ChannelDraftSendStatus.BLOCKED
    assert compliance.blocked_reason == "compliance_blocked"

    first = organ.execute(
        ChannelDraftSendRequest(
            mission_id="mission_channel_rate",
            mode="send",
            channel="email",
            subject="Hello",
            body="Body",
            recipients=["a@example.com"],
            recipient_provenance={"a@example.com": "user_supplied_contact"},
            send_authority_ref="auth_channel_send_1",
            evidence_refs=["ev_channel"],
        ),
        contract=contract,
    )
    second = organ.execute(
        ChannelDraftSendRequest(
            mission_id="mission_channel_rate",
            mode="send",
            channel="email",
            subject="Hello",
            body="Body",
            recipients=["b@example.com"],
            recipient_provenance={"b@example.com": "user_supplied_contact"},
            send_authority_ref="auth_channel_send_1",
            evidence_refs=["ev_channel"],
        ),
        contract=contract,
    )
    assert first.status is ChannelDraftSendStatus.SENT
    assert second.status is ChannelDraftSendStatus.BLOCKED
    assert second.blocked_reason == "rate_limit_exhausted"


def test_channel_request_rejects_raw_secret_content() -> None:
    import pytest

    from sentinel.agent.organs.channel_draft_send_organ_v1 import ChannelDraftSendRequest

    with pytest.raises(ValueError):
        ChannelDraftSendRequest(
            mission_id="mission_channel_secret",
            mode="draft",
            channel="email",
            subject="Hello",
            body="Use " + "Be" + "arer " + "secret-value-1234567890",
            evidence_refs=["ev_channel"],
        )


def test_channel_power_runtime_executor_adapter() -> None:
    from sentinel.agent.organs.channel_draft_send_organ_v1 import (
        ChannelDraftSendContract,
        ChannelSendTransportReceipt,
        build_channel_power_executor,
    )
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        SentinelPowerRuntimeV0,
    )

    executor = build_channel_power_executor(
        contract=ChannelDraftSendContract(allowed_channels=["email"], send_authorized=False),
        sender=lambda _request: ChannelSendTransportReceipt(delivery_ref="not_used"),
    )
    plan = PowerMissionPlan(
        mission_id="mission_channel_power",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="draft",
                    actuator_family=PowerActuatorFamily.CHANNEL,
                    capability_level=PowerActuatorCapabilityLevel.L5,
                    organ_kind="channel_draft_send",
                    action_kind="draft",
                    request={
                        "mode": "draft",
                        "channel": "email",
                        "subject": "Hello",
                        "body": "Draft",
                        "recipients": ["founder@example.com"],
                        "evidence_refs": ["ev_channel"],
                    },
                )
            ]
        ),
    )

    result = SentinelPowerRuntimeV0().run(
        plan,
        config=PowerRuntimeConfig(enabled=True),
        actuator_executor=executor,
    )

    assert result.status == "completed"
    assert result.step_results[0].receipt_refs
    assert result.step_results[0].finalgate_certificate_refs


def test_channel_power_executor_blocks_mislabeled_step_before_sender() -> None:
    from sentinel.agent.organs.channel_draft_send_organ_v1 import (
        ChannelDraftSendContract,
        ChannelSendTransportReceipt,
        build_channel_power_executor,
    )
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionStep,
        PowerStepStatus,
    )

    called = False

    def sender(_request):
        nonlocal called
        called = True
        return ChannelSendTransportReceipt(delivery_ref="must_not_happen")

    executor = build_channel_power_executor(
        contract=ChannelDraftSendContract(allowed_channels=["email"], send_authorized=True),
        sender=sender,
    )
    result = executor(
        PowerMissionStep(
            step_id="channel_mislabeled",
            actuator_family=PowerActuatorFamily.WORKSPACE,
            capability_level=PowerActuatorCapabilityLevel.L3,
            organ_kind="channel_draft_send",
            action_kind="send",
            request={
                "mode": "send",
                "channel": "email",
                "subject": "Hello",
                "body": "Body",
                "recipients": ["founder@example.com"],
                "recipient_provenance": {"founder@example.com": "user_supplied_contact"},
                "send_authority_ref": "auth_channel_send_1",
                "evidence_refs": ["ev_channel"],
            },
        ),
        {"mission_id": "mission_channel_mislabeled"},
    )

    assert result.status is PowerStepStatus.BLOCKED
    assert result.blocked_reason == "unsupported_actuator_family"
    assert called is False
