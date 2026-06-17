from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sentinel.agent.model_execution.redaction import text_hash
from sentinel.agent.organs.reversible_workspace_executor import L3WorkspaceAttemptStatus
from sentinel.perf.hot_cold.artifact_ref_store import ArtifactRefStore
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.operator.mutation_artifact_channel import (
    GovernedMutationArtifactChannel,
    MutationArtifactChannelConfig,
    MutationArtifactChunk,
    MutationArtifactFormat,
    MutationArtifactProposal,
    MutationArtifactStateError,
)
from sentinel.operator.replay import MissionReplayBuilder
from sentinel.operator.real_model_certification import _workspace_request
from sentinel.operator.real_model_certification import (
    CertificationActionProposal,
    CertificationConfig,
    CertificationModelCallRecord,
    CertificationStatus,
    RealModelAgentCertificationRunner,
    SequenceCertificationModelClient,
    _parse_proposal,
)
from sentinel.shared.events import EventBus


INITIAL = "def double(amount: int) -> int:\n    return amount\n"
REPLACEMENT = "def double(amount: int) -> int:\n    return amount * 2\n"
INITIAL_REPORT = "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"total={double(amount)}\"\n"


class _ArtifactStoreSpy:
    def __init__(self) -> None:
        self.put_calls = 0

    def put(self, *_args: object, **_kwargs: object) -> object:
        self.put_calls += 1
        raise AssertionError("artifact_store_should_not_be_called")


def _channel(tmp_path: Path) -> tuple[GovernedMutationArtifactChannel, MissionKernel, str, Path]:
    repo_root = tmp_path / "repo"
    target = repo_root / "src" / "pricing.py"
    target.parent.mkdir(parents=True)
    target.write_text(INITIAL, encoding="utf-8")
    kernel = MissionKernel(run_root=tmp_path / "runs")
    mission = kernel.create_mission(
        session_id="v3-test",
        draft=MissionDraft(title="V3 mutation channel", objective="Apply one governed mutation."),
    )
    kernel.enqueue(mission.mission_id)
    kernel.update_status(mission.mission_id, OperatorMissionStatus.RUNNING, "V3 mutation test started.")
    channel = GovernedMutationArtifactChannel(
        kernel=kernel,
        workspace_root=repo_root,
        mission_id=mission.mission_id,
        run_id="run:v3:test",
        workspace_ref="workspace:controlled-repo",
        config=MutationArtifactChannelConfig(max_chunk_bytes=128, max_artifact_bytes=2_048, max_chunks=8),
        workspace_request_factory=lambda path, content, before_hash: _workspace_request(
            repo_root,
            mission.mission_id,
            path,
            content,
            before_hash,
            remaining_action_count=16,
            remaining_patch_bytes=16_384,
        ),
    )
    return channel, kernel, mission.mission_id, target


def _proposal(mission_id: str, **updates: object) -> MutationArtifactProposal:
    payload: dict[str, object] = {
        "schema_version": "sentinel_mutation_proposal_v1",
        "mission_id": mission_id,
        "run_id": "run:v3:test",
        "mutation_id": "mutation:pricing",
        "workspace_ref": "workspace:controlled-repo",
        "target_paths": ["src/pricing.py"],
        "base_hashes": {"src/pricing.py": text_hash(INITIAL)},
        "mutation_format": MutationArtifactFormat.FULL_TEXT_REPLACEMENT,
        "purpose_summary": "Repair the bounded pricing implementation.",
        "evidence_refs": ["observation:test-failure"],
        "expected_postcondition": "Relevant test passes.",
    }
    payload.update(updates)
    return MutationArtifactProposal.model_validate(payload)


def _chunk(
    mission_id: str,
    *,
    payload: str,
    chunk_index: int = 0,
    chunk_count: int = 1,
    **updates: object,
) -> MutationArtifactChunk:
    data: dict[str, object] = {
        "schema_version": "sentinel_mutation_chunk_v1",
        "mission_id": mission_id,
        "run_id": "run:v3:test",
        "mutation_id": "mutation:pricing",
        "artifact_type": MutationArtifactFormat.FULL_TEXT_REPLACEMENT,
        "target_path": "src/pricing.py",
        "base_hash": text_hash(INITIAL),
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
        "payload": payload,
        "payload_hash": text_hash(payload),
    }
    data.update(updates)
    return MutationArtifactChunk.model_validate(data)


