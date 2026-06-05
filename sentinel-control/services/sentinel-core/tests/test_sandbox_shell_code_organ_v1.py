from __future__ import annotations

from pathlib import Path


def test_shell_code_sandbox_allows_python_version_with_receipt_and_finalgate(tmp_path: Path) -> None:
    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
        ShellCodeSandboxOrganV1,
        ShellCodeSandboxRequest,
        ShellCodeSandboxStatus,
    )

    result = ShellCodeSandboxOrganV1().execute(
        ShellCodeSandboxRequest(
            mission_id="mission_shell_version",
            project_root=tmp_path,
            cwd=".",
            command=["python", "--version"],
        )
    )

    assert result.status is ShellCodeSandboxStatus.SUCCEEDED
    assert result.receipt is not None
    assert result.receipt.exit_code == 0
    assert result.receipt.command_hash
    assert result.receipt.stdout_sha256 or result.receipt.stderr_sha256
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True
    assert result.authority_effect == "none"
    assert result.data_not_instruction is True


def test_shell_code_sandbox_blocks_unallowlisted_and_shell_metacharacters(tmp_path: Path) -> None:
    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
        ShellCodeSandboxOrganV1,
        ShellCodeSandboxRequest,
        ShellCodeSandboxStatus,
    )

    organ = ShellCodeSandboxOrganV1()
    unallowlisted = organ.execute(
        ShellCodeSandboxRequest(
            mission_id="mission_shell_block",
            project_root=tmp_path,
            cwd=".",
            command=["python", "-c", "print('not allowed')"],
        )
    )
    assert unallowlisted.status is ShellCodeSandboxStatus.BLOCKED
    assert unallowlisted.blocked_reason == "command_not_allowlisted"
    assert unallowlisted.receipt is None
    assert unallowlisted.finalgate_certificate is not None
    assert unallowlisted.finalgate_certificate.passed is True

    metachar = organ.execute(
        ShellCodeSandboxRequest(
            mission_id="mission_shell_metachar",
            project_root=tmp_path,
            cwd=".",
            command=["python", "--version", "&&", "whoami"],
        )
    )
    assert metachar.status is ShellCodeSandboxStatus.BLOCKED
    assert metachar.blocked_reason == "forbidden_shell_token"


def test_shell_code_sandbox_blocks_cwd_escape_and_secret_env(tmp_path: Path) -> None:
    import pytest

    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
        ShellCodeSandboxRequest,
    )

    with pytest.raises(ValueError):
        ShellCodeSandboxRequest(
            mission_id="mission_shell_escape",
            project_root=tmp_path,
            cwd="..",
            command=["python", "--version"],
        )

    with pytest.raises(ValueError):
        ShellCodeSandboxRequest(
            mission_id="mission_shell_secret_env",
            project_root=tmp_path,
            cwd=".",
            command=["python", "--version"],
            env={"API_KEY": "Be" + "arer " + "secret-value-1234567890"},
        )


def test_shell_code_sandbox_compileall_records_file_diff_hashes(tmp_path: Path) -> None:
    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
        ShellCodeSandboxOrganV1,
        ShellCodeSandboxRequest,
        ShellCodeSandboxStatus,
    )

    (tmp_path / "module_under_test.py").write_text("VALUE = 1\n", encoding="utf-8")

    result = ShellCodeSandboxOrganV1().execute(
        ShellCodeSandboxRequest(
            mission_id="mission_shell_compileall",
            project_root=tmp_path,
            cwd=".",
            command=["python", "-m", "compileall", "."],
        )
    )

    assert result.status is ShellCodeSandboxStatus.SUCCEEDED
    assert result.receipt is not None
    assert any(path.endswith(".pyc") for path in result.receipt.created_files)
    assert result.receipt.artifact_hashes
    assert result.receipt.after_tree_hash
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True


