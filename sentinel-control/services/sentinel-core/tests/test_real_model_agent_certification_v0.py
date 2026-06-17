from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sentinel.agent.model_execution.redaction import text_hash
from sentinel.operator.real_model_certification import (
    CertificationActionProposal,
    CertificationConfig,
    CertificationModelCallRecord,
    CertificationStatus,
    DEFAULT_BASE_URL,
    ObservationSufficiency,
    RealModelAgentCertificationRunner,
    SafeTaskStateSummary,
    SequenceCertificationModelClient,
    StructuredOutputInvalidCategory,
    _build_semantic_test_observation,
    _parse_proposal,
    _parse_proposal_with_failure,
    main,
)


INITIAL_PRICING = "def double(amount: int) -> int:\n    return amount\n"
INITIAL_REPORT = "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"total={double(amount)}\"\n"
STALE_PRICING = "def double(amount: int) -> int:\n    return amount\n\n# user touched this file during the mission\n"
INITIAL_CATALOG = "def normalize_name(name: str) -> str:\n    return name.strip().lower()\n"


def test_certification_config_requires_explicit_single_model_and_blocks_fallback_auto() -> None:
    config = CertificationConfig(model_id="deepseek-v4-pro")
    contract = config.user_model_contract()

    assert contract.selected_provider_id == "alibaba_model_studio_certification"
    assert contract.selected_backend_id == "alibaba_model_studio_openai_compatible_chat"
    assert contract.selected_model == "deepseek-v4-pro"
    assert contract.user_selected is True

    with pytest.raises(ValidationError):
        CertificationConfig(model_id="deepseek-v4-pro", fallback_enabled=True)
    with pytest.raises(ValidationError):
        CertificationConfig(model_id="deepseek-v4-pro", auto_routing_enabled=True)
    with pytest.raises(ValidationError):
        CertificationConfig(model_id="deepseek-v4-pro", provider_native_tools_enabled=True)

    assert "aliyuncs.com" not in DEFAULT_BASE_URL
    assert "ws-xjtw" not in DEFAULT_BASE_URL


def test_v3_1_experiment_name_enables_governed_mutation_channel() -> None:
    config = CertificationConfig(
        model_id="deepseek-v4-pro",
        experiment_version="V3_1_STATE_AWARE_MUTATION_HANDOFF",
        governed_mutation_channel_enabled=True,
    )

    policy = config.experiment_policy()

    assert policy["experiment_version"] == "V3_1_STATE_AWARE_MUTATION_HANDOFF"
    assert policy["governed_mutation_channel_enabled"] is True


