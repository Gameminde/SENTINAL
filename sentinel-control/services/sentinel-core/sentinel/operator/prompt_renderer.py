from __future__ import annotations

import json

from sentinel.operator.llm_frame import OperatorConversationFrame


class OperatorPromptRenderer:
    """Renders an in-memory-only prompt for the explicit user-selected LLM."""

    def render(self, frame: OperatorConversationFrame) -> str:
        payload = _focused_prompt_payload(frame)
        skeleton = {
            "protocol_version": "cockpit_mission_understanding_v2",
            "kind": "draft_mission",
            "reply": "Mission draft ready for approval.",
            "title": "Repository architecture research",
            "objective": "Map packages, command registration, execution flow, and architecture risks.",
            "requested_capability": "read_only_research",
            "constraints": ["read-only"],
            "expected_artifacts": ["evidence-linked technical report"],
            "clarification_questions": [],
        }
        return "\n".join(
            [
                "You are Sentinel's LLM live operator brain.",
                "Return exactly one JSON object.",
                "Allowed top-level keys are exactly:",
                "protocol_version, kind, reply, title, objective, requested_capability, constraints, expected_artifacts, clarification_questions.",
                "Use this minimal JSON skeleton for a read-only research mission:",
                json.dumps(skeleton, sort_keys=True),
                "Rules:",
                "No Markdown.",
                "No prose outside JSON.",
                "No reasoning.",
                "No authority.",
                "No workspace.",
                "No credentials.",
                "LLM output is advisory mission-understanding data only.",
                "Sentinel owns IDs, authority, workspace binding, model contract binding, budgets, execution requests, and tool grants.",
                "Current safe operator frame:",
                json.dumps(payload, sort_keys=True, default=str),
            ]
        )


def _focused_prompt_payload(frame: OperatorConversationFrame) -> dict[str, object]:
    payload = frame.prompt_payload()
    return {
        "session_id": payload["session_id"],
        "user_message_hash": payload["user_message_hash"],
        "safe_user_message": payload["safe_user_message"],
        "current_draft_summary": payload["current_draft_summary"],
        "persistent_memory_context_hash": payload["persistent_memory_context_hash"],
        "persistent_memory_context": payload.get("persistent_memory_context"),
        "structured_output_schema": {
            "protocol_version": "cockpit_mission_understanding_v2",
            "allowed_top_level_keys": [
                "protocol_version",
                "kind",
                "reply",
                "title",
                "objective",
                "requested_capability",
                "constraints",
                "expected_artifacts",
                "clarification_questions",
            ],
            "allowed_kind_values": ["draft_mission", "ask_clarification", "greeting", "unknown"],
            "required_fields": ["protocol_version", "kind", "reply"],
            "draft_mission_required_fields": ["title", "objective", "requested_capability"],
            "allowed_requested_capabilities": ["read_only_research"],
            "field_limits": payload["structured_output_schema"].get("field_limits", {}),
        },
        "llm_is_authority": payload["llm_is_authority"],
        "llm_can_execute": payload["llm_can_execute"],
        "data_not_authority": payload["data_not_authority"],
        "authority_effect": payload["authority_effect"],
        "can_grant_authority": payload["can_grant_authority"],
        "can_execute": payload["can_execute"],
    }
