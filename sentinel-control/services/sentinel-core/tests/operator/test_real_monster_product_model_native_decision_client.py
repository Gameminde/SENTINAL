from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from sentinel.operator import channel_adapter
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError
from sentinel.operator.mission_artifact_bundle import (
    MissionArtifactBundleExporter,
    MissionArtifactBundleVerifier,
)
from sentinel.operator.product_model_native_decision_client import (
    ProductModelNativeDecisionClient,
)
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ModelLedProductActionKernelTaskLoop,
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.unified_execution_dispatcher import DispatchStatus, UnifiedDispatchResult


def test_json_skill_run_check_maps_to_internal_action_envelope() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"skill": "run_check", "params": {"profile_id": "fake_pass", "args": ["."]}}]),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="run_check"))

    assert isinstance(decision, ActionEnvelope)
    assert decision.capability_id == "code_execution_sandbox"
    assert decision.operation == "code_exec.run_profile"
    assert decision.params == {"profile_id": "fake_pass", "args": ["."]}
    assert decision.can_execute is False


def test_run_check_uses_bounded_plan_over_model_raw_shell_params() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "skill": "run_check",
                    "params": {
                        "profile_id": "raw_shell",
                        "args": ["py -3.13 -m pytest . -q"],
                    },
                }
            ]
        ),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="run_check",
            bounded_check_plan={"profile_id": "pytest_file", "args": ["tests/test_app.py"]},
        )
    )

    assert decision.capability_id == "code_execution_sandbox"
    assert decision.operation == "code_exec.run_profile"
    assert decision.params == {"profile_id": "pytest_file", "args": ["tests/test_app.py"]}


def test_metadata_reply_natural_send_message_maps_to_bounded_channel() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"metadata": {"reply": "I will send the completion message now."}}]),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="send_message"))

    assert decision.capability_id == "bounded_channel"
    assert decision.operation == "send_message"
    assert decision.params["adapter_id"] == "monster_fake_channel"
    assert decision.params["channel"] == "webhook"
    assert decision.params["recipients"] == ["founder@example.com"]
    assert "completion" in str(decision.params["body"]).lower()


def test_model_supplied_channel_fields_cannot_override_granted_local_channel() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "skill": "send_message",
                    "params": {
                        "adapter_id": "untrusted_adapter",
                        "channel": "bounded_local_channel",
                        "recipients": ["attacker@example.com"],
                        "recipient_provenance": {"attacker@example.com": "model_supplied"},
                        "message": "Sentinel number analyzer app is ready.",
                    },
                }
            ]
        ),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="send_message"))

    assert decision.capability_id == "bounded_channel"
    assert decision.operation == "send_message"
    assert decision.params["adapter_id"] == "monster_fake_channel"
    assert decision.params["channel"] == "webhook"
    assert decision.params["recipients"] == ["founder@example.com"]
    assert decision.params["recipient_provenance"] == {
        "founder@example.com": "mission_level_destination_grant",
    }
    assert "Sentinel number analyzer app is ready." in decision.params["body"]
    assert "attacker@example.com" not in str(decision.params)


def test_metadata_reply_send_message_uses_granted_telegram_destination() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"metadata": {"reply": "Send the live completion update now."}}]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="send_message",
            live_channel_destination_grants=[
                {
                    "adapter_id": "telegram_live_adapter",
                    "channel": "telegram",
                    "destination_ref": "telegram:configured-chat",
                }
            ],
        )
    )

    assert decision.capability_id == "bounded_channel"
    assert decision.operation == "send_message"
    assert decision.params["adapter_id"] == "telegram_live_adapter"
    assert decision.params["channel"] == "telegram"
    assert decision.params["recipients"] == ["telegram:configured-chat"]
    assert decision.params["recipient_provenance"] == {
        "telegram:configured-chat": "mission_level_destination_grant",
    }
    assert "live completion" in decision.params["body"].lower()


def test_finish_after_grounded_browser_summary_builds_terminal_answer_payload() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"skill": "finish"}]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="finish",
            recent_product_receipt_refs=["receipt:search", "receipt:extract", "receipt:verify"],
            browser_proof_index_summary={
                "public_evidence_count": 2,
                "public_evidence_ids": ["evidence:python:path-glob", "evidence:python:pathlib"],
            },
            grounded_evidence_summary={
                "present": True,
                "summary_kind": "grounded_open_world_evidence_summary",
                "summary_text": "Path.glob returns paths matching a pattern using pathlib semantics.",
                "objective_satisfaction_status": "supported",
                "negative_result_confirmed": False,
            },
        )
    )

    assert decision.capability_id == "sentinel_loop"
    assert decision.operation == "finish"
    assert decision.params["final_answer"]["answer_text"] == (
        "Path.glob returns paths matching a pattern using pathlib semantics."
    )
    assert decision.params["answer_claims"][0]["evidence_refs"] == [
        "evidence:python:path-glob",
        "evidence:python:pathlib",
    ]
    assert "honest_blocker" not in decision.params


def test_finish_after_partial_browser_summary_does_not_fabricate_terminal_answer_payload() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"skill": "finish"}]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="finish",
            recent_product_receipt_refs=["receipt:search", "receipt:extract", "receipt:verify"],
            browser_proof_index_summary={
                "public_evidence_count": 2,
                "public_evidence_ids": ["evidence:generic-nav", "evidence:generic-entity"],
            },
            grounded_evidence_summary={
                "present": True,
                "summary_kind": "grounded_browser_open_world_evidence_summary",
                "summary_text": (
                    "Open-world browser evidence entities: 6. Objective support: partial. "
                    "Entity kinds remain extensible; unknown fields stay unknown."
                ),
                "objective_satisfaction_status": "partial",
                "objective_relevance_assessed": True,
                "negative_result_confirmed": False,
            },
        )
    )

    assert decision.capability_id == "sentinel_loop"
    assert decision.operation == "finish"
    assert "final_answer" not in decision.params
    assert "honest_blocker" not in decision.params
    assert decision.params["safe_summary"]


def test_natural_finish_after_partial_browser_summary_reroutes_to_live_browser_recommendation() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"metadata": {"reply": "I have enough evidence, summarize and finish."}}]),
        request_factory=_request_factory,
    )
    context = _context(
        recommended_skill="browse_search",
        recent_product_receipt_refs=["receipt:search", "receipt:extract", "receipt:verify", "receipt:summary"],
        dispatch_summaries=[
            {"capability_id": "real_browser_control", "operation": "real_browser.search", "status": "completed"},
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.extract_evidence",
                "status": "completed",
            },
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.verify_extraction",
                "status": "completed",
            },
            {"capability_id": "sentinel_loop", "operation": "summarize_evidence", "status": "completed"},
        ],
        browser_proof_index_summary={
            "public_evidence_count": 2,
            "public_evidence_ids": ["evidence:generic-nav", "evidence:generic-entity"],
        },
        grounded_evidence_summary={
            "present": True,
            "summary_kind": "grounded_browser_open_world_evidence_summary",
            "summary_text": "Open-world browser evidence entities: 6. Objective support: partial.",
            "objective_satisfaction_status": "partial",
            "objective_relevance_assessed": True,
            "negative_result_confirmed": False,
        },
    )
    context.update(
        {
            "finish_available": False,
            "objective_satisfied": False,
            "completion_requirements": {
                "has_real_browser_search_receipt": True,
                "has_real_browser_extraction_receipt": True,
                "has_real_browser_verified_extraction_receipt": True,
                "has_grounded_evidence_summary": True,
                "has_objective_relevance_assessment": True,
                "has_terminal_answer_support": False,
                "has_terminal_blocker_support": False,
            },
            "real_browser_control_summary": {
                "latest_action": {
                    "operation": "real_browser.verify_extraction",
                    "status": "completed",
                    "receipt_count": 1,
                }
            },
        }
    )

    decision = client.complete(context)

    assert decision.capability_id == "real_browser_control"
    assert decision.operation == "real_browser.search"