def test_cli_prints_explicit_policy_hash_without_credential(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTINEL_CERT_MODEL_API_KEY", raising=False)

    code = main(
        [
            "--print-policy-and-exit",
            "--output-root",
            str(tmp_path / "probe"),
            "--repetitions",
            "1",
            "--tasks",
            "C-A1",
            "--experiment-version",
            "V3_1_STATE_AWARE_MUTATION_HANDOFF",
            "--max-steps",
            "18",
            "--max-model-calls",
            "18",
            "--max-tool-steps",
            "16",
            "--max-output-tokens",
            "900",
            "--selector-output-tokens",
            "256",
            "--mutation-output-tokens",
            "2400",
            "--max-mutation-calls-per-proposal",
            "4",
            "--max-mutation-chunk-bytes",
            "8192",
            "--max-mutation-artifact-bytes",
            "32768",
            "--max-mutation-chunks",
            "8",
            "--max-evidence-continuations",
            "1",
            "--provider-retry-budget",
            "1",
            "--max-total-tokens",
            "24000",
            "--max-run-duration-seconds",
            "240",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["experiment_policy_hash"]
    assert payload["experiment_policy"]["experiment_version"] == "V3_1_STATE_AWARE_MUTATION_HANDOFF"
    assert payload["experiment_policy"]["maximum_model_calls"] == 18
    assert payload["experiment_policy"]["maximum_tool_steps"] == 16
    assert payload["experiment_policy"]["selector_output_budget"] == 256
    assert payload["experiment_policy"]["mutation_output_budget"] == 2400
    assert payload["experiment_policy"]["mutation_lane_call_budget_per_proposal"] == 4
    assert payload["experiment_policy"]["mutation_chunk_bytes"] == 8192
    assert payload["experiment_policy"]["mutation_artifact_bytes"] == 32768
    assert payload["experiment_policy"]["mutation_chunk_limit"] == 8
    assert payload["experiment_policy"]["evidence_continuation_budget"] == 1
    assert payload["experiment_policy"]["governed_mutation_channel_enabled"] is True


def test_cli_refuses_policy_hash_mismatch_before_credential_check(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTINEL_CERT_MODEL_API_KEY", raising=False)

    code = main(
        [
            "--base-url",
            "https://provider.invalid/compatible-mode/v1",
            "--output-root",
            str(tmp_path / "probe"),
            "--tasks",
            "C-A1",
            "--experiment-version",
            "V3_1_STATE_AWARE_MUTATION_HANDOFF",
            "--expected-policy-hash",
            "wrong-hash",
        ]
    )

    assert code == 2
    assert "policy hash mismatch" in capsys.readouterr().out


def test_cli_refuses_existing_output_root_before_provider_run(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTINEL_CERT_MODEL_API_KEY", raising=False)
    output_root = tmp_path / "probe"
    output_root.mkdir()

    code = main(
        [
            "--base-url",
            "https://provider.invalid/compatible-mode/v1",
            "--output-root",
            str(output_root),
            "--tasks",
            "C-A1",
            "--experiment-version",
            "V3_1_STATE_AWARE_MUTATION_HANDOFF",
        ]
    )

    assert code == 2
    assert "output root already exists" in capsys.readouterr().out


def test_action_validator_rejects_direct_organ_provider_override_and_raw_secret() -> None:
    with pytest.raises(ValidationError):
        CertificationActionProposal.model_validate(
            {"action": "read_file", "path": "src/pricing.py", "direct_organ_call": "sandbox_shell_code"}
        )
    with pytest.raises(ValidationError):
        CertificationActionProposal.model_validate(
            {"action": "read_file", "path": "src/pricing.py", "provider_override": "other"}
        )
    with pytest.raises(ValidationError):
        CertificationActionProposal.model_validate(
            {
                "action": "replace_file",
                "path": "src/pricing.py",
                "expected_before_hash": "h",
                "content": "token = 'sk-test-secret-value-1234567890'",
            }
        )


def test_run_oracle_overrides_model_self_report_and_retains_failed_run(tmp_path: Path) -> None:
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=1),
        model_client=SequenceCertificationModelClient(
            [{"action": "complete", "rationale_summary": "done without evidence"}]
        ),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)

    assert report.status == "REAL_MODEL_CERTIFICATION_NOT_RUN"
    assert report.summary["failed_runs_retained"] is True
    assert len(report.runs) == 1
    run = report.runs[0]
    assert run.status is CertificationStatus.FAILED
    assert run.oracle_passed is False
    assert run.silent_success_attempts == 1
    assert "HALLUCINATED_SUCCESS" in {reason.value for reason in run.failure_reasons}


def test_fake_model_success_is_not_counted_as_real_model_certification(tmp_path: Path) -> None:
    outputs = [
        {"action": "read_file", "path": "src/pricing.py", "rationale_summary": "inspect pricing"},
        {"action": "read_file", "path": "src/report.py", "rationale_summary": "inspect report"},
        {"action": "run_tests", "command": ["python", "-m", "pytest", "tests/test_pricing.py", "-q"], "rationale_summary": "observe failing test"},
        {
            "action": "replace_file",
            "path": "src/pricing.py",
            "expected_before_hash": text_hash(INITIAL_PRICING),
            "content": "def double(amount: int) -> int:\n    return amount * 2\n",
            "rationale_summary": "repair multiplier",
        },
        {
            "action": "replace_file",
            "path": "src/report.py",
            "expected_before_hash": text_hash(INITIAL_REPORT),
            "content": "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"TOTAL={double(amount)}\"\n",
            "rationale_summary": "repair output format",
        },
        {"action": "run_tests", "command": ["python", "-m", "pytest", "-q"], "rationale_summary": "verify regression"},
        {"action": "complete", "rationale_summary": "tests pass"},
    ]
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=10),
        model_client=SequenceCertificationModelClient(outputs),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)

    assert report.status == "REAL_MODEL_CERTIFICATION_NOT_RUN"
    assert report.runs[0].status is CertificationStatus.PASSED
    assert report.runs[0].real_model_used is False
    assert report.summary["passed_runs"] == 1


def test_partial_task_success_is_not_marked_locked(tmp_path: Path) -> None:
    outputs = [
        {"action": "read_file", "path": "src/pricing.py", "rationale_summary": "inspect pricing"},
        {"action": "read_file", "path": "src/report.py", "rationale_summary": "inspect report"},
        {
            "action": "replace_file",
            "path": "src/pricing.py",
            "expected_before_hash": text_hash(INITIAL_PRICING),
            "content": "def double(amount: int) -> int:\n    return amount * 2\n",
            "rationale_summary": "repair multiplier",
        },
        {
            "action": "replace_file",
            "path": "src/report.py",
            "expected_before_hash": text_hash(INITIAL_REPORT),
            "content": "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"TOTAL={double(amount)}\"\n",
            "rationale_summary": "repair output format",
        },
        {"action": "run_tests", "command": ["python", "-m", "pytest", "-q"], "rationale_summary": "verify regression"},
        {"action": "complete", "rationale_summary": "tests pass"},
    ]
    client = SequenceCertificationModelClient(outputs)
    client.is_real_model = True
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=10),
        model_client=client,
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)

    assert report.runs[0].status is CertificationStatus.PASSED
    assert report.status == "REAL_MODEL_AGENT_CERTIFICATION_PARTIALLY_CLOSED"
    assert report.summary["required_task_coverage"] is False


