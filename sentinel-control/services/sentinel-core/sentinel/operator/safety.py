from __future__ import annotations

from typing import Any

from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    scan_forbidden_payload_categorized,
)


def reject_operator_control_payload(payload: Any, *, context: str) -> None:
    scan = scan_forbidden_payload_categorized(payload, path="$")
    blocked = scan[OrganSafetyScanCategory.ALL.value]
    if blocked:
        raise ValueError(f"{context}: unsafe operator payload")


def assert_data_not_authority(
    *,
    context: str,
    authority_effect: str,
    data_not_authority: bool,
    can_grant_authority: bool,
    can_execute: bool,
) -> None:
    if authority_effect != "none":
        raise ValueError(f"{context}: authority effect must remain none")
    if data_not_authority is not True:
        raise ValueError(f"{context}: must remain data-not-authority")
    if can_grant_authority:
        raise ValueError(f"{context}: cannot grant authority")
    if can_execute:
        raise ValueError(f"{context}: cannot execute")
