from __future__ import annotations

from typing import Any

from sentinel.shared.db import TraceRepository, to_row
from sentinel.shared.enums import TraceEventType
from sentinel.shared.models import AgentAction, AgentRun, DecisionPlan, EvidenceItem, GeneratedAsset, TraceRecord


class TraceLedger:
    def __init__(self, repository: TraceRepository) -> None:
        self.repository = repository

    def create_run(self, user_id: str, input_idea: str, metadata: dict[str, Any] | None = None) -> AgentRun:
        run = AgentRun(user_id=user_id, input_idea=input_idea, metadata=metadata or {})
        self.repository.insert("agent_runs", to_row(run))
        self.record_trace(
            user_id=user_id,
            run_id=run.id,
            event_type=TraceEventType.RUN_STARTED,
            input_snapshot={"input_idea": input_idea, "metadata": metadata or {}},
        )
        return run

    def record_trace(
        self,
        user_id: str,
        run_id: str,
        event_type: TraceEventType,
        input_snapshot: dict[str, Any] | None = None,
        decision_snapshot: dict[str, Any] | None = None,
        action_snapshot: dict[str, Any] | None = None,
        output_snapshot: dict[str, Any] | None = None,
    ) -> TraceRecord:
        record = TraceRecord(
            user_id=user_id,
            run_id=run_id,
            event_type=event_type,
            input_snapshot=input_snapshot or {},
            decision_snapshot=decision_snapshot,
            action_snapshot=action_snapshot,
            output_snapshot=output_snapshot,
        )
        self.repository.insert("trace_records", to_row(record))
        return record

    def record_evidence(self, user_id: str, run_id: str, evidence: EvidenceItem) -> EvidenceItem:
        row = to_row(evidence)
        row["run_id"] = run_id
        row["payload"] = to_row(evidence)
        self.repository.insert("evidence_items", row)
        self.record_trace(
            user_id=user_id,
            run_id=run_id,
            event_type=TraceEventType.EVIDENCE_RECORDED,
            input_snapshot={"evidence_id": evidence.id},
            output_snapshot={"evidence": row},
        )
        return evidence

    def record_decision_plan(self, user_id: str, run_id: str, plan: DecisionPlan) -> DecisionPlan:
        row = {
            "id": plan.id,
            "run_id": run_id,
            "goal": plan.goal,
            "verdict": plan.verdict.value,
            "reasoning_summary": plan.reasoning_summary,
            "confidence": plan.confidence,
            "risk_score": plan.risk_score,
            "raw_json": to_row(plan),
        }
        self.repository.insert("decision_plans", row)
        self.record_trace(
            user_id=user_id,
            run_id=run_id,
            event_type=TraceEventType.DECISION_CREATED,
            input_snapshot={"plan_id": plan.id},
            decision_snapshot=row,
        )
        return plan

    def record_action_proposal(self, user_id: str, run_id: str, action: AgentAction, dry_run_json: dict[str, Any] | None = None) -> AgentAction:
        row = {
            "id": action.id,
            "run_id": run_id,
            "action_type": action.tool,
            "tool": action.tool,
            "intent": action.intent,
            "input_json": action.input,
            "expected_output": action.expected_output,
            "risk_level": action.risk_level.value,
            "requires_approval": action.requires_approval,
            "approval_status": action.approval_status.value,
            "dry_run_json": dry_run_json or {},
            "evidence_refs": action.evidence_refs,
        }
        self.repository.insert("agent_actions", row)
        self.record_trace(
            user_id=user_id,
            run_id=run_id,
            event_type=TraceEventType.ACTION_PROPOSED,
            input_snapshot={"action_id": action.id},
            action_snapshot=row,
        )
        return action

    def record_generated_asset(
        self,
        user_id: str,
        run_id: str,
        asset_type: str,
        title: str,
        content: str,
        file_path: str | None = None,
        evidence_refs: list[str] | None = None,
    ) -> GeneratedAsset:
        asset = GeneratedAsset(
            run_id=run_id,
            asset_type=asset_type,
            title=title,
            content=content,
            file_path=file_path,
            evidence_refs=evidence_refs or [],
        )
        self.repository.insert("generated_assets", to_row(asset))
        self.record_trace(
            user_id=user_id,
            run_id=run_id,
            event_type=TraceEventType.ASSET_GENERATED,
            input_snapshot={"asset_id": asset.id, "evidence_refs": asset.evidence_refs},
            output_snapshot=to_row(asset),
        )
        return asset

