from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.evidence_ranker import sanitize_context_payload
from sentinel.shared.models import SentinelModel, new_id


REQUIRED_DESKTOP_L6_BINDING_REFS = {
    "jarvis_sidecar_rpc_registry",
    "openjarvis_budget_timeout_discipline",
    "openclaw_action_kernel_preview",
    "hermes_context_compression",
    "sentinel_p6r_decision_frame",
}

WORKSPACE_L6_OPERATIONS = {"list_dir", "read_file", "write_file", "create_folder", "rollback_workspace_change"}
WORKSPACE_L6_MUTATIONS = {"write_file", "create_folder"}
HOST_CONTROL_SURFACES = {
    "shell",
    "process",
    "terminal",
    "screenshot",
    "clipboard",
    "desktop_click",
    "desktop_type",
    "desktop_press_keys",
    "desktop_launch_app",
    "desktop_focus_window",
    "sidecar_admin",
}


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _path_containment_proof_hash(*, workspace_root: str, resolved_path: str, relative_path: str) -> str:
    root = Path(workspace_root).resolve()
    resolved = Path(resolved_path).resolve()
    return _hash_payload(
        {
            "workspace_root": str(root),
            "resolved_path": str(resolved),
            "relative_path": relative_path,
        }
    )


class DesktopWorkspaceAuthority(SentinelModel):
    mission_id: str
    root_authority_id: str
    workspace_root: str
    allowed_operations: list[str]
    source_binding_refs: list[str]
    policy_hash: str
    expires_at: datetime
    evidence_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> DesktopWorkspaceAuthority:
        root = Path(self.workspace_root).resolve()
        missing = sorted(REQUIRED_DESKTOP_L6_BINDING_REFS - set(self.source_binding_refs))
        if missing:
            raise ValueError(f"DesktopWorkspaceAuthority requires AgentLab source binding refs:{missing}")
        unknown = sorted(set(self.allowed_operations) - WORKSPACE_L6_OPERATIONS)
        if unknown:
            raise ValueError(f"unsupported Desktop Workspace L6 operation:{unknown}")
        if not self.root_authority_id:
            raise ValueError("DesktopWorkspaceAuthority requires root authority id.")
        if not self.policy_hash:
            raise ValueError("DesktopWorkspaceAuthority requires policy hash.")
        if not self.evidence_refs:
            raise ValueError("DesktopWorkspaceAuthority requires evidence refs.")
        if self.expires_at <= datetime.now(UTC):
            raise ValueError("DesktopWorkspaceAuthority is expired.")
        if self.authority_expansion:
            raise ValueError("DesktopWorkspaceAuthority cannot expand authority.")
        self.workspace_root = str(root)
        return self

    def allows(self, operation: str) -> bool:
        return operation in set(self.allowed_operations)


class WorkspaceOperationBudget(SentinelModel):
    max_operations: int = Field(default=50, gt=0)
    max_read_bytes: int = Field(default=250_000, gt=0)
    max_write_bytes: int = Field(default=250_000, gt=0)
    timeout_seconds: float = Field(default=10.0, gt=0.0)


class WorkspaceTimeoutPolicy(SentinelModel):
    timeout_seconds: float = Field(default=10.0, gt=0.0)
    fallback_to_preview_on_timeout: bool = True


class WorkspaceMutationScope(SentinelModel):
    allowed_operations: list[str]
    allowed_root: str
    shell_process_execution_allowed: bool = False
    live_host_control_allowed: bool = False

    @model_validator(mode="after")
    def _validate(self) -> WorkspaceMutationScope:
        if self.shell_process_execution_allowed:
            raise ValueError("Desktop Workspace L6 cannot allow shell/process execution.")
        if self.live_host_control_allowed:
            raise ValueError("Desktop Workspace L6 cannot allow live host control.")
        return self


class PathContainmentProofRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("pathproof"))
    workspace_root: str
    resolved_path: str
    relative_path: str
    proof_hash: str = ""

    @model_validator(mode="after")
    def _validate(self) -> PathContainmentProofRef:
        root = Path(self.workspace_root).resolve()
        resolved = Path(self.resolved_path).resolve()
        if not _is_within_root(resolved, root):
            raise ValueError("path containment proof cannot prove outside-root path.")
        if not self.proof_hash:
            self.proof_hash = _hash_payload(
                {
                    "workspace_root": str(root),
                    "resolved_path": str(resolved),
                    "relative_path": self.relative_path,
                }
            )
        return self


class WorkspaceRollbackRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("rollback"))
    action: str
    relative_path: str
    previous_exists: bool
    previous_content_hash: str | None = None
    rollback_instruction: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> WorkspaceRollbackRef:
        if not self.evidence_refs:
            raise ValueError("WorkspaceRollbackRef requires evidence refs.")
        if self.action not in WORKSPACE_L6_MUTATIONS:
            raise ValueError("WorkspaceRollbackRef only applies to workspace mutations.")
        return self


class DesktopWorkspaceKillSwitch(SentinelModel):
    mission_id: str
    triggered: bool = False
    reason: str | None = None

    def trigger(self, *, reason: str) -> DesktopWorkspaceKillSwitch:
        return self.model_copy(update={"triggered": True, "reason": reason})


class WorkspaceCostTrace(SentinelModel):
    operation_count: int = Field(ge=0)
    bytes_read: int = Field(ge=0)
    bytes_written: int = Field(ge=0)
    timeout_seconds: float = Field(gt=0.0)


class DesktopWorkspaceL6Receipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("dwsl6"))
    mission_id: str
    action: str
    relative_path: str
    resolved_path: str
    output_summary: dict[str, Any]
    authority_refs: list[str]
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    workspace_root: str
    path_containment_proof_ref: str
    path_containment_proof_hash: str = ""
    rollback_ref: str | None = None
    source_binding_refs: list[str] = Field(default_factory=list)
    cost_trace: WorkspaceCostTrace | None = None
    real_workspace_execution: bool = True
    external_mutation: bool = False
    live_host_control_enabled: bool = False
    shell_process_execution_started: bool = False
    screenshot_clipboard_live: bool = False
    authority_expansion: bool = False
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _validate(self) -> DesktopWorkspaceL6Receipt:
        if self.action not in {
            "desktop_workspace_list_dir_l6",
            "desktop_workspace_read_file_l6",
            "desktop_workspace_write_file_l6",
            "desktop_workspace_create_folder_l6",
        }:
            raise ValueError("unsupported Desktop Workspace L6 action.")
        if not self.authority_refs:
            raise ValueError("DesktopWorkspaceL6Receipt requires authority refs.")
        if not self.evidence_refs:
            raise ValueError("DesktopWorkspaceL6Receipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("DesktopWorkspaceL6Receipt requires trace refs.")
        if not self.path_containment_proof_ref:
            raise ValueError("DesktopWorkspaceL6Receipt requires path containment proof ref.")
        root = Path(self.workspace_root).resolve()
        resolved = Path(self.resolved_path).resolve()
        if not _is_within_root(resolved, root):
            raise ValueError("DesktopWorkspaceL6Receipt resolved path is outside workspace root.")
        expected_proof_hash = _path_containment_proof_hash(
            workspace_root=str(root),
            resolved_path=str(resolved),
            relative_path=self.relative_path,
        )
        if self.path_containment_proof_hash and self.path_containment_proof_hash != expected_proof_hash:
            raise ValueError("DesktopWorkspaceL6Receipt path containment proof hash mismatch.")
        if not self.path_containment_proof_hash:
            self.path_containment_proof_hash = expected_proof_hash
        self.workspace_root = str(root)
        self.resolved_path = str(resolved)
        if self.external_mutation:
            raise ValueError("Desktop Workspace L6 cannot perform external mutation.")
        if self.live_host_control_enabled or self.shell_process_execution_started or self.screenshot_clipboard_live:
            raise ValueError("host-control surfaces are not allowed in Desktop Workspace L6.")
        if self.authority_expansion:
            raise ValueError("DesktopWorkspaceL6Receipt cannot expand authority.")
        if not self.receipt_hash:
            self.receipt_hash = self.expected_hash()
        elif self.receipt_hash != self.expected_hash():
            raise ValueError("DesktopWorkspaceL6Receipt hash mismatch.")
        return self

    def expected_hash(self) -> str:
        return _hash_payload(
            {
                "mission_id": self.mission_id,
                "action": self.action,
                "relative_path": self.relative_path,
                "resolved_path": self.resolved_path,
                "output_summary": self.output_summary,
                "authority_refs": self.authority_refs,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
                "workspace_root": self.workspace_root,
                "path_containment_proof_ref": self.path_containment_proof_ref,
                "path_containment_proof_hash": self.path_containment_proof_hash,
                "rollback_ref": self.rollback_ref,
                "source_binding_refs": self.source_binding_refs,
                "cost_trace": self.cost_trace.model_dump() if self.cost_trace else None,
                "real_workspace_execution": self.real_workspace_execution,
            }
        )


class DesktopWorkspaceL6Result(SentinelModel):
    relative_path: str
    resolved_path: str
    receipt: DesktopWorkspaceL6Receipt
    raw_content: str | None = None
    entries: list[str] = Field(default_factory=list)
    content_hash: str | None = None


class WorkspaceFailureReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("wsfail"))
    mission_id: str
    operation: str
    relative_path: str
    reason: str
    evidence_refs: list[str]
    authority_expansion: bool = False