def test_control_plane_proposal_rejects_mutation_payload_and_reasoning() -> None:
    safe = _proposal("mission:v3")
    dumped = json.dumps(safe.safe_record(), sort_keys=True)

    assert "Repair the bounded pricing implementation." in dumped
    assert "payload" not in dumped
    assert "content" not in dumped

    with pytest.raises(ValidationError):
        MutationArtifactProposal.model_validate({**safe.model_dump(mode="python"), "payload": REPLACEMENT})
    with pytest.raises(ValidationError):
        MutationArtifactProposal.model_validate({**safe.model_dump(mode="python"), "reasoning": "private chain"})
    with pytest.raises(ValidationError):
        MutationArtifactProposal.model_validate(
            {**safe.model_dump(mode="python"), "purpose_summary": "x" * 2_000}
        )


def test_single_chunk_artifact_applies_through_governed_workspace_and_rolls_back(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    accepted = channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT))
    assembly = channel.assemble("mutation:pricing")
    result = channel.apply("mutation:pricing")

    assert accepted.payload_persisted is False
    assert assembly.validation_status == "validated"
    assert assembly.chunk_count == 1
    assert result.workspace_result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
    assert result.receipt_refs
    assert target.read_text(encoding="utf-8") == REPLACEMENT

    rollback = channel.rollback("mutation:pricing", reason="prove reversible V3 mutation")
    assert rollback.rollback_success is True
    assert target.read_text(encoding="utf-8") == INITIAL


def test_multi_chunk_artifact_assembles_only_when_complete(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    midpoint = len(REPLACEMENT) // 2
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT[:midpoint], chunk_index=0, chunk_count=2))

    with pytest.raises(MutationArtifactStateError, match="mutation_chunks_incomplete"):
        channel.assemble("mutation:pricing")
    assert target.read_text(encoding="utf-8") == INITIAL

    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT[midpoint:], chunk_index=1, chunk_count=2))
    assembly = channel.assemble("mutation:pricing")

    assert assembly.chunk_count == 2
    assert assembly.artifact_hash == text_hash(REPLACEMENT)
    assert target.read_text(encoding="utf-8") == INITIAL


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"mission_id": "mission:other"}, "mutation_mission_mismatch"),
        ({"run_id": "run:other"}, "mutation_run_mismatch"),
        ({"mutation_id": "mutation:other"}, "mutation_id_mismatch"),
        ({"target_path": "src/other.py"}, "mutation_target_path_mismatch"),
        ({"base_hash": "stale"}, "mutation_base_hash_mismatch"),
    ],
)
def test_chunk_correlation_must_match_validated_proposal(
    tmp_path: Path, updates: dict[str, object], error: str
) -> None:
    channel, _, mission_id, _ = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    chunk_updates = dict(updates)
    chunk_mission_id = str(chunk_updates.pop("mission_id", mission_id))

    with pytest.raises(MutationArtifactStateError, match=error):
        channel.accept_chunk(_chunk(chunk_mission_id, payload=REPLACEMENT, **chunk_updates))


def test_duplicate_out_of_order_and_wrong_payload_hash_are_rejected(tmp_path: Path) -> None:
    channel, _, mission_id, _ = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    first = _chunk(mission_id, payload=REPLACEMENT[:10], chunk_index=0, chunk_count=2)

    with pytest.raises(MutationArtifactStateError, match="mutation_chunk_out_of_order"):
        channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT[10:], chunk_index=1, chunk_count=2))

    channel.accept_chunk(first)
    with pytest.raises(MutationArtifactStateError, match="mutation_chunk_duplicate"):
        channel.accept_chunk(first)

    with pytest.raises(ValidationError):
        _chunk(mission_id, payload=REPLACEMENT[10:], chunk_index=1, chunk_count=2, payload_hash="wrong")


