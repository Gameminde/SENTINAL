from __future__ import annotations

from pathlib import Path

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_operating_subsystem_live_backend"
URL = "https://example.com/live-backend"
HTML = """
<html>
  <head><title>Live Backend Console</title></head>
  <body>
    <main>
      <h1>Operator Console</h1>
      <input type="text" placeholder="Email" value="founder@example.com" />
      <button>Continue</button>
    </main>
    <script>console.warn("live-console-marker")</script>
  </body>
</html>
"""


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_operating_subsystem_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser operating subsystem live backend mission",
        mission_objective="Bind DevTools metadata to a governed live browser session.",
        success_criteria=["Live DevTools receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live", "browser_devtools_backend_adapter_v1"],
        allowed_actions=[
            "browser_session_open",
            "browser_session_observe",
            "browser_session_interact",
            "browser_session_close",
            "browser_devtools_snapshot",
        ],
        forbidden_actions=[
            "execute_webmcp_tool",
            "browser_payment_spend",
            "generic_browser_login",
            "credential_access",
            "api_mutation",
            "shell",
        ],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def test_devtools_backend_collects_hash_only_metadata_from_live_l5_session(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_devtools_backend_adapter_v1 import (
        BrowserDevToolsAdapter,
        BrowserDevToolsCapability,
        BrowserDevToolsContract,
        BrowserDevToolsRequest,
        BrowserDevToolsStatus,
        BrowserSessionDevToolsBackend,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    mission = _mission()
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    session_contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
    )

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=mission, url=URL, contract=session_contract))
        assert opened.accepted is True

        adapter = BrowserDevToolsAdapter(
            backend=BrowserSessionDevToolsBackend(session_manager=manager, session_id=opened.session_id)
        )
        result = adapter.execute(
            BrowserDevToolsRequest(
                mission=mission,
                url=URL,
                capability=BrowserDevToolsCapability.TAKE_SNAPSHOT,
                contract=BrowserDevToolsContract(
                    mission_id=MISSION_ID,
                    allowed_domains=["example.com"],
                    allowed_capabilities=[BrowserDevToolsCapability.TAKE_SNAPSHOT],
                    allowed_backend_kinds=["browser_session_live"],
                ),
            )
        )

        dumped = result.model_dump_json()
        assert result.accepted is True
        assert result.status is BrowserDevToolsStatus.SUCCEEDED
        assert result.receipt.backend_kind == "browser_session_live"
        assert result.receipt.snapshot_hash
        assert result.receipt.output_hash
        assert result.receipt.page_target_count == 1
        assert result.backend_payload is not None
        assert result.backend_payload.output_hash == result.receipt.output_hash
        assert result.backend_payload.safe_metadata["session_ref"]
        assert result.finalgate_certificate is not None
        assert result.finalgate_certificate.certified is True
        assert "Operator Console" not in dumped
        assert "founder@example.com" not in dumped
        assert "cookie" not in dumped.lower()
        assert "credential" not in dumped.lower()
    finally:
        manager.close_all()