def test_finish_after_negative_browser_summary_builds_honest_blocker_payload() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"skill": "finish"}]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="finish",
            recent_product_receipt_refs=["receipt:search", "receipt:verify"],
            browser_proof_index_summary={
                "public_evidence_count": 1,
                "public_evidence_ids": ["evidence:search:no-results"],
            },
            grounded_evidence_summary={
                "present": True,
                "summary_kind": "grounded_browser_negative_search_summary",
                "summary_text": "The search produced material no-results evidence.",
                "negative_result_confirmed": True,
            },
        )
    )

    assert decision.capability_id == "sentinel_loop"
    assert decision.operation == "finish"
    assert decision.params["honest_blocker"]["reason"] == "The search produced material no-results evidence."
    assert decision.params["honest_blocker"]["available_evidence_refs"] == ["evidence:search:no-results"]
    assert decision.params["answer_claims"][0]["claim_type"] == "declared_unknown"
    assert "final_answer" not in decision.params


def test_canonicalish_bounded_channel_output_is_remapped_through_granted_telegram_destination() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "capability_id": "bounded_channel",
                    "operation": "send_message",
                    "params": {
                        "adapter_id": "model_supplied_adapter",
                        "channel": "telegram",
                        "recipients": ["telegram:configured-chat"],
                        "recipient_provenance": {"telegram:configured-chat": "model_supplied_authority"},
                        "message": "Send the live Telegram update.",
                        "can_execute": True,
                    },
                }
            ]
        ),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="send_message",
            live_channel_destination_grants=[
                {
                    "adapter_id": "telegram_live_adapter",
                    "channel": "telegram",
                    "destination_ref": "telegram:configured-chat",
                }
            ],
        )
    )

    assert decision.capability_id == "bounded_channel"
    assert decision.operation == "send_message"
    assert decision.params["adapter_id"] == "telegram_live_adapter"
    assert decision.params["channel"] == "telegram"
    assert decision.params["recipients"] == ["telegram:configured-chat"]
    assert decision.params["recipient_provenance"] == {
        "telegram:configured-chat": "mission_level_destination_grant",
    }
    assert "model_supplied_authority" not in str(decision.params)
    assert "can_execute" not in decision.params


def test_send_message_body_does_not_echo_hard_boundary_prompt_terms() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "metadata": {
                        "reply": (
                            "Send the live completion update now. Do not request login, payment, "
                            "credentials, browser, or provider-native tools."
                        )
                    }
                }
            ]
        ),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="send_message",
            live_channel_destination_grants=[
                {
                    "adapter_id": "telegram_live_adapter",
                    "channel": "telegram",
                    "destination_ref": "telegram:configured-chat",
                }
            ],
        )
    )

    body = decision.params["body"].lower()
    assert decision.capability_id == "bounded_channel"
    assert decision.operation == "send_message"
    assert "sentinel completion update:" in body
    for marker in ("login", "payment", "credential", "browser", "provider-native"):
        assert marker not in body


def test_natural_finish_intent_maps_to_finish_only_after_receipt_context() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["I have enough proof. Summarize and finish."]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="finish",
            recent_product_receipt_refs=["product_action_kernel_receipt_123"],
        )
    )

    assert decision.capability_id == "sentinel_loop"
    assert decision.operation == "finish"
    assert "summary" in str(decision.params["safe_summary"]).lower()


def test_delegated_product_finish_intent_does_not_spawn_another_worker() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["The delegated product proof is complete. Summarize and finish."]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="finish",
            recent_product_receipt_refs=["product_action_kernel_receipt_worker"],
            dispatch_summaries=[
                {"capability_id": "worker_fleet", "operation": "spawn_worker", "status": "completed"},
                {"capability_id": "worker_fleet", "operation": "spawn_worker", "status": "completed"},
            ],
        )
    )

    assert decision.capability_id == "sentinel_loop"
    assert decision.operation == "finish"


def test_finish_intent_before_required_second_worker_routes_to_spawn_worker() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["The delegated product proof is complete. Summarize and finish."]),
        request_factory=_request_factory,
        preferred_skill_sequence=(
            "create_file",
            "create_file",
            "create_file",
            "run_check",
            "send_message",
            "spawn_worker",
            "spawn_worker",
            "finish",
        ),
    )

    decision = client.complete(
        _context(
            recommended_skill="finish",
            recent_product_receipt_refs=["r1", "r2", "r3", "r4", "r5", "r6"],
            dispatch_summaries=[
                {"capability_id": "workspace_patch", "operation": "apply_patch", "status": "completed"},
                {"capability_id": "workspace_patch", "operation": "apply_patch", "status": "completed"},
                {"capability_id": "workspace_patch", "operation": "apply_patch", "status": "completed"},
                {"capability_id": "code_execution_sandbox", "operation": "code_exec.run_profile", "status": "completed"},
                {"capability_id": "bounded_channel", "operation": "send_message", "status": "completed"},
                {"capability_id": "worker_fleet", "operation": "spawn_worker", "status": "completed"},
            ],
        )
    )

    assert decision.capability_id == "worker_fleet"
    assert decision.operation == "spawn_worker"


def test_ambiguous_safe_intent_uses_primary_recommended_skill() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Looks good, continue with the strongest safe next step."]),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="spawn_worker"))

    assert decision.capability_id == "worker_fleet"
    assert decision.operation == "spawn_worker"
    assert decision.params["role"] == "verifier"
    assert decision.params["max_actions"] == 1


@pytest.mark.parametrize(
    ("reply", "expected_role"),
    [
        ("Delegate a code fixer worker to inspect the implementation plan.", "code_fixer"),
        ("Spawn a verifier worker to check receipts and tests.", "verifier"),
        ("Ask a report writer worker to summarize the proof bundle.", "report_writer"),
        ("Use a researcher worker to review the workspace evidence.", "researcher"),
    ],
)
def test_natural_worker_role_intent_maps_to_reduced_worker_role(reply: str, expected_role: str) -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([reply]),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="spawn_worker"))

    assert decision.capability_id == "worker_fleet"
    assert decision.operation == "spawn_worker"
    assert decision.params["role"] == expected_role
    assert decision.params["max_actions"] == 1


def test_natural_app_creation_intent_maps_to_workspace_patch_plan() -> None:
    base_hash = "a" * 64
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Build the local app by replacing the Sentinel marker."]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="patch",
            workspace_patch_plans=[
                {
                    "target_path": "app.py",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO_SENTINEL_APP",
                    "new_text": "Sentinel model-led local app worked.",
                }
            ],
        )
    )

    assert decision.capability_id == "workspace_patch"
    assert decision.operation == "apply_patch"
    assert decision.target_ref == "app.py"
    assert decision.params == {
        "target_path": "app.py",
        "target_paths": ["app.py"],
        "expected_base_hash": base_hash,
        "old_text": "TODO_SENTINEL_APP",
        "new_text": "Sentinel model-led local app worked.",
    }


