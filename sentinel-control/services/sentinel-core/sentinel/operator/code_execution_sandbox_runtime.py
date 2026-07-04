from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Protocol

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.code_execution_sandbox_models import (
    CodeExecutionFinalCertificate,
    CodeExecutionProfile,
    CodeExecutionReceipt,
    CodeExecutionRequest,
    CodeExecutionResult,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text
from sentinel.shared.models import SentinelModel


class CodeExecutionSandboxRuntimeError(RuntimeError):
    pass


class CodeExecutionProcessResult(SentinelModel):
    exit_code: int
    duration_ms: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


class CodeExecutionRunner(Protocol):
    def run(
        self,
        *,
        executable: str,
        args: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
        env: dict[str, str],
    ) -> CodeExecutionProcessResult:
        ...


SHELL_ARG_MARKERS = frozenset({"&&", "||", "|", ";", ">", "<", "`", "$(", "%comspec%", "\n", "\r"})
NETWORK_ARG_MARKERS = frozenset({"http://", "https://", "ftp://", "ws://", "wss://", "curl", "wget"})
CREDENTIAL_ARG_MARKERS = frozenset(
    {
        "authorization",
        "bearer ",
        "api_key",
        "apikey",
        "secret",
        "password",
        "private key",
        "cookie",
        "session_token",
    }
)
OUTPUT_SECRET_LABEL_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer|password|secret|credential|session[_-]?token)\b\s*[:=]?\s*\S*"
)
FORBIDDEN_PROFILE_EXECUTABLES = frozenset({"powershell", "pwsh", "cmd", "bash", "sh", "curl", "wget", "rm", "del", "move"})


def default_code_execution_profiles() -> dict[str, CodeExecutionProfile]:
    return {
        "fake_pass": CodeExecutionProfile(
            profile_id="fake_pass",
            executable="sentinel_fake",
            fixed_args_prefix=(),
            allowed_arg_kinds=("workspace_path",),
            timeout_seconds=5,
            max_stdout_bytes=1024,
            max_stderr_bytes=1024,
        ),
        "fake_timeout": CodeExecutionProfile(
            profile_id="fake_timeout",
            executable="sentinel_fake",
            fixed_args_prefix=(),
            allowed_arg_kinds=("workspace_path",),
            timeout_seconds=1,
            max_stdout_bytes=1024,
            max_stderr_bytes=1024,
        ),
        "python_compileall": CodeExecutionProfile(
            profile_id="python_compileall",
            executable=sys.executable,
            fixed_args_prefix=("-m", "compileall"),
            allowed_arg_kinds=("workspace_path",),
            timeout_seconds=30,
            max_stdout_bytes=4096,
            max_stderr_bytes=4096,
        ),
        "pytest_file": CodeExecutionProfile(
            profile_id="pytest_file",
            executable=sys.executable,
            fixed_args_prefix=("-m", "pytest", "-q"),
            allowed_arg_kinds=("workspace_file",),
            timeout_seconds=45,
            max_stdout_bytes=8192,
            max_stderr_bytes=8192,
        ),
        "python_module_smoke": CodeExecutionProfile(
            profile_id="python_module_smoke",
            executable=sys.executable,
            fixed_args_prefix=("-m",),
            allowed_arg_kinds=("python_module",),
            timeout_seconds=30,
            max_stdout_bytes=4096,
            max_stderr_bytes=4096,
        ),
    }


