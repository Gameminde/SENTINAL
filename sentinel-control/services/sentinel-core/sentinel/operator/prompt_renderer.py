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
                "You may ask, greet, or draft mission understanding only.",
                "You may not execute, grant authority, unlock credentials, call organs, or override provider/backend/model.",
                "Return exactly one JSON object matching this schema.",
                "Return exactly one JSON object.",
                'Use protocol_version exactly "cockpit_mission_understanding_v2".',
                "Do not emit legacy OperatorLLMDecisionResult, MissionStartProposal, OperatorIntent, "
                "MissionDraft, or MissionAuthoritySummary objects.",
                "Do not wrap in Markdown.",
                "Do not include explanations outside JSON.",
                "Do not include text before or after the JSON.",
                "Do not include a reasoning, thinking, chain_of_thought, tool_calls, raw_prompt, or raw_response field.",
                "Do not include mission IDs, authority summaries, approval scopes, executable action lists, budgets, paths, or credential grants.",
                "Do not include workspace, workspace_ref, path, allowed_paths, model_contract_ref, authority_scope, "
                "approval_scope, allowed_actions, budget, credentials, or can_execute.",
                "Use this minimal object shape for a read-only research mission:",
                json.dumps(
                    {
                        "protocol_version": "cockpit_mission_understanding_v2",
                        "kind": "draft_mission",
                        "reply": "Mission draft ready for approval.",
                        "title": "Repository architecture research",
                        "objective": "Map packages, command registration, execution flow, and architecture risks.",
                        "requested_capability": "read_only_research",
                        "constraints": ["read-only"],
                        "expected_artifacts": ["evidence-linked technical report"],
                        "clarification_questions": [],
                    },
                    sort_keys=True,
                ),
                json.dumps(payload["structured_output_schema"], sort_keys=True),
                "Current safe operator frame:",
                json.dumps(payload, sort_keys=True, default=str),
            ]
        )
