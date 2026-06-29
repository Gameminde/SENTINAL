from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionKernelError, ActionResult
from sentinel.operator.code_execution_sandbox_models import CodeExecutionReceipt
from sentinel.operator.code_execution_sandbox_replay import CodeExecutionReplayView
from sentinel.operator.code_execution_sandbox_runtime import (
    CodeExecutionProcessResult,
    CodeExecutionSandboxRuntime,
    CodeExecutionSandboxRuntimeError,
)
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoop, ModelLedTaskLoopReplay, ModelLedTaskLoopStatus
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.read_only_operator_spine import ReadOnlyActionKind, ReadOnlyDecision, ReadOnlyDecisionClient, ReadOnlyProductionSpineSession
from sentinel.operator.workspace_patch_runtime import WorkspacePatchCheckResult, WorkspacePatchRuntime


def test_power_pack3_allowed_fake_pass_and_compileall_profiles_execute_with_receipts(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    before_workspace = _workspace_fingerprint(fixture.workspace)

    fake_result = fixture.code_runtime.execute(
        ActionEnvelope(capability_id="code_execution_sandbox", operation="code_exec.run_profile", params={"profile_id": "fake_pass"}),
        authority=fixture.authority,
        context={},
    )
    compile_result = fixture.code_runtime.execute(
        ActionEnvelope(
            capability_id="code_execution_sandbox",
            operation="code_exec.run_profile",
            params={"profile_id": "python_compileall", "args": ["src"]},
        ),
        authority=fixture.authority,
        context={},
    )

    assert fake_result.status == "passed"
    assert compile_result.status == "passed"
    assert set(fixture.code_runtime.profiles) >= {"fake_pass", "python_compileall", "pytest_file", "python_module_smoke"}
    assert fake_result.material_action is True
    assert compile_result.material_action is True
    assert fixture.code_runtime.command_execution_count == 2
    assert _workspace_fingerprint(fixture.workspace) == before_workspace
    assert not list(fixture.workspace.rglob("__pycache__"))
    assert fixture.load_code_receipt(fake_result.receipt_refs).verify_hash()
    assert fixture.load_code_receipt(compile_result.receipt_refs).verify_hash()


def test_power_pack3_pytest_file_profile_executes_specific_workspace_test(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)

    result = fixture.code_runtime.execute(
        ActionEnvelope(
            capability_id="code_execution_sandbox",
            operation="code_exec.run_profile",
            params={"profile_id": "pytest_file", "args": ["tests/test_smoke.py"]},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "passed"
    assert result.receipt_refs[0].startswith("code_exec_receipt_")
    assert fixture.code_runtime.command_execution_count == 1


def test_power_pack3_blocks_unknown_raw_shell_metacharacters_path_escape_network_and_credentials(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("print('outside')\n", encoding="utf-8")

    blocked_params = [
        {"profile_id": "unknown", "args": []},
        {"command": "python -m pytest"},
        {"profile_id": "fake_pass", "args": ["&&"]},
        {"profile_id": "python_compileall", "args": ["../outside.py"]},
        {"profile_id": "python_compileall", "args": [str(outside)]},
        {"profile_id": "fake_pass", "args": ["https://example.com"]},
        {"profile_id": "fake_pass", "args": ["Authorization: Bearer token"]},
    ]

    for params in blocked_params:
        with pytest.raises((CodeExecutionSandboxRuntimeError, ValueError)):
            fixture.code_runtime.execute(
                ActionEnvelope(capability_id="code_execution_sandbox", operation="code_exec.run_profile", params=params),
                authority=fixture.authority,
                context={},
            )

    assert fixture.code_runtime.command_execution_count == 0


def test_power_pack3_bounds_and_redacts_stdout_stderr_and_records_timeout_honestly(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, runner=_ScriptedRunner(exit_code=1, stdout="ok " * 200, stderr="secret=hidden\n" * 80, timed_out=True))

    result = fixture.code_runtime.execute(
        ActionEnvelope(
            capability_id="code_execution_sandbox",
            operation="code_exec.run_profile",
            params={"profile_id": "python_compileall", "args": ["src"]},
        ),
        authority=fixture.authority,
        context={},
    )
    receipt = fixture.load_code_receipt(result.receipt_refs)

    assert result.status == "timeout"
    assert result.blocked_reason == "code_exec_timeout"
    assert receipt.status == "timeout"
    assert len(receipt.stdout_excerpt) <= 240
    assert len(receipt.stderr_excerpt) <= 240
    assert "secret=hidden" not in receipt.safe_model_dump()["stderr_excerpt"]


def test_power_pack3_generic_loop_runs_read_only_code_exec_finish_and_context_summarizes_code_execution(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="read_only_research", operation="list_directory", params={"path": "."}),
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "code execution loop done"}),
        ]
    )

    result = fixture.loop(decisions).run()
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)
    code_replay = CodeExecutionReplayView.from_store(
        fixture.kernel.store,
        mission_id=fixture.mission_id,
        workspace_root=fixture.workspace,
    )

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED
    assert result.capability_sequence == (
        "read_only_research:list_directory",
        "code_execution_sandbox:code_exec.run_profile",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 2
    assert decisions.contexts[2]["code_execution_summary"][0]["profile_id"] == "fake_pass"
    assert fixture.code_runtime.command_execution_count == 1
    assert loop_replay.command_executions_delta == 0
    assert code_replay.command_executions_delta == 0
    assert code_replay.receipt_writes_delta == 0
    assert code_replay.artifact_hashes_stable is True


def test_power_pack3_generic_loop_runs_patch_code_exec_read_only_verify_finish(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    base_hash = fixture.readme_hash()
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: run sandbox\n",
                    "new_text": "TODO: sandbox command verified\n",
                },
            ),
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "python_compileall", "args": ["src"]},
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="search_text",
                params={"path": ".", "query": "sandbox command verified"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "patch plus code exec done"}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert "sandbox command verified" in fixture.readme.read_text(encoding="utf-8")
    assert fixture.patch_runtime.patch_application_count == 1
    assert fixture.code_runtime.command_execution_count == 1
    assert fixture.read_only_tool_calls == 1
    assert any(ref.startswith("workspace_patch_receipt_") for ref in result.receipt_refs)
    assert any(ref.startswith("code_exec_receipt_") for ref in result.receipt_refs)


