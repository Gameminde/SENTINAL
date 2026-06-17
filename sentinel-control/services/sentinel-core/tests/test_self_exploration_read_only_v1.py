from __future__ import annotations

from pathlib import Path
import time
from typing import Any

import pytest

from sentinel.agent.model_execution.redaction import text_hash
from sentinel.operator.self_exploration_read_only import (
    ClaimVerificationEvidence,
    IndependentClaimVerifier,
    ReadOnlyOperation,
    ReadOnlyPolicyViolation,
    ReadOnlyRepositorySnapshot,
    SanitizedStageBReportCapture,
    SelfExplorationModelCall,
    SelfExplorationPolicy,
    SelfExplorationRunner,
    SequenceSelfExplorationModelClient,
    _validate_visible_report,
    write_provider_call_checkpoint,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo(root: Path) -> Path:
    _write(root / "README.md", "# Sentinel\n")
    _write(root / "sentinel-control/docs/CURRENT_STATE_LOCK.md", "current truth\n")
    _write(root / "sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md", "master\n")
    _write(root / "sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md", "power\n")
    _write(root / "sentinel-control/docs/reviews/SENTINEL_CURRENT_POWER_MATURITY_MATRIX.md", "matrix\n")
    _write(root / "sentinel-control/docs/reviews/SENTINEL_PRODUCT_POWER_SCORECARD.md", "scorecard\n")
    _write(root / "sentinel-control/docs/reviews/OPUS_AUDIT.md", "previous audit must be hidden\n")
    _write(root / "sentinel-control/services/sentinel-core/sentinel/operator/kernel.py", "class MissionKernel: pass\n")
    _write(root / "sentinel-control/services/sentinel-core/sentinel/power/runtime.py", "class PowerRuntime: pass\n")
    _write(root / "sentinel-control/services/sentinel-core/tests/test_kernel.py", "def test_kernel(): pass\n")
    return root


def test_stage_a_hides_previous_audits_and_truth_docs_until_reconciliation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    policy = SelfExplorationPolicy()
    snapshot = ReadOnlyRepositorySnapshot.freeze(repo_root=repo, policy=policy)

    assert snapshot.can_read("sentinel-control/services/sentinel-core/sentinel/operator/kernel.py", stage="A")
    assert not snapshot.can_read("sentinel-control/docs/reviews/OPUS_AUDIT.md", stage="A")
    assert not snapshot.can_read("README.md", stage="A")
    assert snapshot.can_read("README.md", stage="B")
    assert snapshot.can_read("sentinel-control/docs/reviews/SENTINEL_CURRENT_POWER_MATURITY_MATRIX.md", stage="B")

    with pytest.raises(ReadOnlyPolicyViolation):
        snapshot.read_file("sentinel-control/docs/reviews/OPUS_AUDIT.md", stage="A")


def test_snapshot_blocks_credential_like_paths_even_inside_code_roots(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _write(repo / "sentinel-control/services/sentinel-core/sentinel/.env", "SENTINEL_CERT_MODEL_API_KEY=secret\n")
    _write(repo / "sentinel-control/services/sentinel-core/sentinel/provider_key.pem", "secret\n")
    policy = SelfExplorationPolicy()

    snapshot = ReadOnlyRepositorySnapshot.freeze(repo_root=repo, policy=policy)

    assert not snapshot.can_read("sentinel-control/services/sentinel-core/sentinel/.env", stage="A")
    assert not snapshot.can_read("sentinel-control/services/sentinel-core/sentinel/provider_key.pem", stage="A")
    assert not snapshot.can_read("sentinel-control/services/sentinel-core/sentinel/.env", stage="B")
    with pytest.raises(ReadOnlyPolicyViolation):
        snapshot.read_file("sentinel-control/services/sentinel-core/sentinel/.env", stage="B")


def test_snapshot_does_not_excerpt_secret_like_allowed_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    rel = "sentinel-control/services/sentinel-core/sentinel/operator/benign.py"
    _write(repo / rel, "Authorization: Bearer abcdefghijklmnop1234567890\n")
    policy = SelfExplorationPolicy(max_files_read=12, max_bytes_read=50_000)

    snapshot = ReadOnlyRepositorySnapshot.freeze(repo_root=repo, policy=policy)
    item = next(entry for entry in snapshot.inventory if entry.path == rel)

    assert item.stage_a_accessible is True
    assert item.excerpt is None


def test_read_only_tool_policy_blocks_writes_mutation_and_network() -> None:
    policy = SelfExplorationPolicy()

    policy.validate_operation(ReadOnlyOperation(kind="read_file", target="sentinel-control/services/sentinel-core/sentinel/operator/kernel.py"))
    with pytest.raises(ReadOnlyPolicyViolation):
        policy.validate_operation(ReadOnlyOperation(kind="write_file", target="README.md"))
    with pytest.raises(ReadOnlyPolicyViolation):
        policy.validate_operation(ReadOnlyOperation(kind="commit", target="git commit"))
    with pytest.raises(ReadOnlyPolicyViolation):
        policy.validate_operation(ReadOnlyOperation(kind="network", target="https://example.com"))
    with pytest.raises(ReadOnlyPolicyViolation):
        policy.validate_operation(ReadOnlyOperation(kind="mutation_lane", target="mutation_artifact_v2"))


def test_snapshot_immutability_detects_repository_change(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    policy = SelfExplorationPolicy()
    snapshot = ReadOnlyRepositorySnapshot.freeze(repo_root=repo, policy=policy)

    assert snapshot.verify_unchanged()
    _write(repo / "sentinel-control/services/sentinel-core/sentinel/operator/kernel.py", "class MissionKernel:\n    pass\n")

    assert not snapshot.verify_unchanged()


def test_snapshot_verify_unchanged_handles_large_inventory(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    for index in range(260):
        _write(
            repo / f"sentinel-control/services/sentinel-core/sentinel/operator/generated_{index}.py",
            f"class Generated{index}: pass\n",
        )
    policy = SelfExplorationPolicy(max_files_read=240, max_bytes_read=1_500_000)
    snapshot = ReadOnlyRepositorySnapshot.freeze(repo_root=repo, policy=policy)

    assert len(snapshot.inventory) > 240
    assert snapshot.verify_unchanged()


def test_runner_keeps_hidden_rubric_and_stage_b_truth_out_of_stage_a_prompt(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    output_root = tmp_path / "out"
    policy = SelfExplorationPolicy(max_model_calls=2, max_report_chars=8_000)
    stage_a = "# Stage A\nMissionKernel lives in sentinel-control/services/sentinel-core/sentinel/operator/kernel.py"
    stage_b = "# Final\nFinding F1\nseverity: LOW\npath: sentinel-control/services/sentinel-core/sentinel/operator/kernel.py"
    client = SequenceSelfExplorationModelClient([stage_a, stage_b])

    report = SelfExplorationRunner(policy=policy, model_client=client).run(
        repo_root=repo,
        output_root=output_root,
        expected_policy_hash=policy.policy_hash(),
    )

    assert report.status == "completed"
    assert report.hidden_rubric_exposed is False
    assert "OPUS_AUDIT" not in client.prompts[0]
    assert "SENTINEL_CURRENT_POWER_MATURITY_MATRIX" not in client.prompts[0]
    assert "SENTINEL_CURRENT_POWER_MATURITY_MATRIX" in client.prompts[1]
    assert report.stage_a_report_hash == text_hash(stage_a)
    assert report.final_report_hash == text_hash(stage_b)
    assert (output_root / "self_exploration_report.json").exists()
    assert (output_root / "visible_final_report.md").exists()


def test_runner_rejects_secret_bearing_visible_report(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    policy = SelfExplorationPolicy(max_model_calls=2)
    canary = "sk-test-self-exploration-secret-1234567890"
    client = SequenceSelfExplorationModelClient(
        [
            "# Stage A\nsafe",
            f"# Final\nprovider key {canary}",
        ]
    )
    output_root = tmp_path / "out"

    report = SelfExplorationRunner(policy=policy, model_client=client).run(
        repo_root=repo,
        output_root=output_root,
        expected_policy_hash=policy.policy_hash(),
    )

    assert report.status == "failed"
    assert report.failure_category == "STAGE_B_VISIBLE_REPORT_SAFETY_REJECTED"
    assert (output_root / "self_exploration_report.json").exists()
    for path in output_root.rglob("*"):
        if path.is_file():
            assert canary not in path.read_text(encoding="utf-8")


def test_model_channel_failure_when_reasoning_replaces_visible_report(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    policy = SelfExplorationPolicy(max_model_calls=2)
    client = SequenceSelfExplorationModelClient(
        [
            "# Stage A\nsafe",
            SelfExplorationModelCall(
                visible_text="OK",
                input_tokens=10,
                output_tokens=300,
                reasoning_present=True,
                reasoning_hash="reasoning-hash",
                reasoning_char_count=900,
            ),
        ]
    )

    report = SelfExplorationRunner(policy=policy, model_client=client).run(
        repo_root=repo,
        output_root=tmp_path / "out",
        expected_policy_hash=policy.policy_hash(),
    )

    assert report.status == "failed"
    assert report.verdict == "SELF_EXPLORATION_FAILED"
    assert report.failure_category == "MODEL_PROVIDER_OUTPUT_CHANNEL_FAILURE"


def test_runner_persists_failed_record_when_stage_a_visible_report_is_empty(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    policy = SelfExplorationPolicy(max_model_calls=2)
    client = SequenceSelfExplorationModelClient(
        [
            SelfExplorationModelCall(
                visible_text="",
                input_tokens=100,
                output_tokens=0,
                provider_error="INVALID_RESPONSE_SCHEMA",
            )
        ]
    )

    report = SelfExplorationRunner(policy=policy, model_client=client).run(
        repo_root=repo,
        output_root=tmp_path / "out",
        expected_policy_hash=policy.policy_hash(),
    )

    assert report.status == "failed"
    assert report.failure_category == "STAGE_A_VISIBLE_REPORT_EMPTY"
    assert (tmp_path / "out" / "self_exploration_report.json").exists()
    assert (tmp_path / "out" / "visible_stage_a_report.md").exists()


class MutatingFailureClient:
    is_real_model = False

    def __init__(self, repo: Path, rel: str) -> None:
        self.repo = repo
        self.rel = rel
        self.calls: list[str] = []

    def complete(
        self,
        *,
        prompt: str,
        policy: SelfExplorationPolicy,
        mission_id: str,
        stage: str,
    ) -> SelfExplorationModelCall:
        self.calls.append(stage)
        if stage == "A":
            return SelfExplorationModelCall(
                visible_text="# Stage A\nsafe",
                input_tokens=1,
                output_tokens=1,
                finish_reason="stop",
                reasoning_present=False,
            )
        _write(self.repo / self.rel, "class MissionKernel:\n    pass\n")
        return SelfExplorationModelCall(
            visible_text="",
            input_tokens=1,
            output_tokens=0,
            provider_error="INVALID_RESPONSE_SCHEMA",
        )


def test_runner_verifies_snapshot_unchanged_on_stage_b_failure(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    rel = "sentinel-control/services/sentinel-core/sentinel/operator/kernel.py"
    client = MutatingFailureClient(repo, rel)
    policy = SelfExplorationPolicy(max_model_calls=2)

    report = SelfExplorationRunner(policy=policy, model_client=client).run(
        repo_root=repo,
        output_root=tmp_path / "out",
        expected_policy_hash=policy.policy_hash(),
    )

    assert report.status == "failed"
    assert report.failure_category == "SNAPSHOT_CHANGED_DURING_RUN"
    assert report.snapshot.get("unchanged_after_run") is False
    assert (tmp_path / "out" / "self_exploration_report.json").exists()


class DeadlineProbeClient:
    is_real_model = False

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(
        self,
        *,
        prompt: str,
        policy: SelfExplorationPolicy,
        mission_id: str,
        stage: str,
    ) -> SelfExplorationModelCall:
        self.calls.append(stage)
        return SelfExplorationModelCall(
            visible_text="# Stage A\nsafe" if stage == "A" else "# Final\nsafe",
            input_tokens=1,
            output_tokens=1,
            finish_reason="stop",
            reasoning_present=False,
        )


class SlowStageAClient(DeadlineProbeClient):
    def __init__(self, *, delay_seconds: float = 0.25) -> None:
        super().__init__()
        self.delay_seconds = delay_seconds

    def complete(
        self,
        *,
        prompt: str,
        policy: SelfExplorationPolicy,
        mission_id: str,
        stage: str,
    ) -> SelfExplorationModelCall:
        self.calls.append(stage)
        if stage == "A":
            time.sleep(self.delay_seconds)
            return SelfExplorationModelCall(
                visible_text="# Stage A\nsafe",
                input_tokens=1,
                output_tokens=1,
                finish_reason="stop",
                reasoning_present=False,
            )
        return SelfExplorationModelCall(
            visible_text="# Final\nshould not be called",
            input_tokens=1,
            output_tokens=1,
            finish_reason="stop",
            reasoning_present=False,
        )


def test_runner_blocks_provider_call_when_deadline_exhausted_before_stage_a(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    client = DeadlineProbeClient()
    policy = SelfExplorationPolicy(max_duration_seconds=0.000001)

    report = SelfExplorationRunner(policy=policy, model_client=client).run(
        repo_root=repo,
        output_root=tmp_path / "out",
        expected_policy_hash=policy.policy_hash(),
    )

    assert client.calls == []
    assert report.status == "failed"
    assert report.failure_category == "RUN_DURATION_BUDGET_EXHAUSTED"
    assert report.verdict == "SELF_EXPLORATION_FAILED"


def test_runner_blocks_provider_call_when_deadline_exhausted_before_stage_b(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    client = SlowStageAClient(delay_seconds=1.1)
    policy = SelfExplorationPolicy(max_duration_seconds=1.0)

    report = SelfExplorationRunner(policy=policy, model_client=client).run(
        repo_root=repo,
        output_root=tmp_path / "out",
        expected_policy_hash=policy.policy_hash(),
    )

    assert client.calls == ["A"]
    assert report.status == "failed"
    assert report.failure_category == "RUN_DURATION_BUDGET_EXHAUSTED"
    assert report.stage_a_report_hash == text_hash("# Stage A\nsafe")


def _checkpoint_call() -> SelfExplorationModelCall:
    return SelfExplorationModelCall(
        visible_text="raw visible report must not persist",
        input_tokens=123,
        output_tokens=456,
        latency_seconds=7.5,
        finish_reason="stop",
        output_truncated=False,
        reasoning_present=True,
        reasoning_hash="reasoning-safe-hash",
        reasoning_char_count=99,
        reasoning_token_count=88,
        provider_error=None,
    )


def test_provider_checkpoint_survives_snapshot_verification_exception(tmp_path: Path) -> None:
    checkpoint = write_provider_call_checkpoint(
        tmp_path,
        call=_checkpoint_call(),
        provider_id="provider",
        backend_id="backend",
        model_id="model",
        endpoint_hash="endpoint-hash",
        diagnostic_policy_hash="policy-hash",
        stage_b_prompt_hash="prompt-hash",
    )

    with pytest.raises(RuntimeError):
        raise RuntimeError("snapshot_closeout_failed_after_provider_return")

    stored = (tmp_path / "provider_call_checkpoint.json").read_text(encoding="utf-8")
    assert checkpoint["provider_call_completed"] is True
    assert "raw visible report must not persist" not in stored
    assert "reasoning-safe-hash" in stored


def test_provider_checkpoint_survives_report_validation_exception(tmp_path: Path) -> None:
    write_provider_call_checkpoint(
        tmp_path,
        call=_checkpoint_call(),
        provider_id="provider",
        backend_id="backend",
        model_id="model",
        endpoint_hash="endpoint-hash",
        diagnostic_policy_hash="policy-hash",
        stage_b_prompt_hash="prompt-hash",
    )

    with pytest.raises(ReadOnlyPolicyViolation):
        _validate_visible_report("sk-test-checkpoint-secret-1234567890", stage="B", policy=SelfExplorationPolicy())

    stored = (tmp_path / "provider_call_checkpoint.json").read_text(encoding="utf-8")
    assert "sk-test-checkpoint-secret" not in stored
    assert "raw visible report must not persist" not in stored


def test_provider_checkpoint_survives_terminal_result_persistence_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_provider_call_checkpoint(
        tmp_path,
        call=_checkpoint_call(),
        provider_id="provider",
        backend_id="backend",
        model_id="model",
        endpoint_hash="endpoint-hash",
        diagnostic_policy_hash="policy-hash",
        stage_b_prompt_hash="prompt-hash",
    )

    def fail_write(*args: Any, **kwargs: Any) -> None:
        raise OSError("terminal_result_persistence_failed")

    monkeypatch.setattr(Path, "write_text", fail_write)
    with pytest.raises(OSError):
        (tmp_path / "stage_b_microdiagnostic_result.json").write_text("{}", encoding="utf-8")

    assert (tmp_path / "provider_call_checkpoint.json").exists()


def test_provider_checkpoint_rejects_second_write_and_omits_raw_material(tmp_path: Path) -> None:
    write_provider_call_checkpoint(
        tmp_path,
        call=_checkpoint_call(),
        provider_id="provider",
        backend_id="backend",
        model_id="model",
        endpoint_hash="endpoint-hash",
        diagnostic_policy_hash="policy-hash",
        stage_b_prompt_hash="prompt-hash",
    )

    with pytest.raises(RuntimeError, match="provider_checkpoint_already_exists"):
        write_provider_call_checkpoint(
            tmp_path,
            call=_checkpoint_call(),
            provider_id="provider",
            backend_id="backend",
            model_id="model",
            endpoint_hash="endpoint-hash",
            diagnostic_policy_hash="policy-hash",
            stage_b_prompt_hash="prompt-hash",
        )

    stored = (tmp_path / "provider_call_checkpoint.json").read_text(encoding="utf-8")
    assert "raw visible report must not persist" not in stored
    assert '"raw_prompt_persisted": false' in stored
    assert '"raw_response_persisted": false' in stored
    assert '"raw_reasoning_persisted": false' in stored


def test_provider_checkpoint_can_record_uncompleted_transport_attempt(tmp_path: Path) -> None:
    checkpoint = write_provider_call_checkpoint(
        tmp_path,
        call=SelfExplorationModelCall(visible_text="", provider_error="PROVIDER_TRANSPORT_EXCEPTION"),
        provider_id="provider",
        backend_id="backend",
        model_id="model",
        endpoint_hash="endpoint-hash",
        diagnostic_policy_hash="policy-hash",
        stage_b_prompt_hash="prompt-hash",
        provider_call_completed=False,
    )

    stored = (tmp_path / "provider_call_checkpoint.json").read_text(encoding="utf-8")
    assert checkpoint["provider_call_attempted"] is True
    assert checkpoint["provider_call_completed"] is False
    assert "PROVIDER_TRANSPORT_EXCEPTION" in stored
    assert "Authorization" not in stored
    assert "Bearer " not in stored


def test_sanitized_stage_b_capture_writes_visible_report_hash_and_no_raw_material(tmp_path: Path) -> None:
    capture = SanitizedStageBReportCapture(output_root=tmp_path, policy=SelfExplorationPolicy())
    report = (
        "# Stage B Truth Reconciliation\n\n"
        "Confirmed claim cites sentinel-control/services/sentinel-core/sentinel/operator/kernel.py.\n"
        "Finding: MissionKernel evidence is present.\n"
    )

    result = capture.persist(report)

    assert result["sanitized_report_hash"] == text_hash(report)
    assert (tmp_path / "sanitized_stage_b_report.md").read_text(encoding="utf-8") == report
    assert (tmp_path / "sanitized_stage_b_report_hash.txt").read_text(encoding="utf-8").strip() == text_hash(report)
    assert "raw_prompt" not in (tmp_path / "sanitized_stage_b_report.md").read_text(encoding="utf-8")


def test_sanitized_stage_b_capture_rejects_secret_like_visible_report(tmp_path: Path) -> None:
    capture = SanitizedStageBReportCapture(output_root=tmp_path, policy=SelfExplorationPolicy())

    with pytest.raises(ReadOnlyPolicyViolation, match="sanitized_stage_b_report_failed_safety_scan"):
        capture.persist("Stage B report with key sk-test-visible-secret-1234567890")

    assert not (tmp_path / "sanitized_stage_b_report.md").exists()


def test_sanitized_stage_b_capture_allows_governance_discussion_of_dangerous_surfaces(tmp_path: Path) -> None:
    capture = SanitizedStageBReportCapture(output_root=tmp_path, policy=SelfExplorationPolicy())
    report = (
        "# Stage B\n"
        "Finding: external_action, desktop_action, browser_login, authority_expansion, raw_prompt, "
        "and provider_response are discussed only as blocked Sentinel risk categories. "
        "No concrete credential, token, authorization header, or executable payload is included."
    )

    result = capture.persist(report)

    assert result["sanitized_report_hash"] == text_hash(report)
    assert (tmp_path / "sanitized_stage_b_report.md").exists()


def test_sanitized_stage_b_capture_rejects_second_write(tmp_path: Path) -> None:
    capture = SanitizedStageBReportCapture(output_root=tmp_path, policy=SelfExplorationPolicy())
    capture.persist("# Stage B\nConfirmed finding with sentinel-control/services/sentinel-core/sentinel/operator/kernel.py")

    with pytest.raises(RuntimeError, match="sanitized_stage_b_report_already_exists"):
        capture.persist("# Stage B\nsecond report")


def test_independent_claim_verifier_classifies_confirmed_partial_and_false_positive(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    _write(repo / "sentinel-control/services/sentinel-core/sentinel/operator/kernel.py", "class MissionKernel: pass\n")
    report = "\n".join(
        [
            "- MissionKernel is implemented in sentinel-control/services/sentinel-core/sentinel/operator/kernel.py.",
            "- MissingSymbol is implemented in sentinel-control/services/sentinel-core/sentinel/operator/kernel.py.",
            "- This claim has no citation and should not be trusted.",
        ]
    )

    verifier = IndependentClaimVerifier(repo_root=repo)
    matrix = verifier.verify(report)

    statuses = [row.status for row in matrix.claims]
    assert statuses == ["VALID_CONFIRMED", "PARTIALLY_VALID", "UNVERIFIABLE"]
    assert matrix.summary["valid_confirmed"] == 1
    assert matrix.summary["partially_valid"] == 1
    assert matrix.summary["unverifiable"] == 1


def test_independent_claim_verifier_blocks_cross_run_evidence_refs(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    report = "- Claim cites C:/Users/youcefcheriet/.sentinel-runs/other-run/final_report.json as evidence."

    verifier = IndependentClaimVerifier(repo_root=repo)
    matrix = verifier.verify(report)

    assert matrix.claims[0].status == "FALSE_POSITIVE"
    assert matrix.claims[0].evidence == ClaimVerificationEvidence.BLOCKED_EXTERNAL_RUN_REF
