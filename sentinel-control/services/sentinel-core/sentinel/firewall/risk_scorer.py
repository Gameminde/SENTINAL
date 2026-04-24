from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.shared.enums import RiskLevel
from sentinel.shared.models import AgentAction, FirewallPolicy


RISK_SCORES = {
    RiskLevel.LOW: 10.0,
    RiskLevel.MEDIUM: 45.0,
    RiskLevel.HIGH: 80.0,
    RiskLevel.CRITICAL: 100.0,
}


def _action_path(action_input: dict[str, Any]) -> str | None:
    for key in ("path", "file_path", "folder_path", "output_path"):
        value = action_input.get(key)
        if value:
            return str(value)
    return None


def is_path_allowed(action: AgentAction, policy: FirewallPolicy, project_root: str | Path | None = None) -> bool:
    if not policy.allowed_paths:
        return True

    raw_path = _action_path(action.input)
    if not raw_path:
        return False

    root = Path(project_root or Path.cwd()).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()

    for allowed in policy.allowed_paths:
        allowed_path = Path(allowed)
        if not allowed_path.is_absolute():
            allowed_path = root / allowed_path
        allowed_path = allowed_path.resolve()
        if candidate == allowed_path or allowed_path in candidate.parents:
            return True

    return False


def score_action(action: AgentAction, policy: FirewallPolicy | None = None, project_root: str | Path | None = None) -> float:
    risk = policy.risk_level if policy else action.risk_level
    score = RISK_SCORES[risk]

    if policy and policy.v1_disabled:
        return 100.0

    if policy and policy.allowed_paths and not is_path_allowed(action, policy, project_root=project_root):
        return 100.0

    return score