def test_natural_file_creation_intent_maps_to_workspace_create_file_plan() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Create the new app.py file for this local app."]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="create_file",
            workspace_create_file_plans=[
                {
                    "target_path": "app.py",
                    "new_text": (
                        'APP_MESSAGE = "Sentinel arbitrary local app worked."\n\n'
                        "def main():\n"
                        "    return APP_MESSAGE\n"
                    ),
                }
            ],
        )
    )

    assert decision.capability_id == "workspace_patch"
    assert decision.operation == "apply_patch"
    assert decision.target_ref == "app.py"
    assert decision.params == {
        "target_path": "app.py",
        "target_paths": ["app.py"],
        "create_file": True,
        "new_text": (
            'APP_MESSAGE = "Sentinel arbitrary local app worked."\n\n'
            "def main():\n"
            "    return APP_MESSAGE\n"
        ),
    }


def test_json_create_file_skill_preserves_model_authored_file_content() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "skill": "create_file",
                    "params": {
                        "target_path": "app.py",
                        "new_text": 'def main():\n    return "model-authored app"\n',
                    },
                }
            ]
        ),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="create_file"))

    assert decision.capability_id == "workspace_patch"
    assert decision.operation == "apply_patch"
    assert decision.params == {
        "target_path": "app.py",
        "target_paths": ["app.py"],
        "create_file": True,
        "new_text": 'def main():\n    return "model-authored app"\n',
    }


def test_patch_intent_without_patch_plan_blocks_honestly() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Create the local app now."]),
        request_factory=_request_factory,
    )

    with pytest.raises(ActionKernelError, match="MODEL_NATIVE_DECISION_PATCH_PLAN_MISSING"):
        client.complete(_context(recommended_skill="patch"))


def test_empty_visible_provider_content_blocks_instead_of_falling_back_to_patch() -> None:
    base_hash = "a" * 64
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "normalization_strategy": "empty_visible_content",
                    "visible_content_char_count": 0,
                    "json_object_detected": False,
                }
            ]
        ),
        request_factory=_request_factory,
    )

    with pytest.raises(ActionKernelError, match="MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"):
        client.complete(
            _context(
                recommended_skill="patch",
                workspace_patch_plans=[
                    {
                        "target_path": "app.py",
                        "expected_base_hash": base_hash,
                        "old_text": "TODO_SENTINEL_APP",
                        "new_text": "Sentinel model-led local app worked.",
                    }
                ],
            )
        )


def test_repeated_patch_sequence_uses_next_workspace_patch_plan() -> None:
    first_hash = "a" * 64
    second_hash = "b" * 64
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Continue with the next useful app creation step."]),
        request_factory=_request_factory,
        preferred_skill_sequence=("patch", "patch", "run_check"),
    )

    decision = client.complete(
        _context(
            recommended_skill="run_check",
            workspace_patch_plans=[
                {
                    "target_path": "app.py",
                    "expected_base_hash": first_hash,
                    "old_text": "TODO_SENTINEL_APP",
                    "new_text": "Sentinel model-led local app worked.",
                },
                {
                    "target_path": "README.md",
                    "expected_base_hash": second_hash,
                    "old_text": "TODO_SENTINEL_README",
                    "new_text": "Sentinel local app has a README.",
                },
            ],
            dispatch_summaries=[
                {"capability_id": "workspace_patch", "operation": "apply_patch", "status": "completed"}
            ],
        )
    )

    assert decision.capability_id == "workspace_patch"
    assert decision.operation == "apply_patch"
    assert decision.target_ref == "README.md"
    assert decision.params["expected_base_hash"] == second_hash
    assert decision.params["old_text"] == "TODO_SENTINEL_README"


def test_run_check_uses_bounded_check_plan_when_present() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Run the bounded local check."]),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="run_check",
            bounded_check_plan={"profile_id": "python_compileall", "args": ["."]},
        )
    )

    assert decision.capability_id == "code_execution_sandbox"
    assert decision.operation == "code_exec.run_profile"
    assert decision.params == {"profile_id": "python_compileall", "args": ["."]}


def test_preferred_skill_sequence_overrides_legacy_patch_recommendation_after_code_receipt() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Continue with the next useful mission step."]),
        request_factory=_request_factory,
        preferred_skill_sequence=("run_check", "send_message", "spawn_worker", "finish"),
    )

    decision = client.complete(
        _context(
            recommended_skill="patch",
            recent_product_receipt_refs=["product_action_kernel_receipt_code"],
            dispatch_summaries=[
                {"capability_id": "code_execution_sandbox", "operation": "code_exec.run_profile", "status": "completed"}
            ],
        )
    )

    assert decision.capability_id == "bounded_channel"
    assert decision.operation == "send_message"


def test_compound_plan_chooses_first_material_skill_before_finish() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["I will run the check, send a completion message, then finish."]),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="run_check"))

    assert decision.capability_id == "code_execution_sandbox"
    assert decision.operation == "code_exec.run_profile"


@pytest.mark.parametrize(
    ("reply", "capability_id", "operation"),
    [
        ("Log in to Alibaba and contact the supplier.", "account_authority", "login"),
        ("Pay for the best result now.", "payment_authority", "spend"),
        ("Contact supplier outside the mission grant.", "external_channel", "contact_supplier"),
    ],
)
def test_hard_boundary_intents_map_to_blockable_internal_actions(
    reply: str,
    capability_id: str,
    operation: str,
) -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([reply]),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="browse_search"))

    assert decision.capability_id == capability_id
    assert decision.operation == operation
    assert decision.params == {}


def test_credential_intent_blocks_before_action_envelope_creation() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Read the API secret and use it."]),
        request_factory=_request_factory,
    )

    with pytest.raises(ActionKernelError, match="MODEL_NATIVE_DECISION_HARD_BOUNDARY_CREDENTIAL_ACCESS"):
        client.complete(_context(recommended_skill="run_check"))


def test_raw_provider_or_reasoning_material_is_rejected_not_persisted() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient([{"raw_provider_response": {"reasoning_content": "secret chain"}}]),
        request_factory=_request_factory,
    )

    with pytest.raises(ActionKernelError, match="MODEL_NATIVE_DECISION_FORBIDDEN_RAW_MATERIAL"):
        client.complete(_context(recommended_skill="run_check"))

    assert client.safe_diagnostics[-1]["raw_model_material_persisted"] is False
    assert "secret chain" not in str(client.safe_diagnostics)


def test_product_native_client_uses_browser_native_mapper_for_verify_intent() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Verify the extracted cards."]),
        request_factory=_request_factory,
    )
    context = _context(
        recommended_skill="extract",
        dispatch_summaries=[
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.extract_product_cards",
                "status": "completed",
            }
        ],
    )
    context["completion_requirements"] = {"has_real_browser_extraction_receipt": True}

    decision = client.complete(context)

    assert decision.capability_id == "real_browser_control"
    assert decision.operation == "real_browser.verify_extraction"
    assert client.safe_diagnostics[-1]["mapped_action"] == "real_browser_control.real_browser.verify_extraction"