class CodeExecutionSandboxRuntime:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        mission_id: str,
        workspace_root: Path | str,
        runner: CodeExecutionRunner | None = None,
        profiles: dict[str, CodeExecutionProfile] | None = None,
    ) -> None:
        self.kernel = kernel
        self.mission_id = mission_id
        self.workspace_root = Path(workspace_root).resolve()
        self.runner = runner or _DefaultCodeExecutionRunner()
        self.profiles = profiles or default_code_execution_profiles()
        self.command_execution_count = 0

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        del context
        if envelope.capability_id != "code_execution_sandbox":
            raise CodeExecutionSandboxRuntimeError("code_execution_sandbox_capability_required")
        if envelope.operation == "code_exec.run_profile":
            return self._run_profile(envelope, authority=authority)
        if envelope.operation == "code_exec.inspect_result":
            return self._inspect_result(envelope, authority=authority)
        raise CodeExecutionSandboxRuntimeError(f"code_execution_operation_unsupported:{envelope.operation}")

    def _run_profile(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "code_exec.run_profile")
        params = dict(envelope.params)
        if "command" in params or "shell" in params or "shell_command" in params:
            raise CodeExecutionSandboxRuntimeError("code_exec_raw_shell_blocked")
        profile_id = str(params.get("profile_id") or "")
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise CodeExecutionSandboxRuntimeError("code_exec_profile_not_allowed")
        self._validate_profile(profile)
        args = tuple(str(item) for item in params.get("args", ()))
        self._validate_args(profile, args)
        request = CodeExecutionRequest(
            mission_id=self.mission_id,
            profile_id=profile.profile_id,
            args=args,
            workspace_ref=f"workspace:{self.workspace_root}",
        )
        command_args = tuple(profile.fixed_args_prefix) + args
        process = self._run_process(profile, command_args)
        self.command_execution_count += 1
        stdout_excerpt = _bounded_text(process.stdout, profile.max_stdout_bytes)
        stderr_excerpt = _bounded_text(process.stderr, profile.max_stderr_bytes)
        result_model = CodeExecutionResult(
            mission_id=self.mission_id,
            profile_id=profile.profile_id,
            args_hash=request.args_hash,
            exit_code=process.exit_code,
            duration_ms=process.duration_ms,
            timed_out=process.timed_out,
            stdout_hash=_sha256_text(process.stdout),
            stderr_hash=_sha256_text(process.stderr),
            stdout_excerpt=stdout_excerpt,
            stderr_excerpt=stderr_excerpt,
        )
        status = "timeout" if process.timed_out else "passed" if process.exit_code == 0 else "failed"
        receipt = CodeExecutionReceipt(
            mission_id=self.mission_id,
            request_ref=request.request_id,
            result_ref=result_model.result_id,
            profile_id=profile.profile_id,
            args_hash=request.args_hash,
            workspace_ref=f"workspace:{self.workspace_root}",
            status=status,
            exit_code=process.exit_code,
            duration_ms=process.duration_ms,
            stdout_hash=result_model.stdout_hash,
            stderr_hash=result_model.stderr_hash,
            stdout_excerpt=stdout_excerpt,
            stderr_excerpt=stderr_excerpt,
            result_hash=result_model.result_hash,
        )
        certificate = CodeExecutionFinalCertificate(
            mission_id=self.mission_id,
            status="accepted" if status == "passed" else "blocked",
            accepted=status == "passed",
            reason=f"code_exec_{status}",
            receipt_refs=(receipt.receipt_id,),
            result_refs=(result_model.result_id,),
        )
        self._write_artifact("requests", request.request_id, request.safe_model_dump())
        self._write_artifact("results", result_model.result_id, result_model.safe_model_dump())
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "code_execution_sandbox_profile_completed",
            "Bounded code execution profile completed with receipt.",
            metadata={
                "profile_id": profile.profile_id,
                "args_hash": request.args_hash,
                "exit_code": process.exit_code,
                "status": status,
                "timed_out": process.timed_out,
                "result_hash": result_model.result_hash,
            },
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[certificate.certificate_id],
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status=status,
            receipt_refs=(receipt.receipt_id,),
            finalgate_refs=(certificate.certificate_id,),
            material_action=True,
            observation_summary=f"code execution profile {profile.profile_id} {status}.",
            blocked_reason="code_exec_timeout" if process.timed_out else None if process.exit_code == 0 else "code_exec_failed",
            failure_class=ActionFailureClass.RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE if process.timed_out else None,
            failure_code="EXECUTOR_TIMEOUT" if process.timed_out else None,
            recoverable=process.timed_out,
            result_hash=result_model.result_hash,
        )

    def _inspect_result(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "code_exec.inspect_result")
        receipt_ref = str(envelope.params.get("receipt_ref") or "")
        if not receipt_ref.startswith("code_exec_receipt_"):
            raise CodeExecutionSandboxRuntimeError("code_exec_receipt_ref_required")
        receipt_path = self._artifact_path("receipts", receipt_ref)
        if not receipt_path.is_file():
            raise CodeExecutionSandboxRuntimeError("code_exec_receipt_not_found")
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            material_action=False,
            observation_summary=f"code execution receipt {receipt_ref} inspected.",
            result_hash=stable_hash({"receipt_ref": receipt_ref}),
        )

    def _run_process(self, profile: CodeExecutionProfile, command_args: tuple[str, ...]) -> CodeExecutionProcessResult:
        if profile.profile_id == "fake_pass":
            return CodeExecutionProcessResult(
                exit_code=0,
                duration_ms=0,
                stdout="fake code execution profile passed",
                stderr="",
                timed_out=False,
            )
        if profile.profile_id == "fake_timeout":
            return CodeExecutionProcessResult(
                exit_code=124,
                duration_ms=profile.timeout_seconds * 1000,
                stdout="",
                stderr="fake code execution profile timed out",
                timed_out=True,
            )
        if profile.writes_allowed:
            return self.runner.run(
                executable=profile.executable,
                args=command_args,
                cwd=self.workspace_root,
                timeout_seconds=profile.timeout_seconds,
                env=_minimal_env(),
            )
        with tempfile.TemporaryDirectory(prefix="sentinel-code-exec-") as tmp:
            sandbox_workspace = Path(tmp) / "workspace"
            shutil.copytree(
                self.workspace_root,
                sandbox_workspace,
                ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__"),
            )
            return self.runner.run(
                executable=profile.executable,
                args=command_args,
                cwd=sandbox_workspace,
                timeout_seconds=profile.timeout_seconds,
                env=_minimal_env(),
            )

    def _require_authorized(self, authority: MissionAuthorityEnvelope, action_name: str) -> None:
        if authority.revoked_at is not None:
            raise CodeExecutionSandboxRuntimeError("mission_authority_inactive")
        if action_name not in authority.allowed_actions and action_name.split(".", 1)[-1] not in authority.allowed_actions:
            raise CodeExecutionSandboxRuntimeError("code_exec_action_not_authorized")
        allowed_roots = [Path(item).resolve() for item in authority.allowed_paths]
        if not any(self.workspace_root == root or root in self.workspace_root.parents for root in allowed_roots):
            raise CodeExecutionSandboxRuntimeError("code_exec_workspace_not_authorized")

    def _validate_profile(self, profile: CodeExecutionProfile) -> None:
        if profile.network_allowed:
            raise CodeExecutionSandboxRuntimeError("code_exec_network_blocked")
        executable_name = Path(profile.executable).name.lower()
        if executable_name in FORBIDDEN_PROFILE_EXECUTABLES:
            raise CodeExecutionSandboxRuntimeError("code_exec_ambient_shell_blocked")
        for fixed_arg in profile.fixed_args_prefix:
            self._reject_unsafe_arg(fixed_arg, allow_module_separator=True)

    def _validate_args(self, profile: CodeExecutionProfile, args: tuple[str, ...]) -> None:
        if len(args) > 12:
            raise CodeExecutionSandboxRuntimeError("code_exec_args_not_allowed")
        allowed_kinds = set(profile.allowed_arg_kinds)
        for arg in args:
            if "python_module" in allowed_kinds and len(allowed_kinds) == 1:
                self._validate_module_name(arg)
            else:
                self._validate_workspace_arg(arg)

    def _validate_workspace_arg(self, arg: str) -> None:
        self._reject_unsafe_arg(arg)
        raw = Path(arg)
        if raw.is_absolute():
            raise CodeExecutionSandboxRuntimeError("code_exec_absolute_path_blocked")
        if self._path_uses_symlink(raw):
            raise CodeExecutionSandboxRuntimeError("code_exec_symlink_escape")
        candidate = (self.workspace_root / raw).resolve()
        if candidate != self.workspace_root and self.workspace_root not in candidate.parents:
            raise CodeExecutionSandboxRuntimeError("code_exec_path_escape")

    def _validate_module_name(self, arg: str) -> None:
        self._reject_unsafe_arg(arg, allow_module_separator=True)
        if not arg or "/" in arg or "\\" in arg or arg.startswith(".") or arg.endswith("."):
            raise CodeExecutionSandboxRuntimeError("code_exec_module_not_allowed")
        for part in arg.split("."):
            if not part.isidentifier():
                raise CodeExecutionSandboxRuntimeError("code_exec_module_not_allowed")

    def _reject_unsafe_arg(self, arg: str, *, allow_module_separator: bool = False) -> None:
        lowered = arg.lower()
        if any(marker in lowered for marker in SHELL_ARG_MARKERS):
            raise CodeExecutionSandboxRuntimeError("code_exec_shell_metacharacter_blocked")
        if any(marker in lowered for marker in NETWORK_ARG_MARKERS):
            raise CodeExecutionSandboxRuntimeError("code_exec_network_arg_blocked")
        if any(marker in lowered for marker in CREDENTIAL_ARG_MARKERS):
            raise CodeExecutionSandboxRuntimeError("code_exec_credential_arg_blocked")
        if not allow_module_separator and arg.strip() in {".", ""}:
            return

    def _path_uses_symlink(self, relative: Path) -> bool:
        cursor = self.workspace_root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.exists() and cursor.is_symlink():
                return True
        return False

    def _write_artifact(self, collection: str, artifact_id: str, payload: dict[str, object]) -> None:
        self.kernel.store.atomic_write_json(self._artifact_path(collection, artifact_id), payload)

    def _artifact_path(self, collection: str, artifact_id: str) -> Path:
        return (
            self.kernel.store.mission_dir(self.mission_id, create=True)
            / "code_execution_sandbox"
            / collection
            / f"{artifact_id}.json"
        )

    def _append_event(
        self,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, object],
        receipt_refs: list[str],
        finalgate_refs: list[str],
    ) -> None:
        self.kernel.store.append_event(
            self.mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata,
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
        )