def test_c_a2_requires_specific_test_file_not_any_tests_mutation(tmp_path: Path) -> None:
    outputs = [
        {"action": "read_file", "path": "src/catalog.py", "rationale_summary": "inspect catalog"},
        {
            "action": "replace_file",
            "path": "src/catalog.py",
            "expected_before_hash": text_hash(INITIAL_CATALOG),
            "content": "def normalize_name(name: str) -> str:\n    return name.strip().upper()\n",
            "rationale_summary": "change feature",
        },
        {
            "action": "replace_file",
            "path": "tests/garbage.py",
            "expected_before_hash": text_hash(""),
            "content": "def test_garbage():\n    assert True\n",
            "rationale_summary": "wrong test file",
        },
        {"action": "complete", "rationale_summary": "done"},
    ]
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=8),
        model_client=SequenceCertificationModelClient(outputs),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A2"], repetitions=1)

    assert report.runs[0].status is CertificationStatus.FAILED
    assert any("multi_file_feature_or_test_missing" in step.safe_summary for step in report.runs[0].steps)


def test_c_a3_detects_specific_stale_pricing_write_and_recovers(tmp_path: Path) -> None:
    outputs = [
        {"action": "read_file", "path": "src/pricing.py", "rationale_summary": "inspect pricing"},
        {
            "action": "replace_file",
            "path": "src/pricing.py",
            "expected_before_hash": text_hash(INITIAL_PRICING),
            "content": "def double(amount: int) -> int:\n    return amount * 2\n",
            "rationale_summary": "first repair attempt should be stale guarded",
        },
        {"action": "read_file", "path": "src/pricing.py", "rationale_summary": "reobserve after stale block"},
        {
            "action": "replace_file",
            "path": "src/pricing.py",
            "expected_before_hash": text_hash(STALE_PRICING),
            "content": "def double(amount: int) -> int:\n    return amount * 2\n",
            "rationale_summary": "repair after reobserve",
        },
        {"action": "read_file", "path": "src/report.py", "rationale_summary": "inspect report"},
        {
            "action": "replace_file",
            "path": "src/report.py",
            "expected_before_hash": text_hash(INITIAL_REPORT),
            "content": "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"TOTAL={double(amount)}\"\n",
            "rationale_summary": "repair output format",
        },
        {"action": "run_tests", "command": ["python", "-m", "pytest", "-q"], "rationale_summary": "verify regression"},
        {"action": "complete", "rationale_summary": "tests pass after stale recovery"},
    ]
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=12),
        model_client=SequenceCertificationModelClient(outputs),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A3"], repetitions=1)

    assert report.runs[0].status is CertificationStatus.PASSED
    assert report.runs[0].replans >= 1


