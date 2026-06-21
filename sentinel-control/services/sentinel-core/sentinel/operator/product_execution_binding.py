from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


class ProductExecutionBindingError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ProductExecutionBinding(SentinelModel):
    workspace_ref: str
    model_contract_ref: str
    capability_id: str
    operation: str
    binding_hash: str = ""
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _binding_is_not_authority(self) -> "ProductExecutionBinding":
        assert_data_not_authority(
            context="product_execution_binding",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_payload_for_hash(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload.pop("binding_hash", None)
        return payload

    def with_hash(self) -> "ProductExecutionBinding":
        return self.model_copy(update={"binding_hash": stable_hash(self.safe_payload_for_hash())})


def build_model_contract_ref(contract: UserModelContract | None) -> str:
    if contract is None:
        return "model_contract:deterministic_test:no_explicit_user_model_contract"
    contract_hash = stable_hash(contract.model_dump(mode="json"))
    return (
        "model_contract:"
        f"{contract.selected_provider_id}:"
        f"{contract.selected_backend_id}:"
        f"{contract.selected_model}:"
        f"{contract_hash}"
    )


def build_product_execution_binding(
    *,
    workspace: Path | str,
    run_root: Path | str,
    approval_scope: MissionAuthorityApprovalScope,
    user_model_contract: UserModelContract | None,
    capability_id: str,
    operation: str,
) -> ProductExecutionBinding:
    workspace_path = Path(workspace)
    if any(part == ".." for part in workspace_path.parts):
        raise ProductExecutionBindingError("workspace_path_traversal_ambiguous")
    try:
        canonical_workspace = workspace_path.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise ProductExecutionBindingError("workspace_not_found") from exc
    if not canonical_workspace.is_dir():
        raise ProductExecutionBindingError("workspace_not_directory")
    if _looks_like_sensitive_root(canonical_workspace):
        raise ProductExecutionBindingError("workspace_sensitive_path_blocked")

    canonical_run_root = Path(run_root).expanduser().resolve(strict=False)
    if _path_is_within(canonical_workspace, canonical_run_root):
        raise ProductExecutionBindingError("workspace_inside_run_root")
    if not _workspace_inside_approved_scope(canonical_workspace, approval_scope.allowed_paths):
        raise ProductExecutionBindingError("workspace_outside_approved_scope")

    return ProductExecutionBinding(
        workspace_ref=f"workspace:{canonical_workspace}",
        model_contract_ref=build_model_contract_ref(user_model_contract),
        capability_id=capability_id,
        operation=operation,
    ).with_hash()


def _workspace_inside_approved_scope(workspace: Path, allowed_paths: list[str]) -> bool:
    if not allowed_paths:
        return False
    for allowed in allowed_paths:
        if allowed == ".":
            return True
        allowed_path = Path(allowed).expanduser()
        if not allowed_path.is_absolute():
            continue
        if _path_is_within(workspace, allowed_path.resolve(strict=False)):
            return True
    return False


def _path_is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _looks_like_sensitive_root(path: Path) -> bool:
    sensitive_parts = {
        ".aws",
        ".azure",
        ".codex",
        ".gnupg",
        ".password-store",
        ".sentinel-runs",
        ".ssh",
        "credential",
        "credentials",
        "secret",
        "secrets",
    }
    return any(part.lower() in sensitive_parts for part in path.parts)


__all__ = [
    "ProductExecutionBinding",
    "ProductExecutionBindingError",
    "build_model_contract_ref",
    "build_product_execution_binding",
]