def test_shell_code_sandbox_timeout_produces_safe_failed_receipt(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
        ShellCodeSandboxOrganV1,
        ShellCodeSandboxRequest,
        ShellCodeSandboxStatus,
    )

    def timeout_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["python", "--version"], timeout=1)

    monkeypatch.setattr(subprocess, "run", timeout_run)

    result = ShellCodeSandboxOrganV1().execute(
        ShellCodeSandboxRequest(
            mission_id="mission_shell_timeout",
            project_root=tmp_path,
            cwd=".",
            command=["python", "--version"],
            timeout_seconds=1,
        )
    )

    assert result.status is ShellCodeSandboxStatus.TIMED_OUT
    assert result.receipt is not None
    assert result.receipt.exit_code is None
    assert result.receipt.timed_out is True
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True


def test_shell_code_sandbox_contract_output_cap_cannot_be_weakened(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
        ShellCodeSandboxContract,
        ShellCodeSandboxOrganV1,
        ShellCodeSandboxRequest,
    )

    def loud_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["python", "--version"], returncode=0, stdout=b"x" * 1000, stderr=b"")

    monkeypatch.setattr(subprocess, "run", loud_run)

    result = ShellCodeSandboxOrganV1().execute(
        ShellCodeSandboxRequest(
            mission_id="mission_shell_output_cap",
            project_root=tmp_path,
            cwd=".",
            command=["python", "--version"],
            output_max_bytes=2048,
        ),
        contract=ShellCodeSandboxContract(max_output_bytes=256),
    )

    assert result.receipt is not None
    assert len(result.receipt.stdout_excerpt.encode("utf-8")) == 256
    assert result.receipt.output_truncated is True


def test_shell_code_sandbox_kill_switch_blocks_before_execution(tmp_path: Path) -> None:
    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
        ShellCodeSandboxOrganV1,
        ShellCodeSandboxRequest,
        ShellCodeSandboxStatus,
    )
    from sentinel.organs.kill_switch import OrganKillSwitch

    kill_switch = OrganKillSwitch(
        mission_id="mission_shell_kill",
        organ_id="sandbox_shell_code",
        triggered=True,
        execution_allowed=False,
        reason="test_stop",
    )

    result = ShellCodeSandboxOrganV1().execute(
        ShellCodeSandboxRequest(
            mission_id="mission_shell_kill",
            project_root=tmp_path,
            cwd=".",
            command=["python", "--version"],
        ),
        kill_switch=kill_switch,
    )

    assert result.status is ShellCodeSandboxStatus.BLOCKED
    assert result.blocked_reason == "kill_switch_triggered"
    assert result.receipt is None
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True


def test_shell_code_sandbox_power_runtime_executor_adapter(tmp_path: Path) -> None:
    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import build_shell_code_power_executor
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        SentinelPowerRuntimeV0,
    )

    plan = PowerMissionPlan(
        mission_id="mission_shell_power_runtime",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="version",
                    actuator_family=PowerActuatorFamily.SHELL_SANDBOX,
                    capability_level=PowerActuatorCapabilityLevel.L5,
                    organ_kind="sandbox_shell_code",
                    action_kind="run_command",
                    request={"cwd": ".", "command": ["python", "--version"]},
                )
            ]
        ),
    )

    result = SentinelPowerRuntimeV0().run(
        plan,
        config=PowerRuntimeConfig(enabled=True),
        actuator_executor=build_shell_code_power_executor(project_root=tmp_path),
    )

    assert result.status == "completed"
    assert result.step_results[0].receipt_refs
    assert result.step_results[0].finalgate_certificate_refs


def test_shell_code_power_executor_blocks_mislabeled_step_before_subprocess(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    from sentinel.agent.organs.sandbox_shell_code_organ_v1 import build_shell_code_power_executor
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionStep,
        PowerStepStatus,
    )

    called = False

    def run(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("mislabeled step must not reach subprocess")

    monkeypatch.setattr(subprocess, "run", run)
    executor = build_shell_code_power_executor(project_root=tmp_path)
    result = executor(
        PowerMissionStep(
            step_id="shell_mislabeled",
            actuator_family=PowerActuatorFamily.WORKSPACE,
            capability_level=PowerActuatorCapabilityLevel.L3,
            organ_kind="sandbox_shell_code",
            action_kind="run_command",
            request={"cwd": ".", "command": ["python", "--version"]},
        ),
        {"mission_id": "mission_shell_mislabeled"},
    )

    assert result.status is PowerStepStatus.BLOCKED
    assert result.blocked_reason == "unsupported_actuator_family"
    assert called is False