def test_wrong_aggregate_hash_and_malformed_diff_are_rejected_without_apply(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id, expected_artifact_hash="wrong"))
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT))

    with pytest.raises(MutationArtifactStateError, match="mutation_aggregate_hash_mismatch"):
        channel.assemble("mutation:pricing")
    assert target.read_text(encoding="utf-8") == INITIAL

    second, _, second_mission_id, second_target = _channel(tmp_path / "diff")
    second.begin(_proposal(second_mission_id, mutation_format=MutationArtifactFormat.UNIFIED_DIFF))
    second.accept_chunk(
        _chunk(
            second_mission_id,
            payload="this is not a unified diff",
            artifact_type=MutationArtifactFormat.UNIFIED_DIFF,
        )
    )
    with pytest.raises(MutationArtifactStateError, match="mutation_artifact_malformed"):
        second.assemble("mutation:pricing")
    assert second_target.read_text(encoding="utf-8") == INITIAL


def test_assembly_secret_scan_catches_secret_split_across_chunks(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    split_secret = "token = 'sk-" + "abcdefghijklmnopqrst'\n"
    channel.begin(_proposal(mission_id))
    channel.accept_chunk(_chunk(mission_id, payload=split_secret[:12], chunk_index=0, chunk_count=2))
    channel.accept_chunk(_chunk(mission_id, payload=split_secret[12:], chunk_index=1, chunk_count=2))

    with pytest.raises(MutationArtifactStateError, match="mutation_artifact_secret_like_payload"):
        channel.assemble("mutation:pricing")

    assert target.read_text(encoding="utf-8") == INITIAL


def test_explicit_assembly_secret_scan_runs_before_artifact_store(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    spy = _ArtifactStoreSpy()
    channel.artifact_store = spy
    split_secret = "token = 'sk-" + "abcdefghijklmnopqrst'\n"
    channel.begin(_proposal(mission_id))
    channel.accept_chunk(_chunk(mission_id, payload=split_secret[:12], chunk_index=0, chunk_count=2))
    channel.accept_chunk(_chunk(mission_id, payload=split_secret[12:], chunk_index=1, chunk_count=2))

    with pytest.raises(MutationArtifactStateError, match="mutation_artifact_secret_like_payload"):
        channel.assemble("mutation:pricing")

    assert spy.put_calls == 0
    assert target.read_text(encoding="utf-8") == INITIAL


def test_explicit_assembly_secret_scan_catches_secret_split_across_many_chunks(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    spy = _ArtifactStoreSpy()
    channel.artifact_store = spy
    payloads = ["token = '", "sk-", "abcdefghijklmnopqrst", "'\n"]
    channel.begin(_proposal(mission_id))
    for index, payload in enumerate(payloads):
        channel.accept_chunk(_chunk(mission_id, payload=payload, chunk_index=index, chunk_count=len(payloads)))

    with pytest.raises(MutationArtifactStateError, match="mutation_artifact_secret_like_payload"):
        channel.assemble("mutation:pricing")

    assert spy.put_calls == 0
    assert target.read_text(encoding="utf-8") == INITIAL


def test_intent_bound_proposal_rejects_wrong_intent_chunk(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id, intent_id="intent:expected"))

    with pytest.raises(MutationArtifactStateError, match="mutation_intent_id_mismatch"):
        channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT, intent_id="intent:wrong"))

    assert target.read_text(encoding="utf-8") == INITIAL


def test_artifact_ref_store_still_rejects_llm_exposable_secret_text(tmp_path: Path) -> None:
    store = ArtifactRefStore(tmp_path / "artifact-store", event_bus=EventBus("artifact-store-test"))

    with pytest.raises(ValueError, match="secret pattern detected"):
        store.put(b"token = 'sk-abcdefghijklmnopqrst'\n", content_type="text", llm_exposable=True)


