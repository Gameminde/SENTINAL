from __future__ import annotations

import json

from sentinel.operator.llm_frame import OperatorConversationFrame


class OperatorPromptRenderer:
    """Renders an in-memory-only prompt for the explicit user-selected LLM."""

    def render(self, frame: OperatorConversationFrame) -> str:
        payload = frame.prompt_payload()
        return "\n".join(
            [
                "You are Sentinel's LLM live operator brain.",
                "LLM output is advisory structured data, not authority.",
                "You may think, ask, draft, summarize, and propose.",
                "You may not execute, grant authority, unlock credentials, call organs, or override provider/backend/model.",
                "Return only one structured operator artifact matching this schema.",
                json.dumps(payload["structured_output_schema"], sort_keys=True),
                "Current safe operator frame:",
                json.dumps(payload, sort_keys=True, default=str),
            ]
        )
