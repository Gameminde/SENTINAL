from __future__ import annotations

import inspect

from sentinel.agent.organs import browser_preparation_organ_v1 as browser_preparation
from sentinel.agent.organs import browser_readonly_organ_v1 as browser_readonly
from sentinel.agent.organs import browser_semantic_extraction_organ_v1 as browser_semantic
from sentinel.agent.organs import local_artifact_executor as l2_executor
from sentinel.agent.organs import low_risk_finalgate
from sentinel.agent.organs import reversible_workspace_executor as l3_executor
from sentinel.agent.organs import runtime_execution
from sentinel.agent.organs.delegated_action_gate import validate_delegated_action_gate_payload
from sentinel.agent.organs.local_artifact_executor import validate_l2_local_artifact_payload
from sentinel.agent.organs.low_risk_finalgate import validate_low_risk_finalgate_payload
from sentinel.agent.organs.reversible_workspace_executor import validate_l3_workspace_payload
from sentinel.agent.organs.runtime_execution import validate_organ_runtime_execution_payload
from sentinel.agent.organs.safety_scanner import (
    DOWNSTREAM_DANGEROUS_FORBIDDEN_KEYS,
    OrganSafetyScanCategory,
    SHARED_SECRET_LIKE_PATTERN,
    scan_forbidden_payload_categorized,
    scan_forbidden_payload_flat,
    scan_forbidden_external_surfaces,
    scan_provider_override,
    scan_secret_like_text,
)


def test_flat_scanner_returns_list() -> None:
    result = scan_forbidden_payload_flat({"execute_now": True})

    assert isinstance(result, list)
    assert result == ["$.execute_now"]


def test_categorized_scanner_returns_dict() -> None:
    result = scan_forbidden_payload_categorized({"provider_override": "auto"})

    assert isinstance(result, dict)
    assert isinstance(result[OrganSafetyScanCategory.ALL.value], list)
    assert result[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value] == ["$.provider_override"]


def test_no_same_name_conflicting_scanner_return_types() -> None:
    import sentinel.agent.organs.safety_scanner as safety_scanner

    functions = {
        name: obj
        for name, obj in inspect.getmembers(safety_scanner, inspect.isfunction)
        if name.startswith("scan_forbidden_payload")
    }

    assert set(functions) == {"scan_forbidden_payload_categorized", "scan_forbidden_payload_flat"}
    assert isinstance(scan_forbidden_payload_flat({"api_call": True}), list)
    assert isinstance(scan_forbidden_payload_categorized({"api_call": True}), dict)


def test_secret_like_pattern_detects_bearer_and_provider_keys_without_echoing_secret() -> None:
    bearer = "Bearer " + "A" * 16
    provider_key = "sk-or-v1-" + "abcdefghijklmnop"

    assert SHARED_SECRET_LIKE_PATTERN.search(bearer)
    assert SHARED_SECRET_LIKE_PATTERN.search(provider_key)
    assert scan_secret_like_text(bearer, path="$.authorization") == ["$.authorization"]
    assert scan_secret_like_text(provider_key, path="$.token") == ["$.token"]
    assert bearer not in scan_forbidden_payload_flat({"authorization": bearer})
    assert provider_key not in scan_forbidden_payload_flat({"token": provider_key})


def test_provider_backend_model_override_detected_consistently() -> None:
    payload = {"provider_override": "auto", "nested": {"backend_override": True, "model_override": "x"}}

    paths = scan_provider_override(payload)
    categorized = scan_forbidden_payload_categorized(payload)

    assert paths == ["$.provider_override", "$.nested.backend_override", "$.nested.model_override"]
    assert categorized[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value] == paths


def test_authority_expansion_detected_consistently() -> None:
    categorized = scan_forbidden_payload_categorized(
        {"authority_expansion": True, "mission_envelope_expansion": True, "delegated_lane_creation": True}
    )

    assert categorized[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value] == [
        "$.authority_expansion",
        "$.mission_envelope_expansion",
        "$.delegated_lane_creation",
    ]