def test_power_pack3_production_read_only_verification_uses_granted_workspace_authority(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, production_read_only=True)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="read_only_research", operation="list_directory", params={"path": "."}),
            ActionEnvelope(capability_id="read_only_research", operation="read_file_segment", params={"path": "README.md", "start_line": 1, "line_count": 5}),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "read-only verification succeeded"}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert fixture.read_only_tool_calls == 2
    assert len([ref for ref in result.receipt_refs if ref.startswith("readonly_receipt_")]) == 2


def test_power_pack3_production_read_only_verification_still_blocks_path_escape(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, production_read_only=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="read_only_research", operation="read_file_segment", params={"path": "../outside.txt", "start_line": 1, "line_count": 5}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert fixture.read_only_tool_calls == 1
    assert not result.receipt_refs
    assert result.blocked_reason == "read_only_action_blocked:gate_sequence:out_of_scope:escalate"


def test_power_pack3_production_read_only_receipt_satisfies_objective_and_unlocks_finish_only_turn(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, production_read_only=True)
    base_hash = fixture.readme_hash()
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "python_compileall", "args": ["src"]},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: run sandbox\n",
                    "new_text": "TODO: sandbox command verified\n",
                },
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="search_text",
                params={"path": ".", "query": "sandbox command verified"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "objective satisfied"}),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decisions,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=5, max_material_actions=3)),
        available_actions=(
            "read_only.search_text",
            "workspace_patch.apply_patch",
            "code_exec.run_profile",
            "finish",
        ),
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert result.material_action_count == 3
    assert fixture.read_only_tool_calls == 1
    assert any(ref.startswith("readonly_receipt_") for ref in result.receipt_refs)
    finish_context = decisions.contexts[-1]
    assert finish_context["objective_satisfied"] is True
    assert finish_context["available_actions"] == ["finish"]