def test_safe_report_persists_hashes_not_raw_prompt_or_provider_key(tmp_path: Path) -> None:
    secret = "sk-test-secret-value-abcdef1234567890"
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=1),
        model_client=SequenceCertificationModelClient(
            [{"action": "complete", "rationale_summary": "done without evidence"}]
        ),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    dumped = json.dumps(report.model_dump(mode="json"), sort_keys=True)

    assert secret not in dumped
    assert "raw_prompt" not in dumped
    assert "raw_provider_response" not in dumped
    assert "reasoning_content" not in dumped
    assert "Inspect the controlled repository" not in dumped


def test_invalid_structured_output_fails_closed(tmp_path: Path) -> None:
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=2),
        model_client=SequenceCertificationModelClient(
            [
                {"action": "read_file", "path": "src/pricing.py", "tool_calls": [{"name": "organ"}]},
                {"action": "complete", "rationale_summary": "done"},
            ]
        ),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)

    assert report.runs[0].invalid_structured_outputs == 1
    assert any(step.action == "invalid_structured_output" and not step.accepted for step in report.runs[0].steps)


def test_real_model_payload_aliases_are_normalized_without_accepting_dangerous_fields() -> None:
    proposal = _parse_proposal(
        {
            "next_action": "edit_file",
            "arguments": {
                "file_path": "src/pricing.py",
                "base_hash": "abc",
                "new_content": "def double(amount: int) -> int:\n    return amount * 2\n",
            },
            "rationale": "bounded repair",
        }
    )

    assert proposal is not None
    assert proposal.action.value == "replace_file"
    assert proposal.path == "src/pricing.py"
    assert proposal.expected_before_hash == "abc"

    rejected = _parse_proposal(
        {
            "next_action": "edit_file",
            "arguments": {
                "file_path": "src/pricing.py",
                "base_hash": "abc",
                "new_content": "safe",
                "provider_override": "other",
            },
        }
    )
    assert rejected is None


def test_provider_hash_only_reasoning_metadata_is_ignored_but_raw_reasoning_is_rejected() -> None:
    proposal = _parse_proposal(
        {
            "action": "read_file",
            "path": "src/pricing.py",
            "reasoning_present": True,
            "reasoning_hash": "abc123",
            "rationale_summary": "inspect",
        }
    )
    assert proposal is not None
    assert proposal.action.value == "read_file"

    rejected = _parse_proposal(
        {
            "action": "read_file",
            "path": "src/pricing.py",
            "reasoning": "raw hidden reasoning",
            "rationale_summary": "inspect",
        }
    )
    assert rejected is None


@pytest.mark.parametrize(
    ("payload", "category"),
    [
        ({"raw_text_hash": "hash-only"}, StructuredOutputInvalidCategory.NON_JSON_TEXT),
        ({}, StructuredOutputInvalidCategory.MISSING_REQUIRED_FIELD),
        (
            {"action": "read_file", "path": "src/pricing.py", "unsupported": True},
            StructuredOutputInvalidCategory.EXTRA_UNSUPPORTED_FIELD,
        ),
        (
            {"action": "read_file", "path": "src/pricing.py", "reasoning": "private"},
            StructuredOutputInvalidCategory.REASONING_FIELD_REJECTED,
        ),
        (
            {"actions": [{"action": "read_file", "path": "src/pricing.py"}]},
            StructuredOutputInvalidCategory.MULTIPLE_ACTIONS,
        ),
        (
            {
                "schema_version": "sentinel_cert_decision_v1",
                "decision_type": "action",
                "action": "run_tests",
                "arguments": {"command": 42},
            },
            StructuredOutputInvalidCategory.WRONG_FIELD_TYPE,
        ),
        (
            {
                "schema_version": "unsupported",
                "decision_type": "checkpoint",
                "action": "checkpoint",
                "arguments": {"checkpoint_reason": "uncertain"},
            },
            StructuredOutputInvalidCategory.SCHEMA_VERSION_MISMATCH,
        ),
    ],
)
def test_structured_output_failures_are_safely_classified(
    payload: dict[str, object], category: StructuredOutputInvalidCategory
) -> None:
    proposal, failure = _parse_proposal_with_failure(payload)

    assert proposal is None
    assert failure is not None
    assert failure.category is category
    dumped = json.dumps(failure.model_dump(mode="json"), sort_keys=True)
    assert "private" not in dumped
    assert "raw_text" not in dumped
    assert "provider_response" not in dumped


