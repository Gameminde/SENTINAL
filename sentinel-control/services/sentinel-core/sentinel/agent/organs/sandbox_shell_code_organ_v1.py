from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from sentinel.power.runtime import PowerStepResult, PowerStepStatus
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    SHARED_SECRET_LIKE_PATTERN,
    scan_forbidden_payload_categorized,
    scan_secret_like_text,
)


class ShellCodeSandboxStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMED_OUT = "timed_out"


class ShellCodeSandboxRequest(SentinelModel):
    mission_id: str
    project_root: Path
    cwd: str | Path = "."
    command: list[str]
    timeout_seconds: int = Field(default=30, ge=1, le=120)
    output_max_bytes: int = Field(default=16_384, ge=256, le=131_072)
    env: dict[str, str] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @field_validator("command")
    @classmethod
    def _command_must_be_tokenized_and_secret_free(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("command must contain at least one token")
        normalized: list[str] = []
        for index, token in enumerate(value):
            if not isinstance(token, str) or not token.strip():
                raise ValueError("command tokens must be non-empty strings")
            if scan_secret_like_text(token, path=f"$.command[{index}]"):
                raise ValueError("command token contains a secret-like value")
            normalized.append(token.strip())
        return normalized

    @model_validator(mode="after")
    def _request_is_safe(self) -> ShellCodeSandboxRequest:
        if self.authority_effect != "none":
            raise ValueError("shell/code sandbox request cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("shell/code sandbox request must remain data-not-instruction")
        root = self.project_root.resolve()
        cwd = _resolve_cwd(root, self.cwd)
        if cwd != root and root not in cwd.parents:
            raise ValueError("cwd escapes project_root")
        scan = scan_forbidden_payload_categorized(self.env, path="$.env")
        rejected = [
            *scan[OrganSafetyScanCategory.SECRET.value],
            *scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value],
            *scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value],
            *scan[OrganSafetyScanCategory.UNSAFE_PAYLOAD.value],
        ]
        if rejected:
            raise ValueError("env contains forbidden or secret-like metadata")
        return self

    @property
    def resolved_project_root(self) -> Path:
        return self.project_root.resolve()

    @property
    def resolved_cwd(self) -> Path:
        return _resolve_cwd(self.resolved_project_root, self.cwd)


