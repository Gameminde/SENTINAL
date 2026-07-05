from __future__ import annotations

from typing import Any

import pytest

from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError
from sentinel.operator.mission_artifact_bundle import (
    MissionArtifactBundleExporter,
    MissionArtifactBundleVerifier,
)
from sentinel.operator.product_model_native_decision_client import (
    ProductModelNativeDecisionClient,
)
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost


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


def test_product_loop_default_blocks_empty_visible_content_before_material_action(tmp_path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Recoverable product loop\n", encoding="utf-8")
    decision_client = _RecoveringDecisionClient([ActionKernelError("MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT")])

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_real_product_empty_content_default_block",
        mission_objective="Default behavior should not silently retry empty provider turns.",
        decision_client=decision_client,
        allowed_domains=("example.com",),
        max_model_calls=2,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT"
    assert result.material_action_count == 0
    assert result.product_receipt_refs == ()


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


def _context(
    *,
    recommended_skill: str,
    recent_product_receipt_refs: list[str] | None = None,
    dispatch_summaries: list[dict[str, object]] | None = None,
    workspace_patch_plans: list[dict[str, object]] | None = None,
    bounded_check_plan: dict[str, object] | None = None,
) -> dict[str, Any]:
    action_map = {
        "run_check": "code_execution_sandbox.code_exec.run_profile",
        "send_message": "bounded_channel.send_message",
        "spawn_worker": "worker_fleet.spawn_worker",
        "finish": "sentinel_loop.finish",
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
        "_bounded_check_plan": bounded_check_plan or {},
    }
