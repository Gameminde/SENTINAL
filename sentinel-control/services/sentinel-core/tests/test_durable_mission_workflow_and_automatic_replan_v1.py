from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft
from sentinel.operator.replan_guard import ReplanExecutionGuard
from sentinel.operator.workflow_models import (
    DurableWorkflowRecord,
    ReplanCandidate,
    ReplanDecisionKind,
    ReplanExecutionTarget,
    ReplanExecutionPolicy,
    WorkflowAuthoritySnapshot,
    WorkflowStepState,
)
from sentinel.operator.workflow_store import DurableWorkflowStore
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
    PowerStepStatus,
)


def _envelope(**updates) -> MissionAuthorityEnvelope:
    base = {
        "id": "mission_workflow",
        "user_id": "user_workflow",
        "mission_title": "Launch research workflow",
        "mission_objective": "Research the approved market and prepare a report.",
        "allowed_systems": ["browser", "workspace"],
        "allowed_tools": ["browser_readonly", "reversible_workspace"],
        "allowed_actions": ["observe", "write"],
        "forbidden_actions": ["payment", "send_email"],
        "allowed_paths": ["data/generated_projects"],
        "allowed_domains": ["example.com"],
        "max_actions": 8,
        "max_cost_usd": 5.0,
        "max_recipients": 0,
        "risk_appetite_score": 35.0,
    }
    base.update(updates)
    return MissionAuthorityEnvelope(**base)


def _plan(
    *,
    mission_id: str = "mission_workflow",
    url: str = "https://example.com/research",
    action_kind: str = "observe",
) -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="observe",
                    actuator_family=PowerActuatorFamily.BROWSER,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="browser_readonly",
                    action_kind=action_kind,
                    request={"url": url},
                )
            ]
        ),
    )


def _snapshot(envelope: MissionAuthorityEnvelope | None = None) -> WorkflowAuthoritySnapshot:
    return WorkflowAuthoritySnapshot.from_runtime(
        envelope=envelope or _envelope(),
        plan=_plan(),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
    )


def _candidate(**updates) -> ReplanCandidate:
    base = {
        "workflow_id": "workflow_1",
        "mission_id": "mission_workflow",
        "source_checkpoint_id": "checkpoint_1",
        "mission_objective": _envelope().mission_objective,
        "power_plan": _plan().model_copy(
            update={
                "graph": PowerMissionGraph(
                    steps=[
                        _plan().graph.steps[0].model_copy(
                            update={"request": {"url": "https://example.com/research", "selector": "#alternate"}}
                        )
                    ]
                )
            }
        ),
        "executor_contract_id": "executor:governed:v1",
        "provider_id": "ollama",
        "backend_id": "ollama_openai_compatible",
        "model_id": "qwen3",
        "reason": "alternate authorized browser target after transient failure",
    }
    base.update(updates)
    return ReplanCandidate(**base)


def _evaluate(
    *,
    snapshot: WorkflowAuthoritySnapshot | None = None,
    envelope: MissionAuthorityEnvelope | None = None,
    candidate: ReplanCandidate | None = None,
    completed_action_count: int = 1,
    cost_used_usd: float = 0.25,
    latest_checkpoint_id: str = "checkpoint_1",
):
    current_envelope = envelope or _envelope()
    return ReplanExecutionGuard().evaluate(
        snapshot=snapshot or _snapshot(current_envelope),
        current_envelope=current_envelope,
        candidate=candidate or _candidate(),
        completed_action_count=completed_action_count,
        cost_used_usd=cost_used_usd,
        latest_checkpoint_id=latest_checkpoint_id,
    )


def test_replan_product_default_is_automatic_inside_authority() -> None:
    policy = ReplanExecutionPolicy()

    assert policy.require_confirmation_for_every_replan is False
    assert policy.automatic_inside_authority is True


def test_replan_guard_allows_equivalent_branch_inside_authority() -> None:
    envelope = _envelope()
    decision = _evaluate(snapshot=_snapshot(envelope), envelope=envelope)

    assert decision.kind is ReplanDecisionKind.AUTO_EXECUTE
    assert decision.guard_failures == []
    assert decision.can_execute is False
    assert decision.authority_effect == "none"