class ShellCodeSandboxContract(SentinelModel):
    allowed_prefixes: tuple[tuple[str, ...], ...] = (
        ("python", "-m", "pytest"),
        ("python", "-m", "compileall"),
        ("npm", "test"),
        ("npm", "run", "build"),
        ("node", "--version"),
        ("python", "--version"),
    )
    forbidden_tokens: tuple[str, ...] = (
        ";",
        "&&",
        "||",
        "|",
        ">",
        "<",
        "`",
        "$(",
        "cmd",
        "powershell",
        "pwsh",
        "bash",
        "sh",
        "rm",
        "del",
        "curl",
        "wget",
        "ssh",
        "scp",
    )
    max_timeout_seconds: int = Field(default=120, ge=1)
    max_output_bytes: int = Field(default=131_072, ge=256)
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _contract_is_not_authority(self) -> ShellCodeSandboxContract:
        if self.authority_effect != "none":
            raise ValueError("shell/code sandbox contract cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("shell/code sandbox contract must remain data-not-instruction")
        return self


class ShellCodeSandboxReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("shell_receipt"))
    mission_id: str
    command_hash: str
    command_display: str
    cwd: str
    exit_code: int | None
    timed_out: bool = False
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    output_truncated: bool = False
    before_tree_hash: str
    after_tree_hash: str
    created_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    started_at: datetime
    ended_at: datetime
    authority_effect: str = "none"
    execution_effect: str = "sandboxed_subprocess"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _receipt_is_safe(self) -> ShellCodeSandboxReceipt:
        if self.authority_effect != "none":
            raise ValueError("shell/code sandbox receipt cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("shell/code sandbox receipt must remain data-not-instruction")
        for value in (self.command_display, self.stdout_excerpt, self.stderr_excerpt):
            if SHARED_SECRET_LIKE_PATTERN.search(value):
                raise ValueError("shell/code sandbox receipt contains secret-like text")
        return self


class ShellCodeSandboxFinalGateCertificate(SentinelModel):
    certificate_id: str = Field(default_factory=lambda: new_id("shell_finalgate"))
    mission_id: str
    passed: bool
    status: ShellCodeSandboxStatus
    receipt_ref: str | None = None
    failures: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _certificate_is_not_authority(self) -> ShellCodeSandboxFinalGateCertificate:
        if self.authority_effect != "none":
            raise ValueError("shell/code sandbox certificate cannot grant authority")
        if self.data_not_instruction is not True:
            raise ValueError("shell/code sandbox certificate must remain data-not-instruction")
        return self


class ShellCodeSandboxResult(SentinelModel):
    mission_id: str
    status: ShellCodeSandboxStatus
    receipt: ShellCodeSandboxReceipt | None = None
    finalgate_certificate: ShellCodeSandboxFinalGateCertificate | None = None
    blocked_reason: str | None = None
    safe_summary: str = ""
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_future_execution: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _result_is_not_authority(self) -> ShellCodeSandboxResult:
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("shell/code sandbox result cannot grant authority or execute more")
        if self.can_grant_authority or self.can_approve_future_execution:
            raise ValueError("shell/code sandbox result cannot approve future execution")
        if self.data_not_instruction is not True:
            raise ValueError("shell/code sandbox result must remain data-not-instruction")
        return self


class ShellCodeSandboxFinalGate:
    def certify(self, result: ShellCodeSandboxResult) -> ShellCodeSandboxFinalGateCertificate:
        failures: list[str] = []
        if result.status in {ShellCodeSandboxStatus.SUCCEEDED, ShellCodeSandboxStatus.FAILED, ShellCodeSandboxStatus.TIMED_OUT}:
            if result.receipt is None:
                failures.append("missing_execution_receipt")
        if result.receipt is not None:
            if not result.receipt.command_hash:
                failures.append("missing_command_hash")
            if not result.receipt.after_tree_hash:
                failures.append("missing_after_tree_hash")
            if SHARED_SECRET_LIKE_PATTERN.search(result.receipt.stdout_excerpt + result.receipt.stderr_excerpt):
                failures.append("secret_like_output_excerpt")
        return ShellCodeSandboxFinalGateCertificate(
            mission_id=result.mission_id,
            passed=not failures,
            status=result.status,
            receipt_ref=result.receipt.receipt_id if result.receipt else None,
            failures=failures,
        )


class ShellCodeSandboxOrganV1:
    organ_kind = "sandbox_shell_code"

    def execute(
        self,
        request: ShellCodeSandboxRequest,
        *,
        contract: ShellCodeSandboxContract | None = None,
        kill_switch: Any | None = None,
    ) -> ShellCodeSandboxResult:
        active_contract = contract or ShellCodeSandboxContract()
        if kill_switch is not None and (getattr(kill_switch, "triggered", False) or not getattr(kill_switch, "execution_allowed", True)):
            return self._blocked(request, "kill_switch_triggered")

        block_reason = _command_block_reason(request.command, active_contract)
        if block_reason:
            return self._blocked(request, block_reason)

        root = request.resolved_project_root
        cwd = request.resolved_cwd
        cwd.mkdir(parents=True, exist_ok=True)
        started_at = _utc_now()
        before_manifest = _tree_manifest(root)
        command = _runtime_command(request.command)
        env = _scrubbed_env(request.env)

        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                capture_output=True,
                timeout=min(request.timeout_seconds, active_contract.max_timeout_seconds),
                shell=False,
                check=False,
            )
            status = ShellCodeSandboxStatus.SUCCEEDED if completed.returncode == 0 else ShellCodeSandboxStatus.FAILED
            receipt = _build_receipt(
                request,
                before_manifest,
                started_at=started_at,
                ended_at=_utc_now(),
                exit_code=completed.returncode,
                timed_out=False,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            status = ShellCodeSandboxStatus.TIMED_OUT
            receipt = _build_receipt(
                request,
                before_manifest,
                started_at=started_at,
                ended_at=_utc_now(),
                exit_code=None,
                timed_out=True,
                stdout=exc.stdout or b"",
                stderr=exc.stderr or b"",
            )

        result = ShellCodeSandboxResult(
            mission_id=request.mission_id,
            status=status,
            receipt=receipt,
            safe_summary=f"Sandbox command finished with status {status.value}.",
        )
        return result.model_copy(update={"finalgate_certificate": ShellCodeSandboxFinalGate().certify(result)})

    @staticmethod
    def _blocked(request: ShellCodeSandboxRequest, reason: str) -> ShellCodeSandboxResult:
        result = ShellCodeSandboxResult(
            mission_id=request.mission_id,
            status=ShellCodeSandboxStatus.BLOCKED,
            blocked_reason=reason,
            safe_summary=f"Sandbox command blocked: {reason}.",
        )
        return result.model_copy(update={"finalgate_certificate": ShellCodeSandboxFinalGate().certify(result)})


def build_shell_code_power_executor(*, project_root: str | Path) -> Any:
    root = Path(project_root).resolve()
    organ = ShellCodeSandboxOrganV1()

    def _executor(step: Any, _context: dict[str, Any]) -> PowerStepResult:
        if str(getattr(step, "actuator_family", "")) not in {"shell_sandbox", "PowerActuatorFamily.SHELL_SANDBOX"}:
            return PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.BLOCKED,
                blocked_reason="unsupported_actuator_family",
                safe_summary="Shell/code executor can only run shell_sandbox steps.",
            )
        request_payload = dict(getattr(step, "request", {}) or {})
        request = ShellCodeSandboxRequest(
            mission_id=str(_context.get("mission_id") or "mission_unknown"),
            project_root=root,
            cwd=request_payload.get("cwd", "."),
            command=list(request_payload.get("command") or []),
            timeout_seconds=int(request_payload.get("timeout_seconds", 30)),
            output_max_bytes=int(request_payload.get("output_max_bytes", 16_384)),
        )
        result = organ.execute(request)
        status = PowerStepStatus.SUCCEEDED if result.status is ShellCodeSandboxStatus.SUCCEEDED else PowerStepStatus.FAILED
        if result.status is ShellCodeSandboxStatus.BLOCKED:
            status = PowerStepStatus.BLOCKED
        return PowerStepResult(
            step_id=step.step_id,
            status=status,
            receipt_refs=[result.receipt.receipt_id] if result.receipt else [],
            finalgate_certificate_refs=[result.finalgate_certificate.certificate_id] if result.finalgate_certificate else [],
            blocked_reason=result.blocked_reason,
            safe_summary=result.safe_summary,
        )

    return _executor


