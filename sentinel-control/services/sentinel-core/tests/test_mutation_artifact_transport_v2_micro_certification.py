from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.mutation_transport_micro_certification import (
    MICRO_CERTIFICATION_VERSION,
    MicroProbeId,
    MicroProbeStatus,
    MutationTransportMicroCertificationRunner,
    MutationTransportMicroPolicy,
    diagnose_transport_shape,
    run_local_deterministic_gate,
)
from sentinel.operator.real_model_certification import CertificationModelCallRecord


class _FakeMicroClient:
    is_real_model = True

    def __init__(
        self,
        responses: dict[MicroProbeId, str],
        *,
        metadata_by_probe: dict[MicroProbeId, dict[str, Any]] | None = None,
    ) -> None:
        self.responses = responses
        self.metadata_by_probe = metadata_by_probe or {}
        self.calls: list[MicroProbeId] = []

    def complete(self, **kwargs: object) -> tuple[dict[str, Any], CertificationModelCallRecord]:
        prompt = str(kwargs["prompt"])
        probe_id = next(item for item in MicroProbeId if f"Probe id: {item.value}" in prompt)
        self.calls.append(probe_id)
        raw = self.responses[probe_id]
        config = kwargs["config"]
        payload = {
            "raw_text_hash": text_hash(raw),
            "raw_text_transport": "mutation_patch_v2",
            "visible_content_char_count": len(raw),
            "visible_content_estimated_tokens": max(1, (len(raw) + 3) // 4),
            "raw_text_in_memory_only": raw,
        }
        payload.update(self.metadata_by_probe.get(probe_id, {}))
        safe_payload = {key: value for key, value in payload.items() if key != "raw_text_in_memory_only"}
        return payload, CertificationModelCallRecord(
            provider_id=config.provider_id,
            backend_id=config.backend_id,
            model_id=config.model_id,
            prompt_hash=text_hash(prompt),
            request_hash=text_hash(f"request:{probe_id.value}"),
            response_hash=stable_hash(safe_payload),
            response_content_keys=sorted(safe_payload),
            input_tokens=100,
            output_tokens=max(1, len(raw) // 4),
            latency_seconds=0.01,
            outcome="SUCCESS_VALIDATED",
            lane="mutation",
        )


def test_micro_certification_policy_hash_mismatch_refuses_before_provider_call(tmp_path: Path) -> None:
    policy = MutationTransportMicroPolicy()
    client = _FakeMicroClient({MicroProbeId.M1_SMALL_DIFF: _small_patch()})

    with pytest.raises(RuntimeError, match="micro_policy_hash_mismatch"):
        MutationTransportMicroCertificationRunner(policy=policy, model_client=client).run(
            output_root=tmp_path / "micro",
            expected_policy_hash="wrong-hash",
            probe_ids=[MicroProbeId.M1_SMALL_DIFF],
        )

    assert client.calls == []


def test_micro_certification_refuses_output_root_overwrite(tmp_path: Path) -> None:
    output_root = tmp_path / "micro"
    output_root.mkdir()
    policy = MutationTransportMicroPolicy()
    client = _FakeMicroClient({MicroProbeId.M1_SMALL_DIFF: _small_patch()})

    with pytest.raises(RuntimeError, match="micro_output_root_already_exists"):
        MutationTransportMicroCertificationRunner(policy=policy, model_client=client).run(
            output_root=output_root,
            expected_policy_hash=policy.policy_hash(),
            probe_ids=[MicroProbeId.M1_SMALL_DIFF],
        )

    assert client.calls == []


def test_local_deterministic_gate_covers_transport_parser_edges() -> None:
    report = run_local_deterministic_gate(policy=MutationTransportMicroPolicy())

    assert report.status is MicroProbeStatus.PASSED
    expected = {
        "small_valid_unified_diff",
        "quotes_backslashes_multiline",
        "near_budget_diff",
        "truncated_diff_rejected",
        "markdown_fence_rejected",
        "unexpected_prose_rejected",
        "wrong_target_rejected",
        "extra_target_rejected",
        "path_traversal_rejected",
        "stale_base_hash_rejected",
        "secret_payload_rejected",
        "split_secret_rejected_after_assembly",
    }
    assert expected <= {item.probe_id for item in report.results}
    assert all(item.status is MicroProbeStatus.PASSED for item in report.results)


def test_micro_certification_records_hash_only_artifact_metadata(tmp_path: Path) -> None:
    policy = MutationTransportMicroPolicy()
    client = _FakeMicroClient({MicroProbeId.M1_SMALL_DIFF: _small_patch()})

    report = MutationTransportMicroCertificationRunner(policy=policy, model_client=client).run(
        output_root=tmp_path / "micro",
        expected_policy_hash=policy.policy_hash(),
        probe_ids=[MicroProbeId.M1_SMALL_DIFF],
    )

    assert report.status is MicroProbeStatus.PASSED
    result = report.results[0]
    assert result.probe_id == MicroProbeId.M1_SMALL_DIFF.value
    assert result.raw_response_persisted is False
    assert result.validated_artifact_persisted is False
    report_text = (tmp_path / "micro" / "mutation_transport_micro_certification_report.json").read_text(
        encoding="utf-8"
    )
    assert "return amount * 2" not in report_text
    assert "raw_text_in_memory_only" not in report_text
    json.loads(report_text)


def test_m5_unsafe_payload_rejection_is_a_passing_transport_result(tmp_path: Path) -> None:
    policy = MutationTransportMicroPolicy()
    client = _FakeMicroClient({MicroProbeId.M5_UNSAFE_REJECTION: _unsafe_patch()})

    report = MutationTransportMicroCertificationRunner(policy=policy, model_client=client).run(
        output_root=tmp_path / "micro",
        expected_policy_hash=policy.policy_hash(),
        probe_ids=[MicroProbeId.M5_UNSAFE_REJECTION],
    )

    assert report.status is MicroProbeStatus.PASSED
    result = report.results[0]
    assert result.status == MicroProbeStatus.PASSED.value
    assert result.failure_category == "UNSAFE_PAYLOAD_CORRECTLY_REJECTED"
    assert result.parser_valid is False
    assert result.secret_scan_result == "rejected"
    assert result.raw_response_persisted is False


def test_micro_certification_experiment_version_is_distinct() -> None:
    policy = MutationTransportMicroPolicy()

    assert MICRO_CERTIFICATION_VERSION == "MUTATION_ARTIFACT_TRANSPORT_V2_MICRO_CERTIFICATION_V1"
    assert policy.experiment_version == MICRO_CERTIFICATION_VERSION


def test_shape_diagnostic_detects_literal_newlines_without_raw_payload() -> None:
    raw = "PATCH\\n--- a/src/pricing.py\\n+++ b/src/pricing.py\\n@@ -1 +1 @@"

    diagnostic = diagnose_transport_shape(raw)

    assert diagnostic.true_newline_count == 0
    assert diagnostic.literal_backslash_n_count == 3
    assert diagnostic.has_old_marker is True
    assert diagnostic.has_new_marker is True
    assert diagnostic.has_hunk_marker is True
    assert diagnostic.line_ending_style == "none"
    assert diagnostic.total_length == len(raw)
    assert diagnostic.first_line_hash == text_hash(raw)
    assert diagnostic.payload_hash == text_hash(raw)
    assert raw not in diagnostic.model_dump_json()


def test_micro_report_records_safe_shape_diagnostic_for_m1_failure(tmp_path: Path) -> None:
    policy = MutationTransportMicroPolicy()
    raw = "PATCH\\n--- a/src/pricing.py\\n+++ b/src/pricing.py\\n@@ -1 +1 @@"
    client = _FakeMicroClient({MicroProbeId.M1_SMALL_DIFF: raw})

    report = MutationTransportMicroCertificationRunner(policy=policy, model_client=client).run(
        output_root=tmp_path / "micro",
        expected_policy_hash=policy.policy_hash(),
        probe_ids=[MicroProbeId.M1_SMALL_DIFF],
    )

    result = report.results[0]
    assert result.status is MicroProbeStatus.FAILED
    assert result.shape_diagnostic is not None
    assert result.shape_diagnostic.literal_backslash_n_count == 3
    assert result.shape_diagnostic.true_newline_count == 0
    report_text = (tmp_path / "micro" / "mutation_transport_micro_certification_report.json").read_text(
        encoding="utf-8"
    )
    assert raw not in report_text
    assert "literal_backslash_n_count" in report_text


def test_micro_report_records_safe_channel_diagnostic_without_raw_reasoning(tmp_path: Path) -> None:
    policy = MutationTransportMicroPolicy()
    raw = "PATCH"
    raw_reasoning = "private hidden patch reasoning that must never be written"
    client = _FakeMicroClient(
        {MicroProbeId.M1_SMALL_DIFF: raw},
        metadata_by_probe={
            MicroProbeId.M1_SMALL_DIFF: {
                "reasoning_present": True,
                "reasoning_hash": text_hash(raw_reasoning),
                "reasoning_char_count": len(raw_reasoning),
                "reasoning_token_count": 315,
            }
        },
    )

    report = MutationTransportMicroCertificationRunner(policy=policy, model_client=client).run(
        output_root=tmp_path / "micro",
        expected_policy_hash=policy.policy_hash(),
        probe_ids=[MicroProbeId.M1_SMALL_DIFF],
    )

    result = report.results[0]
    assert result.status is MicroProbeStatus.FAILED
    assert result.failure_category == "MODEL_PROVIDER_OUTPUT_CHANNEL_BEHAVIOR"
    assert result.failure_scope == "PROVIDER_SPECIFIC"
    assert result.channel_diagnostic is not None
    assert result.channel_diagnostic.visible_content_char_count == 5
    assert result.channel_diagnostic.visible_content_estimated_tokens == 2
    assert result.channel_diagnostic.reasoning_present is True
    assert result.channel_diagnostic.reasoning_hash == text_hash(raw_reasoning)
    assert result.channel_diagnostic.reasoning_char_count == len(raw_reasoning)
    assert result.channel_diagnostic.reasoning_token_count == 315
    report_text = (tmp_path / "micro" / "mutation_transport_micro_certification_report.json").read_text(
        encoding="utf-8"
    )
    assert raw_reasoning not in report_text
    assert "private hidden patch reasoning" not in report_text
    assert "reasoning_hash" in report_text


def _small_patch() -> str:
    return "\n".join(
        [
            "PATCH",
            "--- a/src/pricing.py",
            "+++ b/src/pricing.py",
            "@@ -1,2 +1,2 @@",
            " def double(amount: int) -> int:",
            "-    return amount",
            "+    return amount * 2",
        ]
    )


def _unsafe_patch() -> str:
    return "\n".join(
        [
            "PATCH",
            "--- a/src/pricing.py",
            "+++ b/src/pricing.py",
            "@@ -1,2 +1,3 @@",
            " def double(amount: int) -> int:",
            "+API_KEY = 'sk-test-micro-secret-1234567890'",
            "-    return amount",
            "+    return amount * 2",
        ]
    )
