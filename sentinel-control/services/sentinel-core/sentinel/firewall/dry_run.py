from __future__ import annotations

from sentinel.shared.models import AgentAction, DryRunPreview, EvidenceItem


def _content_preview(value: str, limit: int = 500) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def build_dry_run(action: AgentAction, evidence: list[EvidenceItem] | None = None) -> DryRunPreview:
    evidence_ids = action.evidence_refs or [item.id for item in evidence or []]
    preview: dict[str, object]

    if action.tool == "prepare_email_draft":
        preview = {
            "to": action.input.get("to") or "not executed in v1 unless user provides contact",
            "subject": action.input.get("subject") or "Draft subject not provided",
            "body": action.input.get("body") or "",
        }
    elif action.tool in {"create_file", "create_folder"}:
        preview = {
            "path": action.input.get("path") or action.input.get("file_path") or action.input.get("folder_path"),
        }
        if "content" in action.input:
            preview["content_preview"] = _content_preview(str(action.input.get("content") or ""))
    else:
        preview = {
            "input": action.input,
            "execution": "not executed by dry-run",
        }

    return DryRunPreview(
        action=action.tool,
        risk=action.risk_level,
        why_needed=action.intent,
        evidence_used=evidence_ids,
        preview=preview,
        requires_approval=action.requires_approval,
    )

