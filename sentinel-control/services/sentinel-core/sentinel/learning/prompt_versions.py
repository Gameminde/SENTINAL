from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from sentinel.shared.models import new_id


class PromptVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("prompt"))
    name: str
    version: str
    purpose: str
    content: str
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PromptVersionRegistry:
    def __init__(self) -> None:
        self._versions: list[PromptVersion] = []

    def register(self, prompt: PromptVersion) -> PromptVersion:
        if prompt.active:
            self._versions = [
                existing.model_copy(update={"active": False})
                if existing.name == prompt.name else existing
                for existing in self._versions
            ]
        self._versions.append(prompt)
        return prompt

    def active(self, name: str) -> PromptVersion | None:
        for prompt in reversed(self._versions):
            if prompt.name == name and prompt.active:
                return prompt
        return None

    def list(self) -> list[PromptVersion]:
        return list(self._versions)