class _DefaultCodeExecutionRunner:
    def run(
        self,
        *,
        executable: str,
        args: tuple[str, ...],
        cwd: Path,
        timeout_seconds: int,
        env: dict[str, str],
    ) -> CodeExecutionProcessResult:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                [executable, *args],
                cwd=str(cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )
            return CodeExecutionProcessResult(
                exit_code=completed.returncode,
                duration_ms=max(int((time.monotonic() - started) * 1000), 0),
                stdout=completed.stdout,
                stderr=completed.stderr,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
            return CodeExecutionProcessResult(
                exit_code=124,
                duration_ms=max(int((time.monotonic() - started) * 1000), 0),
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
            )


def _minimal_env() -> dict[str, str]:
    allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONPATH"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _bounded_text(value: str, limit_bytes: int) -> str:
    encoded = value.encode("utf-8", errors="replace")[:limit_bytes]
    redacted = redact_operator_text(encoded.decode("utf-8", errors="replace"))
    redacted = OUTPUT_SECRET_LABEL_PATTERN.sub("[REDACTED_SECRET]", redacted)
    return redacted[:240]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "CodeExecutionProcessResult",
    "CodeExecutionRunner",
    "CodeExecutionSandboxRuntime",
    "CodeExecutionSandboxRuntimeError",
    "default_code_execution_profiles",
]