def test_power_pack3_empty_action_envelope_blocks_before_action_kernel_dispatch_with_safe_diagnostics(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="", operation="", params={}),
        ]
    )

    result = fixture.loop(decisions).run()
    events = fixture.kernel.store.load_events(fixture.mission_id)
    blocked_event = next(event for event in reversed(events) if event.event_type == "model_led_task_loop_blocked")

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_ACTION_EMPTY_ENVELOPE"
    assert fixture.read_only_tool_calls == 0
    assert fixture.code_runtime.command_execution_count == 0
    assert fixture.patch_runtime.patch_application_count == 0
    assert result.failure_diagnostics["failure_code"] == "MODEL_ACTION_EMPTY_ENVELOPE"
    assert result.failure_diagnostics["turn_index"] == 1
    assert result.failure_diagnostics["allowed_operations"]
    assert result.failure_diagnostics["last_receipt_refs"] == []
    assert blocked_event.metadata["failure_diagnostics"]["failure_code"] == "MODEL_ACTION_EMPTY_ENVELOPE"
    assert "raw_provider" not in str(blocked_event.metadata).lower()
    assert "reasoning" not in str(blocked_event.metadata).lower()


def test_power_pack3_blank_capability_or_operation_blocks_with_typed_reason(tmp_path: Path) -> None:
    for envelope in [
        ActionEnvelope(capability_id="   ", operation="list_directory", params={"path": "."}),
        ActionEnvelope(capability_id="read_only_research", operation="   ", params={"path": "."}),
    ]:
        case_root = tmp_path / envelope.action_id
        case_root.mkdir()
        fixture = _CodeExecFixture(case_root)
        decisions = ModelLedTaskDecisionClient([envelope])

        result = fixture.loop(decisions).run()

        assert result.status is ModelLedTaskLoopStatus.BLOCKED
        assert result.blocked_reason == "MODEL_ACTION_EMPTY_ENVELOPE"
        assert "action_executor_missing" not in result.blocked_reason
        assert result.failure_diagnostics["failure_code"] == "MODEL_ACTION_EMPTY_ENVELOPE"


def test_power_pack3_context_after_read_only_receipt_guides_next_power_actions(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, production_read_only=True)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="read_only_research", operation="list_directory", params={"path": "."}),
            ActionEnvelope(capability_id="", operation="", params={}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    next_context = decisions.contexts[1]
    assert next_context["progress_state"] == "initial_observation_collected"
    assert "code_execution_sandbox.code_exec.run_profile" in next_context["next_recommended_actions"]
    assert "workspace_patch.apply_patch" in next_context["next_recommended_actions"]
    assert "read_only_research.search_text" in next_context["next_recommended_actions"]
    assert "sentinel_loop.finish" not in next_context["next_recommended_actions"]
    assert "run bounded code execution" in next_context["objective_remaining_steps"]
    assert next_context["completion_requirements"]["requires_code_execution_receipt"] is True
    assert next_context["available_actions"]


def test_power_pack3_pre_patch_read_only_receipt_does_not_satisfy_patch_verification(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, production_read_only=True)
    base_hash = fixture.readme_hash()
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="read_only_research", operation="list_directory", params={"path": "."}),
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "python_compileall", "args": ["src"]},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: run sandbox\n",
                    "new_text": "TODO: sandbox command verified\n",
                },
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "too early"}),
        ]
    )

    result = fixture.loop(decisions).run()
    post_patch_context = decisions.contexts[3]

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_FINISH_BEFORE_POST_PATCH_VERIFICATION"
    assert post_patch_context["objective_satisfied"] is False
    assert post_patch_context["finish_available"] is False
    assert "sentinel_loop.finish" not in post_patch_context["next_recommended_actions"]
    assert "workspace_patch.run_bounded_check" in post_patch_context["next_recommended_actions"]
    assert "read_only_research.search_text" in post_patch_context["next_recommended_actions"]
    assert post_patch_context["completion_requirements"]["requires_verification_receipt"] is True