def test_product_native_client_maps_distinct_browser_affordance_skills() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {"skill": "follow", "params": {"ref": "link:docs"}},
                {"skill": "inspect", "params": {"ref": "link:docs"}},
                {"skill": "search", "params": {"query": "generated columns"}},
                {"skill": "extract_evidence", "params": {"entity_kind": "documentation_page"}},
                {"skill": "verify", "params": {"evidence_refs": ["evidence:docs"]}},
            ]
        ),
        request_factory=_request_factory,
    )
    context = _context(recommended_skill="follow")

    follow = client.complete(context)
    inspect = client.complete(_context(recommended_skill="inspect"))
    search = client.complete(_context(recommended_skill="search"))
    extract = client.complete(_context(recommended_skill="extract_evidence"))
    verify = client.complete(_context(recommended_skill="verify"))

    assert (follow.capability_id, follow.operation, follow.params["ref"]) == (
        "real_browser_control",
        "real_browser.open_result",
        "link:docs",
    )
    assert (inspect.capability_id, inspect.operation, inspect.params["ref"]) == (
        "real_browser_control",
        "real_browser.inspect_result",
        "link:docs",
    )
    assert (search.capability_id, search.operation, search.params["query"]) == (
        "real_browser_control",
        "real_browser.search",
        "generated columns",
    )
    assert (extract.capability_id, extract.operation, extract.params["entity_kind"]) == (
        "real_browser_control",
        "real_browser.extract_evidence",
        "documentation_page",
    )
    assert (verify.capability_id, verify.operation, verify.params["evidence_refs"]) == (
        "real_browser_control",
        "real_browser.verify_extraction",
        ["evidence:docs"],
    )


def test_product_native_client_routes_verified_browser_extraction_to_summary_lane() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["I have enough evidence, summarize and finish."]),
        request_factory=_request_factory,
    )
    context = _context(
        recommended_skill="finish",
        dispatch_summaries=[
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.extract_product_cards",
                "status": "completed",
            },
            {
                "capability_id": "real_browser_control",
                "operation": "real_browser.verify_extraction",
                "status": "completed",
            },
        ],
    )
    context["real_browser_control_summary"] = {
        "latest_action": {
            "operation": "real_browser.verify_extraction",
            "status": "completed",
            "receipt_count": 1,
        }
    }
    context["completion_requirements"] = {
        "has_real_browser_extraction_receipt": True,
        "has_real_browser_verified_extraction_receipt": True,
    }

    decision = client.complete(context)

    assert decision.capability_id == "sentinel_loop"
    assert decision.operation == "summarize_evidence"
    assert client.safe_diagnostics[-1]["mapped_action"] == "sentinel_loop.summarize_evidence"


def test_product_action_kernel_loop_dispatches_summarize_evidence(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    decision_client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence"),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "browser evidence summarized"},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_product_loop_summarize_evidence",
        mission_objective="Summarize verified browser evidence and finish.",
        decision_client=decision_client,
        max_model_calls=3,
        max_material_actions=2,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_product_action_kernel_task_loop_finish"
    assert "sentinel_loop:summarize_evidence" in result.capability_sequence
    assert result.dispatch_results[0].status.value == "completed"


def test_product_task_loop_context_exposes_verified_browser_cards_completion_lane(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    loop = ModelLedProductActionKernelTaskLoop(
        host=host,
        workspace_root=workspace,
        session_id="session_product_loop_browser_context",
        mission_objective="Summarize verified Alibaba product cards and finish.",
        decision_client=ProductActionKernelLoopDecisionClient([]),
    )
    browser_cards = {
        "browser_world_model": {
            "product_or_result_candidate_cards": [
                {
                    "title": "Lightweight sunglasses",
                    "visible_price": "EUR 4.80",
                    "currency_or_unit": "EUR / piece",
                    "minimum_order": "unknown",
                    "supplier_or_store": "Visible supplier",
                    "relevance_to_objective": "relevant",
                    "price_condition_supported": "supported",
                    "objective_relevance_assessed": True,
                    "evidence_ref_hash": "evidence_ref_hash:test",
                }
            ]
        },
        "browser_world_model_summary": {"product_or_result_candidate_count": 1},
    }
    loop.dispatch_results.extend(
        [
            UnifiedDispatchResult(
                status=DispatchStatus.COMPLETED,
                mission_id="mission_extract",
                execution_request_id="request_extract",
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
                receipt_refs=["receipt_extract"],
                finalgate_status="accepted",
                safe_context_cards=browser_cards,
            ),
            UnifiedDispatchResult(
                status=DispatchStatus.COMPLETED,
                mission_id="mission_verify",
                execution_request_id="request_verify",
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
                receipt_refs=["receipt_verify"],
                finalgate_status="accepted",
                safe_context_cards=browser_cards,
            ),
        ]
    )
    loop.product_receipt_refs.extend(["receipt_extract", "receipt_verify"])

    context = loop._compile_context()

    assert context["model_visible_available_actions"] == ["sentinel_loop.summarize_evidence"]
    assert context["completion_requirements"]["has_real_browser_extraction_receipt"] is True
    assert context["completion_requirements"]["has_real_browser_verified_extraction_receipt"] is True
    assert context["completion_requirements"]["product_or_result_candidate_card_count"] == 1
    assert context["browser_world_model"]["product_or_result_candidate_cards"][0]["title"] == "Lightweight sunglasses"
    assert context["real_browser_control_summary"]["latest_action"]["operation"] == "real_browser.verify_extraction"


def test_safe_provider_wrapper_key_is_dropped_before_intent_mapping() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "reply": "Run the bounded local check.",
                    "raw_provider_response": {"reply": "Run the bounded local check."},
                }
            ]
        ),
        request_factory=_request_factory,
    )

    decision = client.complete(_context(recommended_skill="run_check"))

    assert decision.capability_id == "code_execution_sandbox"
    assert decision.operation == "code_exec.run_profile"
    assert client.safe_diagnostics[-1]["raw_model_material_persisted"] is False


def test_visible_text_survives_strict_json_normalization_failure() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "normalization_strategy": "no_json_object_detected",
                    "content": "Run the bounded local check.",
                }
            ]
        ),
        request_factory=_request_factory,
    )

    decision = client.complete(
        _context(
            recommended_skill="run_check",
            bounded_check_plan={"profile_id": "python_compileall", "args": ["."]},
        )
    )

    assert decision.capability_id == "code_execution_sandbox"
    assert decision.operation == "code_exec.run_profile"
    assert decision.params == {"profile_id": "python_compileall", "args": ["."]}
    assert client.safe_diagnostics[-1]["failure_code"] is None
    assert client.safe_diagnostics[-1]["mapped_action"] == "code_execution_sandbox.code_exec.run_profile"


def test_model_native_client_drives_product_loop_bundle_and_replay(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Real Monster Attempt 1\n", encoding="utf-8")
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                "Run the bounded fake/local check.",
                {"metadata": {"reply": "Send the completion message to the bounded local channel."}},
                "Delegate a verifier worker.",
                "I have enough product proof. Summarize and finish.",
            ]
        ),
        request_factory=_request_factory,
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_monster_attempt1_controlled",
        mission_objective="Build a useful local AI app proof path, run checks, send completion, delegate verifier, and finish.",
        decision_client=client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=5,
        max_material_actions=3,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Controlled Monster Runtime product loop proof.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 3
    assert len(result.product_receipt_refs) == 3
    assert client.call_count == 4
    assert replay.reexecuted_actions is False
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True
    assert export.accepted is True
    assert verified.accepted is True