def _command_block_reason(command: list[str], contract: ShellCodeSandboxContract) -> str | None:
    normalized = _normalized_command(command)
    for token in normalized:
        lowered = token.lower()
        if lowered in contract.forbidden_tokens or any(marker in lowered for marker in ("&&", "||", "$(", "`")):
            return "forbidden_shell_token"
    if not any(_has_prefix(normalized, prefix) for prefix in contract.allowed_prefixes):
        return "command_not_allowlisted"
    return None


def _normalized_command(command: list[str]) -> list[str]:
    if not command:
        return []
    executable = command[0]
    if Path(executable).name.lower() in {"python", "python.exe"} or Path(executable).resolve() == Path(sys.executable).resolve():
        executable = "python"
    else:
        executable = Path(executable).name.lower()
    return [executable, *command[1:]]


def _runtime_command(command: list[str]) -> list[str]:
    normalized = _normalized_command(command)
    if normalized and normalized[0] == "python":
        return [sys.executable, *command[1:]]
    return command


def _has_prefix(command: list[str], prefix: tuple[str, ...]) -> bool:
    if len(command) < len(prefix):
        return False
    return tuple(token.lower() for token in command[: len(prefix)]) == prefix


def _resolve_cwd(root: Path, cwd: str | Path) -> Path:
    cwd_path = Path(cwd)
    if not cwd_path.is_absolute():
        cwd_path = root / cwd_path
    return cwd_path.resolve()


def _scrubbed_env(extra: dict[str, str]) -> dict[str, str]:
    allowed_keys = {"PATH", "Path", "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "HOME"}
    env = {key: value for key, value in os.environ.items() if key in allowed_keys}
    for key, value in extra.items():
        if scan_forbidden_payload_categorized({key: value})[OrganSafetyScanCategory.ALL.value]:
            continue
        env[str(key)] = str(value)
    return env


def _tree_manifest(root: Path) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return manifest
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if root not in path.resolve().parents:
            continue
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        manifest[rel] = {"sha256": _sha256_bytes(data), "size_bytes": len(data)}
    return manifest


def _build_receipt(
    request: ShellCodeSandboxRequest,
    before_manifest: dict[str, dict[str, Any]],
    *,
    started_at: datetime,
    ended_at: datetime,
    exit_code: int | None,
    timed_out: bool,
    stdout: bytes,
    stderr: bytes,
) -> ShellCodeSandboxReceipt:
    after_manifest = _tree_manifest(request.resolved_project_root)
    created, modified, deleted = _diff_manifests(before_manifest, after_manifest)
    stdout_excerpt, stdout_truncated = _safe_excerpt(stdout, request.output_max_bytes)
    stderr_excerpt, stderr_truncated = _safe_excerpt(stderr, request.output_max_bytes)
    return ShellCodeSandboxReceipt(
        mission_id=request.mission_id,
        command_hash=_stable_hash(request.command),
        command_display=" ".join(_normalized_command(request.command)),
        cwd=str(request.resolved_cwd),
        exit_code=exit_code,
        timed_out=timed_out,
        stdout_sha256=_sha256_bytes(stdout) if stdout else None,
        stderr_sha256=_sha256_bytes(stderr) if stderr else None,
        stdout_excerpt=stdout_excerpt,
        stderr_excerpt=stderr_excerpt,
        output_truncated=stdout_truncated or stderr_truncated,
        before_tree_hash=_stable_hash(before_manifest),
        after_tree_hash=_stable_hash(after_manifest),
        created_files=created,
        modified_files=modified,
        deleted_files=deleted,
        artifact_hashes={path: str(after_manifest[path]["sha256"]) for path in sorted(created + modified) if path in after_manifest},
        started_at=started_at,
        ended_at=ended_at,
    )


def _diff_manifests(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    created = sorted(after_keys - before_keys)
    deleted = sorted(before_keys - after_keys)
    modified = sorted(key for key in before_keys & after_keys if before[key]["sha256"] != after[key]["sha256"])
    return created, modified, deleted


def _safe_excerpt(data: bytes, max_bytes: int) -> tuple[str, bool]:
    truncated = len(data) > max_bytes
    text = data[:max_bytes].decode("utf-8", errors="replace")
    return SHARED_SECRET_LIKE_PATTERN.sub("[REDACTED_SECRET]", text), truncated


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)