def test_orchestrator_action_backend_executes_governed_l5_session_step(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_devtools_machine_intelligence_v1 import (
        BrowserDevToolsMachineIntelligenceContract,
        BrowserDevToolsMachineIntelligenceOrgan,
        BrowserDevToolsMachineIntelligenceRequest,
    )
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserMultiStepTaskOrchestratorV1,
        BrowserOrchestratorActionKind,
        BrowserOrchestratorContract,
        BrowserOrchestratorRequest,
        BrowserOrchestratorStatus,
        BrowserSessionOrchestratorActionBackend,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    mission = _mission()
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    session_contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
    )
    machine_result = BrowserDevToolsMachineIntelligenceOrgan().analyze(
        BrowserDevToolsMachineIntelligenceRequest(
            mission=mission,
            url=URL,
            contract=BrowserDevToolsMachineIntelligenceContract(mission_id=MISSION_ID, allowed_domains=["example.com"]),
            page_targets=[{"page_id": "page_1", "url": URL, "title": "Live Backend Console"}],
            snapshot_text="Operator Console Email Continue",
            network_events=[],
            console_messages=[],
            screenshot_bytes=b"fixture-png",
            source_backend_receipt_id="live_bdt_rec_1",
        )
    )
    assert machine_result.bundle is not None

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=mission, url=URL, contract=session_contract))
        assert opened.accepted is True
        backend = BrowserSessionOrchestratorActionBackend(
            session_manager=manager,
            mission=mission,
            url=URL,
            session_id=opened.session_id,
            session_contract=session_contract,
            text_by_hash={stable_hash("founder@example.com"): "founder@example.com"},
        )

        result = BrowserMultiStepTaskOrchestratorV1(action_backend=backend).run(
            BrowserOrchestratorRequest(
                mission=mission,
                url=URL,
                contract=BrowserOrchestratorContract(
                    mission_id=MISSION_ID,
                    allowed_domains=["example.com"],
                    allowed_action_kinds=[BrowserOrchestratorActionKind.TYPE],
                ),
                objective_summary="Type email into the live browser session",
                evidence_bundle=machine_result.bundle,
                desired_action_kind=BrowserOrchestratorActionKind.TYPE,
                desired_text="founder@example.com",
                target_hint="Email",
            )
        )

        assert result.accepted is True
        assert result.status is BrowserOrchestratorStatus.VERIFIED
        assert backend.action_attempts == 1
        assert backend.last_session_result is not None
        assert backend.last_session_result.accepted is True
        assert backend.last_session_result.receipt.after_snapshot_hash
        assert result.receipt.action_attempt_count == 1
        assert result.receipt.recovery_attempt_count == 0
        dumped = result.model_dump_json() + backend.last_session_result.model_dump_json()
        assert "founder@example.com" not in dumped
        assert "simulated_browser_action_succeeded" not in dumped
    finally:
        manager.close_all()


def test_live_session_and_orchestrator_results_feed_replay_timeline_without_raw_payload(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_devtools_machine_intelligence_v1 import (
        BrowserDevToolsMachineIntelligenceContract,
        BrowserDevToolsMachineIntelligenceOrgan,
        BrowserDevToolsMachineIntelligenceRequest,
    )
    from sentinel.agent.organs.browser_multi_step_task_orchestrator_v1 import (
        BrowserMultiStepTaskOrchestratorV1,
        BrowserOrchestratorActionKind,
        BrowserOrchestratorContract,
        BrowserOrchestratorRequest,
        BrowserSessionOrchestratorActionBackend,
    )
    from sentinel.agent.organs.browser_observability_replay_studio_v1 import (
        BrowserReplayStudioContract,
        BrowserReplayStudioOrganV1,
        BrowserReplayStudioRequest,
        browser_live_results_to_replay_events,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    mission = _mission()
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    session_contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
    )
    machine_result = BrowserDevToolsMachineIntelligenceOrgan().analyze(
        BrowserDevToolsMachineIntelligenceRequest(
            mission=mission,
            url=URL,
            contract=BrowserDevToolsMachineIntelligenceContract(mission_id=MISSION_ID, allowed_domains=["example.com"]),
            page_targets=[{"page_id": "page_1", "url": URL, "title": "Live Backend Console"}],
            snapshot_text="Operator Console Email Continue",
            source_backend_receipt_id="live_bdt_rec_2",
        )
    )
    assert machine_result.bundle is not None

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=mission, url=URL, contract=session_contract))
        backend = BrowserSessionOrchestratorActionBackend(
            session_manager=manager,
            mission=mission,
            url=URL,
            session_id=opened.session_id,
            session_contract=session_contract,
            text_by_hash={stable_hash("founder@example.com"): "founder@example.com"},
        )
        orchestrator_result = BrowserMultiStepTaskOrchestratorV1(action_backend=backend).run(
            BrowserOrchestratorRequest(
                mission=mission,
                url=URL,
                contract=BrowserOrchestratorContract(
                    mission_id=MISSION_ID,
                    allowed_domains=["example.com"],
                    allowed_action_kinds=[BrowserOrchestratorActionKind.TYPE],
                ),
                objective_summary="Type email into the live browser session",
                evidence_bundle=machine_result.bundle,
                desired_action_kind=BrowserOrchestratorActionKind.TYPE,
                desired_text="founder@example.com",
                target_hint="Email",
            )
        )
        assert backend.last_session_result is not None
        events = browser_live_results_to_replay_events(
            url=URL,
            session_result=backend.last_session_result,
            orchestrator_result=orchestrator_result,
        )
        replay = BrowserReplayStudioOrganV1().build(
            BrowserReplayStudioRequest(
                mission=mission,
                url=URL,
                contract=BrowserReplayStudioContract(mission_id=MISSION_ID, allowed_domains=["example.com"]),
                replay_events=events,
            )
        )

        dumped = replay.model_dump_json()
        assert replay.accepted is True
        assert replay.timeline is not None
        assert replay.timeline.action_count >= 1
        assert replay.timeline.receipt_count >= 2
        assert replay.timeline.finalgate_count >= 2
        assert replay.receipt.redacted_payload_count == 0
        assert backend.last_session_result.receipt.receipt_id in replay.timeline.receipt_refs
        assert orchestrator_result.receipt.receipt_id in replay.timeline.receipt_refs
        assert "founder@example.com" not in dumped
        assert "Operator Console" not in dumped
    finally:
        manager.close_all()