@pytest.mark.parametrize(
    ("candidate_updates", "envelope_updates", "expected_reason"),
    [
        ({"power_plan": _plan(url="https://new.example.net/research")}, {}, "target_scope_expansion"),
        ({"power_plan": _plan(action_kind="extract")}, {}, "action_class_expansion"),
        ({"provider_id": "openai"}, {}, "provider_contract_changed"),
        ({"executor_contract_id": "executor:other"}, {}, "executor_contract_changed"),
        ({}, {"max_actions": 9}, "authority_envelope_changed"),
        ({}, {"revoked_at": _envelope().created_at}, "mission_revoked"),
    ],
)
def test_replan_guard_escalates_on_authority_or_scope_change(
    candidate_updates: dict,
    envelope_updates: dict,
    expected_reason: str,
) -> None:
    baseline = _envelope()
    current = baseline.model_copy(update=envelope_updates)
    decision = _evaluate(
        snapshot=_snapshot(baseline),
        envelope=current,
        candidate=_candidate(**candidate_updates),
    )

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert expected_reason in decision.guard_failures


def test_replan_guard_debug_confirmation_policy_is_not_product_default() -> None:
    envelope = _envelope()
    decision = ReplanExecutionGuard(
        ReplanExecutionPolicy(require_confirmation_for_every_replan=True)
    ).evaluate(
        snapshot=_snapshot(envelope),
        current_envelope=envelope,
        candidate=_candidate(),
        completed_action_count=0,
        cost_used_usd=0.0,
        latest_checkpoint_id="checkpoint_1",
    )

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "operator_confirmation_policy" in decision.guard_failures


def test_completed_workflow_step_requires_receipt_and_finalgate_proof() -> None:
    with pytest.raises(ValueError):
        WorkflowStepState(
            step_id="observe",
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[],
            finalgate_certificate_refs=[],
        )


def test_replan_candidate_cannot_launder_memory_receipt_or_finalgate_into_permission() -> None:
    for field in ("memory_is_authority", "receipt_approves_execution", "finalgate_allows_future_execution"):
        payload = _candidate().model_dump(mode="python")
        payload[field] = True
        with pytest.raises(ValueError):
            ReplanCandidate(**payload)


def test_workflow_store_reuses_mission_run_directory_and_detects_checkpoint_tamper(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    mission = kernel.create_mission(
        session_id="session_workflow",
        draft=MissionDraft(title="Workflow", objective=_envelope().mission_objective),
    )
    store = DurableWorkflowStore(kernel.store)
    envelope = _envelope(id=mission.mission_id)
    plan = _plan(mission_id=mission.mission_id)
    record = DurableWorkflowRecord.create(
        mission_id=mission.mission_id,
        snapshot=WorkflowAuthoritySnapshot.from_runtime(
            envelope=envelope,
            plan=plan,
            executor_contract_id="executor:governed:v1",
        ),
        initial_plan=plan,
    )

    saved = store.create(record=record, initial_plan=plan)
    checkpoint = store.create_checkpoint(saved.workflow_id, safe_reason="initial checkpoint")

    assert (tmp_path / mission.mission_id / "workflow" / "record.json").exists()
    assert store.load(saved.workflow_id).workflow_id == saved.workflow_id
    assert store.verify(saved.workflow_id) is True

    checkpoint_path = tmp_path / mission.mission_id / "workflow" / "checkpoints" / f"{checkpoint.checkpoint_id}.json"
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    payload["safe_reason"] = "tampered"
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    assert store.verify(saved.workflow_id) is False


def test_workflow_store_rejects_authority_snapshot_or_consumed_budget_rewrite(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    mission = kernel.create_mission(
        session_id="session_immutable_workflow",
        draft=MissionDraft(title="Workflow", objective=_envelope().mission_objective),
    )
    store = DurableWorkflowStore(kernel.store)
    envelope = _envelope(id=mission.mission_id)
    plan = _plan(mission_id=mission.mission_id)
    record = store.create(
        record=DurableWorkflowRecord.create(
            mission_id=mission.mission_id,
            snapshot=WorkflowAuthoritySnapshot.from_runtime(
                envelope=envelope,
                plan=plan,
                executor_contract_id="executor:governed:v1",
            ),
            initial_plan=plan,
        ),
        initial_plan=plan,
    )

    with pytest.raises(ValueError, match="authority snapshot immutable"):
        store.update_record(
            record.model_copy(
                update={
                    "snapshot": record.snapshot.model_copy(
                        update={"max_actions": record.snapshot.max_actions + 1}
                    )
                }
            ),
            expected_version=record.record_version,
        )

    with pytest.raises(ValueError, match="status only"):
        store.update_record(
            record.model_copy(update={"completed_action_count": 1, "cost_used_usd": 0.25}),
            expected_version=record.record_version,
        )


def test_replan_guard_binds_candidate_to_latest_verified_checkpoint() -> None:
    decision = _evaluate(latest_checkpoint_id="checkpoint_new")

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "stale_replan_checkpoint" in decision.guard_failures


def test_replan_guard_detects_full_authority_envelope_drift() -> None:
    baseline = _envelope()
    current = baseline.model_copy(update={"success_criteria": ["A different success condition"]})

    decision = _evaluate(snapshot=_snapshot(baseline), envelope=current)

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "authority_envelope_changed" in decision.guard_failures


def test_replan_guard_rejects_exact_step_contract_recombination() -> None:
    baseline = _envelope()
    original = PowerMissionPlan(
        mission_id=baseline.id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="observe",
                    actuator_family=PowerActuatorFamily.BROWSER,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="browser_readonly",
                    action_kind="observe",
                    request={"url": "https://example.com/research", "selector": "#primary"},
                ),
                PowerMissionStep(
                    step_id="write",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write",
                    request={"path": "data/generated_projects/report.md"},
                ),
            ]
        ),
    )
    recombined = original.model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[
                    original.graph.steps[0].model_copy(update={"organ_kind": "reversible_workspace"}),
                    original.graph.steps[1].model_copy(update={"organ_kind": "browser_readonly"}),
                ]
            )
        }
    )

    decision = _evaluate(
        snapshot=WorkflowAuthoritySnapshot.from_runtime(
            envelope=baseline,
            plan=original,
            executor_contract_id="executor:governed:v1",
            provider_id="ollama",
            backend_id="ollama_openai_compatible",
            model_id="qwen3",
        ),
        envelope=baseline,
        candidate=_candidate(power_plan=recombined),
    )

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "step_contract_expansion" in decision.guard_failures