def test_compact_versioned_decision_envelope_is_normalized() -> None:
    proposal, failure = _parse_proposal_with_failure(
        {
            "schema_version": "sentinel_cert_decision_v1",
            "decision_type": "action",
            "action": "read_file",
            "arguments": {"path": "src/pricing.py"},
            "evidence_refs": ["observation:1"],
            "operator_message": "Inspecting the relevant source.",
        }
    )

    assert failure is None
    assert proposal is not None
    assert proposal.action.value == "read_file"
    assert proposal.path == "src/pricing.py"
    assert proposal.schema_version == "sentinel_cert_decision_v1"
    assert proposal.operator_message == "Inspecting the relevant source."


def test_one_invalid_output_gets_one_bounded_repair_and_is_still_counted(tmp_path: Path) -> None:
    outputs = [
        {"raw_text_hash": "non-json-hash"},
        {"action": "read_file", "path": "src/pricing.py"},
        {"action": "read_file", "path": "src/report.py"},
        {
            "action": "replace_file",
            "path": "src/pricing.py",
            "expected_before_hash": text_hash(INITIAL_PRICING),
            "content": "def double(amount: int) -> int:\n    return amount * 2\n",
        },
        {
            "action": "replace_file",
            "path": "src/report.py",
            "expected_before_hash": text_hash(INITIAL_REPORT),
            "content": "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"TOTAL={double(amount)}\"\n",
        },
        {"action": "run_tests", "command": ["python", "-m", "pytest", "-q"]},
        {"action": "complete"},
    ]
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=10),
        model_client=SequenceCertificationModelClient(outputs),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]

    assert run.status is CertificationStatus.PASSED
    assert run.invalid_structured_outputs == 1
    assert run.structured_output_repairs == 1
    assert run.structured_output_repair_calls == 1
    assert run.first_pass_structured_validity_rate == pytest.approx(5 / 6, abs=0.0001)
    assert any("NON_JSON_TEXT" in step.safe_summary for step in run.steps)


def test_second_consecutive_invalid_output_fails_closed_without_unbounded_retry(tmp_path: Path) -> None:
    raw_invalid = "do not persist this raw provider output"
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=8),
        model_client=SequenceCertificationModelClient(
            [
                {"raw_text_hash": text_hash(raw_invalid)},
                {"raw_text_hash": text_hash(raw_invalid + " again")},
                {"action": "complete"},
            ]
        ),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]
    dumped = json.dumps(report.model_dump(mode="json"), sort_keys=True)

    assert run.status is CertificationStatus.FAILED
    assert len(run.model_calls) == 2
    assert run.invalid_structured_outputs == 2
    assert run.structured_output_repairs == 0
    assert "INVALID_STRUCTURED_OUTPUT" in {reason.value for reason in run.failure_reasons}
    assert raw_invalid not in dumped


def test_cli_infrastructure_failure_does_not_print_raw_exception_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "sk-test-secret-value-abcdef1234567890"
    monkeypatch.setenv("SENTINEL_CERT_MODEL_API_KEY", "present-only-for-test")
    monkeypatch.setenv("SENTINEL_CERT_MODEL_BASE_URL", "https://example.test/compatible-mode/v1")

    def fail_run(*args: object, **kwargs: object) -> None:
        raise RuntimeError(f"provider failure included {secret}")

    monkeypatch.setattr(RealModelAgentCertificationRunner, "run_tasks", fail_run)

    exit_code = main(["--output-root", str(tmp_path / "probe"), "--tasks", "C-A1"])
    captured = capsys.readouterr().out

    assert exit_code == 3
    assert "RuntimeError" in captured
    assert secret not in captured
    assert "provider failure included" not in captured