def test_live_devtools_backend_exposes_network_console_and_performance_hashes(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_devtools_backend_adapter_v1 import (
        BrowserDevToolsAdapter,
        BrowserDevToolsCapability,
        BrowserDevToolsContract,
        BrowserDevToolsRequest,
        BrowserSessionDevToolsBackend,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    mission = _mission()
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    session_contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=mission, url=URL, contract=session_contract))
        adapter = BrowserDevToolsAdapter(
            backend=BrowserSessionDevToolsBackend(session_manager=manager, session_id=opened.session_id)
        )
        for capability, attr in [
            (BrowserDevToolsCapability.NETWORK_LEDGER, "network_ledger_hash"),
            (BrowserDevToolsCapability.CONSOLE_LEDGER, "console_ledger_hash"),
            (BrowserDevToolsCapability.PERFORMANCE_TRACE, "performance_trace_hash"),
        ]:
            result = adapter.execute(
                BrowserDevToolsRequest(
                    mission=mission,
                    url=URL,
                    capability=capability,
                    contract=BrowserDevToolsContract(
                        mission_id=MISSION_ID,
                        allowed_domains=["example.com"],
                        allowed_capabilities=[capability],
                        allowed_backend_kinds=["browser_session_live"],
                    ),
                )
            )

            assert result.accepted is True
            assert getattr(result.receipt, attr)
            assert result.backend_payload is not None
            assert getattr(result.backend_payload, attr) == getattr(result.receipt, attr)
            if capability is BrowserDevToolsCapability.NETWORK_LEDGER:
                assert int(result.backend_payload.safe_metadata["network_event_count"]) >= 1
            if capability is BrowserDevToolsCapability.CONSOLE_LEDGER:
                assert int(result.backend_payload.safe_metadata["console_message_count"]) >= 1
            dumped = result.model_dump_json()
            assert "Operator Console" not in dumped
            assert "founder@example.com" not in dumped
            assert "live-console-marker" not in dumped
    finally:
        manager.close_all()


def test_native_cdp_backend_is_hash_only_and_fails_closed_without_transport() -> None:
    from sentinel.agent.organs.browser_devtools_backend_adapter_v1 import (
        BrowserDevToolsAdapter,
        BrowserDevToolsCapability,
        BrowserDevToolsContract,
        BrowserDevToolsRequest,
        BrowserDevToolsStatus,
        BrowserNativeCdpBackend,
    )

    class FakeCdpSession:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def send(self, command: str, params: dict[str, object] | None = None) -> dict[str, object]:
            self.commands.append(command)
            if command == "Performance.getMetrics":
                return {
                    "metrics": [
                        {"name": "TaskDuration", "value": 12.5},
                        {"name": "SensitiveShouldHashOnly", "value": "sensitive-value-should-not-leak"},
                    ]
                }
            return {"ok": True, "sensitive_field": "sensitive-value-should-not-leak"}

    mission = _mission()
    fake_cdp = FakeCdpSession()
    adapter = BrowserDevToolsAdapter(backend=BrowserNativeCdpBackend(cdp_session=fake_cdp, target_ref="target-1"))
    result = adapter.execute(
        BrowserDevToolsRequest(
            mission=mission,
            url=URL,
            capability=BrowserDevToolsCapability.PERFORMANCE_TRACE,
            contract=BrowserDevToolsContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                allowed_capabilities=[BrowserDevToolsCapability.PERFORMANCE_TRACE],
                allowed_backend_kinds=["native_cdp"],
            ),
        )
    )

    dumped = result.model_dump_json()
    assert result.accepted is True
    assert result.status is BrowserDevToolsStatus.SUCCEEDED
    assert result.receipt.backend_kind == "native_cdp"
    assert result.receipt.performance_trace_hash
    assert result.backend_payload is not None
    assert result.backend_payload.safe_metadata["command_count"] >= 2
    assert "Performance.enable" in fake_cdp.commands
    assert "Performance.getMetrics" in fake_cdp.commands
    assert "sensitive-value-should-not-leak" not in dumped
    assert "sensitive_field" not in dumped

    blocked = BrowserDevToolsAdapter(backend=BrowserNativeCdpBackend(cdp_session=None)).execute(
        BrowserDevToolsRequest(
            mission=mission,
            url=URL,
            capability=BrowserDevToolsCapability.NETWORK_LEDGER,
            contract=BrowserDevToolsContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                allowed_capabilities=[BrowserDevToolsCapability.NETWORK_LEDGER],
                allowed_backend_kinds=["native_cdp"],
            ),
        )
    )
    assert blocked.accepted is False
    assert blocked.status is BrowserDevToolsStatus.BLOCKED
    assert blocked.finalgate_certificate is not None
    assert blocked.finalgate_certificate.certified is True


