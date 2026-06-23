from __future__ import annotations

import pytest

from sentinel.operator.model_decision_extractor import (
    ModelDecisionExtractionError,
    extract_read_only_decision_payload,
)


@pytest.mark.parametrize(
    ("raw", "expected_action", "expected_arguments"),
    [
        ({"action": "list_directory", "arguments": {"path": "."}}, "list_directory", {"path": "."}),
        ({"tool": "list_directory", "params": {"path": "."}}, "list_directory", {"path": "."}),
        (
            {"tool_name": "search_text", "args": {"query": "register", "path": "."}},
            "search_text",
            {"query": "register", "path": "."},
        ),
        (
            {"next_step": {"name": "list_directory", "input": {"path": "."}}},
            "list_directory",
            {"path": "."},
        ),
        (
            {"function": {"name": "read_file_segment", "arguments": {"path": "src/app.py", "start_line": 1}}},
            "read_file_segment",
            {"path": "src/app.py", "start_line": 1},
        ),
    ],
)
def test_pack3_13_extracts_common_model_dialects(
    raw: dict[str, object],
    expected_action: str,
    expected_arguments: dict[str, object],
) -> None:
    extraction = extract_read_only_decision_payload(raw)

    assert extraction.payload["action"] == expected_action
    assert extraction.payload["arguments"] == expected_arguments
    assert extraction.payload["evidence_refs"] == []


def test_pack3_13_ignores_safe_metadata_and_sanitized_diagnostic_labels() -> None:
    extraction = extract_read_only_decision_payload(
        {
            "action": "list_directory",
            "arguments": {"path": "."},
            "evidence_refs": [],
            "operator_message": "Inspect root.",
            "finish_reason": "stop",
            "visible_content_char_count": 141,
            "diagnostic_label_hash:05763843d85a01fe39c833dde0246e733d28a1174e7e4a31e9437eaf01f314ef": 12,
        }
    )

    assert extraction.payload == {
        "action": "list_directory",
        "arguments": {"path": "."},
        "evidence_refs": [],
        "operator_message": "Inspect root.",
    }
    assert extraction.diagnostics["extraction_failed"] is False
    assert "diagnostic_label_hash:05763843d85a01fe39c833dde0246e733d28a1174e7e4a31e9437eaf01f314ef" in (
        extraction.diagnostics["ignored_safe_metadata_field_names"]
    )


@pytest.mark.parametrize(
    "raw",
    [
        {"action": "write_file", "arguments": {"path": "README.md"}},
        {"tool": "shell", "params": {"command": "dir"}},
        {"action": "list_directory", "arguments": {"path": "."}, "credential_access": True},
        {"action": "list_directory", "arguments": {"path": "."}, "workspace_ref": "workspace:/tmp"},
        {"action": "list_directory", "arguments": {"path": "."}, "model_contract_ref": "model_contract:x"},
        {"action": "list_directory", "arguments": {"path": "."}, "can_execute": True},
        {"action": "list_directory", "arguments": {"path": "."}, "reasoning_content": "hidden"},
        {"action": "list_directory", "arguments": {"path": "."}, "raw_response": "raw"},
    ],
)
def test_pack3_13_rejects_unsafe_actions_and_control_fields(raw: dict[str, object]) -> None:
    with pytest.raises(ModelDecisionExtractionError) as raised:
        extract_read_only_decision_payload(raw)

    diagnostics = raised.value.diagnostics
    assert diagnostics["extraction_failed"] is True
    assert diagnostics["unsafe_field_names"] or diagnostics["unsafe_action_names"]
    assert "hidden" not in str(diagnostics)
    assert "raw" not in str(diagnostics)


def test_pack3_13_missing_action_fails_with_safe_diagnostics() -> None:
    with pytest.raises(ModelDecisionExtractionError) as raised:
        extract_read_only_decision_payload({"arguments": {"path": "."}, "provider_response_hash": "hash_missing"})

    diagnostics = raised.value.diagnostics
    assert diagnostics["extraction_failed"] is True
    assert "action" in diagnostics["missing_required_canonical_fields"]
    assert diagnostics["provider_response_hash"] == "hash_missing"


def test_pack3_13_missing_arguments_allowed_for_empty_argument_actions_only() -> None:
    list_directory = extract_read_only_decision_payload({"action": "list_directory"})
    finish_exploration = extract_read_only_decision_payload({"action": "finish_exploration"})

    assert list_directory.payload["arguments"] == {}
    assert finish_exploration.payload["arguments"] == {}

    with pytest.raises(ModelDecisionExtractionError) as raised:
        extract_read_only_decision_payload({"action": "search_text"})
    assert "arguments" in raised.value.diagnostics["missing_required_canonical_fields"]
