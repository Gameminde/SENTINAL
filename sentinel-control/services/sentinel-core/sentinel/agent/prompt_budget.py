from __future__ import annotations

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.token_ledger import estimate_tokens


class PromptBudgetAllocator:
    def __init__(self, user_model: UserModelContract) -> None:
        self.user_model = user_model

    @property
    def max_decision_frame_tokens(self) -> int:
        return self.user_model.context_budget_policy.max_decision_frame_tokens

    def estimate_frame_tokens(self, rendered_prompt: str) -> int:
        actual = estimate_tokens(rendered_prompt)
        floor = min(1_000, self.max_decision_frame_tokens)
        return max(floor, actual)

    def within_budget(self, tokens: int) -> bool:
        return tokens <= self.max_decision_frame_tokens