def test_power_pack3_post_patch_read_only_search_text_satisfies_verification(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, production_read_only=True)
    base_hash = fixture.readme_hash()
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="read_only_research", operation="list_directory", params={"path": "."}),
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "python_compileall", "args": ["src"]},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: run sandbox\n",
                    "new_text": "TODO: sandbox command verified\n",
                },
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="search_text",
                params={"path": ".", "query": "sandbox command verified"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "verified"}),
        ]
    )

    result = fixture.loop(decisions).run()
    finish_context = decisions.contexts[-1]

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert finish_context["objective_satisfied"] is True
    assert finish_context["finish_available"] is True
    assert finish_context["recommended_next_action"] == "sentinel_loop.finish"


def test_power_pack3_post_patch_read_file_segment_satisfies_verification(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path, production_read_only=True)
    base_hash = fixture.readme_hash()
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "python_compileall", "args": ["src"]},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: run sandbox\n",
                    "new_text": "TODO: sandbox command verified\n",
                },
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="read_file_segment",
                params={"path": "README.md", "start_line": 1, "line_count": 5},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "verified"}),
        ]
    )

    result = fixture.loop(decisions).run()
    finish_context = decisions.contexts[-1]

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert finish_context["objective_satisfied"] is True
    assert finish_context["completion_requirements"]["requires_verification_receipt"] is False


def test_power_pack3_post_patch_bounded_check_satisfies_verification(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    base_hash = fixture.readme_hash()
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "python_compileall", "args": ["src"]},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: run sandbox\n",
                    "new_text": "TODO: sandbox command verified\n",
                },
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="run_bounded_check",
                params={"command_id": "fake_pass", "args": ["README.md"]},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "verified"}),
        ]
    )

    result = fixture.loop(decisions).run()
    finish_context = decisions.contexts[-1]

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.patch_runtime.verification_run_count == 1
    assert finish_context["objective_satisfied"] is True
    assert finish_context["next_recommended_actions"] == ["sentinel_loop.finish"]


def test_power_pack3_finish_only_turn_available_when_objective_satisfied_at_material_budget(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    base_hash = fixture.readme_hash()
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "python_compileall", "args": ["src"]},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: run sandbox\n",
                    "new_text": "TODO: sandbox command verified\n",
                },
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="search_text",
                params={"path": ".", "query": "sandbox command verified"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "objective satisfied"}),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decisions,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=5, max_material_actions=3)),
        available_actions=(
            "read_only.search_text",
            "workspace_patch.apply_patch",
            "code_exec.run_profile",
            "finish",
        ),
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert result.material_action_count == 3
    assert result.model_call_count == 4
    assert result.capability_sequence[-1] == "sentinel_loop:finish"
    finish_context = decisions.contexts[-1]
    assert finish_context["objective_satisfied"] is True
    assert finish_context["recommended_next_action"] == "sentinel_loop.finish"
    assert finish_context["finish_available"] is True
    assert finish_context["available_actions"] == ["finish"]


def test_power_pack3_budget_without_objective_satisfied_still_closes_honestly(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="code_execution_sandbox",
                operation="code_exec.run_profile",
                params={"profile_id": "fake_pass"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "should not be reached"}),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decisions,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=3, max_material_actions=1)),
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_material_budget_reached"
    assert result.material_action_count == 1
    assert result.model_call_count == 1