def test_kill_or_revocation_blocks_assembly_and_apply(tmp_path: Path) -> None:
    channel, kernel, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT))
    kernel.kill(mission_id)

    with pytest.raises(MutationArtifactStateError, match="operator_mission_terminal:killed"):
        channel.assemble("mutation:pricing")
    assert target.read_text(encoding="utf-8") == INITIAL

    second, second_kernel, second_mission_id, second_target = _channel(tmp_path / "revoked")
    second.begin(_proposal(second_mission_id))
    second.accept_chunk(_chunk(second_mission_id, payload=REPLACEMENT))
    second.assemble("mutation:pricing")
    second_kernel.update_status(second_mission_id, OperatorMissionStatus.REVOKED, "Revoked before apply.")

    with pytest.raises(MutationArtifactStateError, match="operator_mission_terminal:revoked"):
        second.apply("mutation:pricing")
    assert second_target.read_text(encoding="utf-8") == INITIAL


def test_kill_after_apply_does_not_block_safety_rollback(tmp_path: Path) -> None:
    channel, kernel, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT))
    channel.assemble("mutation:pricing")
    channel.apply("mutation:pricing")
    kernel.kill(mission_id)

    rollback = channel.rollback("mutation:pricing", reason="restore after operator kill")

    assert rollback.rollback_success is True
    assert target.read_text(encoding="utf-8") == INITIAL


def test_provider_interruption_preserves_accepted_chunks_without_duplicate_apply(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT[:10], chunk_index=0, chunk_count=2))

    channel.record_provider_interruption("mutation:pricing", safe_error_class="PROVIDER_ERROR")

    assert channel.accepted_chunk_indexes("mutation:pricing") == [0]
    assert target.read_text(encoding="utf-8") == INITIAL
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT[10:], chunk_index=1, chunk_count=2))
    channel.assemble("mutation:pricing")
    first = channel.apply("mutation:pricing")
    second = channel.apply("mutation:pricing")

    assert first.workspace_result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
    assert second.status == "duplicate_apply_blocked"
    assert target.read_text(encoding="utf-8") == REPLACEMENT


def test_replay_reconstructs_mutation_evidence_without_reapplying(tmp_path: Path) -> None:
    channel, kernel, mission_id, target = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT))
    channel.assemble("mutation:pricing")
    channel.apply("mutation:pricing")
    before_replay = target.read_text(encoding="utf-8")

    replay = MissionReplayBuilder(kernel.store).build(mission_id)

    assert replay.reexecuted_actions is False
    assert replay.can_execute is False
    assert [event.event_type for event in replay.events if event.event_type.startswith("mutation")] == [
        "mutation_proposed",
        "mutation_artifact_chunk_accepted",
        "mutation_artifact_assembly_completed",
        "mutation_applied",
    ]
    assert target.read_text(encoding="utf-8") == before_replay


def test_workspace_request_factory_cannot_redirect_validated_artifact(tmp_path: Path) -> None:
    channel, _, mission_id, target = _channel(tmp_path)
    other = target.parent / "other.py"
    other.write_text("safe = True\n", encoding="utf-8")
    channel.begin(_proposal(mission_id))
    channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT))
    channel.assemble("mutation:pricing")
    channel.workspace_request_factory = lambda path, content, before_hash: _workspace_request(
        channel.workspace_root,
        mission_id,
        "src/other.py",
        "safe = False\n",
        text_hash("safe = True\n"),
        remaining_action_count=16,
        remaining_patch_bytes=16_384,
    )

    with pytest.raises(MutationArtifactStateError, match="mutation_workspace_request_mismatch"):
        channel.apply("mutation:pricing")

    assert target.read_text(encoding="utf-8") == INITIAL
    assert other.read_text(encoding="utf-8") == "safe = True\n"


def test_safe_records_never_persist_raw_provider_wrapper_or_payload(tmp_path: Path) -> None:
    channel, _, mission_id, _ = _channel(tmp_path)
    channel.begin(_proposal(mission_id))
    receipt = channel.accept_chunk(_chunk(mission_id, payload=REPLACEMENT))
    assembly = channel.assemble("mutation:pricing")
    dumped = json.dumps(
        {
            "receipt": receipt.model_dump(mode="json"),
            "assembly": assembly.model_dump(mode="json"),
            "events": channel.safe_event_records("mutation:pricing"),
        },
        sort_keys=True,
    )

    assert REPLACEMENT not in dumped
    assert "raw_provider_response" not in dumped
    assert "reasoning" not in dumped
    assert assembly.artifact_hash in dumped


