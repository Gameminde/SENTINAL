from __future__ import annotations

from sentinel.shared.models import AgentAction


class EmailDraftExecutor:
    def prepare_email_draft(self, action: AgentAction) -> dict[str, str]:
        return {
            "status": "draft_created",
            "sent": "false",
            "to": str(action.input.get("to") or ""),
            "subject": str(action.input.get("subject") or ""),
            "body": str(action.input.get("body") or ""),
        }

