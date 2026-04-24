from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.firewall import assert_allowed, review_action
from sentinel.execution.email_draft_executor import EmailDraftExecutor
from sentinel.execution.file_executor import FileExecutor
from sentinel.shared.enums import ApprovalStatus
from sentinel.shared.models import AgentAction, EvidenceItem, FirewallReview


class ActionRunner:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.file_executor = FileExecutor(self.project_root)
        self.email_draft_executor = EmailDraftExecutor()

    def run(
        self,
        action: AgentAction,
        evidence: list[EvidenceItem] | None = None,
        approval_status: ApprovalStatus | None = None,
    ) -> tuple[FirewallReview, dict[str, Any]]:
        review = review_action(
            action,
            evidence=evidence,
            approval_status=approval_status,
            project_root=self.project_root,
        )
        assert_allowed(review)

        if action.tool == "create_folder":
            return review, self.file_executor.create_folder(action)
        if action.tool == "create_file":
            return review, self.file_executor.create_file(action)
        if action.tool == "prepare_email_draft":
            return review, self.email_draft_executor.prepare_email_draft(action)

        raise ValueError(f"No safe executor registered for {action.tool}.")

