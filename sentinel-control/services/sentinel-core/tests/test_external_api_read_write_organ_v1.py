from __future__ import annotations


def test_external_api_get_allowed_domain_hashes_body_without_raw_body() -> None:
    from sentinel.agent.organs.external_api_read_write_organ_v1 import (
        ExternalAPIContract,
        ExternalAPIOrganV1,
        ExternalAPIRequest,
        ExternalAPIStatus,
        ExternalAPITransportResponse,
    )

    calls: list[str] = []

    def transport(request):
        calls.append(request.url)
        return ExternalAPITransportResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body=b'{"ok": true, "secret": "not persisted raw"}',
        )

    result = ExternalAPIOrganV1(transport=transport).execute(
        ExternalAPIRequest(mission_id="mission_api_get", method="GET", url="https://api.example.com/v1/items"),
        contract=ExternalAPIContract(allowed_domains=["api.example.com"], allowed_methods=["GET", "HEAD"]),
    )

    assert result.status is ExternalAPIStatus.SUCCEEDED
    assert calls == ["https://api.example.com/v1/items"]
    assert result.receipt is not None
    assert result.receipt.response_body_sha256
    assert result.receipt.response_body_quarantine_ref is None
    assert "not persisted raw" not in str(result.model_dump(mode="json"))
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True


def test_external_api_blocks_domain_mismatch_without_transport_call() -> None:
    from sentinel.agent.organs.external_api_read_write_organ_v1 import (
        ExternalAPIContract,
        ExternalAPIOrganV1,
        ExternalAPIRequest,
        ExternalAPIStatus,
    )

    called = False

    def transport(_request):
        nonlocal called
        called = True
        raise AssertionError("transport must not be called")

    result = ExternalAPIOrganV1(transport=transport).execute(
        ExternalAPIRequest(mission_id="mission_api_domain", method="GET", url="https://evil.example/v1/items"),
        contract=ExternalAPIContract(allowed_domains=["api.example.com"], allowed_methods=["GET"]),
    )

    assert result.status is ExternalAPIStatus.BLOCKED
    assert result.blocked_reason == "domain_not_allowed"
    assert called is False
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True


def test_external_api_mutation_requires_explicit_authority() -> None:
    from sentinel.agent.organs.external_api_read_write_organ_v1 import (
        ExternalAPIContract,
        ExternalAPIOrganV1,
        ExternalAPIRequest,
        ExternalAPIStatus,
        ExternalAPITransportResponse,
    )

    blocked = ExternalAPIOrganV1(transport=lambda _request: ExternalAPITransportResponse(status_code=201)).execute(
        ExternalAPIRequest(mission_id="mission_api_post_block", method="POST", url="https://api.example.com/v1/items"),
        contract=ExternalAPIContract(allowed_domains=["api.example.com"], allowed_methods=["POST"]),
    )
    assert blocked.status is ExternalAPIStatus.BLOCKED
    assert blocked.blocked_reason == "mutation_authority_missing"

    called_methods: list[str] = []

    def transport(request):
        called_methods.append(request.method)
        return ExternalAPITransportResponse(status_code=201, headers={"x-created": "1"}, body=b'{"created": true}')

    allowed = ExternalAPIOrganV1(transport=transport).execute(
        ExternalAPIRequest(
            mission_id="mission_api_post_allow",
            method="POST",
            url="https://api.example.com/v1/items",
            body=b'{"name": "demo"}',
            mutation_authority_ref="auth_api_mutation_1",
        ),
        contract=ExternalAPIContract(
            allowed_domains=["api.example.com"],
            allowed_methods=["POST"],
            mutation_authorized=True,
        ),
    )

    assert allowed.status is ExternalAPIStatus.SUCCEEDED
    assert called_methods == ["POST"]
    assert allowed.receipt is not None
    assert allowed.receipt.mutation_authority_ref == "auth_api_mutation_1"


def test_external_api_rejects_raw_auth_cookie_token_headers() -> None:
    import pytest

    from sentinel.agent.organs.external_api_read_write_organ_v1 import ExternalAPIRequest

    with pytest.raises(ValueError):
        ExternalAPIRequest(
            mission_id="mission_api_header",
            method="GET",
            url="https://api.example.com/v1/items",
            headers={"Authorization": "Be" + "arer " + "secret-value-1234567890"},
        )


def test_external_api_rate_limit_blocks_after_budget() -> None:
    from sentinel.agent.organs.external_api_read_write_organ_v1 import (
        ExternalAPIContract,
        ExternalAPIOrganV1,
        ExternalAPIRateLimitLedger,
        ExternalAPIRequest,
        ExternalAPIStatus,
        ExternalAPITransportResponse,
    )

    ledger = ExternalAPIRateLimitLedger()
    organ = ExternalAPIOrganV1(
        transport=lambda _request: ExternalAPITransportResponse(status_code=200, body=b"{}"),
        rate_ledger=ledger,
    )
    contract = ExternalAPIContract(
        allowed_domains=["api.example.com"],
        allowed_methods=["GET"],
        max_requests_per_domain=1,
    )

    first = organ.execute(
        ExternalAPIRequest(mission_id="mission_api_rate", method="GET", url="https://api.example.com/one"),
        contract=contract,
    )
    second = organ.execute(
        ExternalAPIRequest(mission_id="mission_api_rate", method="GET", url="https://api.example.com/two"),
        contract=contract,
    )

    assert first.status is ExternalAPIStatus.SUCCEEDED
    assert second.status is ExternalAPIStatus.BLOCKED
    assert second.blocked_reason == "rate_limit_exhausted"


def test_external_api_response_body_quarantine_is_hash_ref_only() -> None:
    from sentinel.agent.organs.external_api_read_write_organ_v1 import (
        ExternalAPIContract,
        ExternalAPIOrganV1,
        ExternalAPIRequest,
        ExternalAPITransportResponse,
    )

    result = ExternalAPIOrganV1(
        transport=lambda _request: ExternalAPITransportResponse(status_code=200, body=b"large raw body")
    ).execute(
        ExternalAPIRequest(mission_id="mission_api_quarantine", method="GET", url="https://api.example.com/items"),
        contract=ExternalAPIContract(
            allowed_domains=["api.example.com"],
            allowed_methods=["GET"],
            allow_response_body_quarantine=True,
        ),
    )

    assert result.receipt is not None
    assert result.receipt.response_body_quarantine_ref
    assert "large raw body" not in str(result.model_dump(mode="json"))


def test_external_api_power_runtime_executor_adapter() -> None:
    from sentinel.agent.organs.external_api_read_write_organ_v1 import (
        ExternalAPIContract,
        ExternalAPITransportResponse,
        build_external_api_power_executor,
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

    executor = build_external_api_power_executor(
        contract=ExternalAPIContract(allowed_domains=["api.example.com"], allowed_methods=["GET"]),
        transport=lambda _request: ExternalAPITransportResponse(status_code=200, body=b"{}"),
    )
    plan = PowerMissionPlan(
        mission_id="mission_api_power",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="api_read",
                    actuator_family=PowerActuatorFamily.EXTERNAL_API,
                    capability_level=PowerActuatorCapabilityLevel.L5,
                    organ_kind="external_api",
                    action_kind="request",
                    request={"method": "GET", "url": "https://api.example.com/items"},
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
