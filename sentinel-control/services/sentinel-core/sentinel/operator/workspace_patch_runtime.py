from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Protocol

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.workspace_patch_models import (
    WorkspacePatchCheckResult,
    WorkspacePatchEvidence,
    WorkspacePatchFinalCertificate,
    WorkspacePatchProposal,
    WorkspacePatchReceipt,
    WorkspacePatchVerificationReceipt,
)


class WorkspacePatchRuntimeError(RuntimeError):
    pass


class WorkspacePatchCheckRunner(Protocol):
    def run(self, *, command_id: str, args: tuple[str, ...], cwd: Path) -> WorkspacePatchCheckResult:
        ...


SENSITIVE_WORKSPACE_PATCH_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        "authority-scope.json",
        "credentials.json",
        "model-contract.json",
        "secrets.json",
    }
)

ALLOWED_CHECK_COMMAND_IDS = frozenset({"fake_pass", "python_compileall", "pytest_file"})
SHELL_ARG_MARKERS = frozenset({"&&", "||", "|", ";", ">", "<", "`", "$(", "%COMSPEC%"})


class WorkspacePatchRuntime:
    def __init__(
        self,
        *,
        kernel: MissionKernel,
        mission_id: str,
        workspace_root: Path | str,
        check_runner: WorkspacePatchCheckRunner | None = None,
        allowed_check_command_ids: tuple[str, ...] | None = None,
    ) -> None:
        self.kernel = kernel
        self.mission_id = mission_id
        self.workspace_root = Path(workspace_root).resolve()
        self.check_runner = check_runner or _DefaultWorkspacePatchCheckRunner()
        self.allowed_check_command_ids = frozenset(allowed_check_command_ids or tuple(ALLOWED_CHECK_COMMAND_IDS))
        self.patch_application_count = 0
        self.verification_run_count = 0

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        del context
        if envelope.capability_id != "workspace_patch":
            raise WorkspacePatchRuntimeError("workspace_patch_capability_required")
        if envelope.operation == "apply_patch":
            return self._apply_patch(envelope, authority=authority)
        if envelope.operation == "verify_file_hash":
            return self._verify_file_hash(envelope, authority=authority)
        if envelope.operation == "run_bounded_check":
            return self._run_bounded_check(envelope, authority=authority)
        if envelope.operation == "finish_patch_step":
            return ActionResult(
                action_id=envelope.action_id,
                capability_id=envelope.capability_id,
                operation=envelope.operation,
                status="completed",
                material_action=False,
                observation_summary="workspace patch step finished.",
            )
        raise WorkspacePatchRuntimeError(f"workspace_patch_operation_unsupported:{envelope.operation}")

    def _apply_patch(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "workspace_patch.apply_patch")
        params = dict(envelope.params)
        target_path = str(params.get("target_path") or envelope.target_ref or "")
        declared_targets = tuple(str(item) for item in params.get("target_paths", params.get("declared_target_paths", [target_path])))
        if len(set(declared_targets)) != 1 or declared_targets[0] != target_path:
            raise WorkspacePatchRuntimeError("workspace_patch_multiple_targets_blocked")
        path = self._resolve_target(target_path, must_exist=True)
        expected_base_hash = str(params.get("expected_base_hash") or "")
        if not expected_base_hash:
            raise WorkspacePatchRuntimeError("workspace_patch_expected_base_hash_required")
        before_bytes = path.read_bytes()
        before_hash = _sha256_bytes(before_bytes)
        if before_hash != expected_base_hash:
            raise WorkspacePatchRuntimeError("workspace_patch_base_hash_mismatch")
        old_text = str(params.get("old_text") or "")
        new_text = str(params.get("new_text") or "")
        if not old_text:
            raise WorkspacePatchRuntimeError("workspace_patch_old_text_required")
        _reject_patch_content(new_text)
        try:
            current_text = before_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspacePatchRuntimeError("workspace_patch_binary_target_blocked") from exc
        normalized_old_text = _normalize_patch_newlines(old_text)
        normalized_new_text = _normalize_patch_newlines(new_text)
        normalized_current_text = _normalize_patch_newlines(current_text)
        if normalized_old_text not in normalized_current_text:
            raise WorkspacePatchRuntimeError("workspace_patch_not_applicable")
        updated_text = normalized_current_text.replace(normalized_old_text, normalized_new_text, 1)
        patch_hash = stable_hash(
            {
                "target_path": self._relative(path),
                "expected_base_hash": expected_base_hash,
                "old_text_hash": _sha256_text(old_text),
                "new_text_hash": _sha256_text(new_text),
            }
        )
        proposal = WorkspacePatchProposal(
            mission_id=self.mission_id,
            target_path=self._relative(path),
            expected_base_hash=expected_base_hash,
            before_hash=before_hash,
            patch_hash=patch_hash,
            declared_target_paths=(self._relative(path),),
        )
        path.write_text(updated_text, encoding="utf-8")
        self.patch_application_count += 1
        after_bytes = path.read_bytes()
        after_hash = _sha256_bytes(after_bytes)
        evidence = WorkspacePatchEvidence(
            mission_id=self.mission_id,
            target_path=self._relative(path),
            before_hash=before_hash,
            after_hash=after_hash,
            patch_hash=patch_hash,
            byte_delta=len(after_bytes) - len(before_bytes),
            line_delta=updated_text.count("\n") - current_text.count("\n"),
        )
        receipt = WorkspacePatchReceipt(
            mission_id=self.mission_id,
            target_path=self._relative(path),
            status="success",
            before_hash=before_hash,
            after_hash=after_hash,
            patch_hash=patch_hash,
            evidence_refs=(evidence.evidence_id,),
        )
        certificate = WorkspacePatchFinalCertificate(
            mission_id=self.mission_id,
            status="accepted",
            accepted=True,
            reason="workspace_patch_applied",
            receipt_refs=(receipt.receipt_id,),
            evidence_refs=(evidence.evidence_id,),
        )
        self._write_artifact("proposals", proposal.proposal_id, proposal.safe_model_dump())
        self._write_artifact("evidence", evidence.evidence_id, evidence.safe_model_dump())
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "workspace_patch_applied",
            "Workspace patch applied inside granted workspace.",
            metadata={
                "target_path": self._relative(path),
                "before_hash": before_hash,
                "after_hash": after_hash,
                "patch_hash": patch_hash,
            },
            receipt_refs=[receipt.receipt_id],
            finalgate_refs=[certificate.certificate_id],
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=(receipt.receipt_id,),
            evidence_refs=(evidence.evidence_id,),
            finalgate_refs=(certificate.certificate_id,),
            material_action=True,
            observation_summary=f"patch applied to {self._relative(path)} with hash-anchored receipt.",
        )

    def _verify_file_hash(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "workspace_patch.verify_file_hash")
        params = dict(envelope.params)
        path = self._resolve_target(str(params.get("target_path") or envelope.target_ref or ""), must_exist=True)
        expected_hash = str(params.get("expected_hash") or "")
        actual_hash = _sha256_bytes(path.read_bytes())
        status = "passed" if expected_hash and actual_hash == expected_hash else "failed"
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status=status,
            material_action=False,
            observation_summary=f"hash verification {status} for {self._relative(path)}.",
            result_hash=stable_hash({"target_path": self._relative(path), "actual_hash": actual_hash, "status": status}),
        )

    def _run_bounded_check(self, envelope: ActionEnvelope, *, authority: MissionAuthorityEnvelope) -> ActionResult:
        self._require_authorized(authority, "workspace_patch.run_bounded_check")
        params = dict(envelope.params)
        if "command" in params:
            raise WorkspacePatchRuntimeError("workspace_patch_shell_blocked")
        command_id = str(params.get("command_id") or "")
        if command_id not in self.allowed_check_command_ids:
            raise WorkspacePatchRuntimeError("workspace_patch_check_not_allowed")
        args = tuple(str(item) for item in params.get("args", ()))
        self._validate_check_args(args)
        result = self.check_runner.run(command_id=command_id, args=args, cwd=self.workspace_root)
        self.verification_run_count += 1
        status = "passed" if result.exit_status == 0 else "failed"
        receipt = WorkspacePatchVerificationReceipt(
            mission_id=self.mission_id,
            command_id=result.command_id,
            args=result.args,
            status=status,
            exit_status=result.exit_status,
            duration_ms=result.duration_ms,
            stdout_hash=_sha256_text(result.stdout),
            stderr_hash=_sha256_text(result.stderr),
            stdout_excerpt=result.stdout[:240],
            stderr_excerpt=result.stderr[:240],
        )
        certificate = WorkspacePatchFinalCertificate(
            mission_id=self.mission_id,
            status="accepted" if status == "passed" else "blocked",
            accepted=status == "passed",
            reason=f"workspace_patch_check_{status}",
            receipt_refs=(receipt.receipt_id,),
        )
        self._write_artifact("receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_artifact("finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self._append_event(
            "workspace_patch_verification_completed",
            "Workspace patch bounded verification completed.",
            metadata={
                "command_id": command_id,
                "arg_count": len(args),
                "exit_status": result.exit_status,
                "status": status,
                "result_hash": receipt.result_hash,
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
            observation_summary=f"bounded check {command_id} {status}.",
            result_hash=receipt.result_hash,
        )

    def _require_authorized(self, authority: MissionAuthorityEnvelope, action_name: str) -> None:
        if authority.revoked_at is not None:
            raise WorkspacePatchRuntimeError("mission_authority_inactive")
        if action_name not in authority.allowed_actions and action_name.split(".", 1)[-1] not in authority.allowed_actions:
            raise WorkspacePatchRuntimeError("workspace_patch_action_not_authorized")
        allowed_roots = [Path(item).resolve() for item in authority.allowed_paths]
        if not any(self.workspace_root == root or root in self.workspace_root.parents for root in allowed_roots):
            raise WorkspacePatchRuntimeError("workspace_patch_workspace_not_authorized")

    def _resolve_target(self, requested: str, *, must_exist: bool) -> Path:
        if not requested.strip():
            raise WorkspacePatchRuntimeError("workspace_patch_target_required")
        raw = Path(requested)
        if raw.is_absolute():
            raise WorkspacePatchRuntimeError("workspace_patch_absolute_path_blocked")
        if any(part in SENSITIVE_WORKSPACE_PATCH_NAMES for part in raw.parts):
            raise WorkspacePatchRuntimeError("workspace_patch_sensitive_target_blocked")
        if self._path_uses_symlink(raw):
            raise WorkspacePatchRuntimeError("workspace_patch_symlink_escape")
        candidate = (self.workspace_root / raw).resolve()
        if candidate != self.workspace_root and self.workspace_root not in candidate.parents:
            raise WorkspacePatchRuntimeError("workspace_patch_path_escape")
        if must_exist and not candidate.is_file():
            raise WorkspacePatchRuntimeError("workspace_patch_target_not_file")
        return candidate

    def _path_uses_symlink(self, relative: Path) -> bool:
        cursor = self.workspace_root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.exists() and cursor.is_symlink():
                return True
        return False

    def _validate_check_args(self, args: tuple[str, ...]) -> None:
        if len(args) > 12:
            raise WorkspacePatchRuntimeError("workspace_patch_check_not_allowed")
        for arg in args:
            lowered = arg.lower()
            if any(marker.lower() in lowered for marker in SHELL_ARG_MARKERS):
                raise WorkspacePatchRuntimeError("workspace_patch_shell_blocked")
            if any(marker in lowered for marker in ("http://", "https://", "authorization", "bearer", "api_key", "secret")):
                raise WorkspacePatchRuntimeError("workspace_patch_check_not_allowed")
            if "/" in arg or "\\" in arg or "." in arg:
                self._resolve_target(arg, must_exist=False)

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.workspace_root).as_posix()

    def _write_artifact(self, collection: str, artifact_id: str, payload: dict[str, object]) -> None:
        path = self.kernel.store.mission_dir(self.mission_id, create=True) / "workspace_patch" / collection / f"{artifact_id}.json"
        self.kernel.store.atomic_write_json(path, payload)

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


class _DefaultWorkspacePatchCheckRunner:
    def run(self, *, command_id: str, args: tuple[str, ...], cwd: Path) -> WorkspacePatchCheckResult:
        if command_id != "fake_pass":
            raise WorkspacePatchRuntimeError("workspace_patch_check_runner_missing")
        return WorkspacePatchCheckResult(
            command_id=command_id,
            args=args,
            exit_status=0,
            duration_ms=0,
            stdout="fake check passed",
            stderr="",
            cwd_hash=_sha256_text(str(cwd)),
        )


def _reject_patch_content(value: str) -> None:
    lowered = value.lower()
    markers = (
        "api_key=",
        "authorization:",
        "bearer ",
        "password=",
        "private key",
        "raw_prompt",
        "raw_response",
        "raw_reasoning",
        "reasoning_content",
        "credential",
        "secret=",
    )
    if any(marker in lowered for marker in markers):
        raise WorkspacePatchRuntimeError("workspace_patch_forbidden_content")


def _normalize_patch_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "WorkspacePatchCheckResult",
    "WorkspacePatchCheckRunner",
    "WorkspacePatchRuntime",
    "WorkspacePatchRuntimeError",
]