def test_provider_failure_is_not_misclassified_as_invalid_structured_output(tmp_path: Path) -> None:
    class ProviderFailureClient:
        is_real_model = True

        def complete(self, **kwargs: object) -> tuple[None, CertificationModelCallRecord]:
            return None, CertificationModelCallRecord(
                provider_id="alibaba_model_studio_certification",
                backend_id="alibaba_model_studio_openai_compatible_chat",
                model_id="deepseek-v4-pro",
                prompt_hash="prompt-hash",
                request_hash="request-hash",
                outcome="PROVIDER_ERROR",
                safe_error_class="PROVIDER_ERROR",
            )

    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=8, provider_retry_budget=0),
        model_client=ProviderFailureClient(),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]

    assert run.status is CertificationStatus.FAILED
    assert len(run.model_calls) == 1
    assert run.invalid_structured_outputs == 0
    assert run.structured_output_repair_calls == 0
    assert any(step.action == "model_call_failed" for step in run.steps)
    assert "RUNTIME_FAILURE" in {reason.value for reason in run.failure_reasons}


def test_blocked_tool_request_is_counted_as_invalid_tool_request(tmp_path: Path) -> None:
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=2),
        model_client=SequenceCertificationModelClient(
            [
                {"action": "run_tests", "command": ["definitely-not-allowlisted"]},
                {"action": "complete"},
            ]
        ),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]

    assert run.invalid_tool_requests == 1
    assert any(
        step.action == "run_tests" and step.failure_reason == "WRONG_TOOL_SELECTION" for step in run.steps
    )


def test_semantic_test_observation_preserves_error_location_and_expected_actual() -> None:
    observation = _build_semantic_test_observation(
        command=["python", "-m", "pytest", "-q"],
        status="failed",
        exit_code=1,
        stdout=(
            "================ FAILURES ================\n"
            "tests/test_pricing.py:5: AssertionError\n"
            "E assert 'total=7' == 'TOTAL=14'\n"
            "E - TOTAL=14\n"
            "E + total=7\n"
            + ("noise\n" * 500)
        ),
        stderr="",
        max_excerpt_chars=240,
    )

    assert observation.sufficiency is ObservationSufficiency.TRUNCATED_BUT_CONTINUABLE
    assert observation.truncated is True
    assert observation.continuation_handle
    assert "tests/test_pricing.py:5" in observation.diagnostic_excerpt
    assert "total=7" in observation.diagnostic_excerpt
    assert "TOTAL=14" in observation.diagnostic_excerpt


def test_insufficient_semantic_observation_requests_bounded_continuation() -> None:
    observation = _build_semantic_test_observation(
        command=["python", "-m", "pytest", "-q"],
        status="failed",
        exit_code=1,
        stdout="generic truncated output\n" + ("noise\n" * 500),
        stderr="",
        max_excerpt_chars=80,
    )

    assert observation.sufficiency is ObservationSufficiency.INSUFFICIENT_REOBSERVE_REQUIRED
    assert observation.continuation_handle
    assert observation.legal_next_actions == ["request_bounded_continuation"]


def test_safe_task_state_summary_rejects_reasoning_like_fields() -> None:
    summary = SafeTaskStateSummary(
        current_hypothesis="Observed test failure may require a bounded source repair.",
        evidence_refs=["test:1"],
        completed_requirements=["test_failure_observed"],
        remaining_requirements=["independent_test_pass_not_observed"],
        last_failure_category="TEST_FAILED",
        next_action="read_file",
    )
    assert summary.next_action == "read_file"

    with pytest.raises(ValidationError):
        SafeTaskStateSummary.model_validate(
            {
                "current_hypothesis": "safe",
                "evidence_refs": [],
                "completed_requirements": [],
                "remaining_requirements": [],
                "last_failure_category": "TEST_FAILED",
                "next_action": "read_file",
                "reasoning": "private chain",
            }
        )


