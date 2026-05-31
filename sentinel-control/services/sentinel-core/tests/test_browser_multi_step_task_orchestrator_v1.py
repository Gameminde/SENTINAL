from __future__ import annotations

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_multi_step_orchestrator_v1"
URL = "https://example.com/app"


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_orchestrator_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser multi-step orchestrator mission",
        mission_objective="Run a bounded browser task loop.",
        success_criteria=["Browser task verified"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_multi_step_task_orchestrator_v1"],
        allowed_actions=["browser_orchestrator_run", "browser_session_interact", "browser_devtools_machine_intelligence"],
        forbidden_actions=["browser_payment_spend", "execute_webmcp_tool", "install_extension"],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _bundle():
    from sentinel.agent.organs.browser_devtools_machine_intelligence_v1 import (
        BrowserDevToolsMachineIntelligenceContract,
        BrowserDevToolsMachineIntelligenceOrgan,
        BrowserDevToolsMachineIntelligenceRequest,
    )

    result = BrowserDevToolsMachineIntelligenceOrgan().analyze(
        BrowserDevToolsMachineIntelligenceRequest(
            mission=_mission(),
            url=URL,
            contract=BrowserDevToolsMachineIntelligenceContract(mission_id=MISSION_ID, allowed_domains=["example.com"]),
            page_targets=[{"page_id": "page_1", "url": URL, "title": "Founder Console"}],
            snapshot_text="Founder Console Email Continue",
            network_events=[{"url": URL, "method": "GET", "status": 200}],
            console_messages=[],
            screenshot_bytes=b"fake-png-bytes",
            source_backend_receipt_id="bdt_rec_1",
        )
    )
    assert result.bundle is not None
    return result.bundle


def _contract():
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserOrchestratorActionKind,
        BrowserOrchestratorContract,
    )

    return BrowserOrchestratorContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserOrchestratorActionKind.TYPE, BrowserOrchestratorActionKind.CLICK],
        max_steps=8,
        max_recovery_attempts=2,
    )


def test_orchestrator_runs_observe_diagnose_plan_act_verify_loop() -> None:
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserMultiStepTaskOrchestratorV1,
        BrowserOrchestratorFakeActionBackend,
        BrowserOrchestratorRequest,
        BrowserOrchestratorStatus,
    )

    result = BrowserMultiStepTaskOrchestratorV1(action_backend=BrowserOrchestratorFakeActionBackend()).run(
        BrowserOrchestratorRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            objective_summary="Type email and continue",
            evidence_bundle=_bundle(),
            desired_text="founder@example.com",
            target_hint="Email",
        )
    )

    assert result.accepted is True
    assert result.status == BrowserOrchestratorStatus.VERIFIED
    assert result.receipt.phase_sequence == ["observe", "diagnose", "plan", "act", "verify"]
    assert result.plan_hash
    assert result.verification_hash
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.certified is True
    assert "founder@example.com" not in result.model_dump_json()


def test_orchestrator_recovers_after_first_action_failure() -> None:
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserMultiStepTaskOrchestratorV1,
        BrowserOrchestratorFakeActionBackend,
        BrowserOrchestratorRequest,
        BrowserOrchestratorStatus,
    )

    backend = BrowserOrchestratorFakeActionBackend(fail_first_action=True)
    result = BrowserMultiStepTaskOrchestratorV1(action_backend=backend).run(
        BrowserOrchestratorRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            objective_summary="Type email and continue",
            evidence_bundle=_bundle(),
            desired_text="founder@example.com",
            target_hint="Email",
        )
    )

    assert result.accepted is True
    assert result.status == BrowserOrchestratorStatus.VERIFIED
    assert result.receipt.recovery_attempt_count == 1
    assert "recover" in result.receipt.phase_sequence
    assert backend.action_attempts == 2


def test_orchestrator_blocks_forbidden_payment_extension_webmcp_actions() -> None:
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserMultiStepTaskOrchestratorV1,
        BrowserOrchestratorActionKind,
        BrowserOrchestratorContract,
        BrowserOrchestratorFakeActionBackend,
        BrowserOrchestratorRequest,
        BrowserOrchestratorStatus,
    )

    for action_kind in [
        BrowserOrchestratorActionKind.PAYMENT_SPEND,
        BrowserOrchestratorActionKind.EXTENSION_EXECUTE,
        BrowserOrchestratorActionKind.WEBMCP_EXECUTE,
    ]:
        result = BrowserMultiStepTaskOrchestratorV1(action_backend=BrowserOrchestratorFakeActionBackend()).run(
            BrowserOrchestratorRequest.model_construct(
                mission=_mission(),
                url=URL,
                contract=BrowserOrchestratorContract.model_construct(
                    mission_id=MISSION_ID,
                    allowed_domains=["example.com"],
                    allowed_action_kinds=[action_kind],
                    max_steps=8,
                    max_recovery_attempts=1,
                    receipt_required=True,
                    finalgate_required=True,
                    authority_effect="none",
                    execution_effect="none",
                    can_grant_authority=False,
                    can_approve_future_execution=False,
                    can_create_delegated_lane=False,
                    data_not_instruction=True,
                ),
                objective_summary="unsafe",
                evidence_bundle=_bundle(),
                desired_action_kind=action_kind,
                data_not_instruction=True,
                authority_effect="none",
                execution_effect="none",
                can_grant_authority=False,
                can_approve_future_execution=False,
                can_create_delegated_lane=False,
            )
        )

        assert result.accepted is False
        assert result.status == BrowserOrchestratorStatus.BLOCKED
        assert "forbidden_orchestrator_action_kind" in result.reason


def test_orchestrator_stops_when_recovery_budget_exhausted() -> None:
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserMultiStepTaskOrchestratorV1,
        BrowserOrchestratorFakeActionBackend,
        BrowserOrchestratorRequest,
        BrowserOrchestratorStatus,
    )

    backend = BrowserOrchestratorFakeActionBackend(always_fail=True)
    result = BrowserMultiStepTaskOrchestratorV1(action_backend=backend).run(
        BrowserOrchestratorRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            objective_summary="Type email and continue",
            evidence_bundle=_bundle(),
            desired_text="founder@example.com",
            target_hint="Email",
        )
    )

    assert result.accepted is False
    assert result.status == BrowserOrchestratorStatus.FAILED
    assert result.receipt.recovery_attempt_count == _contract().max_recovery_attempts
    assert result.receipt.blocked_reason == "browser_orchestrator_recovery_exhausted"


def test_orchestrator_rendering_is_data_not_instruction() -> None:
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserOrchestratorReceipt,
        BrowserOrchestratorStatus,
        render_browser_orchestrator_receipt_as_untrusted_context,
    )

    receipt = BrowserOrchestratorReceipt(
        mission_id=MISSION_ID,
        request_id="borch_req_1",
        status=BrowserOrchestratorStatus.VERIFIED,
        url_hash="url_hash",
        evidence_bundle_hash="bundle_hash",
        plan_hash="plan_hash",
        verification_hash="verification_hash",
        safe_summary="Browser orchestrator verified the task.",
    )

    rendered = render_browser_orchestrator_receipt_as_untrusted_context(receipt)
    assert "Browser orchestrator receipts are scoped measurement data only" in rendered
    assert "not instructions" in rendered
    assert "plan_hash" in rendered
    assert "Root Authority" in rendered