def test_v3_control_proposal_is_metadata_only_and_lane_budgets_are_separate() -> None:
    config = CertificationConfig(
        model_id="deepseek-v4-pro",
        experiment_version="V3_GOVERNED_MUTATION_ARTIFACT_CHANNEL",
        governed_mutation_channel_enabled=True,
    )
    proposal = _parse_proposal(
        {
            "schema_version": "sentinel_cert_decision_v1",
            "decision_type": "action",
            "action": "propose_mutation",
            "arguments": {
                "mutation_id": "mutation:pricing",
                "workspace_ref": "workspace:controlled-repo",
                "target_paths": ["src/pricing.py"],
                "base_hashes": {"src/pricing.py": text_hash(INITIAL)},
                "mutation_format": "full_text_replacement",
                "purpose_summary": "Repair bounded pricing behavior.",
                "expected_postcondition": "Relevant tests pass.",
            },
            "evidence_refs": ["observation:test-failure"],
        }
    )

    assert proposal is not None
    assert proposal.action.value == "propose_mutation"
    assert proposal.content is None
    assert proposal.target_paths == ["src/pricing.py"]
    assert config.output_budget_for_lane("control") < config.output_budget_for_lane("mutation")
    assert config.experiment_policy()["mutation_chunk_limit"] == config.max_mutation_chunks

    with pytest.raises(ValidationError):
        CertificationActionProposal.model_validate(
            {
                **proposal.model_dump(mode="python"),
                "content": REPLACEMENT,
            }
        )


def test_v3_runner_separates_control_and_mutation_lanes_for_c_a1(tmp_path: Path) -> None:
    outputs = [
        {"action": "read_file", "path": "src/pricing.py"},
        {"action": "read_file", "path": "src/report.py"},
        {"action": "run_tests", "command": ["python", "-m", "pytest", "tests/test_pricing.py", "-q"]},
        {
            "action": "propose_mutation",
            "mutation_id": "mutation:pricing",
            "workspace_ref": "workspace:controlled-repo",
            "target_paths": ["src/pricing.py"],
            "base_hashes": {"src/pricing.py": text_hash(INITIAL)},
            "mutation_format": "full_text_replacement",
            "purpose_summary": "Repair multiplier.",
            "expected_postcondition": "Pricing returns doubled value.",
        },
        {
            "schema_version": "sentinel_mutation_chunk_v1",
            "mission_id": "use_runner_mission_id",
            "run_id": "use_runner_run_id",
            "mutation_id": "mutation:pricing",
            "artifact_type": "full_text_replacement",
            "target_path": "src/pricing.py",
            "base_hash": text_hash(INITIAL),
            "chunk_index": 0,
            "chunk_count": 1,
            "payload": REPLACEMENT,
            "payload_hash": text_hash(REPLACEMENT),
        },
        {
            "action": "propose_mutation",
            "mutation_id": "mutation:report",
            "workspace_ref": "workspace:controlled-repo",
            "target_paths": ["src/report.py"],
            "base_hashes": {"src/report.py": text_hash(INITIAL_REPORT)},
            "mutation_format": "full_text_replacement",
            "purpose_summary": "Repair rendered output.",
            "expected_postcondition": "Report uses required output format.",
        },
        {
            "schema_version": "sentinel_mutation_chunk_v1",
            "mission_id": "use_runner_mission_id",
            "run_id": "use_runner_run_id",
            "mutation_id": "mutation:report",
            "artifact_type": "full_text_replacement",
            "target_path": "src/report.py",
            "base_hash": text_hash(INITIAL_REPORT),
            "chunk_index": 0,
            "chunk_count": 1,
            "payload": INITIAL_REPORT.replace('f"total={double(amount)}"', 'f"TOTAL={double(amount)}"'),
            "payload_hash": text_hash(
                INITIAL_REPORT.replace('f"total={double(amount)}"', 'f"TOTAL={double(amount)}"')
            ),
        },
        {"action": "run_tests", "command": ["python", "-m", "pytest", "-q"]},
        {"action": "complete"},
    ]
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(
            model_id="deepseek-v4-pro",
            max_steps_per_run=12,
            experiment_version="V3_GOVERNED_MUTATION_ARTIFACT_CHANNEL",
            governed_mutation_channel_enabled=True,
        ),
        model_client=SequenceCertificationModelClient(outputs),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]

    assert run.status is CertificationStatus.PASSED
    assert run.oracle_passed is True
    assert run.control_calls == 7
    assert run.mutation_generation_calls == 2
    assert run.mutation_chunk_count == 2
    assert run.partial_mutation_applications == 0
    assert run.mutation_validation_result == "validated_and_applied"
    assert all(call.lane in {"control", "mutation"} for call in run.model_calls)
    assert sum(call.lane == "mutation" for call in run.model_calls) == 2
    assert sum(step.action == "replace_file" and step.accepted for step in run.steps) == 0
    assert sum(step.action == "propose_mutation" and step.accepted for step in run.steps) == 2
    assert run.receipt_complete is True
    assert run.finalgate_complete is True
    assert run.replay_complete is True