def test_replan_guard_counts_retry_budget_as_worst_case_actions() -> None:
    candidate_plan = _plan().model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[_plan().graph.steps[0].model_copy(update={"retry_budget": 8})]
            )
        }
    )

    decision = _evaluate(candidate=_candidate(power_plan=candidate_plan), completed_action_count=0)

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "action_budget_expansion" in decision.guard_failures


def test_replan_guard_rejects_same_domain_new_endpoint_but_allows_selector_change() -> None:
    new_endpoint = _evaluate(
        candidate=_candidate(power_plan=_plan(url="https://example.com/new-endpoint"))
    )
    selector_change = _evaluate(
        candidate=_candidate(
            power_plan=_plan().model_copy(
                update={
                    "graph": PowerMissionGraph(
                        steps=[_plan().graph.steps[0].model_copy(update={"request": {"url": "https://example.com/research", "selector": "#alternate"}})]
                    )
                }
            )
        )
    )

    assert new_endpoint.kind is ReplanDecisionKind.ESCALATE
    assert "target_scope_expansion" in new_endpoint.guard_failures
    assert selector_change.kind is ReplanDecisionKind.AUTO_EXECUTE


def test_replan_guard_treats_case_distinct_paths_as_distinct_targets() -> None:
    envelope = _envelope()
    original = PowerMissionPlan(
        mission_id=envelope.id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="write",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write",
                    request={"path": "data/generated_projects/report.md"},
                )
            ]
        ),
    )
    changed = original.model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[original.graph.steps[0].model_copy(update={"request": {"path": "data/generated_projects/Report.md"}})]
            )
        }
    )

    decision = _evaluate(
        snapshot=WorkflowAuthoritySnapshot.from_runtime(
            envelope=envelope,
            plan=original,
            executor_contract_id="executor:governed:v1",
        ),
        envelope=envelope,
        candidate=_candidate(
            power_plan=changed,
            provider_id=None,
            backend_id=None,
            model_id=None,
        ),
    )

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "target_scope_expansion" in decision.guard_failures


