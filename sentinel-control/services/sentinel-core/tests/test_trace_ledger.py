from sentinel.learning import TraceLedger
from sentinel.shared.db import InMemoryTraceRepository
from sentinel.shared.enums import EvidenceType, RiskLevel, TraceEventType, Verdict
from sentinel.shared.models import AgentAction, DecisionPlan, EvidenceItem


def test_trace_ledger_records_run_decision_actions_and_assets():
    repository = InMemoryTraceRepository()
    ledger = TraceLedger(repository)
    user_id = "user_123"

    run = ledger.create_run(user_id=user_id, input_idea="AI invoice follow-up for freelancers")
    evidence = EvidenceItem(
        source="reddit",
        url="https://example.com/post",
        quote="I hate chasing unpaid invoices.",
        summary="Freelancers report repeated invoice chasing pain.",
        confidence=0.9,
        freshness_score=0.8,
        relevance_score=0.95,
        evidence_type=EvidenceType.PAIN,
    )
    ledger.record_evidence(user_id=user_id, run_id=run.id, evidence=evidence)

    action = AgentAction(
        tool="prepare_email_draft",
        intent="Validate interest from target ICP",
        input={"subject": "Invoice follow-ups", "body": "Short draft"},
        expected_output="Email draft",
        risk_level=RiskLevel.MEDIUM,
        requires_approval=True,
        evidence_refs=[evidence.id],
    )
    plan = DecisionPlan(
        goal="Decide GTM path",
        evidence=[evidence],
        reasoning_summary="Pain exists, but more WTP proof is needed.",
        proposed_actions=[action],
        confidence=0.72,
        risk_score=45,
        verdict=Verdict.RESEARCH_MORE,
    )
    ledger.record_decision_plan(user_id=user_id, run_id=run.id, plan=plan)
    ledger.record_action_proposal(
        user_id=user_id,
        run_id=run.id,
        action=action,
        dry_run_json={"action": "prepare_email_draft", "evidence_used": [evidence.id]},
    )
    ledger.record_generated_asset(
        user_id=user_id,
        run_id=run.id,
        asset_type="verdict",
        title="00_VERDICT.md",
        content="Research more before building.",
        file_path="data/generated_projects/demo/00_VERDICT.md",
        evidence_refs=[evidence.id],
    )

    assert len(repository.list("agent_runs")) == 1
    assert len(repository.list("evidence_items")) == 1
    assert len(repository.list("decision_plans")) == 1
    assert len(repository.list("agent_actions")) == 1
    assert len(repository.list("generated_assets")) == 1

    traces = repository.list("trace_records")
    assert [row["event_type"] for row in traces] == [
        TraceEventType.RUN_STARTED.value,
        TraceEventType.EVIDENCE_RECORDED.value,
        TraceEventType.DECISION_CREATED.value,
        TraceEventType.ACTION_PROPOSED.value,
        TraceEventType.ASSET_GENERATED.value,
    ]
    assert repository.list("agent_actions")[0]["evidence_refs"] == [evidence.id]
    assert repository.list("generated_assets")[0]["evidence_refs"] == [evidence.id]

