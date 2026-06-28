from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionResult
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import (
    ModelLedTaskDecisionClient,
    ModelLedTaskLoop,
    ModelLedTaskLoopReplay,
    ModelLedTaskLoopStatus,
)
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyActionKind,
    ReadOnlyDecision,
    ReadOnlyDecisionClient,
    ReadOnlyProductionSpineSession,
)
from sentinel.operator.workspace_patch_replay import WorkspacePatchReplayView
from sentinel.operator.workspace_patch_runtime import (
    WorkspacePatchCheckResult,
    WorkspacePatchRuntime,
    WorkspacePatchRuntimeError,
)
from sentinel.operator.workspace_patch_models import (
    WorkspacePatchReceipt,
    WorkspacePatchVerificationReceipt,
)


def test_power_pack2_generic_loop_applies_patch_runs_check_reads_back_and_replays_without_mutation(
    tmp_path: Path,
) -> None:
    fixture = _PatchLoopFixture(tmp_path)
    before_hash = _sha256_file(fixture.readme)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="read_only_research",
                operation="read_file_segment",
                target_ref="README.md",
                params={"path": "README.md", "start_line": 1, "line_count": 20},
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                target_ref="README.md",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": before_hash,
                    "old_text": "TODO: old marker\n",
                    "new_text": "TODO: model-led patch landed\n",
                },
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="run_bounded_check",
                target_ref="README.md",
                params={"command_id": "fake_pass", "args": ["README.md"]},
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="search_text",
                target_ref="README.md",
                params={"path": ".", "query": "model-led patch landed"},
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Patch loop complete."},
            ),
        ]
    )

    result = fixture.loop(decisions).run()
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)
    patch_replay = WorkspacePatchReplayView.from_store(
        fixture.kernel.store,
        mission_id=fixture.mission_id,
        workspace_root=fixture.workspace,
    )

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED
    assert "model-led patch landed" in fixture.readme.read_text(encoding="utf-8")
    assert fixture.patch_runtime.patch_application_count == 1
    assert fixture.check_runner.call_count == 1
    assert result.material_action_count == 4
    assert result.capability_sequence == (
        "read_only_research:read_file_segment",
        "workspace_patch:apply_patch",
        "workspace_patch:run_bounded_check",
        "read_only_research:search_text",
        "sentinel_loop:finish",
    )
    assert any(ref.startswith("workspace_patch_receipt_") for ref in result.receipt_refs)
    assert any(ref.startswith("workspace_patch_verification_") for ref in result.receipt_refs)
    assert fixture.load_patch_receipt(result.receipt_refs).verify_hash()
    assert fixture.load_verification_receipt(result.receipt_refs).verify_hash()
    assert decisions.contexts[2]["workspace_patch_summary"][0]["operation"] == "apply_patch"
    assert decisions.contexts[3]["workspace_verification_summary"][0]["status"] == "passed"
    assert loop_replay.workspace_mutations_delta == 0
    assert patch_replay.patch_applications_delta == 0
    assert patch_replay.verification_runs_delta == 0
    assert patch_replay.receipt_writes_delta == 0
    assert patch_replay.artifact_hashes_stable is True


def test_power_pack2_hash_mismatch_blocks_without_write(tmp_path: Path) -> None:
    fixture = _PatchLoopFixture(tmp_path)

    with pytest.raises(WorkspacePatchRuntimeError, match="workspace_patch_base_hash_mismatch"):
        fixture.patch_runtime.execute(
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                target_ref="README.md",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": "0" * 64,
                    "old_text": "TODO: old marker\n",
                    "new_text": "TODO: should not land\n",
                },
            ),
            authority=fixture.authority,
            context={},
        )

    assert "should not land" not in fixture.readme.read_text(encoding="utf-8")
    assert fixture.patch_runtime.patch_application_count == 0