def test_replan_guard_escalates_l6_and_credential_using_candidates() -> None:
    l6_plan = _plan().model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[
                    _plan().graph.steps[0].model_copy(
                        update={
                            "capability_level": PowerActuatorCapabilityLevel.L6,
                            "organ_kind": "browser_login_credential_session_broker_l6",
                            "action_kind": "browser_login",
                            "request": {
                                "url": "https://example.com/research",
                                "credential_ref_id": "credential_ref:approved",
                            },
                        }
                    )
                ]
            )
        }
    )
    l6_envelope = _envelope(
        allowed_actions=["browser_login"],
        allowed_tools=["browser_login_credential_session_broker_l6"],
    )
    snapshot = WorkflowAuthoritySnapshot.from_runtime(
        envelope=l6_envelope,
        plan=l6_plan,
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
    )

    decision = _evaluate(
        snapshot=snapshot,
        envelope=l6_envelope,
        candidate=_candidate(power_plan=l6_plan),
    )

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "special_authority_boundary" in decision.guard_failures
    assert "credential_scope_unproven" in decision.guard_failures


def test_agent_runtime_replan_requires_typed_action_plan_before_auto_execution() -> None:
    candidate = ReplanCandidate(
        workflow_id="workflow_1",
        mission_id="mission_workflow",
        source_checkpoint_id="checkpoint_1",
        mission_objective=_envelope().mission_objective,
        execution_target=ReplanExecutionTarget.AGENT_RUNTIME,
        agent_user_input={"mission_id": "mission_workflow", "continuation": "safe context"},
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="continue with opaque AgentRuntime input",
    )

    decision = _evaluate(candidate=candidate)

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "agent_runtime_replan_requires_typed_plan" in decision.guard_failures


def test_replan_guard_binds_full_model_contract_hash_when_present() -> None:
    envelope = _envelope()
    snapshot = WorkflowAuthoritySnapshot.from_runtime(
        envelope=envelope,
        plan=_plan(),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        model_contract_hash="model-contract:approved",
    )

    decision = _evaluate(
        snapshot=snapshot,
        envelope=envelope,
        candidate=_candidate(model_contract_hash="model-contract:changed"),
    )

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "provider_contract_changed" in decision.guard_failures


def test_replan_guard_escalates_positive_cost_without_typed_cost_proof() -> None:
    decision = _evaluate(candidate=_candidate(estimated_cost_usd=0.01))

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "unproven_cost_estimate" in decision.guard_failures


def test_replan_guard_escalates_compound_irreversible_action_name() -> None:
    envelope = _envelope(allowed_actions=["delete_file"], allowed_tools=["reversible_workspace"])
    delete_plan = PowerMissionPlan(
        mission_id=envelope.id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="delete",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="reversible_workspace",
                    action_kind="delete_file",
                    request={"path": "data/generated_projects/report.md"},
                )
            ]
        ),
    )
    snapshot = WorkflowAuthoritySnapshot.from_runtime(
        envelope=envelope,
        plan=delete_plan,
        executor_contract_id="executor:governed:v1",
    )

    decision = _evaluate(
        snapshot=snapshot,
        envelope=envelope,
        candidate=_candidate(
            power_plan=delete_plan,
            provider_id=None,
            backend_id=None,
            model_id=None,
        ),
    )

    assert decision.kind is ReplanDecisionKind.ESCALATE
    assert "irreversible_action_boundary" in decision.guard_failures


def test_workflow_rejects_secret_bearing_url_before_persistence(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    mission = kernel.create_mission(
        session_id="session_secret_plan",
        draft=MissionDraft(title="Workflow", objective=_envelope().mission_objective),
    )
    envelope = _envelope(id=mission.mission_id)
    secret_plan = PowerMissionPlan(
        mission_id=mission.mission_id,
        graph=PowerMissionGraph(
            steps=[
                _plan(mission_id=mission.mission_id).graph.steps[0].model_copy(
                    update={"request": {"url": "https://example.com/research?token=rawsecretvalue123"}}
                )
            ]
        ),
    )

    with pytest.raises(ValueError, match="workflow_plan_contains_forbidden_persisted_payload"):
        WorkflowAuthoritySnapshot.from_runtime(
            envelope=envelope,
            plan=secret_plan,
            executor_contract_id="executor:governed:v1",
        )

    persisted = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*") if path.is_file())
    assert "rawsecretvalue123" not in persisted


def test_replan_candidate_rejects_secret_like_persisted_reason() -> None:
    with pytest.raises(ValueError, match="replan candidate contains secret-like persisted metadata"):
        _candidate(reason="retry because Bearer abcdefghijklmnopqrstuvwxyz was rejected")
