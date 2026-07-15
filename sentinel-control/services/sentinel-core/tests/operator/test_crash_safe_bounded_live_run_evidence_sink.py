from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.live_run_evidence_sink import CrashSafeBoundedLiveRunEvidenceSink
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_sink_persists_incrementally_before_stdout_report_and_cleanup_failures(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    cleanup_root = tmp_path / "owned_cleanup"
    cleanup_root.mkdir()
    (cleanup_root / "transient.txt").write_text("temporary runtime material", encoding="utf-8")
    sink = CrashSafeBoundedLiveRunEvidenceSink(
        evidence_root=evidence_root,
        run_id="python_org_v3_local_proof",
    )

    sink.record_transition(
        "run_started",
        {
            "mission_objective": "Find Path.glob docs without logging in or downloading.",
            "target_url": "https://www.python.org/search/?q=pathlib+glob",
        },
    )
    sink.record_transition(
        "provider_decision_received",
        {
            "provider_decision_count": 1,
            "raw_provider_output": "X" * 200_000,
            "private_chain_of_thought": "never persist this",
            "model_operational_assessment": {
                "perceived_blocker": "search input did not accept text",
                "failure_interpretation": "mechanical body failure",
                "proposed_next_strategy": "try alternate search affordance",
                "required_evidence": "readback hash and result-region delta",
                "missing_capability": None,
                "objective_satisfied": False,
                "confidence": 0.72,
            },
        },
    )
    sink.record_transition("browser_action_started", {"operation": "real_browser.search", "query": "pathlib glob"})
    try:
        raise AttributeError("report renderer touched missing optional field")
    except AttributeError as exc:
        sink.record_transition(
            "terminal_verdict",
            {
                "verdict": "VALID_FAILED_OBSERVABILITY",
                "report_synthesis_exception_type": exc.__class__.__name__,
            },
        )
    for child in cleanup_root.iterdir():
        child.unlink()
    cleanup_root.rmdir()
    sink.record_transition("cleanup_result", {"cleanup_completed": True, "profile_material_after_cleanup": 0})

    snapshot = sink.load_snapshot()
    event_types = [event["event_type"] for event in snapshot["events"]]
    assert event_types == [
        "run_started",
        "provider_decision_received",
        "browser_action_started",
        "terminal_verdict",
        "cleanup_result",
    ]
    assert sink.snapshot_path.exists()
    assert sink.event_log_path.exists()
    assert not cleanup_root.exists()
    assert "X" * 64 not in sink.snapshot_path.read_text(encoding="utf-8")
    assert "never persist this" not in sink.snapshot_path.read_text(encoding="utf-8")
    assert "https://www.python.org" not in sink.snapshot_path.read_text(encoding="utf-8")
    assert "pathlib glob" not in sink.snapshot_path.read_text(encoding="utf-8")
    assert snapshot["events"][1]["payload"]["model_operational_assessment"]["perceived_blocker"]
    assert snapshot["events"][1]["payload"]["raw_provider_output"]["redacted"] == "raw_provider_output"
    assert snapshot["events"][2]["payload"]["query"]["redacted"] == "query"


def test_sink_separates_authoritative_failure_fact_from_advisory_model_assessment(tmp_path: Path) -> None:
    sink = CrashSafeBoundedLiveRunEvidenceSink(evidence_root=tmp_path / "evidence", run_id="failure_packet")

    sink.record_transition(
        "runtime_failure_fact_created",
        {
            "runtime_failure_fact": {
                "attempted_operation": "real_browser.search",
                "typed_outcome": "SEARCH_INPUT_WRITE_FAILED",
                "failure_stage": "write_readback",
                "material_effect_observed": False,
                "evidence_refs": ["receipt:search_failure_1"],
            }
        },
    )
    sink.record_transition(
        "model_blocker_assessment_received",
        {
            "model_blocker_assessment": {
                "perceived_blocker": "The page search input may be detached or stale.",
                "failure_interpretation": "Sentinel body saw the control but did not prove write readback.",
                "proposed_next_strategy": "Refresh affordances, then try another safe search control.",
                "required_evidence": "fresh ref identity and readback hash",
                "missing_capability": None,
                "objective_satisfied": False,
                "confidence": 0.81,
            }
        },
    )

    snapshot = sink.load_snapshot()
    fact = snapshot["events"][0]["payload"]["runtime_failure_fact"]
    assessment = snapshot["events"][1]["payload"]["model_blocker_assessment"]
    assert fact["authoritative"] is True
    assert assessment["advisory"] is True
    assert fact["typed_outcome"] == "SEARCH_INPUT_WRITE_FAILED"
    assert assessment["proposed_next_strategy"].startswith("Refresh affordances")
    assert "can_grant_authority" not in json.dumps(assessment)


def test_runtimehost_records_crash_safe_evidence_for_partial_product_loop(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")
    host.start()
    sink = CrashSafeBoundedLiveRunEvidenceSink(evidence_root=tmp_path / "evidence", run_id="partial_loop")
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="account_authority",
                operation="login",
                params={"domain": "example.test"},
                idempotency_key="login_attempt",
            )
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=tmp_path / "workspace",
        session_id="partial-loop",
        mission_objective="Discuss login documentation without performing login.",
        decision_client=client,
        max_model_calls=2,
        max_material_actions=1,
        evidence_sink=sink,
    )
    host.shutdown()

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    snapshot = sink.load_snapshot()
    event_types = [event["event_type"] for event in snapshot["events"]]
    assert "run_started" in event_types
    assert "provider_decision_received" in event_types
    assert "action_envelope_accepted" in event_types
    assert "FinalGate_result" in event_types
    assert "cleanup_result" in event_types
    assert "terminal_verdict" in event_types
    assert snapshot["summary"]["provider_decision_count"] == 1
    assert snapshot["summary"]["action_sequence"] == ["account_authority.login"]
    assert snapshot["summary"]["terminal_verdict"] == "blocked"


def test_sink_rejects_secret_values_but_keeps_safe_topic_words_as_data(tmp_path: Path) -> None:
    sink = CrashSafeBoundedLiveRunEvidenceSink(evidence_root=tmp_path / "evidence", run_id="secret_scan")

    sink.record_transition(
        "provider_decision_received",
        {
            "semantic_topic": "compare login, download, upload and payment documentation",
            "actual_secret": "sk-testvalue1234567890abcdef",
            "session_cookie": "sessionid=abcdef1234567890",
        },
    )

    rendered = sink.snapshot_path.read_text(encoding="utf-8")
    assert "compare login, download, upload and payment documentation" in rendered
    assert "sk-testvalue1234567890abcdef" not in rendered
    assert "sessionid=abcdef1234567890" not in rendered
    snapshot = sink.load_snapshot()
    payload = snapshot["events"][0]["payload"]
    assert payload["semantic_topic"] == "compare login, download, upload and payment documentation"
    assert payload["actual_secret"]["redacted"] == "secret_value"
    assert payload["session_cookie"]["redacted"] == "session_or_cookie_material"