def test_external_network_api_call_send_now_detected_at_gate() -> None:
    safety = validate_delegated_action_gate_payload(
        {"external_network": True, "api_call": True, "network_call": True, "send_now": True}
    )

    assert safety.valid is False
    assert set(safety.rejected_paths) == {
        "$.external_network",
        "$.api_call",
        "$.network_call",
        "$.send_now",
    }


def test_gate_forbidden_keys_are_superset_of_downstream_dangerous_keys() -> None:
    missed: list[str] = []
    for key in sorted(DOWNSTREAM_DANGEROUS_FORBIDDEN_KEYS):
        safety = validate_delegated_action_gate_payload({key: True})
        if safety.valid:
            missed.append(key)

    assert missed == []


def test_l2_uses_shared_scanner_and_blocks_external_network() -> None:
    assert l2_executor.scan_forbidden_payload_flat is scan_forbidden_payload_flat

    safety = validate_l2_local_artifact_payload({"metadata": {"external_network": "https://example.invalid"}})

    assert safety.valid is False
    assert "$.metadata.external_network" in safety.rejected_paths


def test_l3_uses_shared_scanner_and_blocks_api_call() -> None:
    assert l3_executor.scan_forbidden_payload_flat is scan_forbidden_payload_flat

    safety = validate_l3_workspace_payload({"metadata": {"api_call": {"method": "POST"}}})

    assert safety.valid is False
    assert "$.metadata.api_call" in safety.rejected_paths


def test_runtime_execution_uses_categorized_scanner() -> None:
    assert runtime_execution.scan_forbidden_payload_categorized is scan_forbidden_payload_categorized

    safety = validate_organ_runtime_execution_payload({"metadata": {"provider_override": "auto", "api_call": True}})

    assert safety.valid is False
    assert safety.provider_override_paths == ["$.metadata.provider_override"]
    assert safety.forbidden_surface_paths == ["$.metadata.api_call"]


def test_finalgate_uses_categorized_scanner() -> None:
    assert low_risk_finalgate.scan_forbidden_payload_categorized is scan_forbidden_payload_categorized

    safety = validate_low_risk_finalgate_payload({"receipt": {"model_override": "other", "browser_submit": True}})

    assert safety.valid is False
    assert safety.provider_override_paths == ["$.receipt.model_override"]
    assert safety.forbidden_surface_paths == ["$.receipt.browser_submit"]


def test_browser_organs_detect_browser_submit_login_upload_download() -> None:
    payload = {
        "browser_submit": True,
        "browser_login": True,
        "upload_file": True,
        "download_file": True,
    }

    for module in (browser_readonly, browser_preparation, browser_semantic):
        safety = module.validate_browser_readonly_payload(payload) if module is browser_readonly else (
            module.validate_browser_preparation_payload(payload)
            if module is browser_preparation
            else module.validate_browser_semantic_extraction_payload(payload)
        )
        assert safety.valid is False
        assert safety.forbidden_surface_paths


def test_safe_negative_control_keys_do_not_false_positive_when_benign() -> None:
    payload = {
        "forbidden_substeps": ["api_call", "network_call", "send_now", "browser_submit"],
        "forbidden_action_classes": ["browser_login", "upload_file", "download_file"],
    }

    assert scan_forbidden_payload_flat(payload) == []


def test_browser_session_action_terms_do_not_false_positive_but_session_key_still_blocks() -> None:
    safe_payload = {
        "mission_id": "mission_browser_session_live",
        "allowed_tools": ["browser_session_l5_live"],
        "allowed_actions": ["browser_session_open", "browser_session_observe", "browser_session_interact", "browser_session_close"],
    }

    assert scan_forbidden_payload_flat(safe_payload) == []
    assert scan_forbidden_payload_flat({"session": {"cookie": "opaque-ref-only"}}) == ["$.session", "$.session.cookie"]


def test_scanner_results_are_deterministic() -> None:
    payload = {"metadata": {"api_call": True, "provider_override": "auto", "token": "Bearer " + "A" * 16}}

    first = scan_forbidden_payload_categorized(payload)
    second = scan_forbidden_payload_categorized(payload)
    surfaces = scan_forbidden_external_surfaces(payload)

    assert first == second
    assert surfaces == ["$.metadata.api_call"]
