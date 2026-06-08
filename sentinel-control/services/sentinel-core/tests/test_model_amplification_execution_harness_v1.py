from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.harness_models import (
    AnalysisKernelConfig,
    ContentAddressedArtifact,
    HarnessCompressionPolicy,
    HarnessWorkerRequest,
    HashAnchoredPatch,
    ToolOutputEnvelope,
)
from sentinel.operator.harness_replay import HarnessReplayBuilder
from sentinel.operator.harness_runtime import AmplificationHarnessRuntime, HarnessRuntimeError
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.telemetry import TelemetryEventKind, TelemetryMetricKind


def test_harness_models_are_data_not_authority_and_reject_control_fields(tmp_path: Path) -> None:
    artifact = ContentAddressedArtifact.from_bytes(
        mission_id="mission_harness",
        logical_path="analysis/market.txt",
        content=b"market notes",
        media_type="text/plain",
    )

    assert artifact.sha256 == stable_hash("market notes")
    assert artifact.authority_effect == "none"
    assert artifact.can_execute is False
    assert artifact.can_grant_authority is False

    with pytest.raises(ValueError, match="harness output cannot request authority"):
        ToolOutputEnvelope(
            mission_id="mission_harness",
            tool_name="debugger",
            safe_summary="needs root",
            raw_output_bytes=100,
            minimized_output={"authority_grant": "root"},
            evidence_refs=["evidence_1"],
        )

    with pytest.raises(ValueError, match="provider/backend/model override"):
        HarnessWorkerRequest(
            mission_id="mission_harness",
            objective="analyze result",
            result_contract={"required_evidence_refs": 1},
            metadata={"provider_id": "other-provider"},
        )