class WorkspaceOperationAdapter:
    def __init__(
        self,
        *,
        authority: DesktopWorkspaceAuthority,
        budget: WorkspaceOperationBudget,
        kill_switch: DesktopWorkspaceKillSwitch | None = None,
    ) -> None:
        self.authority = authority
        self.budget = budget
        self.kill_switch = kill_switch
        self._operation_count = 0
        self._bytes_read = 0
        self._bytes_written = 0
        self.root = Path(authority.workspace_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def list_dir(self, relative_path: str = ".") -> DesktopWorkspaceL6Result:
        path = self._prepare("list_dir", relative_path, mutation=False)
        entries = sorted(item.name for item in path.iterdir())
        receipt = self._receipt(
            action="desktop_workspace_list_dir_l6",
            relative_path=relative_path,
            path=path,
            output_summary={"entry_count": len(entries), "entries": entries[:50]},
        )
        return DesktopWorkspaceL6Result(relative_path=relative_path, resolved_path=str(path), entries=entries, receipt=receipt)

    def read_file(self, relative_path: str) -> DesktopWorkspaceL6Result:
        path = self._prepare("read_file", relative_path, mutation=False)
        content = path.read_text(encoding="utf-8")
        byte_count = len(content.encode("utf-8"))
        if byte_count > self.budget.max_read_bytes:
            raise ValueError("read byte budget exceeded")
        self._bytes_read += byte_count
        content_hash = _hash_text(content)
        receipt = self._receipt(
            action="desktop_workspace_read_file_l6",
            relative_path=relative_path,
            path=path,
            output_summary={"bytes": byte_count, "content_hash": content_hash, "content_preview": sanitize_context_payload(content[:120])},
        )
        return DesktopWorkspaceL6Result(
            relative_path=relative_path,
            resolved_path=str(path),
            raw_content=content,
            content_hash=content_hash,
            receipt=receipt,
        )

    def write_file(self, relative_path: str, content: str) -> DesktopWorkspaceL6Result:
        path = self._prepare("write_file", relative_path, mutation=True)
        byte_count = len(content.encode("utf-8"))
        if byte_count > self.budget.max_write_bytes:
            raise ValueError("write byte budget exceeded")
        previous_exists = path.exists()
        previous_content_hash = _hash_text(path.read_text(encoding="utf-8")) if previous_exists and path.is_file() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._bytes_written += byte_count
        rollback = self._rollback_ref(
            action="write_file",
            relative_path=relative_path,
            previous_exists=previous_exists,
            previous_content_hash=previous_content_hash,
        )
        receipt = self._receipt(
            action="desktop_workspace_write_file_l6",
            relative_path=relative_path,
            path=path,
            output_summary={"bytes": byte_count, "content_hash": _hash_text(content)},
            rollback_ref=rollback.id,
        )
        return DesktopWorkspaceL6Result(relative_path=relative_path, resolved_path=str(path), content_hash=_hash_text(content), receipt=receipt)

    def create_folder(self, relative_path: str) -> DesktopWorkspaceL6Result:
        path = self._prepare("create_folder", relative_path, mutation=True)
        previous_exists = path.exists()
        path.mkdir(parents=True, exist_ok=True)
        rollback = self._rollback_ref(
            action="create_folder",
            relative_path=relative_path,
            previous_exists=previous_exists,
            previous_content_hash=None,
        )
        receipt = self._receipt(
            action="desktop_workspace_create_folder_l6",
            relative_path=relative_path,
            path=path,
            output_summary={"created": not previous_exists},
            rollback_ref=rollback.id,
        )
        return DesktopWorkspaceL6Result(relative_path=relative_path, resolved_path=str(path), receipt=receipt)

    def _prepare(self, operation: str, relative_path: str, *, mutation: bool) -> Path:
        if not self.authority.allows(operation):
            raise ValueError(f"operation not allowed:{operation}")
        if mutation and self.kill_switch is not None and self.kill_switch.triggered:
            raise ValueError(f"workspace mutation blocked by kill switch:{self.kill_switch.reason}")
        if self._operation_count >= self.budget.max_operations:
            raise ValueError("operation budget exceeded")
        self._operation_count += 1
        return self._resolve(relative_path)

    def _resolve(self, relative_path: str) -> Path:
        requested = Path(relative_path)
        candidate = requested.resolve() if requested.is_absolute() else (self.root / requested).resolve()
        if not _is_within_root(candidate, self.root):
            raise ValueError("workspace escape blocked")
        return candidate

    def _path_proof(self, *, relative_path: str, path: Path) -> PathContainmentProofRef:
        return PathContainmentProofRef(
            workspace_root=str(self.root),
            resolved_path=str(path),
            relative_path=relative_path,
        )

    def _rollback_ref(
        self,
        *,
        action: str,
        relative_path: str,
        previous_exists: bool,
        previous_content_hash: str | None,
    ) -> WorkspaceRollbackRef:
        instruction = "restore_previous_content" if previous_exists else "delete_created_path"
        return WorkspaceRollbackRef(
            action=action,
            relative_path=relative_path,
            previous_exists=previous_exists,
            previous_content_hash=previous_content_hash,
            rollback_instruction=instruction,
            evidence_refs=self.authority.evidence_refs,
        )

    def _receipt(
        self,
        *,
        action: str,
        relative_path: str,
        path: Path,
        output_summary: dict[str, Any],
        rollback_ref: str | None = None,
    ) -> DesktopWorkspaceL6Receipt:
        proof = self._path_proof(relative_path=relative_path, path=path)
        return DesktopWorkspaceL6Receipt(
            mission_id=self.authority.mission_id,
            action=action,
            relative_path=relative_path,
            resolved_path=str(path),
            output_summary=sanitize_context_payload(output_summary),
            authority_refs=[self.authority.root_authority_id, self.authority.policy_hash],
            evidence_refs=self.authority.evidence_refs,
            trace_refs=[f"desktop_workspace_l6:{action}"],
            workspace_root=str(self.root),
            path_containment_proof_ref=proof.id,
            path_containment_proof_hash=proof.proof_hash,
            rollback_ref=rollback_ref,
            source_binding_refs=self.authority.source_binding_refs,
            cost_trace=WorkspaceCostTrace(
                operation_count=self._operation_count,
                bytes_read=self._bytes_read,
                bytes_written=self._bytes_written,
                timeout_seconds=self.budget.timeout_seconds,
            ),
        )


class WorkspaceDiffSummary(SentinelModel):
    action: str
    relative_path: str
    bytes_changed: int = Field(ge=0)
    content_hash: str | None = None
    rollback_ref: str | None = None


class WorkspaceContextCard(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("wscard"))
    mission_id: str
    changed_paths: list[str]
    diff_summaries: list[WorkspaceDiffSummary]
    receipt_refs: list[str]
    rollback_refs: list[str]
    path_containment_proof_refs: list[str]
    raw_file_contents_included: bool = False
    raw_workspace_tree_included: bool = False
    authority_expansion: bool = False

    @classmethod
    def from_receipts(
        cls,
        *,
        mission_id: str,
        receipts: list[DesktopWorkspaceL6Receipt],
        max_changed_paths: int = 20,
    ) -> WorkspaceContextCard:
        sorted_receipts = sorted(receipts, key=lambda receipt: receipt.id)
        changed_paths = sorted({receipt.relative_path for receipt in receipts})[:max_changed_paths]
        summaries = [
            WorkspaceDiffSummary(
                action=receipt.action,
                relative_path=receipt.relative_path,
                bytes_changed=int(receipt.output_summary.get("bytes", 0)),
                content_hash=receipt.output_summary.get("content_hash"),
                rollback_ref=receipt.rollback_ref,
            )
            for receipt in sorted_receipts
        ]
        return cls(
            mission_id=mission_id,
            changed_paths=changed_paths,
            diff_summaries=summaries,
            receipt_refs=[receipt.id for receipt in sorted_receipts],
            rollback_refs=sorted({receipt.rollback_ref for receipt in receipts if receipt.rollback_ref}),
            path_containment_proof_refs=sorted({receipt.path_containment_proof_ref for receipt in receipts}),
            raw_file_contents_included=False,
            raw_workspace_tree_included=False,
            authority_expansion=False,
        )


class DesktopDecisionFrameSlice(SentinelModel):
    mission_id: str
    authority_card: dict[str, Any]
    workspace_context_card: WorkspaceContextCard
    selected_tool_surface: list[str]
    current_blockers: list[str] = Field(default_factory=list)
    next_decision_options: list[str]
    receipt_refs: list[str]
    raw_file_contents_included: bool = False
    raw_workspace_tree_included: bool = False
    authority_expansion: bool = False

    @classmethod
    def from_context_card(
        cls,
        *,
        authority: DesktopWorkspaceAuthority,
        context_card: WorkspaceContextCard,
        blockers: list[str] | None = None,
    ) -> DesktopDecisionFrameSlice:
        tools = sorted(set(authority.allowed_operations))
        if {"write_file", "create_folder"} & set(tools):
            tools.append("rollback_workspace_change")
        tools = sorted(set(tools))
        return cls(
            mission_id=authority.mission_id,
            authority_card={
                "root_authority_id": authority.root_authority_id,
                "workspace_root": authority.workspace_root,
                "allowed_operations": sorted(authority.allowed_operations),
                "policy_hash": authority.policy_hash,
                "authority_expansion": False,
            },
            workspace_context_card=context_card,
            selected_tool_surface=tools,
            current_blockers=blockers or [],
            next_decision_options=[
                "continue_workspace_edit",
                "rollback_workspace_change",
                "request_authority_extension",
                "stop_for_review",
            ],
            receipt_refs=context_card.receipt_refs,
            raw_file_contents_included=False,
            raw_workspace_tree_included=False,
            authority_expansion=False,
        )


class WorkspaceActionKernel(SentinelModel):
    allowed_operations: list[str]
    source_binding_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> WorkspaceActionKernel:
        missing = sorted(REQUIRED_DESKTOP_L6_BINDING_REFS - set(self.source_binding_refs))
        if missing:
            raise ValueError(f"WorkspaceActionKernel missing source binding refs:{missing}")
        if set(self.allowed_operations) - WORKSPACE_L6_OPERATIONS:
            raise ValueError("WorkspaceActionKernel contains unsupported operation.")
        return self


class WorkspaceCapabilityScanner(SentinelModel):
    allowed_surfaces: list[str] = Field(default_factory=lambda: sorted(WORKSPACE_L6_OPERATIONS))
    blocked_surfaces: list[str] = Field(default_factory=lambda: sorted(HOST_CONTROL_SURFACES))


class DesktopWorkspaceFinalGateDecision(SentinelModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)


class DesktopWorkspaceL6FinalGate:
    def verify(self, receipt: DesktopWorkspaceL6Receipt) -> DesktopWorkspaceFinalGateDecision:
        failures: list[str] = []
        if receipt.authority_expansion:
            failures.append("authority expansion detected")
        if not receipt.path_containment_proof_ref:
            failures.append("path containment proof missing")
        expected_proof_hash = _path_containment_proof_hash(
            workspace_root=receipt.workspace_root,
            resolved_path=receipt.resolved_path,
            relative_path=receipt.relative_path,
        )
        if receipt.path_containment_proof_hash != expected_proof_hash:
            failures.append("path containment proof hash mismatch")
        if not _is_within_root(Path(receipt.resolved_path).resolve(), Path(receipt.workspace_root).resolve()):
            failures.append("path containment proof outside workspace root")
        if receipt.action in {"desktop_workspace_write_file_l6", "desktop_workspace_create_folder_l6"} and not receipt.rollback_ref:
            failures.append("rollback ref missing")
        if receipt.live_host_control_enabled:
            failures.append("live host control detected")
        if receipt.shell_process_execution_started:
            failures.append("shell/process execution detected")
        if receipt.screenshot_clipboard_live:
            failures.append("screenshot/clipboard live surface detected")
        if receipt.external_mutation:
            failures.append("external mutation detected")
        if not receipt.receipt_hash or receipt.receipt_hash != receipt.expected_hash():
            failures.append("receipt hash mismatch")
        return DesktopWorkspaceFinalGateDecision(passed=not failures, failures=failures)


class WorkspaceReceiptAdapter(SentinelModel):
    adapter_name: str = "desktop_workspace_l6_receipt_adapter"
    required_receipt_fields: list[str] = Field(
        default_factory=lambda: [
            "mission_id",
            "action",
            "relative_path",
            "resolved_path",
            "workspace_root",
            "path_containment_proof_ref",
            "path_containment_proof_hash",
            "rollback_ref",
            "receipt_hash",
        ]
    )