def test_model_native_client_patches_local_app_then_checks_channel_worker_finish(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "app.py").write_text(
        'def main():\n    return "TODO_SENTINEL_APP"\n\nif __name__ == "__main__":\n    print(main())\n',
        encoding="utf-8",
    )
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                "Build the local app.",
                "Run the bounded local check.",
                {"metadata": {"reply": "Send the completion message to the bounded local channel."}},
                "Delegate a verifier worker.",
                "I have enough product proof. Summarize and finish.",
            ]
        ),
        request_factory=_request_factory,
        preferred_skill_sequence=("patch", "run_check", "send_message", "spawn_worker", "finish"),
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_pack1_local_app",
        mission_objective="Create a useful local Sentinel app, run a bounded check, notify the local channel, delegate verifier, and finish.",
        decision_client=client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=6,
        max_material_actions=4,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Controlled local app creation product loop proof.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 4
    assert len(result.product_receipt_refs) == 4
    assert client.call_count == 5
    assert "Sentinel model-led local app worked." in (workspace / "app.py").read_text(encoding="utf-8")
    assert replay.reexecuted_actions is False
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True
    assert export.accepted is True
    assert verified.accepted is True


def test_model_native_client_creates_multi_file_local_app_then_checks_channel_worker_finish(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    (workspace / "tests").mkdir(parents=True)
    (workspace / "app.py").write_text(
        'APP_MESSAGE = "TODO_SENTINEL_APP_MESSAGE"\n\n'
        "def main():\n"
        "    return APP_MESSAGE\n\n"
        'if __name__ == "__main__":\n'
        "    print(main())\n",
        encoding="utf-8",
    )
    (workspace / "README.md").write_text("# Sentinel Local App\n\nTODO_SENTINEL_APP_README\n", encoding="utf-8")
    (workspace / "tests" / "test_app.py").write_text("TODO_SENTINEL_APP_TEST\n", encoding="utf-8")
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                "Create the local app implementation.",
                "Update the README for the app.",
                "Add the app test file.",
                "Run the bounded local check.",
                "Send the completion message to the bounded local channel.",
                "Delegate a verifier worker.",
                "The app has enough proof. Summarize and finish.",
            ]
        ),
        request_factory=_request_factory,
        preferred_skill_sequence=("patch", "patch", "patch", "run_check", "send_message", "spawn_worker", "finish"),
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_pack2_multi_file_app",
        mission_objective="Create a useful multi-file local Sentinel app, run a bounded check, notify, delegate verifier, and finish.",
        decision_client=client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=8,
        max_material_actions=6,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Controlled multi-file local app creation product loop proof.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 6
    assert len(result.product_receipt_refs) == 6
    assert client.call_count == 7
    assert "Sentinel model-led local app worked." in (workspace / "app.py").read_text(encoding="utf-8")
    assert "ProductActionKernel" in (workspace / "README.md").read_text(encoding="utf-8")
    assert "test_main_returns_message" in (workspace / "tests" / "test_app.py").read_text(encoding="utf-8")
    assert replay.reexecuted_actions is False
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True
    assert export.accepted is True
    assert verified.accepted is True


def test_model_native_client_creates_arbitrary_local_app_files_then_checks_channel_worker_finish(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "MISSION.md").write_text(
        "# Arbitrary local app mission\n\n"
        "Create a tiny Python app from scratch with README and tests.\n",
        encoding="utf-8",
    )
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                "Create app.py for the local Sentinel app.",
                "Create README.md for the app.",
                "Create tests/test_app.py for the app.",
                "Run the bounded local check.",
                "Send the completion message to the bounded local channel.",
                "Delegate a verifier worker.",
                "The app has enough product proof. Summarize and finish.",
            ]
        ),
        request_factory=_request_factory,
        preferred_skill_sequence=(
            "create_file",
            "create_file",
            "create_file",
            "run_check",
            "send_message",
            "spawn_worker",
            "finish",
        ),
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_pack3_arbitrary_file_app",
        mission_objective=(
            "Create an arbitrary local Sentinel app from scratch, run a bounded check, notify, "
            "delegate verifier, and finish."
        ),
        decision_client=client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=8,
        max_material_actions=6,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Controlled arbitrary local app file creation product loop proof.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 6
    assert len(result.product_receipt_refs) == 6
    assert client.call_count == 7
    assert "Sentinel arbitrary local app worked." in (workspace / "app.py").read_text(encoding="utf-8")
    assert "from scratch" in (workspace / "README.md").read_text(encoding="utf-8")
    assert "test_main_returns_message" in (workspace / "tests" / "test_app.py").read_text(encoding="utf-8")
    assert replay.reexecuted_actions is False
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True
    assert export.accepted is True
    assert verified.accepted is True


def test_number_analyzer_objective_creates_useful_app_files_then_checks_exports_and_finishes(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "MISSION.md").write_text(
        "# Useful app mission\n\n"
        "Create a tiny Python number analyzer from scratch. It should compute count, total, and average.\n",
        encoding="utf-8",
    )
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                "Create app.py for the useful number analyzer.",
                "Create README.md for the number analyzer.",
                "Create tests/test_app.py for count, total, and average.",
                "Run the bounded local check.",
                "Send the completion message to the bounded local channel.",
                "Delegate a verifier worker.",
                "The useful app has enough product proof. Summarize and finish.",
            ]
        ),
        request_factory=_request_factory,
        preferred_skill_sequence=(
            "create_file",
            "create_file",
            "create_file",
            "run_check",
            "send_message",
            "spawn_worker",
            "finish",
        ),
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_pack_useful_number_analyzer_app",
        mission_objective=(
            "Create a useful tiny Python number analyzer app from scratch. "
            "The app must expose analyze_numbers(values) with count, total, and average, "
            "run a bounded pytest check, notify the local channel, delegate verifier, and finish."
        ),
        decision_client=client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=8,
        max_material_actions=6,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Controlled useful number analyzer product loop proof.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    app_text = (workspace / "app.py").read_text(encoding="utf-8")
    test_text = (workspace / "tests" / "test_app.py").read_text(encoding="utf-8")
    readme_text = (workspace / "README.md").read_text(encoding="utf-8")

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert "def analyze_numbers" in app_text
    assert "count" in app_text
    assert "total" in app_text
    assert "average" in app_text
    assert "Sentinel useful number analyzer worked." in app_text
    assert "analyze_numbers([1, 2, 3])" in test_text
    assert "average" in test_text
    assert "number analyzer" in readme_text.lower()
    assert "Sentinel arbitrary local app worked." not in app_text
    assert replay.reexecuted_actions is False
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True
    assert export.accepted is True
    assert verified.accepted is True