def test_v3_total_model_call_budget_covers_control_and_mutation_lanes(tmp_path: Path) -> None:
    client = SequenceCertificationModelClient(
        [
            {"action": "run_tests", "command": ["python", "-m", "pytest", "tests/test_pricing.py"]},
            {"action": "read_file", "path": "src/pricing.py"},
            {
                "action": "propose_mutation",
                "mutation_id": "mutation:pricing",
                "workspace_ref": "workspace:controlled-repo",
                "target_paths": ["src/pricing.py"],
                "base_hashes": {"src/pricing.py": text_hash(INITIAL)},
                "mutation_format": "full_text_replacement",
                "purpose_summary": "Repair multiplier.",
                "expected_postcondition": "Pricing returns doubled value.",
            },
            {
                "schema_version": "sentinel_mutation_chunk_v1",
                "mission_id": "use_runner_mission_id",
                "run_id": "use_runner_run_id",
                "mutation_id": "mutation:pricing",
                "artifact_type": "full_text_replacement",
                "target_path": "src/pricing.py",
                "base_hash": text_hash(INITIAL),
                "chunk_index": 0,
                "chunk_count": 2,
                "payload": REPLACEMENT[:10],
                "payload_hash": text_hash(REPLACEMENT[:10]),
            },
            {
                "schema_version": "sentinel_mutation_chunk_v1",
                "mission_id": "use_runner_mission_id",
                "run_id": "use_runner_run_id",
                "mutation_id": "mutation:pricing",
                "artifact_type": "full_text_replacement",
                "target_path": "src/pricing.py",
                "base_hash": text_hash(INITIAL),
                "chunk_index": 1,
                "chunk_count": 2,
                "payload": REPLACEMENT[10:],
                "payload_hash": text_hash(REPLACEMENT[10:]),
            },
            {"action": "complete"},
        ]
    )
    runner = RealModelAgentCertificationRunner(
            config=CertificationConfig(
                model_id="deepseek-v4-pro",
                max_steps_per_run=10,
                max_total_model_calls=4,
                experiment_version="V3_GOVERNED_MUTATION_ARTIFACT_CHANNEL",
                governed_mutation_channel_enabled=True,
            ),
        model_client=client,
    )

    run = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1).runs[0]

    assert len(run.model_calls) == 4
    assert run.control_calls == 3
    assert run.mutation_generation_calls == 1
    assert run.status is CertificationStatus.FAILED