def test_power_pack2_blocks_path_escape_absolute_outside_and_symlink_escape(tmp_path: Path) -> None:
    fixture = _PatchLoopFixture(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    symlink_path = fixture.workspace / "linked-outside.txt"
    try:
        symlink_path.symlink_to(outside)
    except (OSError, NotImplementedError):
        symlink_path = None

    for target in ("../outside.txt", str(outside)):
        with pytest.raises(WorkspacePatchRuntimeError, match="workspace_patch_path_escape|workspace_patch_absolute_path_blocked"):
            fixture.patch_runtime.execute(
                _patch_envelope(target, "irrelevant", "x", "y"),
                authority=fixture.authority,
                context={},
            )
    if symlink_path is not None:
        with pytest.raises(WorkspacePatchRuntimeError, match="workspace_patch_symlink_escape"):
            fixture.patch_runtime.execute(
                _patch_envelope("linked-outside.txt", _sha256_file(outside), "outside\n", "mutated\n"),
                authority=fixture.authority,
                context={},
            )


def test_power_pack2_rejects_multiple_targets_sensitive_targets_and_credential_like_content(tmp_path: Path) -> None:
    fixture = _PatchLoopFixture(tmp_path)
    base_hash = _sha256_file(fixture.readme)

    with pytest.raises(WorkspacePatchRuntimeError, match="workspace_patch_multiple_targets_blocked"):
        fixture.patch_runtime.execute(
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "target_paths": ["README.md", "src/app.py"],
                    "expected_base_hash": base_hash,
                    "old_text": "TODO: old marker\n",
                    "new_text": "TODO: hidden second write\n",
                },
            ),
            authority=fixture.authority,
            context={},
        )
    with pytest.raises(WorkspacePatchRuntimeError, match="workspace_patch_sensitive_target_blocked"):
        fixture.patch_runtime.execute(
            _patch_envelope(".env", "", "", "ENV_VALUE=1\n"),
            authority=fixture.authority,
            context={},
        )
    with pytest.raises(ValueError, match="credential|secret"):
        ActionEnvelope(
            capability_id="workspace_patch",
            operation="apply_patch",
            params={
                "target_path": "README.md",
                "expected_base_hash": base_hash,
                "old_text": "TODO: old marker\n",
                "new_text": "api_key=abc123\n",
            },
        )


def test_power_pack2_bounded_check_rejects_unknown_or_ambient_shell_commands(tmp_path: Path) -> None:
    fixture = _PatchLoopFixture(tmp_path)

    for params in (
        {"command": "python -m pytest tests -q"},
        {"command_id": "unknown", "args": []},
        {"command_id": "fake_pass", "args": ["README.md", "&&", "whoami"]},
    ):
        with pytest.raises(WorkspacePatchRuntimeError, match="workspace_patch_check_not_allowed|workspace_patch_shell_blocked"):
            fixture.patch_runtime.execute(
                ActionEnvelope(
                    capability_id="workspace_patch",
                    operation="run_bounded_check",
                    target_ref="README.md",
                    params=params,
                ),
                authority=fixture.authority,
                context={},
            )

    result = fixture.patch_runtime.execute(
        ActionEnvelope(
            capability_id="workspace_patch",
            operation="run_bounded_check",
            target_ref="README.md",
            params={"command_id": "fake_pass", "args": ["README.md"]},
        ),
        authority=fixture.authority,
        context={},
    )
    assert result.status == "passed"
    assert result.material_action is True
    assert result.receipt_refs[0].startswith("workspace_patch_verification_")
    assert fixture.check_runner.call_count == 1


def test_power_pack2_loop_guard_counts_patch_and_check_as_material_actions(tmp_path: Path) -> None:
    fixture = _PatchLoopFixture(tmp_path)
    before_hash = _sha256_file(fixture.readme)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="apply_patch",
                params={
                    "target_path": "README.md",
                    "expected_base_hash": before_hash,
                    "old_text": "TODO: old marker\n",
                    "new_text": "TODO: one material action\n",
                },
            ),
            ActionEnvelope(
                capability_id="workspace_patch",
                operation="run_bounded_check",
                params={"command_id": "fake_pass", "args": ["README.md"]},
            ),
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
    assert fixture.patch_runtime.patch_application_count == 1
    assert fixture.check_runner.call_count == 0


