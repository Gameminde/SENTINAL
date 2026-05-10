from __future__ import annotations

from sentinel.agent.context_engine import ContextNeed


class ToolSurfaceRouter:
    """Minimizes the tool surface shown to the LLM for the next decision."""

    def select_tools(
        self,
        *,
        candidate_tools: list[str],
        need: ContextNeed,
        allowed_tools: list[str],
        forbidden_tools: list[str],
    ) -> list[str]:
        allowed = set(allowed_tools)
        forbidden = set(forbidden_tools)
        selected: list[str] = []
        for tool in candidate_tools:
            if tool in forbidden or tool not in allowed:
                continue
            if self._relevant(tool, need):
                selected.append(tool)
        return sorted(set(selected))

    @staticmethod
    def _relevant(tool: str, need: ContextNeed) -> bool:
        tool_tokens = {part for part in tool.lower().replace("-", "_").split("_") if part}
        if tool_tokens & set(need.keywords):
            return True
        if any(token in need.objective.lower() for token in tool_tokens):
            return True
        return False