def test_phase2_quality_gate_handles_root_test_hygiene_and_two_workers_before_finish(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "skill": "create_file",
                    "params": {
                        "target_path": "test_app.py",
                        "new_text": (
                            "from app import analyze_numbers\n\n\n"
                            "def test_root_file_is_malformed():\n"
                            "    result([1, 2, 3])\n"
                        ),
                    },
                },
                "Continue creating the useful number analyzer product files.",
                "Continue creating the useful number analyzer product files.",
                "Continue creating the useful number analyzer product files.",
                "Continue creating the test hygiene config.",
                "Run the bounded semantic check.",
                "Send the bounded local completion message.",
                "Delegate a researcher worker to inspect the product evidence.",
                "The delegated product proof is complete. Summarize and finish.",
                "The delegated product proof is complete. Summarize and finish.",
            ]
        ),
        request_factory=_request_factory,
        preferred_skill_sequence=(
            "create_file",
            "create_file",
            "create_file",
            "run_check",
            "send_message",
            "spawn_worker",
            "spawn_worker",
            "finish",
        ),
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_monster_attempt6b_local_quality_gate",
        mission_objective=(
            "Create a useful tiny Python number analyzer app from scratch. "
            "It must expose analyze_numbers(values) with count, total, and average, "
            "run semantic tests, send a bounded fake/local channel update, "
            "delegate a researcher worker and a verifier worker under reduced authority, and finish."
        ),
        decision_client=client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=10,
        max_material_actions=9,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)
    worker_roles = [
        str(item.get("worker_role") or "")
        for item in _collect_worker_receipts_for_test(host, result.mission_ids)
    ]

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "worker_fleet:spawn_worker",
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert (workspace / "pytest.ini").read_text(encoding="utf-8") == "[pytest]\ntestpaths = tests\n"
    assert (workspace / "tests" / "test_app.py").is_file()
    assert sorted(worker_roles) == ["report_writer", "researcher"]
    assert replay.reexecuted_actions is False
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0


def test_product_loop_recovers_duplicate_create_file_target_to_next_missing_app_file(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "MISSION.md").write_text(
        "# Arbitrary local app mission\n\nCreate a tiny Python app from scratch.\n",
        encoding="utf-8",
    )
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {
                    "skill": "create_file",
                    "params": {
                        "target_path": "app.py",
                        "new_text": 'def main():\n    return "Sentinel arbitrary local app worked."\n',
                    },
                },
                {
                    "skill": "create_file",
                    "params": {
                        "target_path": "app.py",
                        "new_text": 'def main():\n    return "duplicate app"\n',
                    },
                },
                "Continue with the next missing app file.",
                "Continue with the next missing app file.",
                "Run the bounded local check.",
                "Send the completion message to the bounded local channel.",
                "Delegate a verifier worker.",
                "The app has enough product proof. Summarize and finish.",
            ]
        ),
        request_factory=_request_factory,
        preferred_skill_sequence=(
            "create_file",
            "create_file",
            "create_file",
            "run_check",
            "send_message",
            "spawn_worker",
            "finish",
        ),
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_create_duplicate_recovery",
        mission_objective="Create an arbitrary local Sentinel app from scratch, recover duplicates, and finish.",
        decision_client=client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=8,
        max_material_actions=6,
        max_recoverable_action_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.material_action_count == 6
    assert len(result.product_receipt_refs) == 6
    assert (
        (workspace / "app.py").read_text(encoding="utf-8")
        == 'def main():\n    return "Sentinel arbitrary local app worked."\n'
    )
    assert (workspace / "README.md").is_file()
    assert (workspace / "tests" / "test_app.py").is_file()
    assert client.safe_diagnostics[2]["mapped_action"] == "workspace_patch.apply_patch"