def test_power_pack3_inspect_result_is_non_material_and_loop_guard_counts_run_profile_as_material(tmp_path: Path) -> None:
    fixture = _CodeExecFixture(tmp_path)
    run_result = fixture.code_runtime.execute(
        ActionEnvelope(capability_id="code_execution_sandbox", operation="code_exec.run_profile", params={"profile_id": "fake_pass"}),
        authority=fixture.authority,
        context={},
    )
    inspect_result = fixture.code_runtime.execute(
        ActionEnvelope(
            capability_id="code_execution_sandbox",
            operation="code_exec.inspect_result",
            params={"receipt_ref": run_result.receipt_refs[0]},
        ),
        authority=fixture.authority,
        context={},
    )

    assert inspect_result.status == "completed"
    assert inspect_result.material_action is False
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="code_execution_sandbox", operation="code_exec.run_profile", params={"profile_id": "fake_pass"}),
            ActionEnvelope(capability_id="code_execution_sandbox", operation="code_exec.run_profile", params={"profile_id": "fake_pass", "args": ["README.md"]}),
        ]
    )
    result = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decisions,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=3, max_material_actions=1)),
    ).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_material_budget_reached"
    assert result.material_action_count == 1
    assert fixture.code_runtime.command_execution_count == 2


class _CodeExecFixture:
    def __init__(self, tmp_path: Path, runner: object | None = None, production_read_only: bool = False) -> None:
        self.production_read_only = production_read_only
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir()
        self.readme = self.workspace / "README.md"
        self.readme.write_text("# Project\n\nTODO: run sandbox\n", encoding="utf-8")
        (self.workspace / "src").mkdir()
        (self.workspace / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.workspace / "tests").mkdir()
        (self.workspace / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack3",
            draft=MissionDraft(
                title="Model-led code execution sandbox",
                objective="Let the model run bounded local command profiles inside a granted workspace.",
                constraints=["profile-only", "receipts always", "no ambient shell"],
                expected_artifacts=["code execution receipt"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack3",
                allowed_actions=[
                    "list_directory",
                    "read_file_segment",
                    "search_text",
                    "workspace_patch.apply_patch",
                    "workspace_patch.run_bounded_check",
                    "code_exec.run_profile",
                    "code_exec.inspect_result",
                    "finish",
                ],
                forbidden_actions=["shell", "network", "credential_access", "package_install"],
                summary="Read-only, workspace patching, and bounded code execution profiles are granted.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.code_runtime = CodeExecutionSandboxRuntime(
            kernel=self.kernel,
            mission_id=self.mission_id,
            workspace_root=self.workspace,
            runner=runner,
        )
        self.patch_runtime = WorkspacePatchRuntime(
            kernel=self.kernel,
            mission_id=self.mission_id,
            workspace_root=self.workspace,
            check_runner=_FakeBoundedCheckRunner(),
        )
        self.read_only_tool_calls = 0
        self.action_kernel = ActionKernel(
            executors={
                "read_only_research": self._execute_read_only,
                "workspace_patch": lambda envelope, context: self.patch_runtime.execute(
                    envelope,
                    authority=self.authority,
                    context=context,
                ),
                "code_execution_sandbox": lambda envelope, context: self.code_runtime.execute(
                    envelope,
                    authority=self.authority,
                    context=context,
                ),
            }
        )

    def envelope(self) -> MissionAuthorityEnvelope:
        now = datetime.now(UTC)
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_youcef",
            mission_title="Model-led code execution sandbox",
            mission_objective="Run bounded command profiles inside the approved workspace.",
            allowed_tools=["read_only_research", "workspace_patch", "code_execution_sandbox"],
            allowed_actions=[
                "list_directory",
                "read_file_segment",
                "search_text",
                "workspace_patch.apply_patch",
                "workspace_patch.run_bounded_check",
                "code_exec.run_profile",
                "code_exec.inspect_result",
                "finish",
            ],
            forbidden_actions=["shell", "network", "credential_access", "package_install"],
            allowed_paths=[str(self.workspace)],
            max_actions=12,
            expires_at=now + timedelta(minutes=30),
        )

    def loop(self, decision_client: ModelLedTaskDecisionClient) -> ModelLedTaskLoop:
        return ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decision_client,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=8, max_material_actions=6)),
            available_actions=(
                "read_only.list_directory",
                "read_only.read_file_segment",
                "read_only.search_text",
                "workspace_patch.apply_patch",
                "workspace_patch.run_bounded_check",
                "code_exec.run_profile",
                "code_exec.inspect_result",
                "finish",
            ),
        )

    def readme_hash(self) -> str:
        return hashlib.sha256(self.readme.read_bytes()).hexdigest()

    def load_code_receipt(self, receipt_refs: tuple[str, ...]) -> CodeExecutionReceipt:
        receipt_ref = next(ref for ref in receipt_refs if ref.startswith("code_exec_receipt_"))
        path = self.kernel.store.mission_dir(self.mission_id) / "code_execution_sandbox" / "receipts" / f"{receipt_ref}.json"
        return CodeExecutionReceipt.model_validate_json(path.read_text(encoding="utf-8"))

    def _execute_read_only(self, envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        del context
        self.read_only_tool_calls += 1
        if self.production_read_only:
            session = ReadOnlyProductionSpineSession(
                cockpit=_KernelBackedCockpit(self.kernel),
                mission_id=self.mission_id,
                snapshot_root=self.workspace,
                decision_client=ReadOnlyDecisionClient(
                    [
                        ReadOnlyDecision(
                            action=ReadOnlyActionKind(envelope.operation),
                            arguments=dict(envelope.params),
                        )
                    ]
                ),
                stop_after_first_material_receipt=True,
                low_friction_read_only_power_mode=True,
                owns_kernel_terminal=False,
            )
            result = session.run_via_agent_runtime(envelope=self.authority)
            if result.status != "completed":
                raise ActionKernelError(f"read_only_action_blocked:{result.blocked_reason}")
            return ActionResult(
                action_id=envelope.action_id,
                capability_id=envelope.capability_id,
                operation=envelope.operation,
                status="completed",
                receipt_refs=tuple(result.receipt_refs),
                finalgate_refs=tuple(result.finalgate_refs),
                material_action=True,
                observation_summary=f"{envelope.operation} completed with {len(result.receipt_refs)} receipt(s).",
            )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=(f"readonly_receipt_{self.read_only_tool_calls}",),
            evidence_refs=(f"readonly_evidence_{self.read_only_tool_calls}",),
            material_action=True,
            observation_summary=f"{envelope.operation} completed.",
        )