def test_provider_retry_preserves_state_without_duplicate_material_action(tmp_path: Path) -> None:
    valid_outputs = [
        {"action": "read_file", "path": "src/pricing.py"},
        {"action": "read_file", "path": "src/report.py"},
        {
            "action": "replace_file",
            "path": "src/pricing.py",
            "expected_before_hash": text_hash(INITIAL_PRICING),
            "content": "def double(amount: int) -> int:\n    return amount * 2\n",
        },
        {
            "action": "replace_file",
            "path": "src/report.py",
            "expected_before_hash": text_hash(INITIAL_REPORT),
            "content": "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"TOTAL={double(amount)}\"\n",
        },
        {"action": "run_tests", "command": ["python", "-m", "pytest", "-q"]},
        {"action": "complete"},
    ]

    class ProviderErrorThenValidClient(SequenceCertificationModelClient):
        is_real_model = True

        def __init__(self) -> None:
            super().__init__(valid_outputs)
            self.failed_once = False

        def complete(self, **kwargs: object) -> tuple[dict[str, object] | None, CertificationModelCallRecord]:
            if self.calls == 3 and not self.failed_once:
                self.failed_once = True
                self.calls += 1
                return None, CertificationModelCallRecord(
                    provider_id="alibaba_model_studio_certification",
                    backend_id="alibaba_model_studio_openai_compatible_chat",
                    model_id="deepseek-v4-pro",
                    prompt_hash="prompt-hash",
                    request_hash="request-hash",
                    outcome="PROVIDER_ERROR",
                    safe_error_class="PROVIDER_ERROR",
                )
            return super().complete(**kwargs)

    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=12, provider_retry_budget=1),
        model_client=ProviderErrorThenValidClient(),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]

    assert run.status is CertificationStatus.PASSED
    assert run.provider_error_count == 1
    assert run.provider_retry_count == 1
    assert run.provider_continuity_preserved is True
    assert run.invalid_structured_outputs == 0
    assert run.duplicate_material_side_effects == 0
    assert sum(step.action == "replace_file" and step.accepted for step in run.steps) == 2


def test_early_terminal_decision_fails_oracle_when_requirements_remain(tmp_path: Path) -> None:
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=1),
        model_client=SequenceCertificationModelClient([{"action": "complete"}]),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]

    assert run.status is CertificationStatus.FAILED
    assert run.oracle_passed is False
    assert run.silent_success_attempts == 1


def test_report_counters_match_retained_run_counters(tmp_path: Path) -> None:
    runner = RealModelAgentCertificationRunner(
        config=CertificationConfig(model_id="deepseek-v4-pro", max_steps_per_run=2),
        model_client=SequenceCertificationModelClient(
            [{"raw_text_hash": "non-json"}, {"action": "complete"}]
        ),
    )

    report = runner.run_tasks(output_root=tmp_path, task_ids=["C-A1"], repetitions=1)
    run = report.runs[0]

    assert report.summary["invalid_structured_outputs"] == run.invalid_structured_outputs
    assert report.summary["provider_error_count"] == run.provider_error_count
    assert report.summary["provider_retry_count"] == run.provider_retry_count


def test_v2_experiment_policy_is_explicit_and_hash_bound() -> None:
    config = CertificationConfig(model_id="deepseek-v4-pro")
    policy = config.experiment_policy()

    assert policy["experiment_version"] == "V2_SEMANTIC_RECOVERY"
    assert policy["task"] == "C-A1"
    assert policy["maximum_model_calls"] == config.max_steps_per_run
    assert policy["maximum_tool_steps"] == config.max_tool_steps_per_run
    assert policy["maximum_tokens"] == config.max_total_tokens
    assert policy["maximum_duration_seconds"] == config.max_run_duration_seconds
    assert policy["provider_retry_budget"] == 1
    assert policy["structured_repair_budget"] == 1
    assert config.experiment_policy_hash() == config.experiment_policy_hash()