def test_product_loop_can_recover_once_from_empty_visible_content_before_material_action(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Recoverable product loop\n", encoding="utf-8")
    decision_client = _RecoveringDecisionClient(
        [
            ActionKernelError("MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"),
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass", "args": ["."]},
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Recovered from empty first model turn and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_empty_content_recovery",
        mission_objective="Recover from one empty provider turn, run a bounded check, and finish.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=1,
        max_recoverable_model_decision_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.model_call_count == 3
    assert result.capability_sequence == (
        "code_execution_sandbox:code_exec.run_profile",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 1
    assert decision_client.contexts[1]["recoverable_decision_observations"][0]["failure_code"] == (
        "MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"
    )


def test_product_loop_default_recovers_one_visible_content_unsupported_before_material_action(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Recoverable product loop\n", encoding="utf-8")
    decision_client = _RecoveringDecisionClient(
        [
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": _sha256_file(workspace / "README.md"),
                    "old_text": "# Recoverable product loop\n",
                    "new_text": "# Recoverable product loop\n\nRecovered from unsupported visible content.\n",
                },
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Recovered from unsupported first visible content and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_visible_content_unsupported_default_recovery",
        mission_objective="Recover once from unsupported first visible content, patch, and finish.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=4,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 1
    assert decision_client.contexts[1]["recoverable_decision_observations"][0]["failure_code"] == (
        "MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"
    )


def test_product_loop_routes_model_native_send_to_granted_telegram_transport(tmp_path, monkeypatch) -> None:
    calls: list[object] = []

    class _TelegramResponse:
        status = 200

        def read(self, _limit: int = 8192) -> bytes:
            return b'{"ok":true,"result":{"message_id":4242}}'

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return _TelegramResponse()

    monkeypatch.setenv("SENTINEL_TELEGRAM_BOT_TOKEN", "test-token-not-persisted")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CHAT_ID", "test-chat-not-persisted")
    monkeypatch.setattr(channel_adapter, "_default_urlopen", fake_urlopen)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Live channel product spine\n", encoding="utf-8")
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(
            [
                {"metadata": {"reply": "Send the bounded live Telegram completion update now."}},
                {"skill": "finish", "params": {"safe_summary": "Telegram product spine send completed."}},
            ]
        ),
        request_factory=_request_factory,
        preferred_skill_sequence=("send_message", "finish"),
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_live_telegram_product_spine",
        mission_objective="Send one bounded live Telegram completion update and finish.",
        decision_client=client,
        allowed_domains=("telegram:configured-chat",),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED, result.blocked_reason
    assert result.capability_sequence == ("bounded_channel:send_message", "sentinel_loop:finish")
    assert len(calls) == 1
    rendered = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore") for path in (tmp_path / "runs").rglob("*.json")
    )
    assert "telegram:4242" in rendered
    assert "test-token-not-persisted" not in rendered
    assert "test-chat-not-persisted" not in rendered


def test_product_loop_default_blocks_repeated_visible_content_unsupported_before_material_action(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Recoverable product loop\n", encoding="utf-8")
    decision_client = _RecoveringDecisionClient(
        [
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_visible_content_unsupported_repeated_default_block",
        mission_objective="Default behavior should block repeated unsupported provider turns before material work.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"
    assert result.material_action_count == 0
    assert result.product_receipt_refs == ()


def test_product_loop_can_recover_from_empty_visible_content_after_material_receipt(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Recoverable product loop\n", encoding="utf-8")
    decision_client = _RecoveringDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass", "args": ["."]},
            ),
            ActionKernelError("MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"),
            ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                params={
                    "adapter_id": "monster_fake_channel",
                    "channel": "webhook",
                    "body": "Recovered after material receipt.",
                    "recipients": ["founder@example.com"],
                    "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
                    "evidence_refs": ["evidence:post_material_recovery"],
                },
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Recovered after material receipt and finished."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_post_material_empty_content_recovery",
        mission_objective="Recover from an empty provider turn after a first material receipt.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=5,
        max_material_actions=2,
        max_recoverable_model_decision_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.model_call_count == 4
    assert result.capability_sequence == (
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 2
    assert len(result.product_receipt_refs) == 2
    assert decision_client.contexts[2]["recoverable_decision_observations"][0]["failure_code"] == (
        "MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"
    )
    assert decision_client.contexts[2]["recent_product_receipt_refs"] == [result.product_receipt_refs[0]]


def test_product_loop_default_recovers_empty_visible_content_after_material_receipt(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Recoverable product loop\n", encoding="utf-8")
    decision_client = _RecoveringDecisionClient(
        [
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": _sha256_file(workspace / "README.md"),
                    "old_text": "# Recoverable product loop\n",
                    "new_text": "# Recoverable product loop\n\nFirst material receipt exists.\n",
                },
            ),
            ActionKernelError("MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"),
            ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                params={
                    "adapter_id": "monster_fake_channel",
                    "channel": "webhook",
                    "body": "Recovered after post-material empty provider turn.",
                    "recipients": ["founder@example.com"],
                    "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
                    "evidence_refs": ["evidence:post_material_recovery_default"],
                },
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Default post-material empty provider recovery completed."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_post_material_empty_content_default_recovery",
        mission_objective="Recover by default from an empty provider turn after a first material receipt.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=5,
        max_material_actions=2,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "bounded_channel:send_message",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 2
    assert decision_client.contexts[2]["recoverable_decision_observations"][0]["failure_code"] == (
        "MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"
    )


def test_product_loop_uses_post_app_recovery_plans_after_repeated_provider_friction(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app_text = (
        "def analyze_numbers(values):\n"
        "    if not values:\n"
        "        return {\"count\": 0, \"total\": 0, \"average\": 0.0}\n"
        "    count = len(values)\n"
        "    total = sum(values)\n"
        "    average = total / count\n"
        "    return {\"count\": count, \"total\": total, \"average\": average}\n"
    )
    decision_client = _RecoveringDecisionClient(
        [
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "app.py",
                    "target_paths": ["app.py"],
                    "create_file": True,
                    "new_text": app_text,
                },
            ),
            ActionKernelError("MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
            ActionKernelError("MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED"),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_post_app_artifact_recovery_plans",
        mission_objective=(
            "Create a useful tiny Python number analyzer app from scratch. "
            "The app must expose analyze_numbers(values) with count, total, and average, "
            "run bounded semantic tests, notify the local channel, delegate researcher and report_writer workers, and finish."
        ),
        decision_client=decision_client,
        allowed_domains=("example.com", "local.worker"),
        max_model_calls=9,
        max_material_actions=8,
        max_recoverable_action_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "workspace_patch:apply_patch",
        "code_execution_sandbox:code_exec.run_profile",
        "bounded_channel:send_message",
        "worker_fleet:spawn_worker",
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert (workspace / "README.md").is_file()
    assert (workspace / "tests" / "test_app.py").is_file()
    test_text = (workspace / "tests" / "test_app.py").read_text(encoding="utf-8")
    assert "from app import analyze_numbers" in test_text
    assert "import analyze_numbers, main" not in test_text
    worker_receipts = _collect_worker_receipts_for_test(host, result.mission_ids)
    assert {receipt["worker_role"] for receipt in worker_receipts} == {"researcher", "report_writer"}


def test_created_app_workspace_recommends_run_check_not_dead_patch(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    (workspace / "tests").mkdir(parents=True)
    (workspace / "app.py").write_text(
        'APP_MESSAGE = "Sentinel arbitrary local app worked."\n\n'
        "def main():\n"
        "    return APP_MESSAGE\n",
        encoding="utf-8",
    )
    (workspace / "README.md").write_text("# Sentinel Local App\n", encoding="utf-8")
    (workspace / "tests" / "test_app.py").write_text(
        "from app import main\n\n\n"
        "def test_main_returns_message():\n"
        '    assert main() == "Sentinel arbitrary local app worked."\n',
        encoding="utf-8",
    )
    decision_client = _RecoveringDecisionClient([ActionKernelError("STOP_AFTER_CONTEXT_CAPTURE")])

    host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_created_app_ready_for_check",
        mission_objective="Create a tiny Python app from scratch, run checks, send completion, and finish.",
        decision_client=decision_client,
        max_model_calls=1,
        max_material_actions=1,
    )

    assert decision_client.contexts[0]["primary_model_recommended_next_skill"] == "run_check"
    assert decision_client.contexts[0]["primary_model_next_recommended_skills"][0] == "run_check"
    assert decision_client.contexts[0]["_bounded_check_plan"] == {
        "profile_id": "pytest_file",
        "args": ["tests/test_app.py"],
    }
    assert decision_client.contexts[0]["workspace_file_summaries"][0]["path"] == "app.py"
    assert "def main" in decision_client.contexts[0]["workspace_file_summaries"][0]["content_excerpt"]


def test_root_level_test_file_is_repair_plan_before_bounded_check(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    (workspace / "tests").mkdir(parents=True)
    (workspace / "app.py").write_text(
        "def analyze_numbers(values):\n"
        "    numbers = list(values)\n"
        "    return {\"count\": len(numbers), \"total\": sum(numbers), \"average\": 0 if not numbers else sum(numbers) / len(numbers)}\n",
        encoding="utf-8",
    )
    (workspace / "test_app.py").write_text(
        "from app import analyze_numbers\n\n\n"
        "def test_root_file_is_malformed():\n"
        "    result([1, 2, 3])\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_app.py").write_text(
        "from app import analyze_numbers\n\n\n"
        "def test_analyze_numbers():\n"
        "    assert analyze_numbers([1, 2, 3])[\"total\"] == 6\n",
        encoding="utf-8",
    )
    (workspace / "README.md").write_text("# Sentinel Number Analyzer\n", encoding="utf-8")
    decision_client = _RecoveringDecisionClient([ActionKernelError("STOP_AFTER_CONTEXT_CAPTURE")])

    host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_root_test_hygiene",
        mission_objective="Create a useful tiny Python number analyzer app from scratch, run checks, send completion, and finish.",
        decision_client=decision_client,
        max_model_calls=1,
        max_material_actions=1,
    )

    assert decision_client.contexts[0]["primary_model_recommended_next_skill"] == "create_file"
    assert decision_client.contexts[0]["_workspace_create_file_plans"][0]["target_path"] == "pytest.ini"
    assert "testpaths = tests" in decision_client.contexts[0]["_workspace_create_file_plans"][0]["new_text"]


def test_exhausted_create_sequence_still_honors_hygiene_create_plan_before_run_check() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Continue with the next product proof."]),
        request_factory=_request_factory,
        preferred_skill_sequence=(
            "create_file",
            "create_file",
            "create_file",
            "run_check",
            "send_message",
            "spawn_worker",
            "finish",
        ),
    )

    decision = client.complete(
        _context(
            recommended_skill="run_check",
            recent_product_receipt_refs=["r1", "r2", "r3"],
            dispatch_summaries=[
                {"capability_id": "workspace_patch", "operation": "apply_patch", "status": "completed"},
                {"capability_id": "workspace_patch", "operation": "apply_patch", "status": "completed"},
                {"capability_id": "workspace_patch", "operation": "apply_patch", "status": "completed"},
            ],
            workspace_create_file_plans=[
                {"target_path": "pytest.ini", "new_text": "[pytest]\ntestpaths = tests\n"}
            ],
            bounded_check_plan={"profile_id": "pytest_file", "args": ["tests/test_app.py"]},
        )
    )

    assert decision.capability_id == "workspace_patch"
    assert decision.operation == "apply_patch"
    assert decision.target_ref == "pytest.ini"


def test_product_loop_recovers_failed_semantic_check_with_patch_then_finish(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    (workspace / "tests").mkdir(parents=True)
    bad_app = 'def greet(name):\n    return f"Hello, {name}!"\n'
    fixed_app = (
        'APP_MESSAGE = "Sentinel arbitrary local app worked."\n\n'
        "def main():\n"
        "    return APP_MESSAGE\n"
    )
    app_path = workspace / "app.py"
    app_path.write_text(bad_app, encoding="utf-8")
    (workspace / "README.md").write_text("# Sentinel Local App\n", encoding="utf-8")
    (workspace / "tests" / "test_app.py").write_text(
        "from app import main\n\n\n"
        "def test_main_returns_message():\n"
        '    assert main() == "Sentinel arbitrary local app worked."\n',
        encoding="utf-8",
    )
    decision_client = _RecoveringDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "pytest_file", "args": ["tests/test_app.py"]},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "app.py",
                    "expected_base_hash": _sha256_file(app_path),
                    "old_text": bad_app,
                    "new_text": fixed_app,
                },
            ),
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "pytest_file", "args": ["tests/test_app.py"]},
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Semantic app test recovered and passed."},
            ),
        ]
    )

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_semantic_check_recovery",
        mission_objective="Create and repair a tiny Python app from scratch until semantic tests pass.",
        decision_client=decision_client,
        max_model_calls=4,
        max_material_actions=3,
        max_recoverable_action_failures=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "code_execution_sandbox:code_exec.run_profile",
        "workspace_patch:apply_patch",
        "code_execution_sandbox:code_exec.run_profile",
        "sentinel_loop:finish",
    )
    assert decision_client.contexts[1]["recoverable_action_observations"][0]["failure_code"] == "code_exec_failed"
    assert decision_client.contexts[1]["primary_model_recommended_next_skill"] == "patch"
    assert app_path.read_text(encoding="utf-8") == fixed_app


def test_sequence_skips_exhausted_create_file_after_semantic_check_passed() -> None:
    client = ProductModelNativeDecisionClient(
        model_client=_FakeModelClient(["Continue with the next product proof."]),
        request_factory=_request_factory,
        preferred_skill_sequence=(
            "create_file",
            "create_file",
            "create_file",
            "run_check",
            "send_message",
            "finish",
        ),
    )

    decision = client.complete(
        _context(
            recommended_skill="create_file",
            recent_product_receipt_refs=["r1", "r2", "r3", "r4"],
            dispatch_summaries=[
                {
                    "status": "completed",
                    "capability_id": "workspace_patch",
                    "operation": "apply_patch",
                },
                {
                    "status": "completed",
                    "capability_id": "workspace_patch",
                    "operation": "apply_patch",
                },
                {
                    "status": "completed",
                    "capability_id": "workspace_patch",
                    "operation": "apply_patch",
                },
                {
                    "status": "completed",
                    "capability_id": "code_execution_sandbox",
                    "operation": "code_exec.run_profile",
                },
            ],
            workspace_create_file_plans=[],
            workspace_patch_plans=[],
            bounded_check_plan={"profile_id": "pytest_file", "args": ["tests/test_app.py"]},
        )
    )

    assert decision.capability_id == "bounded_channel"
    assert decision.operation == "send_message"


class _FakeModelClient:
    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = list(outputs)
        self.requests: list[Any] = []

    def complete(self, request: Any) -> Any:
        self.requests.append(request)
        if not self.outputs:
            raise AssertionError("fake model exhausted")
        return self.outputs.pop(0)


class _RecoveringDecisionClient:
    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = list(outputs)
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        self.contexts.append(context)
        if not self.outputs:
            raise AssertionError("recovering model exhausted")
        output = self.outputs.pop(0)
        if isinstance(output, ActionKernelError):
            raise output
        return output


def _request_factory(context: dict[str, Any], prompt: str) -> dict[str, str]:
    assert "ActionEnvelope" not in prompt
    return {
        "runtime": "product_model_native_decision_test",
        "prompt_hash": str(abs(hash(prompt))),
        "context_loop_id": str(context["loop_id"]),
    }


def _sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collect_worker_receipts_for_test(host: SentinelRuntimeHost, mission_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for mission_id in mission_ids:
        mission_dir = host.kernel.store.mission_dir(mission_id)
        for path in sorted(mission_dir.glob("worker_fleet/receipts/*.json")):
            receipts.append(json.loads(path.read_text(encoding="utf-8")))
    return receipts


def _context(
    *,
    recommended_skill: str,
    recent_product_receipt_refs: list[str] | None = None,
    dispatch_summaries: list[dict[str, object]] | None = None,
    workspace_patch_plans: list[dict[str, object]] | None = None,
    workspace_create_file_plans: list[dict[str, object]] | None = None,
    bounded_check_plan: dict[str, object] | None = None,
    live_channel_destination_grants: list[dict[str, object]] | None = None,
    browser_proof_index_summary: dict[str, object] | None = None,
    grounded_evidence_summary: dict[str, object] | None = None,
) -> dict[str, Any]:
    action_map = {
        "create_file": "workspace_patch.apply_patch",
        "run_check": "code_execution_sandbox.code_exec.run_profile",
        "send_message": "bounded_channel.send_message",
        "spawn_worker": "worker_fleet.spawn_worker",
        "finish": "sentinel_loop.finish",
        "observe": "real_browser_control.real_browser.observe",
        "navigate": "real_browser_control.real_browser.open",
        "search": "real_browser_control.real_browser.search",
        "follow": "real_browser_control.real_browser.open_result",
        "inspect": "real_browser_control.real_browser.inspect_result",
        "extract_evidence": "real_browser_control.real_browser.extract_evidence",
        "verify": "real_browser_control.real_browser.verify_extraction",
        "browse_search": "real_browser_control.real_browser.search",
        "extract": "real_browser_control.real_browser.extract_product_cards",
    }
    return {
        "loop_id": "loop_test",
        "mission_objective": "Build a useful local AI app, run checks, send completion, and finish.",
        "primary_model_surface": "model_visible_skills",
        "primary_model_language": "simple_mission_skills",
        "action_envelope_language": "internal_runtime_only",
        "model_visible_skills": list(action_map),
        "primary_model_recommended_next_skill": recommended_skill,
        "primary_model_next_recommended_skills": [recommended_skill],
        "runtime_internal_action_map": action_map,
        "recent_product_receipt_refs": recent_product_receipt_refs or [],
        "dispatch_summaries": dispatch_summaries or [],
        "_workspace_patch_plans": workspace_patch_plans or [],
        "_workspace_create_file_plans": workspace_create_file_plans or [],
        "_bounded_check_plan": bounded_check_plan or {},
        "live_channel_destination_grants": live_channel_destination_grants or [],
        "browser_proof_index_summary": browser_proof_index_summary or {},
        "grounded_evidence_summary": grounded_evidence_summary or {},
    }