def test_visual_grounding_builds_from_live_session_screenshot_without_persisting_raw_bytes(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )
    from sentinel.agent.organs.browser_visual_grounding_ocr_v1 import (
        BrowserVisualGroundingContract,
        BrowserVisualGroundingOrganV1,
        browser_visual_grounding_request_from_live_session,
    )

    mission = _mission()
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    session_contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])
    visual_contract = BrowserVisualGroundingContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=mission, url=URL, contract=session_contract))
        request = browser_visual_grounding_request_from_live_session(
            session_manager=manager,
            mission=mission,
            url=URL,
            session_id=opened.session_id,
            contract=visual_contract,
            ocr_detections=[
                {
                    "text": "Continue",
                    "bbox": {"x": 25, "y": 30, "width": 100, "height": 40},
                    "confidence": 0.93,
                    "role_hint": "button",
                }
            ],
        )
        result = BrowserVisualGroundingOrganV1().ground(request)

        dumped = result.model_dump_json()
        assert result.accepted is True
        assert result.receipt.screenshot_hash
        assert result.receipt.screenshot_byte_count > 0
        assert result.receipt.target_count == 1
        assert result.finalgate_certificate is not None
        assert result.finalgate_certificate.certified is True
        assert "Continue" not in dumped
        assert "screenshot_bytes" not in dumped
        assert "Operator Console" not in dumped
    finally:
        manager.close_all()


def test_live_devtools_metadata_feeds_failure_recovery_plan_without_raw_console(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_failure_recovery_engine_v1 import (
        BrowserFailureRecoveryActionKind,
        BrowserFailureRecoveryContract,
        BrowserFailureRecoveryEngineV1,
        BrowserFailureRecoveryKind,
        browser_failure_recovery_request_from_live_devtools_metadata,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    mission = _mission()
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    session_contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])
    recovery_contract = BrowserFailureRecoveryContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=mission, url=URL, contract=session_contract))
        metadata = manager.devtools_metadata_for_session(
            mission_id=MISSION_ID,
            session_id=str(opened.session_id),
            capability="console_ledger",
        )
        assert metadata is not None
        request = browser_failure_recovery_request_from_live_devtools_metadata(
            mission=mission,
            url=URL,
            contract=recovery_contract,
            evidence_bundle_hash=stable_hash({"source": "live-devtools", "session": opened.session_id}),
            devtools_metadata=metadata,
        )
        result = BrowserFailureRecoveryEngineV1().plan(request)

        dumped = result.model_dump_json()
        assert result.accepted is True
        assert result.finalgate_certificate is not None
        assert result.finalgate_certificate.certified is True
        assert BrowserFailureRecoveryKind.SPA_OR_CONSOLE_ERROR in {failure.kind for failure in result.plan.failures}
        assert BrowserFailureRecoveryActionKind.CHECK_NETWORK_CONSOLE in {step.action_kind for step in result.plan.steps}
        assert "live-console-marker" not in dumped
        assert "Operator Console" not in dumped
    finally:
        manager.close_all()
