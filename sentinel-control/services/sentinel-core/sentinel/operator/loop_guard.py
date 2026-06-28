from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sentinel.operator.action_kernel import ActionEnvelope, ActionResult


class LoopGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoopGuardConfig:
    max_model_calls: int = 8
    max_material_actions: int = 8
    max_same_action_hash: int = 3
    max_repeated_target: int = 4
    max_no_progress_turns: int = 3
    deadline_seconds: int = 120


@dataclass
class LoopGuard:
    config: LoopGuardConfig = field(default_factory=LoopGuardConfig)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    action_hash_counts: dict[str, int] = field(default_factory=dict)
    target_counts: dict[str, int] = field(default_factory=dict)
    no_progress_turns: int = 0

    def check_before_model_call(self, model_calls_used: int) -> None:
        self._check_deadline()
        if model_calls_used >= self.config.max_model_calls:
            raise LoopGuardError("loop_guard_model_call_budget")

    def check_before_action(self, envelope: ActionEnvelope) -> None:
        self._check_deadline()
        action_hash = envelope.action_hash
        self.action_hash_counts[action_hash] = self.action_hash_counts.get(action_hash, 0) + 1
        if self.action_hash_counts[action_hash] > self.config.max_same_action_hash:
            raise LoopGuardError("loop_guard_repeated_action")
        target = f"{envelope.capability_id}:{envelope.operation}:{envelope.target_ref or ''}"
        self.target_counts[target] = self.target_counts.get(target, 0) + 1
        if self.target_counts[target] > self.config.max_repeated_target:
            raise LoopGuardError("loop_guard_repeated_target")

    def record_result(self, result: ActionResult) -> None:
        if result.receipt_refs or result.evidence_refs or result.status == "completed":
            self.no_progress_turns = 0
        else:
            self.no_progress_turns += 1
        if self.no_progress_turns > self.config.max_no_progress_turns:
            raise LoopGuardError("loop_guard_no_progress")

    def material_budget_reached(self, material_actions_used: int) -> bool:
        return material_actions_used >= self.config.max_material_actions

    def _check_deadline(self) -> None:
        if datetime.now(UTC) > self.started_at + timedelta(seconds=self.config.deadline_seconds):
            raise LoopGuardError("loop_guard_deadline")


__all__ = ["LoopGuard", "LoopGuardConfig", "LoopGuardError"]
