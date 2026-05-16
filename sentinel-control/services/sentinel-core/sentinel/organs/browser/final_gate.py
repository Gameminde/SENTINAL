"""Browser organ FinalGate checks module.

Task 5.2-C3 (Browser Legacy Consolidation, Wave C3 — FinalGate ownership
finalized).

This module OWNS the 14 browser-specific :class:`CoreGateCheck` entries
previously held by ``sentinel.agent.final_gate.CoreFinalGate``. Wave C
introduced the parity wrapper; Wave C2 swapped the default registry;
Wave C3 (this file) physically moved the check bodies and their
browser-specific helpers into the organ package. No delegation to
``CoreFinalGate`` remains.

Byte-equivalence with the legacy
:class:`sentinel.agent.final_gate_registry.BrowserChecksModule` is
preserved: same 14 check names in the same order, with identical
``CoreGateCheck`` payloads (``name``, ``kind``, ``passed``, ``message``,
``details``). The parity tests in
``tests/test_browser_organ_final_gate.py`` enforce this.

Organ-layering contract
-----------------------
* This module MUST NOT import from ``sentinel.agent.browser.*`` — the
  legacy browser surface is not in the organ layer. AST-enforced by
  ``test_browser_organ_final_gate_uses_no_agent_browser_imports``.
* This module MUST NOT import the :class:`CoreFinalGate` class.
  AST-enforced by
  ``test_browser_organ_final_gate_does_not_import_core_final_gate``.
  Importing sibling types :class:`CoreGateCheck` and
  :class:`CoreGateCheckKind` from ``sentinel.agent.final_gate`` is
  allowed — those are the shared pydantic result types that every
  FinalGate module emits, not part of ``CoreFinalGate``'s private
  browser surface.
* Hash/constant imports flow from ``sentinel.organs.browser.*`` (Tasks
  5.2-A/B migrated the underlying modules).

Wave D dependency note
----------------------
Wave D3 migrated ``sentinel.agent.browser.interaction_execution`` into
``sentinel.organs.browser.interaction_execution``. The frozenset
:data:`P3H_ALLOWED_EXECUTION_INTENT_VALUES` below is now a direct
derivation from the organ-side ``P3H_ALLOWED_EXECUTION_INTENTS``
constant; the earlier Wave C3 duplicate has been eliminated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Sibling types only — NOT the CoreFinalGate class. These are the shared
# pydantic result types emitted by every FinalGate module.
from sentinel.agent.final_gate import CoreGateCheck, CoreGateCheckKind
from sentinel.organs.browser.cdp_ax import verify_cdp_ax_tree_hash
from sentinel.organs.browser.dom_snapshot import verify_dom_snapshot_hash
from sentinel.organs.browser.interaction_dry_run import (
    P3G_FORBIDDEN_INTERACTION_NAMES,
    verify_browser_interaction_plan_hash,
)
from sentinel.organs.browser.observability import verify_browser_network_ledger_hash
from sentinel.organs.browser.ui_observation import verify_ui_observation_hash
from sentinel.organs.browser.visual_observation import verify_visual_observation_hash
from sentinel.shared.events import AgentEventType

if TYPE_CHECKING:
    from pathlib import Path

    from sentinel.agent.models import AgentRunResult


# ---------------------------------------------------------------------------
# P3H allowed-intent values. Post-Wave-D3 these derive from the
# organ-side executor's ``P3H_ALLOWED_EXECUTION_INTENTS`` frozenset.
# ---------------------------------------------------------------------------
from sentinel.organs.browser.interaction_execution import (  # noqa: E402
    P3H_ALLOWED_EXECUTION_INTENTS as _P3H_ALLOWED_EXECUTION_INTENTS,
)

P3H_ALLOWED_EXECUTION_INTENT_VALUES: frozenset[str] = frozenset(
    intent.value if hasattr(intent, "value") else intent
    for intent in _P3H_ALLOWED_EXECUTION_INTENTS
)


# ---------------------------------------------------------------------------
# Private helpers — copied verbatim from the cognitive-layer CoreFinalGate
# module. They are browser-specific (except for _enum_value/_list_len
# which are trivial one-liners duplicated here to avoid a cross-layer
# import for two lines of code).
# ---------------------------------------------------------------------------


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else -1


def _accepted_compiled_event_ids(result: "AgentRunResult") -> set[str]:
    return {
        event.id
        for event in result.trace
        if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
    }


def _artifact_events_by_id(result: "AgentRunResult") -> dict[str, Any]:
    return {
        str(event.payload.get("artifact_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
    }


def _check_basic_v3_event(payload: dict[str, Any], event: Any, compiled_events: set[str], errors: list[str], prefix: str) -> None:
    event_id = event.id
    if not payload.get("authority_grant_id"):
        errors.append(f"{prefix}_missing_grant_{event_id}")
    if not payload.get("context_pack_id"):
        errors.append(f"{prefix}_missing_context_pack_{event_id}")
    compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
    if not compiled_trace_id:
        errors.append(f"{prefix}_missing_compiled_intent_{event_id}")
    elif event.event_type.name.endswith("REJECTED") or str(event.event_type).endswith("_rejected"):
        return
    elif compiled_trace_id not in compiled_events:
        errors.append(f"{prefix}_compiled_intent_missing_{event_id}")
    elif compiled_trace_id not in event.trace_refs:
        errors.append(f"{prefix}_compiled_trace_ref_missing_{event_id}")
    if not payload.get("receipt_id") and not (event.event_type.name.endswith("REJECTED") or str(event.event_type).endswith("_rejected")):
        errors.append(f"{prefix}_missing_receipt_{event_id}")


def _check_artifact_pair(
    artifact_id: Any,
    expected_hash: Any,
    event: Any,
    artifact_events: dict[str, Any],
    errors: list[str],
    prefix: str,
) -> None:
    event_id = event.id
    artifact_id = str(artifact_id or "")
    if not artifact_id:
        errors.append(f"{prefix}_missing_artifact_{event_id}")
        return
    artifact_event = artifact_events.get(artifact_id)
    if artifact_event is None:
        errors.append(f"{prefix}_artifact_event_missing_{event_id}")
        return
    if artifact_event.sequence >= event.sequence:
        errors.append(f"{prefix}_artifact_order_invalid_{event_id}")
    if expected_hash and artifact_event.payload.get("sha256") != expected_hash:
        errors.append(f"{prefix}_artifact_hash_mismatch_{event_id}")


def _check_no_credential_payload(payload: dict[str, Any], errors: list[str], code: str) -> None:
    forbidden = ("password", "secret", "token", "credential_value", "cookie_value")

    def visit(value: Any) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                if any(marker in str(key).lower() for marker in forbidden):
                    return True
                if visit(item):
                    return True
        elif isinstance(value, list):
            return any(visit(item) for item in value)
        elif isinstance(value, str):
            lowered = value.lower()
            return any(marker in lowered for marker in ("password=", "bearer ", "secret=", "cookie:"))
        return False

    if visit(payload):
        errors.append(code)


def _browser_lifecycle_check_url_policy(
    *,
    event: Any,
    url_events: dict[str, Any],
    url_trace_id: str,
    expected_final_url: str | None,
    errors: list[str],
    prefix: str,
    require_allowed: bool = True,
) -> None:
    event_id = event.id
    if not url_trace_id:
        errors.append(f"{prefix}_missing_url_policy_{event_id}")
        return
    url_event = url_events.get(url_trace_id)
    if url_event is None:
        errors.append(f"{prefix}_url_policy_missing_{event_id}")
        return
    if url_event.sequence >= event.sequence:
        errors.append(f"{prefix}_url_policy_order_invalid_{event_id}")
    if url_trace_id not in event.trace_refs:
        errors.append(f"{prefix}_missing_url_trace_ref_{event_id}")
    if require_allowed and str(_enum_value(url_event.payload.get("status")) or "").lower() != "allowed":
        errors.append(f"{prefix}_url_policy_not_allowed_{event_id}")
    if expected_final_url is not None and url_event.payload.get("final_url") != expected_final_url:
        errors.append(f"{prefix}_url_policy_final_url_mismatch_{event_id}")


def _browser_v25_boundary_errors(payload: dict[str, Any], event_id: str, errors: list[str]) -> None:
    if payload.get("stateless_public") is not True:
        errors.append(f"browser_v25_not_stateless_{event_id}")
    if payload.get("cookies_enabled") is not False:
        errors.append(f"browser_v25_cookies_enabled_{event_id}")
    if payload.get("storage_enabled") is not False:
        errors.append(f"browser_v25_storage_enabled_{event_id}")
    if payload.get("js_enabled") is not False:
        errors.append(f"browser_v25_js_enabled_{event_id}")
    if payload.get("downloads_enabled") is not False:
        errors.append(f"browser_v25_downloads_enabled_{event_id}")


# ---------------------------------------------------------------------------
# Check 1 / 14: browser_capability_receipts
# ---------------------------------------------------------------------------


def _check_browser_capability_receipts(result: "AgentRunResult") -> CoreGateCheck:
    url_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.BROWSER_URL_CLASSIFIED
    }
    policy_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.TOOL_POLICY_DECIDED
    }
    capture_events = {
        event.id: event
        for event in result.trace
        if event.event_type
        in {
            AgentEventType.BROWSER_EVIDENCE_COLLECTED,
            AgentEventType.BROWSER_SNAPSHOT_CAPTURED,
            AgentEventType.BROWSER_INTERACTION_EXECUTED,
            AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED,
            AgentEventType.BROWSER_DOWNLOAD_QUARANTINED,
            AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED,
            AgentEventType.BROWSER_PRIVATE_SESSION_STARTED,
            AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED,
            AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED,
            AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED,
            AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED,
            AgentEventType.BROWSER_HAR_BODY_CAPTURED,
        }
    }
    artifact_events = {
        str(event.payload.get("artifact_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
    }
    errors: list[str] = []

    for event_id, event in capture_events.items():
        payload = event.payload
        receipt_id = payload.get("receipt_id")
        url_trace_id = payload.get("url_policy_trace_id")
        if not receipt_id:
            errors.append(f"browser_event_missing_receipt_{event_id}")
        no_url_policy_required = {
            AgentEventType.BROWSER_INTERACTION_EXECUTED,
            AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED,
            AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED,
            AgentEventType.BROWSER_PRIVATE_SESSION_STARTED,
            AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED,
            AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED,
            AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED,
            AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED,
            AgentEventType.BROWSER_HAR_BODY_CAPTURED,
        }
        if event.event_type in no_url_policy_required:
            url_trace_id = None
        elif not url_trace_id or url_trace_id not in url_events:
            errors.append(f"browser_event_missing_url_policy_{event_id}")
        elif url_trace_id:
            url_event = url_events[url_trace_id]
            if url_trace_id not in event.trace_refs:
                errors.append(f"browser_event_missing_url_trace_ref_{event_id}")
            if url_event.sequence >= event.sequence:
                errors.append(f"browser_event_url_policy_order_invalid_{event_id}")

        artifact_pairs: list[tuple[str, str | None]] = []
        if event.event_type == AgentEventType.BROWSER_EVIDENCE_COLLECTED:
            artifact_pairs.append((str(payload.get("artifact_id") or ""), payload.get("artifact_sha256")))
        elif event.event_type == AgentEventType.BROWSER_SNAPSHOT_CAPTURED:
            artifact_pairs.append((str(payload.get("snapshot_artifact_id") or ""), payload.get("snapshot_artifact_sha256")))
            if payload.get("screenshot_artifact_id"):
                artifact_pairs.append((str(payload.get("screenshot_artifact_id") or ""), payload.get("screenshot_artifact_sha256")))
            if payload.get("pdf_artifact_id"):
                artifact_pairs.append((str(payload.get("pdf_artifact_id") or ""), payload.get("pdf_artifact_sha256")))
            if not payload.get("accessibility_snapshot_sha256"):
                errors.append(f"browser_snapshot_missing_accessibility_hash_{event_id}")
            if not payload.get("accessibility_page_sha256"):
                errors.append(f"browser_snapshot_missing_accessibility_page_hash_{event_id}")
            if not isinstance(payload.get("accessibility_ref_count"), int):
                errors.append(f"browser_snapshot_invalid_accessibility_ref_count_{event_id}")
            if not isinstance(payload.get("accessibility_interactive_count"), int):
                errors.append(f"browser_snapshot_invalid_accessibility_interactive_count_{event_id}")
            if not isinstance(payload.get("accessibility_ref_ids"), list):
                errors.append(f"browser_snapshot_invalid_accessibility_ref_ids_{event_id}")
            screenshot_metadata = payload.get("screenshot_metadata")
            if payload.get("screenshot_artifact_id") and not isinstance(screenshot_metadata, dict):
                errors.append(f"browser_snapshot_invalid_screenshot_metadata_{event_id}")
            elif payload.get("screenshot_artifact_id"):
                if not isinstance(screenshot_metadata.get("normalized"), bool):
                    errors.append(f"browser_snapshot_invalid_screenshot_normalized_{event_id}")
                if not isinstance(screenshot_metadata.get("bytes"), int):
                    errors.append(f"browser_snapshot_invalid_screenshot_bytes_{event_id}")
                if not screenshot_metadata.get("content_type"):
                    errors.append(f"browser_snapshot_missing_screenshot_content_type_{event_id}")
            pdf_metadata = payload.get("pdf_metadata")
            if payload.get("pdf_artifact_id"):
                if not isinstance(pdf_metadata, dict):
                    errors.append(f"browser_snapshot_invalid_pdf_metadata_{event_id}")
                else:
                    if pdf_metadata.get("content_type") != "application/pdf":
                        errors.append(f"browser_snapshot_pdf_content_type_invalid_{event_id}")
                    if not isinstance(pdf_metadata.get("bytes"), int):
                        errors.append(f"browser_snapshot_pdf_bytes_invalid_{event_id}")
            element_screenshots = payload.get("element_screenshot_artifacts")
            if element_screenshots is None:
                element_screenshots = []
            if not isinstance(element_screenshots, list):
                errors.append(f"browser_snapshot_element_screenshots_invalid_{event_id}")
                element_screenshots = []
            for item_index, item in enumerate(element_screenshots):
                if not isinstance(item, dict):
                    errors.append(f"browser_snapshot_element_screenshot_invalid_{event_id}_{item_index}")
                    continue
                artifact_pairs.append((str(item.get("artifact_id") or ""), item.get("artifact_sha256")))
                if not item.get("ref_id"):
                    errors.append(f"browser_snapshot_element_screenshot_missing_ref_{event_id}_{item_index}")
                item_meta = item.get("screenshot_metadata")
                if not isinstance(item_meta, dict):
                    errors.append(f"browser_snapshot_element_screenshot_metadata_invalid_{event_id}_{item_index}")
                elif not isinstance(item_meta.get("normalized"), bool):
                    errors.append(f"browser_snapshot_element_screenshot_normalized_invalid_{event_id}_{item_index}")
            network_ledger = payload.get("network_ledger")
            network_ledger_sha256 = payload.get("network_ledger_sha256")
            if not network_ledger_sha256:
                errors.append(f"browser_snapshot_missing_network_ledger_hash_{event_id}")
            if not isinstance(network_ledger, dict):
                errors.append(f"browser_snapshot_missing_network_ledger_{event_id}")
            elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                errors.append(f"browser_snapshot_network_ledger_hash_mismatch_{event_id}")
            elif (
                payload.get("network_request_count") != _list_len(network_ledger.get("requests", []))
                or payload.get("network_response_count") != _list_len(network_ledger.get("responses", []))
                or payload.get("network_failure_count") != _list_len(network_ledger.get("failures", []))
                or payload.get("console_message_count") != _list_len(network_ledger.get("console", []))
                or payload.get("page_error_count") != _list_len(network_ledger.get("page_errors", []))
            ):
                errors.append(f"browser_snapshot_network_ledger_count_mismatch_{event_id}")
            for field_name in (
                "network_request_count",
                "network_response_count",
                "network_failure_count",
                "console_message_count",
                "page_error_count",
            ):
                if not isinstance(payload.get(field_name), int):
                    errors.append(f"browser_snapshot_invalid_{field_name}_{event_id}")
            if not isinstance(payload.get("network_ledger_truncated"), bool):
                errors.append(f"browser_snapshot_invalid_network_ledger_truncated_{event_id}")
            if not isinstance(payload.get("browser_health"), dict):
                errors.append(f"browser_snapshot_invalid_browser_health_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_INTERACTION_EXECUTED:
            artifact_pairs.append((str(payload.get("after_snapshot_artifact_id") or ""), payload.get("after_snapshot_artifact_sha256")))
            artifact_pairs.append((str(payload.get("after_screenshot_artifact_id") or ""), payload.get("after_screenshot_artifact_sha256")))
            if not payload.get("plan_trace_event_id"):
                errors.append(f"browser_interaction_missing_plan_trace_{event_id}")
            if not payload.get("before_snapshot_trace_event_id"):
                errors.append(f"browser_interaction_missing_before_snapshot_trace_{event_id}")
            if payload.get("same_origin") is not True:
                errors.append(f"browser_interaction_not_same_origin_{event_id}")
            network_ledger = payload.get("network_ledger")
            network_ledger_sha256 = payload.get("network_ledger_sha256")
            if not network_ledger_sha256:
                errors.append(f"browser_interaction_missing_network_ledger_hash_{event_id}")
            if not isinstance(network_ledger, dict):
                errors.append(f"browser_interaction_missing_network_ledger_{event_id}")
            elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                errors.append(f"browser_interaction_network_ledger_hash_mismatch_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED:
            artifact_pairs.append((str(payload.get("post_submit_snapshot_artifact_id") or ""), payload.get("post_submit_snapshot_artifact_sha256")))
            if payload.get("post_submit_screenshot_artifact_id"):
                artifact_pairs.append((str(payload.get("post_submit_screenshot_artifact_id") or ""), payload.get("post_submit_screenshot_artifact_sha256")))
            if payload.get("authority_class") != "browser_form_submit":
                errors.append(f"browser_form_submit_authority_class_invalid_{event_id}")
            if not payload.get("authority_grant_id"):
                errors.append(f"browser_form_submit_missing_authority_grant_{event_id}")
            if not payload.get("compiled_intent_trace_id"):
                errors.append(f"browser_form_submit_missing_compiled_intent_{event_id}")
            if not payload.get("context_pack_id"):
                errors.append(f"browser_form_submit_missing_context_pack_{event_id}")
            if not payload.get("plan_trace_event_id"):
                errors.append(f"browser_form_submit_missing_plan_trace_{event_id}")
            if not payload.get("before_snapshot_trace_event_id"):
                errors.append(f"browser_form_submit_missing_before_snapshot_trace_{event_id}")
            if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
                errors.append(f"browser_form_submit_cross_origin_not_authorized_{event_id}")
            network_ledger = payload.get("network_ledger")
            network_ledger_sha256 = payload.get("network_ledger_sha256")
            if not network_ledger_sha256:
                errors.append(f"browser_form_submit_missing_network_ledger_hash_{event_id}")
            if not isinstance(network_ledger, dict):
                errors.append(f"browser_form_submit_missing_network_ledger_{event_id}")
            elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                errors.append(f"browser_form_submit_network_ledger_hash_mismatch_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_DOWNLOAD_QUARANTINED:
            artifact_pairs.append((str(payload.get("artifact_id") or ""), payload.get("artifact_sha256")))
            if payload.get("authority_class") != "browser_download_quarantine":
                errors.append(f"browser_download_authority_class_invalid_{event_id}")
            if not payload.get("authority_grant_id"):
                errors.append(f"browser_download_missing_authority_grant_{event_id}")
            if not payload.get("compiled_intent_trace_id"):
                errors.append(f"browser_download_missing_compiled_intent_{event_id}")
            if not payload.get("context_pack_id"):
                errors.append(f"browser_download_missing_context_pack_{event_id}")
            if payload.get("promoted") is not False:
                errors.append(f"browser_download_promoted_in_quarantine_event_{event_id}")
            if payload.get("mime_type_allowed") is not True:
                errors.append(f"browser_download_mime_not_allowed_{event_id}")
            if not isinstance(payload.get("size_bytes"), int) or not isinstance(payload.get("max_bytes"), int):
                errors.append(f"browser_download_invalid_size_metadata_{event_id}")
            elif payload.get("size_bytes") > payload.get("max_bytes"):
                errors.append(f"browser_download_size_exceeds_max_{event_id}")
            if not str(payload.get("quarantine_relative_path") or "").startswith("browser/download_quarantine/"):
                errors.append(f"browser_download_quarantine_path_invalid_{event_id}")
            if not payload.get("download_sha256"):
                errors.append(f"browser_download_missing_download_hash_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED:
            artifact_pairs.append((str(payload.get("source_artifact_id") or ""), payload.get("source_artifact_sha256")))
            artifact_pairs.append((str(payload.get("post_upload_snapshot_artifact_id") or ""), payload.get("post_upload_snapshot_artifact_sha256")))
            if payload.get("post_upload_screenshot_artifact_id"):
                artifact_pairs.append((str(payload.get("post_upload_screenshot_artifact_id") or ""), payload.get("post_upload_screenshot_artifact_sha256")))
            if payload.get("authority_class") != "browser_upload_authorized":
                errors.append(f"browser_upload_authority_class_invalid_{event_id}")
            if not payload.get("authority_grant_id"):
                errors.append(f"browser_upload_missing_authority_grant_{event_id}")
            if not payload.get("compiled_intent_trace_id"):
                errors.append(f"browser_upload_missing_compiled_intent_{event_id}")
            if not payload.get("context_pack_id"):
                errors.append(f"browser_upload_missing_context_pack_{event_id}")
            if not payload.get("plan_trace_event_id"):
                errors.append(f"browser_upload_missing_plan_trace_{event_id}")
            if not payload.get("before_snapshot_trace_event_id"):
                errors.append(f"browser_upload_missing_before_snapshot_trace_{event_id}")
            if not payload.get("source_artifact_id") or not payload.get("source_artifact_sha256"):
                errors.append(f"browser_upload_missing_source_artifact_{event_id}")
            if not payload.get("upload_ref_id"):
                errors.append(f"browser_upload_missing_ref_{event_id}")
            if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
                errors.append(f"browser_upload_cross_origin_not_authorized_{event_id}")
            network_ledger = payload.get("network_ledger")
            network_ledger_sha256 = payload.get("network_ledger_sha256")
            if not network_ledger_sha256:
                errors.append(f"browser_upload_missing_network_ledger_hash_{event_id}")
            if not isinstance(network_ledger, dict):
                errors.append(f"browser_upload_missing_network_ledger_{event_id}")
            elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                errors.append(f"browser_upload_network_ledger_hash_mismatch_{event_id}")
        elif event.event_type in {AgentEventType.BROWSER_PRIVATE_SESSION_STARTED, AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED}:
            artifact_pairs.append((str(payload.get("receipt_artifact_id") or ""), payload.get("receipt_artifact_sha256")))
            if payload.get("authority_class") != "browser_private_session":
                errors.append(f"browser_private_session_authority_class_invalid_{event_id}")
            if not payload.get("session_id") or not payload.get("profile_id"):
                errors.append(f"browser_private_session_missing_session_ids_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED:
            artifact_pairs.append((str(payload.get("post_login_snapshot_artifact_id") or ""), payload.get("post_login_snapshot_artifact_sha256")))
            if payload.get("authority_class") != "browser_login_authority":
                errors.append(f"browser_login_authority_class_invalid_{event_id}")
            if payload.get("login_success") is not True:
                errors.append(f"browser_login_not_successful_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED:
            artifact_pairs.append((str(payload.get("summary_artifact_id") or ""), payload.get("summary_artifact_sha256")))
            if payload.get("authority_class") != "browser_cookie_storage_contract":
                errors.append(f"browser_cookie_storage_authority_class_invalid_{event_id}")
            if payload.get("redaction_applied") is not True or payload.get("raw_value_exposed") is True:
                errors.append(f"browser_cookie_storage_redaction_invalid_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED:
            artifact_pairs.append((str(payload.get("result_artifact_id") or ""), payload.get("result_artifact_sha256")))
            if payload.get("authority_class") != "browser_js_evaluate_sandboxed":
                errors.append(f"browser_js_authority_class_invalid_{event_id}")
            if payload.get("script_hash_allowed") is not True or payload.get("network_calls_blocked") is not True:
                errors.append(f"browser_js_contract_flags_invalid_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_HAR_BODY_CAPTURED:
            artifact_pairs.append((str(payload.get("har_artifact_id") or ""), payload.get("har_artifact_sha256")))
            if payload.get("authority_class") != "browser_har_body_capture":
                errors.append(f"browser_har_authority_class_invalid_{event_id}")
            if payload.get("redaction_applied") is not True:
                errors.append(f"browser_har_redaction_missing_{event_id}")
        for artifact_id, expected_hash in artifact_pairs:
            if not artifact_id:
                errors.append(f"browser_event_missing_artifact_{event_id}")
                continue
            artifact_event = artifact_events.get(artifact_id)
            if artifact_event is None:
                errors.append(f"browser_event_artifact_trace_missing_{event_id}_{artifact_id}")
                continue
            if expected_hash and artifact_event.payload.get("sha256") != expected_hash:
                errors.append(f"browser_event_artifact_hash_mismatch_{event_id}_{artifact_id}")
            if artifact_event.sequence >= event.sequence:
                errors.append(f"browser_event_artifact_order_invalid_{event_id}_{artifact_id}")

    for index, item in enumerate(result.controlled_capability_results):
        if not item.get("accepted") or not item.get("browser_trace_event_id"):
            continue
        browser_trace_event_id = str(item.get("browser_trace_event_id"))
        event = capture_events.get(browser_trace_event_id)
        if event is None:
            errors.append(f"browser_result_trace_missing_{index}")
            continue
        if item.get("trace_event_id") != browser_trace_event_id:
            errors.append(f"browser_result_trace_alias_mismatch_{index}")
        policy_trace_id = str(item.get("policy_trace_id") or "")
        policy_event = policy_events.get(policy_trace_id)
        if policy_event is None:
            errors.append(f"browser_result_policy_trace_missing_{index}")
        else:
            if policy_event.sequence >= event.sequence:
                errors.append(f"browser_result_policy_order_invalid_{index}")
            policy_payload = policy_event.payload
            if policy_payload.get("tool_id") != item.get("tool_id"):
                errors.append(f"browser_result_policy_tool_mismatch_{index}")
            if policy_payload.get("action") != item.get("action"):
                errors.append(f"browser_result_policy_action_mismatch_{index}")
            if policy_payload.get("allowed") is not True:
                errors.append(f"browser_result_policy_not_allowed_{index}")
        if event.payload.get("receipt_id") != item.get("receipt_id"):
            errors.append(f"browser_result_receipt_mismatch_{index}")
        event_artifact_ids = {
            str(value)
            for value in (
                event.payload.get("artifact_id"),
                event.payload.get("snapshot_artifact_id"),
                event.payload.get("screenshot_artifact_id"),
                event.payload.get("pdf_artifact_id"),
                event.payload.get("after_snapshot_artifact_id"),
                event.payload.get("after_screenshot_artifact_id"),
                event.payload.get("post_submit_snapshot_artifact_id"),
                event.payload.get("post_submit_screenshot_artifact_id"),
                event.payload.get("post_upload_snapshot_artifact_id"),
                event.payload.get("post_upload_screenshot_artifact_id"),
                event.payload.get("receipt_artifact_id"),
                event.payload.get("post_login_snapshot_artifact_id"),
                event.payload.get("summary_artifact_id"),
                event.payload.get("result_artifact_id"),
                event.payload.get("har_artifact_id"),
                event.payload.get("source_artifact_id"),
            )
            if value
        }
        for element_item in event.payload.get("element_screenshot_artifacts") or []:
            if isinstance(element_item, dict) and element_item.get("artifact_id"):
                event_artifact_ids.add(str(element_item.get("artifact_id")))
        if not set(item.get("artifact_ids") or []).issubset(event_artifact_ids):
            errors.append(f"browser_result_artifact_mismatch_{index}")
        if not item.get("receipt_id"):
            errors.append(f"browser_result_missing_receipt_{index}")
        if not item.get("artifact_ids"):
            errors.append(f"browser_result_missing_artifacts_{index}")

    return CoreGateCheck(
        name="browser_capability_receipts",
        kind=CoreGateCheckKind.ARTIFACT,
        passed=not errors,
        message="Browser capability events are bound to URL policy, artifacts, and receipts." if not errors else "Browser capability receipt contract failed.",
        details={"errors": errors},
    )



# ---------------------------------------------------------------------------
# Check 2 / 14: browser_interaction_dry_run_contract
# ---------------------------------------------------------------------------


def _check_browser_interaction_dry_run_contract(result: "AgentRunResult") -> CoreGateCheck:
    snapshot_events = [
        event
        for event in result.trace
        if event.event_type == AgentEventType.BROWSER_SNAPSHOT_CAPTURED
    ]
    snapshots_by_hash = {
        str(event.payload.get("accessibility_snapshot_sha256")): event
        for event in snapshot_events
        if event.payload.get("accessibility_snapshot_sha256")
    }
    plan_events = [
        event
        for event in result.trace
        if event.event_type == AgentEventType.BROWSER_INTERACTION_PLAN_CREATED
    ]
    errors: list[str] = []

    for event in result.trace:
        if event.event_type != AgentEventType.CONTROLLED_CAPABILITY_EXECUTED:
            continue
        action = str(event.payload.get("action") or "").lower()
        if action in {
            "browser_click",
            "browser_type",
            "browser_fill",
            "browser_select",
            "browser_press",
            "browser_hover",
            "browser_submit",
            "browser_upload",
            "browser_download",
            "browser_interaction_execute",
        }:
            errors.append(f"browser_real_interaction_event_in_p3g_{event.id}")

    for event in plan_events:
        payload = event.payload
        event_id = event.id
        plan = payload.get("plan")
        plan_sha256 = payload.get("plan_sha256")
        if not payload.get("dry_run_only"):
            errors.append(f"browser_interaction_plan_not_dry_run_{event_id}")
        if not isinstance(plan, dict):
            errors.append(f"browser_interaction_plan_missing_payload_{event_id}")
            continue
        if plan.get("dry_run_only") is not True:
            errors.append(f"browser_interaction_plan_payload_not_dry_run_{event_id}")
        if plan.get("plan_sha256") != plan_sha256:
            errors.append(f"browser_interaction_plan_hash_payload_mismatch_{event_id}")
        if not verify_browser_interaction_plan_hash(plan, str(plan_sha256 or "")):
            errors.append(f"browser_interaction_plan_hash_invalid_{event_id}")

        snapshot_hash = str(plan.get("snapshot_sha256") or "")
        page_hash = str(plan.get("page_sha256") or "")
        snapshot_event = snapshots_by_hash.get(snapshot_hash)
        if snapshot_event is None:
            errors.append(f"browser_interaction_plan_snapshot_missing_{event_id}")
            continue
        if snapshot_event.sequence >= event.sequence:
            errors.append(f"browser_interaction_plan_snapshot_order_invalid_{event_id}")
        if snapshot_event.id not in event.trace_refs:
            errors.append(f"browser_interaction_plan_missing_snapshot_trace_ref_{event_id}")
        if snapshot_event.payload.get("accessibility_page_sha256") != page_hash:
            errors.append(f"browser_interaction_plan_page_hash_mismatch_{event_id}")

        ref_ids = snapshot_event.payload.get("accessibility_ref_ids")
        if not isinstance(ref_ids, list):
            errors.append(f"browser_interaction_plan_snapshot_refs_unavailable_{event_id}")
        else:
            allowed_refs = {str(ref_id) for ref_id in ref_ids}
            for ref_id in plan.get("required_ref_ids", []):
                if str(ref_id) not in allowed_refs:
                    errors.append(f"browser_interaction_plan_unknown_ref_{event_id}_{ref_id}")

        intents = [str(intent).lower() for intent in payload.get("intents", [])]
        plan_steps = plan.get("steps", [])
        if not isinstance(plan_steps, list):
            errors.append(f"browser_interaction_plan_steps_invalid_{event_id}")
            plan_steps = []
        step_intents = [str(step.get("intent", "")).lower() for step in plan_steps if isinstance(step, dict)]
        for intent in [*intents, *step_intents]:
            if intent in P3G_FORBIDDEN_INTERACTION_NAMES:
                errors.append(f"browser_interaction_plan_forbidden_intent_{event_id}_{intent}")
            if any(token in intent for token in P3G_FORBIDDEN_INTERACTION_NAMES):
                errors.append(f"browser_interaction_plan_forbidden_intent_token_{event_id}_{intent}")

    return CoreGateCheck(
        name="browser_interaction_dry_run_contract",
        kind=CoreGateCheckKind.ARTIFACT,
        passed=not errors,
        message="Browser interaction plans are dry-run, snapshot-bound, and ref-verified." if not errors else "Browser interaction dry-run contract failed.",
        details={"errors": errors},
    )


# ---------------------------------------------------------------------------
# Check 3 / 14: browser_interaction_execution_contract
# ---------------------------------------------------------------------------


def _check_browser_interaction_execution_contract(result: "AgentRunResult") -> CoreGateCheck:
    plan_events = {
        str(event.payload.get("plan_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.BROWSER_INTERACTION_PLAN_CREATED and event.payload.get("plan_id")
    }
    snapshot_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.BROWSER_SNAPSHOT_CAPTURED
    }
    artifact_events = {
        str(event.payload.get("artifact_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
    }
    allowed_intents = set(P3H_ALLOWED_EXECUTION_INTENT_VALUES)
    errors: list[str] = []

    for event in result.trace:
        if event.event_type != AgentEventType.BROWSER_INTERACTION_EXECUTED:
            continue
        event_id = event.id
        payload = event.payload
        plan_id = str(payload.get("plan_id") or "")
        plan_sha256 = str(payload.get("plan_sha256") or "")
        plan = payload.get("plan")
        plan_event = plan_events.get(plan_id)
        if plan_event is None:
            errors.append(f"browser_interaction_execution_plan_missing_{event_id}")
        elif plan_event.sequence >= event.sequence:
            errors.append(f"browser_interaction_execution_plan_order_invalid_{event_id}")
        elif plan_event.id not in event.trace_refs:
            errors.append(f"browser_interaction_execution_missing_plan_trace_ref_{event_id}")
        if not isinstance(plan, dict):
            errors.append(f"browser_interaction_execution_plan_payload_missing_{event_id}")
        elif not verify_browser_interaction_plan_hash(plan, plan_sha256):
            errors.append(f"browser_interaction_execution_plan_hash_invalid_{event_id}")
        elif plan_event is not None and plan_event.payload.get("plan_sha256") != plan_sha256:
            errors.append(f"browser_interaction_execution_plan_hash_mismatch_{event_id}")

        before_snapshot_trace = str(payload.get("before_snapshot_trace_event_id") or "")
        before_snapshot_event = snapshot_events.get(before_snapshot_trace)
        if before_snapshot_event is None:
            errors.append(f"browser_interaction_execution_before_snapshot_missing_{event_id}")
        else:
            if before_snapshot_event.sequence >= event.sequence:
                errors.append(f"browser_interaction_execution_before_snapshot_order_invalid_{event_id}")
            if before_snapshot_trace not in event.trace_refs:
                errors.append(f"browser_interaction_execution_missing_before_snapshot_trace_ref_{event_id}")
            if before_snapshot_event.payload.get("accessibility_snapshot_sha256") != payload.get("before_snapshot_sha256"):
                errors.append(f"browser_interaction_execution_before_snapshot_hash_mismatch_{event_id}")
            if before_snapshot_event.payload.get("accessibility_page_sha256") != payload.get("before_page_sha256"):
                errors.append(f"browser_interaction_execution_before_page_hash_mismatch_{event_id}")

        if payload.get("same_origin") is not True:
            errors.append(f"browser_interaction_execution_same_origin_missing_{event_id}")
        if not payload.get("receipt_id"):
            errors.append(f"browser_interaction_execution_receipt_missing_{event_id}")
        if not payload.get("after_snapshot_sha256") or not payload.get("after_page_sha256"):
            errors.append(f"browser_interaction_execution_after_hash_missing_{event_id}")

        intents = [str(intent).lower() for intent in payload.get("executed_intents", [])]
        if not intents:
            errors.append(f"browser_interaction_execution_intents_missing_{event_id}")
        for intent in intents:
            if intent not in allowed_intents:
                errors.append(f"browser_interaction_execution_intent_not_delegated_{event_id}_{intent}")
            if any(token in intent for token in P3G_FORBIDDEN_INTERACTION_NAMES):
                errors.append(f"browser_interaction_execution_forbidden_intent_token_{event_id}_{intent}")

        snapshot_artifact_id = str(payload.get("after_snapshot_artifact_id") or "")
        snapshot_artifact = artifact_events.get(snapshot_artifact_id)
        if snapshot_artifact is None:
            errors.append(f"browser_interaction_execution_after_artifact_missing_{event_id}")
        else:
            if snapshot_artifact.sequence >= event.sequence:
                errors.append(f"browser_interaction_execution_after_artifact_order_invalid_{event_id}")
            if payload.get("after_snapshot_artifact_sha256") != snapshot_artifact.payload.get("sha256"):
                errors.append(f"browser_interaction_execution_after_artifact_hash_mismatch_{event_id}")

        screenshot_artifact_id = str(payload.get("after_screenshot_artifact_id") or "")
        if screenshot_artifact_id:
            screenshot_artifact = artifact_events.get(screenshot_artifact_id)
            if screenshot_artifact is None:
                errors.append(f"browser_interaction_execution_after_screenshot_missing_{event_id}")
            elif payload.get("after_screenshot_artifact_sha256") != screenshot_artifact.payload.get("sha256"):
                errors.append(f"browser_interaction_execution_after_screenshot_hash_mismatch_{event_id}")

        network_ledger = payload.get("network_ledger")
        network_ledger_sha256 = str(payload.get("network_ledger_sha256") or "")
        if not isinstance(network_ledger, dict):
            errors.append(f"browser_interaction_execution_network_ledger_missing_{event_id}")
        elif not verify_browser_network_ledger_hash(network_ledger, network_ledger_sha256):
            errors.append(f"browser_interaction_execution_network_ledger_hash_invalid_{event_id}")

    return CoreGateCheck(
        name="browser_interaction_execution_contract",
        kind=CoreGateCheckKind.ARTIFACT,
        passed=not errors,
        message="Limited browser interactions are plan-bound, authority-traced, and recaptured." if not errors else "Browser interaction execution contract failed.",
        details={"errors": errors},
    )



# ---------------------------------------------------------------------------
# Check 4 / 14: browser_public_lifecycle_contract
# ---------------------------------------------------------------------------


def _check_browser_public_lifecycle_contract(result: "AgentRunResult") -> CoreGateCheck:
    url_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.BROWSER_URL_CLASSIFIED
    }
    sessions: dict[str, dict[str, Any]] = {}
    tabs: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    lifecycle_events = {
        AgentEventType.BROWSER_PUBLIC_SESSION_STARTED,
        AgentEventType.BROWSER_PUBLIC_TAB_OPENED,
        AgentEventType.BROWSER_PUBLIC_TAB_NAVIGATED,
        AgentEventType.BROWSER_PUBLIC_TAB_CLOSED,
        AgentEventType.BROWSER_PUBLIC_SESSION_CLOSED,
        AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED,
    }
    expected_status = {
        AgentEventType.BROWSER_PUBLIC_SESSION_STARTED: "active",
        AgentEventType.BROWSER_PUBLIC_TAB_OPENED: "active",
        AgentEventType.BROWSER_PUBLIC_TAB_NAVIGATED: "active",
        AgentEventType.BROWSER_PUBLIC_TAB_CLOSED: "closed",
        AgentEventType.BROWSER_PUBLIC_SESSION_CLOSED: "closed",
        AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED: "rejected",
    }

    for event in result.trace:
        if event.event_type not in lifecycle_events:
            continue
        payload = event.payload
        event_id = event.id
        if str(_enum_value(payload.get("status")) or "").lower() != expected_status[event.event_type]:
            errors.append(f"browser_public_lifecycle_status_invalid_{event_id}")
        if payload.get("stateless_public") is not True:
            errors.append(f"browser_public_lifecycle_not_stateless_{event_id}")
        if payload.get("cookies_enabled") is not False:
            errors.append(f"browser_public_lifecycle_cookies_enabled_{event_id}")
        if payload.get("storage_enabled") is not False:
            errors.append(f"browser_public_lifecycle_storage_enabled_{event_id}")

        if event.event_type == AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED:
            if not payload.get("action"):
                errors.append(f"browser_public_lifecycle_rejection_missing_action_{event_id}")
            if not payload.get("reason"):
                errors.append(f"browser_public_lifecycle_rejection_missing_reason_{event_id}")
            url_trace_id = str(payload.get("url_policy_trace_id") or "")
            if url_trace_id:
                _browser_lifecycle_check_url_policy(
                    event=event,
                    url_events=url_events,
                    url_trace_id=url_trace_id,
                    expected_final_url=None,
                    errors=errors,
                    prefix="browser_public_lifecycle_rejection",
                    require_allowed=False,
                )
            continue

        if not payload.get("receipt_id"):
            errors.append(f"browser_public_lifecycle_missing_receipt_{event_id}")

        if event.event_type == AgentEventType.BROWSER_PUBLIC_SESSION_STARTED:
            session_id = str(payload.get("session_id") or "")
            if not session_id:
                errors.append(f"browser_public_session_missing_id_{event_id}")
                continue
            if session_id in sessions:
                errors.append(f"browser_public_session_duplicate_{event_id}_{session_id}")
                continue
            max_tabs = payload.get("max_tabs")
            if not isinstance(max_tabs, int) or max_tabs < 1:
                errors.append(f"browser_public_session_invalid_max_tabs_{event_id}")
                max_tabs = 0
            sessions[session_id] = {
                "status": "active",
                "max_tabs": max_tabs,
                "active_tabs": set(),
                "sequence": event.sequence,
            }

        elif event.event_type == AgentEventType.BROWSER_PUBLIC_TAB_OPENED:
            session_id = str(payload.get("session_id") or "")
            tab_id = str(payload.get("tab_id") or "")
            session = sessions.get(session_id)
            if session is None:
                errors.append(f"browser_public_tab_open_session_missing_{event_id}")
                continue
            if session["status"] != "active":
                errors.append(f"browser_public_tab_open_session_closed_{event_id}")
            active_tabs = session["active_tabs"]
            if len(active_tabs) >= int(session["max_tabs"]):
                errors.append(f"browser_public_tab_open_limit_exceeded_{event_id}")
            if not tab_id:
                errors.append(f"browser_public_tab_open_missing_tab_id_{event_id}")
                continue
            if tab_id in tabs:
                errors.append(f"browser_public_tab_duplicate_{event_id}_{tab_id}")
                continue
            final_url = str(payload.get("final_url") or "")
            url_trace_id = str(payload.get("url_policy_trace_id") or "")
            _browser_lifecycle_check_url_policy(
                event=event,
                url_events=url_events,
                url_trace_id=url_trace_id,
                expected_final_url=final_url,
                errors=errors,
                prefix="browser_public_tab_open",
            )
            tabs[tab_id] = {
                "session_id": session_id,
                "status": "active",
                "current_url": final_url,
                "navigation_count": int(payload.get("navigation_count") or 0),
                "sequence": event.sequence,
            }
            active_tabs.add(tab_id)

        elif event.event_type == AgentEventType.BROWSER_PUBLIC_TAB_NAVIGATED:
            session_id = str(payload.get("session_id") or "")
            tab_id = str(payload.get("tab_id") or "")
            session = sessions.get(session_id)
            tab = tabs.get(tab_id)
            if session is None:
                errors.append(f"browser_public_tab_nav_session_missing_{event_id}")
                continue
            if session["status"] != "active":
                errors.append(f"browser_public_tab_nav_session_closed_{event_id}")
            if tab is None:
                errors.append(f"browser_public_tab_nav_tab_missing_{event_id}")
                continue
            if tab["session_id"] != session_id:
                errors.append(f"browser_public_tab_nav_session_mismatch_{event_id}")
            if tab["status"] != "active":
                errors.append(f"browser_public_tab_nav_tab_closed_{event_id}")
            if payload.get("previous_url") != tab["current_url"]:
                errors.append(f"browser_public_tab_nav_previous_url_mismatch_{event_id}")
            navigation_count = payload.get("navigation_count")
            if not isinstance(navigation_count, int) or navigation_count != int(tab["navigation_count"]) + 1:
                errors.append(f"browser_public_tab_nav_count_invalid_{event_id}")
                navigation_count = int(tab["navigation_count"])
            final_url = str(payload.get("final_url") or "")
            url_trace_id = str(payload.get("url_policy_trace_id") or "")
            _browser_lifecycle_check_url_policy(
                event=event,
                url_events=url_events,
                url_trace_id=url_trace_id,
                expected_final_url=final_url,
                errors=errors,
                prefix="browser_public_tab_nav",
            )
            tab["current_url"] = final_url
            tab["navigation_count"] = navigation_count

        elif event.event_type == AgentEventType.BROWSER_PUBLIC_TAB_CLOSED:
            session_id = str(payload.get("session_id") or "")
            tab_id = str(payload.get("tab_id") or "")
            session = sessions.get(session_id)
            tab = tabs.get(tab_id)
            if session is None:
                errors.append(f"browser_public_tab_close_session_missing_{event_id}")
                continue
            if tab is None:
                errors.append(f"browser_public_tab_close_tab_missing_{event_id}")
                continue
            if tab["session_id"] != session_id:
                errors.append(f"browser_public_tab_close_session_mismatch_{event_id}")
            if tab["status"] != "active":
                errors.append(f"browser_public_tab_close_tab_not_active_{event_id}")
            if payload.get("final_url") != tab["current_url"]:
                errors.append(f"browser_public_tab_close_url_mismatch_{event_id}")
            tab["status"] = "closed"
            session["active_tabs"].discard(tab_id)

        elif event.event_type == AgentEventType.BROWSER_PUBLIC_SESSION_CLOSED:
            session_id = str(payload.get("session_id") or "")
            session = sessions.get(session_id)
            if session is None:
                errors.append(f"browser_public_session_close_missing_{event_id}")
                continue
            if session["status"] != "active":
                errors.append(f"browser_public_session_close_not_active_{event_id}")
            closed_tab_ids = payload.get("closed_tab_ids")
            if not isinstance(closed_tab_ids, list):
                errors.append(f"browser_public_session_close_invalid_tab_ids_{event_id}")
                closed_tab_ids = []
            active_tabs = set(session["active_tabs"])
            missing_closed = sorted(active_tabs - {str(tab_id) for tab_id in closed_tab_ids})
            if missing_closed:
                errors.append(f"browser_public_session_close_missing_active_tabs_{event_id}:{','.join(missing_closed)}")
            for tab_id in closed_tab_ids:
                tab = tabs.get(str(tab_id))
                if tab is None:
                    errors.append(f"browser_public_session_close_unknown_tab_{event_id}_{tab_id}")
                    continue
                if tab["session_id"] != session_id:
                    errors.append(f"browser_public_session_close_tab_session_mismatch_{event_id}_{tab_id}")
                tab["status"] = "closed"
            session["active_tabs"].clear()
            session["status"] = "closed"

    return CoreGateCheck(
        name="browser_public_lifecycle_contract",
        kind=CoreGateCheckKind.ARTIFACT,
        passed=not errors,
        message="Public browser lifecycle events are stateless, URL-policy-bound, and ordered." if not errors else "Public browser lifecycle contract failed.",
        details={"errors": errors},
    )


# ---------------------------------------------------------------------------
# Check 5 / 14: browser_reliability_supervisor_contract
# ---------------------------------------------------------------------------


def _check_browser_reliability_supervisor_contract(result: "AgentRunResult") -> CoreGateCheck:
    leases: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    supervisor_events = {
        AgentEventType.BROWSER_POOL_LEASED,
        AgentEventType.BROWSER_POOL_RELEASED,
        AgentEventType.BROWSER_HEALTH_CHECKED,
        AgentEventType.BROWSER_OPERATION_RETRIED,
        AgentEventType.BROWSER_SUPERVISOR_REJECTED,
    }
    valid_health_statuses = {"healthy", "degraded", "unavailable"}

    for event in result.trace:
        if event.event_type not in supervisor_events:
            continue
        payload = event.payload
        event_id = event.id

        if payload.get("stateless_public") is not True:
            errors.append(f"browser_supervisor_not_stateless_{event_id}")
        if payload.get("cookies_enabled") is not False:
            errors.append(f"browser_supervisor_cookies_enabled_{event_id}")
        if payload.get("storage_enabled") is not False:
            errors.append(f"browser_supervisor_storage_enabled_{event_id}")
        if payload.get("js_enabled") is not False:
            errors.append(f"browser_supervisor_js_enabled_{event_id}")
        if payload.get("downloads_enabled") is not False:
            errors.append(f"browser_supervisor_downloads_enabled_{event_id}")

        if event.event_type == AgentEventType.BROWSER_POOL_LEASED:
            if str(_enum_value(payload.get("status")) or "").lower() != "leased":
                errors.append(f"browser_pool_lease_status_invalid_{event_id}")
            if not payload.get("receipt_id"):
                errors.append(f"browser_pool_lease_missing_receipt_{event_id}")
            lease_id = str(payload.get("lease_id") or "")
            if not lease_id:
                errors.append(f"browser_pool_lease_missing_id_{event_id}")
                continue
            if lease_id in leases:
                errors.append(f"browser_pool_lease_duplicate_{event_id}_{lease_id}")
                continue
            max_operations = payload.get("max_operations")
            operation_count = payload.get("operation_count")
            if not isinstance(max_operations, int) or max_operations < 1:
                errors.append(f"browser_pool_lease_invalid_max_operations_{event_id}")
                max_operations = 0
            if not isinstance(operation_count, int) or operation_count != 0:
                errors.append(f"browser_pool_lease_invalid_operation_count_{event_id}")
                operation_count = 0
            leases[lease_id] = {
                "status": "leased",
                "sequence": event.sequence,
                "max_operations": max_operations,
                "operation_count": operation_count,
                "lease_event_id": event.id,
            }

        elif event.event_type == AgentEventType.BROWSER_POOL_RELEASED:
            if str(_enum_value(payload.get("status")) or "").lower() != "released":
                errors.append(f"browser_pool_release_status_invalid_{event_id}")
            if not payload.get("receipt_id"):
                errors.append(f"browser_pool_release_missing_receipt_{event_id}")
            lease_id = str(payload.get("lease_id") or "")
            lease = leases.get(lease_id)
            if lease is None:
                errors.append(f"browser_pool_release_unknown_lease_{event_id}")
                continue
            if lease["status"] != "leased":
                errors.append(f"browser_pool_release_lease_not_active_{event_id}")
            if lease["lease_event_id"] not in event.trace_refs:
                errors.append(f"browser_pool_release_missing_lease_trace_ref_{event_id}")
            operation_count = payload.get("operation_count")
            if not isinstance(operation_count, int) or operation_count < 0:
                errors.append(f"browser_pool_release_invalid_operation_count_{event_id}")
            elif operation_count > int(lease["max_operations"]):
                errors.append(f"browser_pool_release_operation_count_exceeds_max_{event_id}")
            lease["status"] = "released"

        elif event.event_type == AgentEventType.BROWSER_HEALTH_CHECKED:
            status = str(_enum_value(payload.get("status")) or "").lower()
            if status not in valid_health_statuses:
                errors.append(f"browser_health_status_invalid_{event_id}")
            if not payload.get("health_check_id"):
                errors.append(f"browser_health_missing_check_id_{event_id}")
            if not isinstance(payload.get("latency_ms"), int):
                errors.append(f"browser_health_invalid_latency_{event_id}")
            if not isinstance(payload.get("consecutive_failures"), int):
                errors.append(f"browser_health_invalid_consecutive_failures_{event_id}")
            lease_id = str(payload.get("lease_id") or "")
            if lease_id:
                lease = leases.get(lease_id)
                if lease is None:
                    errors.append(f"browser_health_unknown_lease_{event_id}")
                else:
                    if lease["status"] != "leased":
                        errors.append(f"browser_health_lease_not_active_{event_id}")
                    if lease["lease_event_id"] not in event.trace_refs:
                        errors.append(f"browser_health_missing_lease_trace_ref_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_OPERATION_RETRIED:
            if str(_enum_value(payload.get("status")) or "").lower() != "retrying":
                errors.append(f"browser_retry_status_invalid_{event_id}")
            if not payload.get("operation_name"):
                errors.append(f"browser_retry_missing_operation_name_{event_id}")
            if not payload.get("reason"):
                errors.append(f"browser_retry_missing_reason_{event_id}")
            if payload.get("retryable") is not True:
                errors.append(f"browser_retry_not_marked_retryable_{event_id}")
            attempt_number = payload.get("attempt_number")
            max_attempts = payload.get("max_attempts")
            if not isinstance(attempt_number, int) or attempt_number < 1:
                errors.append(f"browser_retry_invalid_attempt_number_{event_id}")
                attempt_number = 0
            if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 5:
                errors.append(f"browser_retry_invalid_max_attempts_{event_id}")
                max_attempts = 0
            if attempt_number >= max_attempts:
                errors.append(f"browser_retry_attempt_not_bounded_{event_id}")
            lease_id = str(payload.get("lease_id") or "")
            if lease_id:
                lease = leases.get(lease_id)
                if lease is None:
                    errors.append(f"browser_retry_unknown_lease_{event_id}")
                else:
                    if lease["status"] != "leased":
                        errors.append(f"browser_retry_lease_not_active_{event_id}")
                    if lease["lease_event_id"] not in event.trace_refs:
                        errors.append(f"browser_retry_missing_lease_trace_ref_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_SUPERVISOR_REJECTED:
            if str(_enum_value(payload.get("status")) or "").lower() != "rejected":
                errors.append(f"browser_supervisor_rejection_status_invalid_{event_id}")
            if not payload.get("operation_name") and not payload.get("action"):
                errors.append(f"browser_supervisor_rejection_missing_operation_{event_id}")
            if not payload.get("reason"):
                errors.append(f"browser_supervisor_rejection_missing_reason_{event_id}")

    return CoreGateCheck(
        name="browser_reliability_supervisor_contract",
        kind=CoreGateCheckKind.ARTIFACT,
        passed=not errors,
        message="Browser reliability supervisor events are bounded, stateless, and ordered." if not errors else "Browser reliability supervisor contract failed.",
        details={"errors": errors},
    )



# ---------------------------------------------------------------------------
# Check 6 / 14: browser_v25_observation_and_operator_contract
# ---------------------------------------------------------------------------


def _check_browser_v25_observation_and_operator_contract(result: "AgentRunResult") -> CoreGateCheck:
    v25_event_types = {
        AgentEventType.BROWSER_UI_OBSERVATION_CAPTURED,
        AgentEventType.BROWSER_UI_OBSERVATION_REJECTED,
        AgentEventType.BROWSER_CDP_AX_TREE_CAPTURED,
        AgentEventType.BROWSER_DOM_SNAPSHOT_CAPTURED,
        AgentEventType.BROWSER_VISUAL_OBSERVATION_CAPTURED,
        AgentEventType.BROWSER_ADVANCED_POOL_STARTED,
        AgentEventType.BROWSER_ADVANCED_POOL_LEASED,
        AgentEventType.BROWSER_ADVANCED_POOL_RELEASED,
        AgentEventType.BROWSER_MULTITAB_STRATEGY_EXECUTED,
        AgentEventType.BROWSER_VERIFICATION_COMPLETED,
        AgentEventType.BROWSER_LOOP_DETECTED,
    }
    v25_events = [event for event in result.trace if event.event_type in v25_event_types]
    if not v25_events:
        return CoreGateCheck(
            name="browser_v25_observation_and_operator_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=True,
            message="No Browser V2.5 observation/operator events were emitted.",
        )

    errors: list[str] = []
    advanced_leases: dict[str, dict[str, Any]] = {}
    valid_verdicts = {"accepted", "needs_repair", "inconclusive"}

    for event in v25_events:
        payload = event.payload
        event_id = event.id
        _browser_v25_boundary_errors(payload, event_id, errors)

        if event.event_type == AgentEventType.BROWSER_CDP_AX_TREE_CAPTURED:
            tree = payload.get("tree")
            expected_hash = payload.get("tree_sha256")
            if not isinstance(tree, dict):
                errors.append(f"browser_v25_ax_tree_missing_{event_id}")
                continue
            if not verify_cdp_ax_tree_hash(tree, str(expected_hash or "")):
                errors.append(f"browser_v25_ax_tree_hash_mismatch_{event_id}")
            if payload.get("node_count") != tree.get("node_count"):
                errors.append(f"browser_v25_ax_tree_node_count_mismatch_{event_id}")
            if not isinstance(payload.get("backend_node_count"), int):
                errors.append(f"browser_v25_ax_tree_backend_count_invalid_{event_id}")
            if not payload.get("root_id"):
                errors.append(f"browser_v25_ax_tree_missing_root_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_DOM_SNAPSHOT_CAPTURED:
            snapshot = payload.get("snapshot")
            expected_hash = payload.get("snapshot_sha256")
            if not isinstance(snapshot, dict):
                errors.append(f"browser_v25_dom_snapshot_missing_{event_id}")
                continue
            if not verify_dom_snapshot_hash(snapshot, str(expected_hash or "")):
                errors.append(f"browser_v25_dom_snapshot_hash_mismatch_{event_id}")
            if payload.get("node_count") != snapshot.get("node_count"):
                errors.append(f"browser_v25_dom_snapshot_node_count_mismatch_{event_id}")
            if payload.get("layout_count") != snapshot.get("layout_count"):
                errors.append(f"browser_v25_dom_snapshot_layout_count_mismatch_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_UI_OBSERVATION_CAPTURED:
            observation_set = payload.get("observation_set")
            expected_hash = payload.get("observation_sha256")
            if not isinstance(observation_set, dict):
                errors.append(f"browser_v25_ui_observation_missing_{event_id}")
                continue
            if not verify_ui_observation_hash(observation_set, str(expected_hash or "")):
                errors.append(f"browser_v25_ui_observation_hash_mismatch_{event_id}")
            observations = observation_set.get("observations")
            if not isinstance(observations, list):
                errors.append(f"browser_v25_ui_observation_items_invalid_{event_id}")
            elif payload.get("observation_count") != len(observations):
                errors.append(f"browser_v25_ui_observation_count_mismatch_{event_id}")
            if not isinstance(payload.get("source_count"), int) or payload.get("source_count") < 1:
                errors.append(f"browser_v25_ui_observation_source_count_invalid_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_VISUAL_OBSERVATION_CAPTURED:
            observation = payload.get("observation")
            expected_hash = payload.get("observation_sha256")
            if not isinstance(observation, dict):
                errors.append(f"browser_v25_visual_observation_missing_{event_id}")
                continue
            if not verify_visual_observation_hash(observation, str(expected_hash or "")):
                errors.append(f"browser_v25_visual_observation_hash_mismatch_{event_id}")
            if not payload.get("source_screenshot_sha256"):
                errors.append(f"browser_v25_visual_observation_missing_source_hash_{event_id}")
            bytes_observed = payload.get("bytes_observed")
            max_bytes = payload.get("max_bytes")
            if not isinstance(bytes_observed, int) or not isinstance(max_bytes, int) or bytes_observed > max_bytes:
                errors.append(f"browser_v25_visual_observation_bytes_invalid_{event_id}")
            if payload.get("ocr_dependency") != "stub":
                errors.append(f"browser_v25_visual_observation_ocr_dependency_invalid_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_ADVANCED_POOL_STARTED:
            capacity = payload.get("capacity")
            instance_ids = payload.get("instance_ids")
            if not isinstance(capacity, int) or capacity < 1:
                errors.append(f"browser_v25_pool_capacity_invalid_{event_id}")
            if not isinstance(instance_ids, list) or len(instance_ids) != capacity:
                errors.append(f"browser_v25_pool_instance_count_mismatch_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_ADVANCED_POOL_LEASED:
            if str(_enum_value(payload.get("status")) or "").lower() != "leased":
                errors.append(f"browser_v25_pool_lease_status_invalid_{event_id}")
            lease_id = str(payload.get("lease_id") or "")
            instance_id = str(payload.get("instance_id") or "")
            if not lease_id or not instance_id:
                errors.append(f"browser_v25_pool_lease_missing_identity_{event_id}")
                continue
            if lease_id in advanced_leases:
                errors.append(f"browser_v25_pool_lease_duplicate_{event_id}_{lease_id}")
                continue
            advanced_leases[lease_id] = {"instance_id": instance_id, "status": "leased", "event_id": event.id}

        elif event.event_type == AgentEventType.BROWSER_ADVANCED_POOL_RELEASED:
            if str(_enum_value(payload.get("status")) or "").lower() != "released":
                errors.append(f"browser_v25_pool_release_status_invalid_{event_id}")
            lease_id = str(payload.get("lease_id") or "")
            lease = advanced_leases.get(lease_id)
            if lease is None:
                errors.append(f"browser_v25_pool_release_unknown_lease_{event_id}")
                continue
            if lease["status"] != "leased":
                errors.append(f"browser_v25_pool_release_not_active_{event_id}")
            if lease["event_id"] not in event.trace_refs:
                errors.append(f"browser_v25_pool_release_missing_lease_trace_ref_{event_id}")
            if payload.get("instance_id") != lease["instance_id"]:
                errors.append(f"browser_v25_pool_release_instance_mismatch_{event_id}")
            lease["status"] = "released"

        elif event.event_type == AgentEventType.BROWSER_MULTITAB_STRATEGY_EXECUTED:
            tab_ids = payload.get("tab_ids")
            final_urls = payload.get("final_urls")
            tab_count = payload.get("tab_count")
            max_tabs = payload.get("max_tabs")
            if not isinstance(tab_count, int) or not isinstance(max_tabs, int) or tab_count < 1 or tab_count > max_tabs:
                errors.append(f"browser_v25_multitab_count_invalid_{event_id}")
            if not isinstance(tab_ids, list) or len(tab_ids) != tab_count:
                errors.append(f"browser_v25_multitab_ids_mismatch_{event_id}")
            if not isinstance(final_urls, list) or len(final_urls) != tab_count:
                errors.append(f"browser_v25_multitab_urls_mismatch_{event_id}")
            if not event.trace_refs:
                errors.append(f"browser_v25_multitab_missing_lifecycle_trace_refs_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_VERIFICATION_COMPLETED:
            verdict = str(_enum_value(payload.get("verdict")) or "").lower()
            if verdict not in valid_verdicts:
                errors.append(f"browser_v25_verifier_verdict_invalid_{event_id}")
            if not payload.get("checked_receipt_id"):
                errors.append(f"browser_v25_verifier_missing_receipt_{event_id}")
            if not payload.get("before_snapshot_sha256") or not payload.get("after_snapshot_sha256"):
                errors.append(f"browser_v25_verifier_missing_snapshot_hash_{event_id}")
            findings = payload.get("findings")
            if not isinstance(findings, list):
                errors.append(f"browser_v25_verifier_findings_invalid_{event_id}")
            elif verdict == "accepted" and findings:
                errors.append(f"browser_v25_verifier_accepted_with_findings_{event_id}")
            trace_ref_count = payload.get("trace_ref_count")
            if not isinstance(trace_ref_count, int) or trace_ref_count < 1:
                errors.append(f"browser_v25_verifier_missing_trace_refs_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_LOOP_DETECTED:
            repeated_count = payload.get("repeated_count")
            threshold = payload.get("threshold")
            if not isinstance(repeated_count, int) or not isinstance(threshold, int) or repeated_count < threshold:
                errors.append(f"browser_v25_loop_count_invalid_{event_id}")
            if not payload.get("loop_key"):
                errors.append(f"browser_v25_loop_missing_key_{event_id}")

        elif event.event_type == AgentEventType.BROWSER_UI_OBSERVATION_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v25_ui_observation_rejection_missing_reason_{event_id}")

    return CoreGateCheck(
        name="browser_v25_observation_and_operator_contract",
        kind=CoreGateCheckKind.EVIDENCE,
        passed=not errors,
        message="Browser V2.5 observation/operator events are proof-bound and public/stateless." if not errors else "Browser V2.5 observation/operator contract failed.",
        details={"errors": errors},
    )


# ---------------------------------------------------------------------------
# Check 7 / 14: browser_v3_form_submit_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_form_submit_contract(result: "AgentRunResult") -> CoreGateCheck:
    form_events = [
        event
        for event in result.trace
        if event.event_type in {AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED, AgentEventType.BROWSER_FORM_SUBMIT_REJECTED}
    ]
    if not form_events:
        return CoreGateCheck(
            name="browser_v3_form_submit_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=True,
            message="No Browser V3 form-submit events were emitted.",
        )

    errors: list[str] = []
    compiled_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
    }
    artifact_events = {
        str(event.payload.get("artifact_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
    }

    for event in form_events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_form_submit":
            errors.append(f"browser_v3_form_submit_authority_class_invalid_{event_id}")
        if not payload.get("authority_grant_id"):
            errors.append(f"browser_v3_form_submit_missing_grant_{event_id}")
        if not payload.get("context_pack_id"):
            errors.append(f"browser_v3_form_submit_missing_context_pack_{event_id}")
        compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
        if not compiled_trace_id:
            errors.append(f"browser_v3_form_submit_missing_compiled_intent_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED:
            compiled_event = compiled_events.get(compiled_trace_id)
            if compiled_event is None:
                errors.append(f"browser_v3_form_submit_compiled_intent_missing_{event_id}")
            elif compiled_trace_id not in event.trace_refs:
                errors.append(f"browser_v3_form_submit_missing_compiled_trace_ref_{event_id}")
        if event.event_type == AgentEventType.BROWSER_FORM_SUBMIT_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_form_submit_rejection_missing_reason_{event_id}")
            continue

        if not payload.get("receipt_id"):
            errors.append(f"browser_v3_form_submit_missing_receipt_{event_id}")
        plan = payload.get("plan")
        plan_sha256 = payload.get("plan_sha256")
        if not isinstance(plan, dict):
            errors.append(f"browser_v3_form_submit_missing_plan_{event_id}")
        elif not verify_browser_interaction_plan_hash(plan, str(plan_sha256 or "")):
            errors.append(f"browser_v3_form_submit_plan_hash_mismatch_{event_id}")
        if not payload.get("plan_trace_event_id"):
            errors.append(f"browser_v3_form_submit_missing_plan_trace_{event_id}")
        if not payload.get("before_snapshot_trace_event_id"):
            errors.append(f"browser_v3_form_submit_missing_before_snapshot_trace_{event_id}")
        if not payload.get("before_snapshot_sha256") or not payload.get("after_snapshot_sha256"):
            errors.append(f"browser_v3_form_submit_missing_snapshot_hash_{event_id}")
        if not payload.get("form_ref_id") or not payload.get("submit_ref_id"):
            errors.append(f"browser_v3_form_submit_missing_refs_{event_id}")
        if str(payload.get("submit_kind") or "").lower() not in {"submit", "post", "send", "publish"}:
            errors.append(f"browser_v3_form_submit_kind_invalid_{event_id}")
        if not payload.get("expected_effect"):
            errors.append(f"browser_v3_form_submit_missing_expected_effect_{event_id}")
        if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
            errors.append(f"browser_v3_form_submit_cross_origin_not_authorized_{event_id}")

        network_ledger = payload.get("network_ledger")
        network_ledger_sha256 = payload.get("network_ledger_sha256")
        if not isinstance(network_ledger, dict):
            errors.append(f"browser_v3_form_submit_missing_network_ledger_{event_id}")
        elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
            errors.append(f"browser_v3_form_submit_network_ledger_hash_mismatch_{event_id}")

        artifact_id = str(payload.get("post_submit_snapshot_artifact_id") or "")
        artifact_hash = payload.get("post_submit_snapshot_artifact_sha256")
        artifact_event = artifact_events.get(artifact_id)
        if not artifact_id:
            errors.append(f"browser_v3_form_submit_missing_post_snapshot_artifact_{event_id}")
        elif artifact_event is None:
            errors.append(f"browser_v3_form_submit_post_snapshot_artifact_missing_{event_id}")
        else:
            if artifact_event.sequence >= event.sequence:
                errors.append(f"browser_v3_form_submit_post_snapshot_artifact_order_invalid_{event_id}")
            if artifact_hash and artifact_event.payload.get("sha256") != artifact_hash:
                errors.append(f"browser_v3_form_submit_post_snapshot_artifact_hash_mismatch_{event_id}")

    return CoreGateCheck(
        name="browser_v3_form_submit_contract",
        kind=CoreGateCheckKind.EVIDENCE,
        passed=not errors,
        message="Browser V3 form-submit events are authority-bound and proof-certified." if not errors else "Browser V3 form-submit contract failed.",
        details={"errors": errors},
    )



# ---------------------------------------------------------------------------
# Check 8 / 14: browser_v3_download_quarantine_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_download_quarantine_contract(result: "AgentRunResult") -> CoreGateCheck:
    download_events = [
        event
        for event in result.trace
        if event.event_type in {AgentEventType.BROWSER_DOWNLOAD_QUARANTINED, AgentEventType.BROWSER_DOWNLOAD_REJECTED}
    ]
    if not download_events:
        return CoreGateCheck(
            name="browser_v3_download_quarantine_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=True,
            message="No Browser V3 download-quarantine events were emitted.",
        )

    errors: list[str] = []
    compiled_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
    }
    url_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.BROWSER_URL_CLASSIFIED
    }
    artifact_events = {
        str(event.payload.get("artifact_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
    }

    for event in download_events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_download_quarantine":
            errors.append(f"browser_v3_download_authority_class_invalid_{event_id}")
        if not payload.get("authority_grant_id"):
            errors.append(f"browser_v3_download_missing_grant_{event_id}")
        if not payload.get("context_pack_id"):
            errors.append(f"browser_v3_download_missing_context_pack_{event_id}")
        compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
        if not compiled_trace_id:
            errors.append(f"browser_v3_download_missing_compiled_intent_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_DOWNLOAD_QUARANTINED:
            compiled_event = compiled_events.get(compiled_trace_id)
            if compiled_event is None:
                errors.append(f"browser_v3_download_compiled_intent_missing_{event_id}")
            elif compiled_trace_id not in event.trace_refs:
                errors.append(f"browser_v3_download_missing_compiled_trace_ref_{event_id}")

        url_trace_id = str(payload.get("url_policy_trace_id") or "")
        if not url_trace_id:
            errors.append(f"browser_v3_download_missing_url_policy_{event_id}")
        else:
            url_event = url_events.get(url_trace_id)
            if url_event is None:
                errors.append(f"browser_v3_download_url_policy_missing_{event_id}")
            else:
                if url_event.sequence >= event.sequence:
                    errors.append(f"browser_v3_download_url_policy_order_invalid_{event_id}")
                if url_trace_id not in event.trace_refs:
                    errors.append(f"browser_v3_download_missing_url_trace_ref_{event_id}")
                if event.event_type == AgentEventType.BROWSER_DOWNLOAD_QUARANTINED and str(url_event.payload.get("status")) != "allowed":
                    errors.append(f"browser_v3_download_url_policy_not_allowed_{event_id}")

        if event.event_type == AgentEventType.BROWSER_DOWNLOAD_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_download_rejection_missing_reason_{event_id}")
            continue

        if not payload.get("receipt_id"):
            errors.append(f"browser_v3_download_missing_receipt_{event_id}")
        if payload.get("promoted") is not False:
            errors.append(f"browser_v3_download_promoted_{event_id}")
        if payload.get("mime_type_allowed") is not True:
            errors.append(f"browser_v3_download_mime_not_allowed_{event_id}")
        if str(payload.get("quarantine_relative_path") or "").startswith("browser/download_quarantine/") is not True:
            errors.append(f"browser_v3_download_quarantine_path_invalid_{event_id}")
        if not payload.get("filename_hash"):
            errors.append(f"browser_v3_download_missing_filename_hash_{event_id}")
        size_bytes = payload.get("size_bytes")
        max_bytes = payload.get("max_bytes")
        if not isinstance(size_bytes, int) or not isinstance(max_bytes, int):
            errors.append(f"browser_v3_download_invalid_size_metadata_{event_id}")
        elif size_bytes > max_bytes:
            errors.append(f"browser_v3_download_size_exceeds_max_{event_id}")

        artifact_id = str(payload.get("artifact_id") or "")
        artifact_hash = payload.get("artifact_sha256")
        download_hash = payload.get("download_sha256")
        artifact_event = artifact_events.get(artifact_id)
        if not artifact_id:
            errors.append(f"browser_v3_download_missing_artifact_{event_id}")
        elif artifact_event is None:
            errors.append(f"browser_v3_download_artifact_missing_{event_id}")
        else:
            if artifact_event.sequence >= event.sequence:
                errors.append(f"browser_v3_download_artifact_order_invalid_{event_id}")
            if artifact_hash and artifact_event.payload.get("sha256") != artifact_hash:
                errors.append(f"browser_v3_download_artifact_hash_mismatch_{event_id}")
            if download_hash and artifact_event.payload.get("sha256") != download_hash:
                errors.append(f"browser_v3_download_hash_mismatch_{event_id}")
            if artifact_event.payload.get("artifact_type") != "browser_download_quarantine":
                errors.append(f"browser_v3_download_artifact_type_invalid_{event_id}")

    return CoreGateCheck(
        name="browser_v3_download_quarantine_contract",
        kind=CoreGateCheckKind.EVIDENCE,
        passed=not errors,
        message="Browser V3 download-quarantine events are authority-bound and quarantine-certified." if not errors else "Browser V3 download-quarantine contract failed.",
        details={"errors": errors},
    )


# ---------------------------------------------------------------------------
# Check 9 / 14: browser_v3_upload_authorized_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_upload_authorized_contract(result: "AgentRunResult") -> CoreGateCheck:
    upload_events = [
        event
        for event in result.trace
        if event.event_type in {AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED, AgentEventType.BROWSER_UPLOAD_AUTHORIZED_REJECTED}
    ]
    if not upload_events:
        return CoreGateCheck(
            name="browser_v3_upload_authorized_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=True,
            message="No Browser V3 authorized-upload events were emitted.",
        )

    errors: list[str] = []
    compiled_events = {
        event.id: event
        for event in result.trace
        if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
    }
    artifact_events = {
        str(event.payload.get("artifact_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
    }

    for event in upload_events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_upload_authorized":
            errors.append(f"browser_v3_upload_authority_class_invalid_{event_id}")
        if not payload.get("authority_grant_id"):
            errors.append(f"browser_v3_upload_missing_grant_{event_id}")
        if not payload.get("context_pack_id"):
            errors.append(f"browser_v3_upload_missing_context_pack_{event_id}")
        compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
        if not compiled_trace_id:
            errors.append(f"browser_v3_upload_missing_compiled_intent_{event_id}")
        elif event.event_type == AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED:
            compiled_event = compiled_events.get(compiled_trace_id)
            if compiled_event is None:
                errors.append(f"browser_v3_upload_compiled_intent_missing_{event_id}")
            elif compiled_trace_id not in event.trace_refs:
                errors.append(f"browser_v3_upload_missing_compiled_trace_ref_{event_id}")

        if event.event_type == AgentEventType.BROWSER_UPLOAD_AUTHORIZED_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_upload_rejection_missing_reason_{event_id}")
            continue

        if not payload.get("receipt_id"):
            errors.append(f"browser_v3_upload_missing_receipt_{event_id}")
        plan = payload.get("plan")
        plan_sha256 = payload.get("plan_sha256")
        if not isinstance(plan, dict):
            errors.append(f"browser_v3_upload_missing_plan_{event_id}")
        elif not verify_browser_interaction_plan_hash(plan, str(plan_sha256 or "")):
            errors.append(f"browser_v3_upload_plan_hash_mismatch_{event_id}")
        if not payload.get("plan_trace_event_id"):
            errors.append(f"browser_v3_upload_missing_plan_trace_{event_id}")
        if not payload.get("before_snapshot_trace_event_id"):
            errors.append(f"browser_v3_upload_missing_before_snapshot_trace_{event_id}")
        if not payload.get("before_snapshot_sha256") or not payload.get("after_snapshot_sha256"):
            errors.append(f"browser_v3_upload_missing_snapshot_hash_{event_id}")
        if not payload.get("upload_ref_id"):
            errors.append(f"browser_v3_upload_missing_upload_ref_{event_id}")
        if not payload.get("expected_effect"):
            errors.append(f"browser_v3_upload_missing_expected_effect_{event_id}")
        if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
            errors.append(f"browser_v3_upload_cross_origin_not_authorized_{event_id}")

        network_ledger = payload.get("network_ledger")
        network_ledger_sha256 = payload.get("network_ledger_sha256")
        if not isinstance(network_ledger, dict):
            errors.append(f"browser_v3_upload_missing_network_ledger_{event_id}")
        elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
            errors.append(f"browser_v3_upload_network_ledger_hash_mismatch_{event_id}")

        source_artifact_id = str(payload.get("source_artifact_id") or "")
        source_artifact_hash = payload.get("source_artifact_sha256")
        source_artifact_event = artifact_events.get(source_artifact_id)
        if not source_artifact_id:
            errors.append(f"browser_v3_upload_missing_source_artifact_{event_id}")
        elif source_artifact_event is None:
            errors.append(f"browser_v3_upload_source_artifact_missing_{event_id}")
        else:
            if source_artifact_event.sequence >= event.sequence:
                errors.append(f"browser_v3_upload_source_artifact_order_invalid_{event_id}")
            if source_artifact_hash and source_artifact_event.payload.get("sha256") != source_artifact_hash:
                errors.append(f"browser_v3_upload_source_artifact_hash_mismatch_{event_id}")

        snapshot_artifact_id = str(payload.get("post_upload_snapshot_artifact_id") or "")
        snapshot_artifact_hash = payload.get("post_upload_snapshot_artifact_sha256")
        snapshot_artifact_event = artifact_events.get(snapshot_artifact_id)
        if not snapshot_artifact_id:
            errors.append(f"browser_v3_upload_missing_post_snapshot_artifact_{event_id}")
        elif snapshot_artifact_event is None:
            errors.append(f"browser_v3_upload_post_snapshot_artifact_missing_{event_id}")
        else:
            if snapshot_artifact_event.sequence >= event.sequence:
                errors.append(f"browser_v3_upload_post_snapshot_artifact_order_invalid_{event_id}")
            if snapshot_artifact_hash and snapshot_artifact_event.payload.get("sha256") != snapshot_artifact_hash:
                errors.append(f"browser_v3_upload_post_snapshot_artifact_hash_mismatch_{event_id}")

    return CoreGateCheck(
        name="browser_v3_upload_authorized_contract",
        kind=CoreGateCheckKind.EVIDENCE,
        passed=not errors,
        message="Browser V3 authorized-upload events are authority-bound and artifact-certified." if not errors else "Browser V3 authorized-upload contract failed.",
        details={"errors": errors},
    )



# ---------------------------------------------------------------------------
# Check 10 / 14: browser_v3_private_session_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_private_session_contract(result: "AgentRunResult") -> CoreGateCheck:
    events = [
        event
        for event in result.trace
        if event.event_type
        in {
            AgentEventType.BROWSER_PRIVATE_SESSION_STARTED,
            AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED,
            AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED,
        }
    ]
    if not events:
        return CoreGateCheck(name="browser_v3_private_session_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 private-session events were emitted.")
    errors: list[str] = []
    starts: dict[str, Any] = {}
    closes: dict[str, Any] = {}
    compiled = _accepted_compiled_event_ids(result)
    artifacts = _artifact_events_by_id(result)
    for event in events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_private_session":
            errors.append(f"browser_v3_private_session_class_invalid_{event_id}")
        _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_private_session")
        if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_private_session_rejection_missing_reason_{event_id}")
            continue
        session_id = str(payload.get("session_id") or "")
        if not session_id or not payload.get("profile_id"):
            errors.append(f"browser_v3_private_session_missing_ids_{event_id}")
        if payload.get("session_scope") != "per_mission":
            errors.append(f"browser_v3_private_session_scope_invalid_{event_id}")
        if not payload.get("storage_state_sha256"):
            errors.append(f"browser_v3_private_session_missing_storage_hash_{event_id}")
        _check_artifact_pair(payload.get("receipt_artifact_id"), payload.get("receipt_artifact_sha256"), event, artifacts, errors, "browser_v3_private_session_receipt")
        if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_STARTED:
            if payload.get("created") is not True:
                errors.append(f"browser_v3_private_session_not_created_{event_id}")
            starts[session_id] = event
        if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED:
            if payload.get("destroyed") is not True or payload.get("profile_destroyed") is not True:
                errors.append(f"browser_v3_private_session_not_destroyed_{event_id}")
            closes[session_id] = event
    for session_id, start_event in starts.items():
        close_event = closes.get(session_id)
        if close_event is None:
            errors.append(f"browser_v3_private_session_missing_close_{session_id}")
        elif close_event.sequence <= start_event.sequence:
            errors.append(f"browser_v3_private_session_close_order_invalid_{session_id}")
    return CoreGateCheck(name="browser_v3_private_session_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 private sessions are opened and destroyed with proof." if not errors else "Browser V3 private-session contract failed.", details={"errors": errors})


# ---------------------------------------------------------------------------
# Check 11 / 14: browser_v3_login_authority_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_login_authority_contract(result: "AgentRunResult") -> CoreGateCheck:
    events = [
        event
        for event in result.trace
        if event.event_type in {AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED}
    ]
    if not events:
        return CoreGateCheck(name="browser_v3_login_authority_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 login-authority events were emitted.")
    errors: list[str] = []
    compiled = _accepted_compiled_event_ids(result)
    artifacts = _artifact_events_by_id(result)
    private_events = {event.id: event for event in result.trace if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_STARTED}
    for event in events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_login_authority":
            errors.append(f"browser_v3_login_class_invalid_{event_id}")
        _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_login")
        _check_no_credential_payload(payload, errors, f"browser_v3_login_credential_leak_{event_id}")
        if event.event_type == AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_login_rejection_missing_reason_{event_id}")
            continue
        session_trace_id = str(payload.get("private_session_trace_event_id") or "")
        session_event = private_events.get(session_trace_id)
        if session_event is None:
            errors.append(f"browser_v3_login_missing_private_session_{event_id}")
        elif session_event.sequence >= event.sequence:
            errors.append(f"browser_v3_login_private_session_order_invalid_{event_id}")
        if payload.get("login_success") is not True:
            errors.append(f"browser_v3_login_not_successful_{event_id}")
        if not payload.get("account_id") or not payload.get("login_url_hash"):
            errors.append(f"browser_v3_login_missing_account_or_url_hash_{event_id}")
        if not payload.get("plan_sha256") or not payload.get("plan_trace_event_id"):
            errors.append(f"browser_v3_login_missing_plan_{event_id}")
        _check_artifact_pair(payload.get("post_login_snapshot_artifact_id"), payload.get("post_login_snapshot_artifact_sha256"), event, artifacts, errors, "browser_v3_login_post_snapshot")
    return CoreGateCheck(name="browser_v3_login_authority_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 login events are session-bound and credential-redacted." if not errors else "Browser V3 login contract failed.", details={"errors": errors})


# ---------------------------------------------------------------------------
# Check 12 / 14: browser_v3_cookie_storage_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_cookie_storage_contract(result: "AgentRunResult") -> CoreGateCheck:
    events = [
        event
        for event in result.trace
        if event.event_type in {AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED}
    ]
    if not events:
        return CoreGateCheck(name="browser_v3_cookie_storage_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 cookie/storage events were emitted.")
    errors: list[str] = []
    compiled = _accepted_compiled_event_ids(result)
    artifacts = _artifact_events_by_id(result)
    private_events = {event.id: event for event in result.trace if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_STARTED}
    for event in events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_cookie_storage_contract":
            errors.append(f"browser_v3_cookie_storage_class_invalid_{event_id}")
        _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_cookie_storage")
        if event.event_type == AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_cookie_storage_rejection_missing_reason_{event_id}")
            continue
        session_trace_id = str(payload.get("private_session_trace_event_id") or "")
        if session_trace_id not in private_events:
            errors.append(f"browser_v3_cookie_storage_missing_private_session_{event_id}")
        if payload.get("redaction_applied") is not True or payload.get("raw_value_exposed") is True:
            errors.append(f"browser_v3_cookie_storage_redaction_invalid_{event_id}")
        if payload.get("operation") not in {"redacted_summary", "clear_scoped_storage"}:
            errors.append(f"browser_v3_cookie_storage_operation_invalid_{event_id}")
        _check_artifact_pair(payload.get("summary_artifact_id"), payload.get("summary_artifact_sha256"), event, artifacts, errors, "browser_v3_cookie_storage_summary")
    return CoreGateCheck(name="browser_v3_cookie_storage_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 cookie/storage contracts are redacted and session-bound." if not errors else "Browser V3 cookie/storage contract failed.", details={"errors": errors})


# ---------------------------------------------------------------------------
# Check 13 / 14: browser_v3_js_evaluate_sandboxed_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_js_evaluate_sandboxed_contract(result: "AgentRunResult") -> CoreGateCheck:
    events = [
        event
        for event in result.trace
        if event.event_type in {AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED}
    ]
    if not events:
        return CoreGateCheck(name="browser_v3_js_evaluate_sandboxed_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 sandboxed-JS events were emitted.")
    errors: list[str] = []
    compiled = _accepted_compiled_event_ids(result)
    artifacts = _artifact_events_by_id(result)
    for event in events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_js_evaluate_sandboxed":
            errors.append(f"browser_v3_js_class_invalid_{event_id}")
        _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_js")
        if event.event_type == AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_js_rejection_missing_reason_{event_id}")
            continue
        if payload.get("script_hash_allowed") is not True:
            errors.append(f"browser_v3_js_script_hash_not_allowed_{event_id}")
        if payload.get("network_calls_blocked") is not True:
            errors.append(f"browser_v3_js_network_calls_not_blocked_{event_id}")
        if not isinstance(payload.get("result_size_bytes"), int) or not isinstance(payload.get("max_result_bytes"), int):
            errors.append(f"browser_v3_js_size_metadata_invalid_{event_id}")
        elif payload.get("result_size_bytes") > payload.get("max_result_bytes"):
            errors.append(f"browser_v3_js_result_too_large_{event_id}")
        _check_artifact_pair(payload.get("result_artifact_id"), payload.get("result_artifact_sha256"), event, artifacts, errors, "browser_v3_js_result")
    return CoreGateCheck(name="browser_v3_js_evaluate_sandboxed_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 sandboxed JS is hash-allowlisted and artifact-bound." if not errors else "Browser V3 sandboxed-JS contract failed.", details={"errors": errors})


# ---------------------------------------------------------------------------
# Check 14 / 14: browser_v3_har_body_capture_contract
# ---------------------------------------------------------------------------


def _check_browser_v3_har_body_capture_contract(result: "AgentRunResult") -> CoreGateCheck:
    events = [
        event
        for event in result.trace
        if event.event_type in {AgentEventType.BROWSER_HAR_BODY_CAPTURED, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED}
    ]
    if not events:
        return CoreGateCheck(name="browser_v3_har_body_capture_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 HAR/body events were emitted.")
    errors: list[str] = []
    compiled = _accepted_compiled_event_ids(result)
    artifacts = _artifact_events_by_id(result)
    for event in events:
        payload = event.payload
        event_id = event.id
        if payload.get("authority_class") != "browser_har_body_capture":
            errors.append(f"browser_v3_har_class_invalid_{event_id}")
        _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_har")
        if event.event_type == AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED:
            if not payload.get("reason"):
                errors.append(f"browser_v3_har_rejection_missing_reason_{event_id}")
            continue
        if payload.get("redaction_applied") is not True:
            errors.append(f"browser_v3_har_redaction_missing_{event_id}")
        if not isinstance(payload.get("record_count"), int) or not isinstance(payload.get("max_records"), int):
            errors.append(f"browser_v3_har_record_metadata_invalid_{event_id}")
        elif payload.get("record_count") > payload.get("max_records"):
            errors.append(f"browser_v3_har_record_limit_exceeded_{event_id}")
        if not isinstance(payload.get("total_bytes"), int) or not isinstance(payload.get("max_bytes"), int):
            errors.append(f"browser_v3_har_byte_metadata_invalid_{event_id}")
        elif payload.get("total_bytes") > payload.get("max_bytes"):
            errors.append(f"browser_v3_har_byte_limit_exceeded_{event_id}")
        _check_artifact_pair(payload.get("har_artifact_id"), payload.get("har_artifact_sha256"), event, artifacts, errors, "browser_v3_har_artifact")
    return CoreGateCheck(name="browser_v3_har_body_capture_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 HAR/body capture is bounded, redacted, and artifact-bound." if not errors else "Browser V3 HAR/body contract failed.", details={"errors": errors})


# ---------------------------------------------------------------------------
# Public module class — FinalGateCheckModule protocol implementation.
# ---------------------------------------------------------------------------


class BrowserOrganChecksModule:
    """Organ-side FinalGate module owning the 14 browser-specific checks.

    Implements the ``FinalGateCheckModule`` protocol expected by
    :class:`sentinel.agent.final_gate_registry.FinalGateRegistry`.

    Task 5.2-C3: the check bodies now live in this module. No delegation
    to ``CoreFinalGate`` remains. Byte-equivalence with the legacy
    :class:`sentinel.agent.final_gate_registry.BrowserChecksModule` is
    preserved and tested in ``tests/test_browser_organ_final_gate.py``.

    The module name remains ``"browser_organ"`` (distinct from the
    legacy ``"browser"``) so the legacy module can coexist in a
    registry during the deprecation window (e.g., for side-by-side
    parity comparison).
    """

    name = "browser_organ"

    def checks(
        self,
        result: "AgentRunResult",
        *,
        allowed_project_root: "Path | None" = None,
    ) -> list[CoreGateCheck]:
        return [
            _check_browser_capability_receipts(result),
            _check_browser_interaction_dry_run_contract(result),
            _check_browser_interaction_execution_contract(result),
            _check_browser_public_lifecycle_contract(result),
            _check_browser_reliability_supervisor_contract(result),
            _check_browser_v25_observation_and_operator_contract(result),
            _check_browser_v3_form_submit_contract(result),
            _check_browser_v3_download_quarantine_contract(result),
            _check_browser_v3_upload_authorized_contract(result),
            _check_browser_v3_private_session_contract(result),
            _check_browser_v3_login_authority_contract(result),
            _check_browser_v3_cookie_storage_contract(result),
            _check_browser_v3_js_evaluate_sandboxed_contract(result),
            _check_browser_v3_har_body_capture_contract(result),
        ]


# Alias: the task spec mentions ``BrowserOrganFinalGate`` as an acceptable
# public name. Expose both identifiers — the class is the same object.
BrowserOrganFinalGate = BrowserOrganChecksModule


__all__ = ["BrowserOrganChecksModule", "BrowserOrganFinalGate"]