def test_content_addressed_artifacts_and_hash_anchored_edits_detect_drift(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AmplificationHarnessRuntime(kernel)
    session = runtime.start_session(mission_id=mission_id, envelope=_envelope(mission_id))
    artifact = runtime.record_artifact(
        mission_id=mission_id,
        session_id=session.session_id,
        logical_path="analysis/business.txt",
        content="old market analysis",
        media_type="text/plain",
    )
    patch = HashAnchoredPatch(
        mission_id=mission_id,
        artifact_ref=artifact.artifact_ref,
        base_sha256=artifact.sha256,
        expected_sha256=stable_hash("new market analysis"),
        replacement_text="new market analysis",
        safe_summary="Update analysis with new evidence.",
        evidence_refs=["evidence_patch"],
    )

    verified = runtime.verify_edit(mission_id=mission_id, session_id=session.session_id, patch=patch)

    assert verified.status == "verified"
    assert verified.after_sha256 == stable_hash("new market analysis")
    assert verified.authority_effect == "none"

    drifted = patch.model_copy(update={"base_sha256": "0" * 64})
    rejected = runtime.verify_edit(mission_id=mission_id, session_id=session.session_id, patch=drifted)

    assert rejected.status == "rejected"
    assert rejected.reject_reason == "base_hash_mismatch"
    assert kernel.store.verify_timeline(mission_id) is True


def test_analysis_kernel_blocks_ambient_execution_and_raw_persistence(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AmplificationHarnessRuntime(kernel)
    session = runtime.start_session(mission_id=mission_id, envelope=_envelope(mission_id))

    with pytest.raises(ValueError, match="analysis kernel cannot access ambient execution"):
        runtime.start_analysis_kernel(
            mission_id=mission_id,
            session_id=session.session_id,
            config=AnalysisKernelConfig(
                kernel_name="unsafe",
                input_refs=["artifact_1"],
                allow_network=True,
            ),
        )

    result = runtime.run_analysis_kernel(
        mission_id=mission_id,
        session_id=session.session_id,
        config=AnalysisKernelConfig(kernel_name="safe", input_refs=["artifact_1"]),
        safe_summary="OPENAI_API_KEY=sk-test-1234567890",
        output={"finding": "Bearer raw-kernel-token", "evidence_refs": ["evidence_kernel"]},
    )

    payload = _harness_payload(kernel, mission_id)
    assert result.status == "completed"
    assert "sk-test-1234567890" not in payload
    assert "raw-kernel-token" not in payload
    assert "[REDACTED_SECRET]" in payload


def test_tool_output_minimization_and_context_compression_preserve_required_refs(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AmplificationHarnessRuntime(kernel)
    session = runtime.start_session(mission_id=mission_id, envelope=_envelope(mission_id))
    output = runtime.minimize_tool_output(
        mission_id=mission_id,
        session_id=session.session_id,
        envelope=ToolOutputEnvelope(
            mission_id=mission_id,
            tool_name="pytest",
            safe_summary="A long diagnostic output was minimized.",
            raw_output_bytes=10_000,
            minimized_output={"summary": "tests failed", "excerpt": "failure in unit test"},
            evidence_refs=["evidence_tool"],
            receipt_refs=["receipt_tool"],
            finalgate_certificate_refs=["finalgate_tool"],
            memory_feedback_refs=["memory_tool"],
        ),
    )

    context_pack = runtime.build_context_pack(
        mission_id=mission_id,
        session_id=session.session_id,
        safe_goal="Summarize diagnostics.",
        tool_results=[output],
        required_refs=["evidence_tool", "receipt_tool", "finalgate_tool", "memory_tool"],
        compression_policy=HarnessCompressionPolicy(max_items=1, max_summary_chars=24),
    )

    assert output.raw_output_persisted is False
    assert output.output_hash
    assert context_pack.compressed is True
    assert set(context_pack.required_refs_preserved) == {"evidence_tool", "receipt_tool", "finalgate_tool", "memory_tool"}
    assert "evidence_tool" in context_pack.evidence_refs
    assert len(context_pack.safe_context_items[0]) <= 24


def test_worker_safe_amplification_detects_conflicts_and_keeps_child_authority(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AmplificationHarnessRuntime(kernel)
    session = runtime.start_session(mission_id=mission_id, envelope=_envelope(mission_id))
    request_a = HarnessWorkerRequest(
        mission_id=mission_id,
        objective="Estimate market size.",
        result_contract={"required_evidence_refs": 1, "conflict_key": "market_size"},
        evidence_refs=["evidence_a"],
    )
    request_b = HarnessWorkerRequest(
        mission_id=mission_id,
        objective="Verify market size.",
        result_contract={"required_evidence_refs": 1, "conflict_key": "market_size"},
        evidence_refs=["evidence_b"],
    )

    result_a = runtime.submit_worker_result(
        mission_id=mission_id,
        session_id=session.session_id,
        request=request_a,
        safe_summary="Market is small.",
        output={"answer": "small"},
        evidence_refs=["evidence_a"],
    )
    result_b = runtime.submit_worker_result(
        mission_id=mission_id,
        session_id=session.session_id,
        request=request_b,
        safe_summary="Market is large.",
        output={"answer": "large"},
        evidence_refs=["evidence_b"],
    )
    merge = runtime.merge_worker_results(mission_id=mission_id, session_id=session.session_id, results=[result_a, result_b])

    assert result_a.minimized is True
    assert result_a.child_authority_subset is True
    assert merge.outcome == "conflict"
    assert merge.conflict_records
    assert merge.conflict_records[0].conflict_key == "market_size"


def test_harness_blocks_model_contract_override_and_uses_memory_as_context_only(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AmplificationHarnessRuntime(kernel)
    with pytest.raises(HarnessRuntimeError, match="provider_backend_model_override_rejected"):
        runtime.start_session(
            mission_id=mission_id,
            envelope=_envelope(mission_id),
            provider_id="selected-provider",
            backend_id="selected-backend",
            model_id="selected-model",
            requested_provider_id="other-provider",
        )

    session = runtime.start_session(
        mission_id=mission_id,
        envelope=_envelope(mission_id),
        memory_context_refs=["memory_context_1"],
    )

    assert session.memory_context_refs == ["memory_context_1"]
    assert session.memory_is_authority is False
    assert session.can_grant_authority is False


def test_harness_replay_and_telemetry_reconstruct_without_reexecution(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AmplificationHarnessRuntime(kernel)
    session = runtime.start_session(mission_id=mission_id, envelope=_envelope(mission_id))
    artifact = runtime.record_artifact(
        mission_id=mission_id,
        session_id=session.session_id,
        logical_path="analysis/replay.txt",
        content="replay evidence",
    )
    output = runtime.minimize_tool_output(
        mission_id=mission_id,
        session_id=session.session_id,
        envelope=ToolOutputEnvelope(
            mission_id=mission_id,
            tool_name="diagnostic",
            safe_summary="Diagnostic summarized.",
            raw_output_bytes=500,
            minimized_output={"summary": "ok"},
            evidence_refs=["evidence_replay"],
        ),
    )
    runtime.complete_session(mission_id=mission_id, session_id=session.session_id, safe_summary="Harness completed.")

    replay = HarnessReplayBuilder(kernel.store).build(mission_id, session.session_id)
    event_kinds = [event.event_kind for event in kernel.telemetry_sink.store.load_events()]
    metric_kinds = [metric.metric_kind for metric in kernel.telemetry_sink.store.load_metrics()]

    assert replay.reexecuted_actions is False
    assert replay.tampered is False
    assert replay.session.session_id == session.session_id
    assert replay.artifact_refs == [artifact.artifact_ref]
    assert replay.tool_result_refs == [output.tool_result_ref]
    assert TelemetryEventKind.HARNESS_SESSION_STARTED in event_kinds
    assert TelemetryEventKind.HARNESS_TOOL_OUTPUT_MINIMIZED in event_kinds
    assert TelemetryMetricKind.HARNESS_TOOL_OUTPUT_BYTES_INPUT in metric_kinds
    assert TelemetryMetricKind.HARNESS_TOOL_OUTPUT_BYTES_PERSISTED in metric_kinds


def test_harness_state_redacts_raw_prompt_provider_response_reasoning_and_credentials(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AmplificationHarnessRuntime(kernel)
    session = runtime.start_session(mission_id=mission_id, envelope=_envelope(mission_id))
    runtime.record_artifact(
        mission_id=mission_id,
        session_id=session.session_id,
        logical_path="analysis/secret.txt",
        content="OPENAI_API_KEY=sk-test-1234567890",
        metadata={
            "raw_prompt": "Bearer raw-prompt-token",
            "provider_response": "session_token=raw-provider-token",
            "reasoning": "cookie: raw-reasoning-token",
            "credential_value": "raw-credential-value",
        },
    )

    payload = _harness_payload(kernel, mission_id)

    assert "sk-test-1234567890" not in payload
    assert "raw-prompt-token" not in payload
    assert "raw-provider-token" not in payload
    assert "raw-reasoning-token" not in payload
    assert "raw-credential-value" not in payload
    assert "[REDACTED" in payload


def _kernel_with_mission(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_harness",
        draft=MissionDraft(
            title="Harness mission",
            objective="Amplify model execution with safe harness state.",
            constraints=["no provider fallback", "no new authority"],
            expected_artifacts=["harness summary"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="draft_harness",
            allowed_actions=["read", "write"],
            forbidden_actions=["payment", "credential_unlock"],
            summary="Harness test only.",
        ),
    )
    return kernel, record.mission_id


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_harness",
        mission_title="Harness mission",
        mission_objective="Amplify the explicitly selected model without new authority.",
        allowed_systems=["workspace"],
        allowed_tools=["workspace", "diagnostic"],
        allowed_actions=["read", "write", "analyze"],
        allowed_paths=["analysis", "data/generated_projects"],
        max_duration_minutes=60,
        max_actions=10,
        max_cost_usd=1.0,
        max_recipients=0,
    )


def _harness_payload(kernel: MissionKernel, mission_id: str) -> str:
    harness_root = kernel.store.mission_dir(mission_id) / "harness"
    return "\n".join(path.read_text(encoding="utf-8") for path in harness_root.rglob("*.json"))