class _KernelBackedCockpit:
    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel

    def handle(self, _message: str) -> None:
        return None


class _ScriptedRunner:
    def __init__(self, *, exit_code: int, stdout: str, stderr: str, timed_out: bool = False) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out

    def run(self, *, executable: str, args: tuple[str, ...], cwd: Path, timeout_seconds: int, env: dict[str, str]) -> CodeExecutionProcessResult:
        del executable, args, cwd, timeout_seconds, env
        return CodeExecutionProcessResult(
            exit_code=self.exit_code,
            duration_ms=12,
            stdout=self.stdout,
            stderr=self.stderr,
            timed_out=self.timed_out,
        )


class _FakeBoundedCheckRunner:
    def run(self, *, command_id: str, args: tuple[str, ...], cwd: Path) -> WorkspacePatchCheckResult:
        return WorkspacePatchCheckResult(
            command_id=command_id,
            args=args,
            exit_status=0,
            duration_ms=3,
            stdout="fake check passed",
            stderr="",
            cwd_hash=str(hash(cwd)),
        )


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None


def _workspace_fingerprint(workspace: Path) -> tuple[str, ...]:
    rows: list[str] = []
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace).as_posix()
        if path.is_file():
            rows.append(f"F|{relative}|{hashlib.sha256(path.read_bytes()).hexdigest()}")
        elif path.is_dir():
            rows.append(f"D|{relative}")
    return tuple(rows)