class _PatchLoopFixture:
    def __init__(self, tmp_path: Path) -> None:
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir()
        self.readme = self.workspace / "README.md"
        self.readme.write_text("# Project\n\nTODO: old marker\n", encoding="utf-8")
        (self.workspace / "src").mkdir()
        (self.workspace / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack2",
            draft=MissionDraft(
                title="Model-led workspace patch",
                objective="Let the model patch and verify files inside a granted workspace.",
                constraints=["hash anchored", "receipts always", "no ambient shell"],
                expected_artifacts=["patch receipt", "verification receipt"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack2",
                allowed_actions=[
                    "read_file_segment",
                    "search_text",
                    "workspace_patch.apply_patch",
                    "workspace_patch.run_bounded_check",
                    "finish",
                ],
                forbidden_actions=["shell", "network", "credential_access", "authority_mutation"],
                summary="Read-only plus hash-anchored workspace patching is granted.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.check_runner = _FakeBoundedCheckRunner()
        self.patch_runtime = WorkspacePatchRuntime(
            kernel=self.kernel,
            mission_id=self.mission_id,
            workspace_root=self.workspace,
            check_runner=self.check_runner,
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
            }
        )

    def envelope(self) -> MissionAuthorityEnvelope:
        now = datetime.now(UTC)
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_youcef",
            mission_title="Model-led workspace patch",
            mission_objective="Patch and verify a file inside the approved workspace.",
            allowed_tools=["read_only_research", "workspace_patch"],
            allowed_actions=[
                "read_file_segment",
                "search_text",
                "workspace_patch.apply_patch",
                "workspace_patch.run_bounded_check",
                "finish",
            ],
            forbidden_actions=["shell", "network", "credential_access", "authority_mutation"],
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
                "read_only.read_file_segment",
                "read_only.search_text",
                "workspace_patch.apply_patch",
                "workspace_patch.run_bounded_check",
                "finish",
            ),
        )

    def _execute_read_only(self, envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        del context
        self.read_only_tool_calls += 1
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
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status=result.status,
            receipt_refs=tuple(result.receipt_refs),
            evidence_refs=tuple(_evidence_refs_for_latest_read_only(self.kernel, self.mission_id)),
            finalgate_refs=tuple(result.finalgate_refs),
            material_action=True,
            observation_summary=f"{envelope.operation} completed.",
        )

    def load_patch_receipt(self, receipt_refs: tuple[str, ...]) -> WorkspacePatchReceipt:
        receipt_ref = next(ref for ref in receipt_refs if ref.startswith("workspace_patch_receipt_"))
        path = self.kernel.store.mission_dir(self.mission_id) / "workspace_patch" / "receipts" / f"{receipt_ref}.json"
        return WorkspacePatchReceipt.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def load_verification_receipt(self, receipt_refs: tuple[str, ...]) -> WorkspacePatchVerificationReceipt:
        receipt_ref = next(ref for ref in receipt_refs if ref.startswith("workspace_patch_verification_"))
        path = self.kernel.store.mission_dir(self.mission_id) / "workspace_patch" / "receipts" / f"{receipt_ref}.json"
        return WorkspacePatchVerificationReceipt.model_validate(json.loads(path.read_text(encoding="utf-8")))


class _FakeBoundedCheckRunner:
    def __init__(self) -> None:
        self.call_count = 0

    def run(self, *, command_id: str, args: tuple[str, ...], cwd: Path) -> WorkspacePatchCheckResult:
        self.call_count += 1
        return WorkspacePatchCheckResult(
            command_id=command_id,
            args=args,
            exit_status=0,
            duration_ms=3,
            stdout="fake check passed",
            stderr="",
            cwd_hash=_hash_text(str(cwd)),
        )


def _patch_envelope(target_path: str, expected_base_hash: str, old_text: str, new_text: str) -> ActionEnvelope:
    return ActionEnvelope(
        capability_id="workspace_patch",
        operation="apply_patch",
        target_ref=target_path,
        params={
            "target_path": target_path,
            "expected_base_hash": expected_base_hash,
            "old_text": old_text,
            "new_text": new_text,
        },
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _evidence_refs_for_latest_read_only(kernel: MissionKernel, mission_id: str) -> list[str]:
    evidence_root = kernel.store.mission_dir(mission_id) / "read_only_spine" / "evidence"
    if not evidence_root.exists():
        return []
    return [path.stem for path in sorted(evidence_root.glob("*.json"))]


class _KernelBackedCockpit:
    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel

    def handle(self, _message: str) -> None:
        return None


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