def test_v3_runner_preserves_accepted_chunk_across_bounded_provider_retry(tmp_path: Path) -> None:
    class InterruptSecondMutationCallClient(SequenceCertificationModelClient):
        def __init__(self, outputs: list[dict[str, object]]) -> None:
            super().__init__(outputs)
            self.mutation_calls = 0
            self.interrupted = False

        def complete(self, **kwargs: object):
            if kwargs.get("lane") == "mutation":
                self.mutation_calls += 1
                if self.mutation_calls == 2 and not self.interrupted:
                    self.interrupted = True
                    config = kwargs["config"]
                    return None, CertificationModelCallRecord(
                        provider_id=config.provider_id,
                        backend_id=config.backend_id,
                        model_id=config.model_id,
                        prompt_hash="safe-prompt-hash",
                        request_hash="safe-request-hash",
                        input_tokens=10,
                        output_tokens=0,
                        latency_seconds=0.01,
                        outcome="PROVIDER_ERROR",
                        safe_error_class="PROVIDER_ERROR",
                        lane="mutation",
                    )
            return super().complete(**kwargs)

    outputs: list[dict[str, object]] = [
        {"action": "run_tests", "command": ["python", "-m", "pytest", "tests/test_pricing.py"]},
        {"action": "read_file", "path": "src/pricing.py"},
        {
            "action": "propose_mutation",
            "mutation_id": "mutation:pricing",
            "workspace_ref": "workspace:controlled-repo",
            "target_paths": ["src/pricing.py"],
            "base_hashes": {"src/pricing.py": text_hash(INITIAL)},
            "mutation_format": "full_text_replacement",
            "purpose_summary": "Repair multiplier.",
            "expected_postcondition": "Pricing returns doubled value.",
        },
        {
            "schema_version": "sentinel_mutation_chunk_v1",
            "mission_id": "use_runner_mission_id",
            "run_id": "use_runner_run_id",
            "mutation_id": "mutation:pricing",
            "artifact_type": "full_text_replacement",
            "target_path": "src/pricing.py",
            "base_hash": text_hash(INITIAL),
            "chunk_index": 0,
            "chunk_count": 2,
            "payload": REPLACEMENT[:10],
            "payload_hash": text_hash(REPLACEMENT[:10]),
        },
        {
            "schema_version": "sentinel_mutation_chunk_v1",
            "mission_id": "use_runner_mission_id",
            "run_id": "use_runner_run_id",
            "mutation_id": "mutation:pricing",
            "artifact_type": "full_text_replacement",
            "target_path": "src/pricing.py",
            "base_hash": text_hash(INITIAL),
            "chunk_index": 1,
            "chunk_count": 2,
                "payload": REPLACEMENT[10:],
                "payload_hash": text_hash(REPLACEMENT[10:]),
            },
            {"action": "read_file", "path": "src/report.py"},
            {
                "action": "propose_mutation",
            "mutation_id": "mutation:report",
            "workspace_ref": "workspace:controlled-repo",
            "target_paths": ["src/report.py"],
            "base_hashes": {"src/report.py": text_hash(INITIAL_REPORT)},
            "mutation_format": "full_text_replacement",
            "purpose_summary": "Repair rendered output.",
            "expected_postcondition": "Report uses required output format.",
        },
        {
            "schema_version": "sentinel_mutation_chunk_v1",
            "mission_id": "use_runner_mission_id",
            "run_id": "use_runner_run_id",
            "mutation_id": "mutation:report",
            "artifact_type": "full_text_replacement",
            "target_path": "src/report.py",
            "base_hash": text_hash(INITIAL_REPORT),
            "chunk_index": 0,
            "chunk_count": 1,
            "payload": INITIAL_REPORT.replace('f"total={double(amount)}"', 'f"TOTAL={double(amount)}"'),
            "payload_hash": text_hash(
                INITIAL_REPORT.replace('f"total={double(amount)}"', 'f"TOTAL={double(amount)}"')
            ),
        },
        {"action": "run_tests", "command": ["python", "-m", "pytest", "-q"]},
        {"action": "complete"},
    ]
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(
            model_id="deepseek-v4-pro",
            max_steps_per_run=10,
            provider_retry_budget=1,
            experiment_version="V3_GOVERNED_MUTATION_ARTIFACT_CHANNEL",
            governed_mutation_channel_enabled=True,
        ),
        model_client=InterruptSecondMutationCallClient(outputs),
    )

    run = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1).runs[0]

    assert run.status is CertificationStatus.PASSED
    assert run.oracle_passed is True
    assert run.provider_error_count == 1
    assert run.provider_retry_count == 1
    assert run.provider_continuity_preserved is True
    assert run.mutation_chunk_count == 3
    assert run.duplicate_material_side_effects == 0
    assert sum(step.action == "propose_mutation" and step.accepted for step in run.steps) == 2
