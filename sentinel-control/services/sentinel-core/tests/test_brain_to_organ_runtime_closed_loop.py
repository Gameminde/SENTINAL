from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agent import AgentEventType, AgentPhase, AgentRuntime
from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
    OrganRuntimeExecutionStatus,
)
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs.browser.models import BrowserFetchedPage
from sentinel.shared.enums import MissionMode, MissionStatus, MissionType


NOW = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)

SAFE_ACTIONS = [
    "create_project_folder",
    "create_markdown_file",
    "export_json",
    "generate_gtm_pack",
    "generate_landing_copy",
    "generate_outreach_drafts_without_sending",
    "create_watchlist",
    "generate_research_questions",
    "write_trace",
]


class FakeBrowserReadOnlyFetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, request: Any, final_url: str) -> BrowserFetchedPage:
        self.calls.append(final_url)
        return BrowserFetchedPage(
            final_url="https://example.com/research",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=(
                "<html><title>Research</title><body>"
                "Customers report slow onboarding. Pricing starts at $49 per month. "
                "A public case study reports 30 percent faster activation."
                "</body></html>"
            ),
        )


def _envelope(mission_id: str = "mission_closed_loop", **updates: Any) -> MissionAuthorityEnvelope:
    data = {
        "id": mission_id,
        "user_id": "user_closed_loop",
        "mission_type": MissionType.GTM,
        "mission_title": "Closed loop runtime test",
        "mission_objective": "Exercise Brain to Organ runtime dispatch under explicit opt-in.",
        "success_criteria": ["runtime remains default-off", "dispatch is receipted when enabled"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace", "public_web"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": SAFE_ACTIONS,
        "forbidden_actions": ["send_email", "run_shell_command", "browser_submit", "credential_access", "api_mutation"],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 0.0,
    }
    data.update(updates)
    return MissionAuthorityEnvelope(**data)


def _local_config(**updates: Any) -> OrganRuntimeExecutionConfig:
    data = {
        "enabled": True,
        "organ_dispatch_enabled": True,
        "temporary_candidate_bridge_enabled": True,
        "mode": OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY,
        "allowed_action_levels": [DelegatedActionLevel.L2, DelegatedActionLevel.L3],
        "allowed_organs": ["local_artifact", "reversible_workspace"],
        "allow_l2": True,
        "allow_l3": True,
    }
    data.update(updates)
    return OrganRuntimeExecutionConfig(**data)


def _browser_config(**updates: Any) -> OrganRuntimeExecutionConfig:
    data = {
        "enabled": True,
        "organ_dispatch_enabled": True,
        "temporary_candidate_bridge_enabled": True,
        "mode": OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY,
        "allowed_action_levels": [DelegatedActionLevel.L4],
        "allowed_organs": ["browser_readonly", "browser_preparation", "browser_semantic_extraction"],
        "allow_l2": False,
        "allow_l3": False,
        "allow_browser_readonly": True,
        "allow_browser_preparation": True,
        "allow_browser_semantic_extraction": True,
    }
    data.update(updates)
    return OrganRuntimeExecutionConfig(**data)


def _dispatch_payload(
    *,
    action_candidates: list[dict[str, Any]],
    authority: dict[str, Any],
    budget: dict[str, Any] | None = None,
    available_evidence_refs: list[str] | None = None,
    organ_contracts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    refs = available_evidence_refs or sorted({ref for c in action_candidates for ref in c.get("evidence_refs", [])})
    return {
        "idea": "Sentinel closed-loop dispatch fixture",
        "organ_dispatch": {
            "action_candidates": action_candidates,
            "authority": authority,
            "budget": budget
            or {
                "remaining_action_count": 8,
                "remaining_retries": 1,
                "remaining_tokens": 100_000,
                "organ_budget_units": {"file_operation": 8, "browser": 8},
            },
            "available_evidence_refs": refs,
            "organ_contracts": organ_contracts or {},
        },
    }


def _local_authority(levels: list[str] | None = None, organs: list[str] | None = None) -> dict[str, Any]:
    return {
        "root_authority_present": True,
        "allowed_action_levels": levels or ["L2", "L3"],
        "allowed_organs": organs or ["file_operation"],
        "max_risk": "medium",
        "credential_scope": "none",
        "allowed_substeps": ["create_generated_report", "replace_text_file", "append_text_file"],
        "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit", "credential"],
    }


def _browser_authority() -> dict[str, Any]:
    return {
        "root_authority_present": True,
        "special_authority": True,
        "user_review_granted": True,
        "allowed_action_levels": ["L4"],
        "allowed_organs": ["browser"],
        "max_risk": "medium",
        "credential_scope": "none",
        "allowed_substeps": ["browser_read_public_page", "browser_prepare_plan", "browser_semantic_extract"],
        "forbidden_substeps": ["submit", "login", "upload", "download", "credential", "javascript"],
    }


def _l2_contracts(root: Path) -> dict[str, dict[str, Any]]:
    return {
        "file_operation": {
            "available": True,
            "allowed_action_levels": ["L2"],
            "required_receipt_fields": ["path_metadata", "artifact_hash", "lane_id", "gate_result_id"],
            "allowed_substeps": ["create_generated_report"],
            "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit", "credential"],
            "allowed_workspace_root": str(root / "generated_root"),
            "allowed_artifact_subdir": "artifacts",
            "max_artifact_bytes": 4096,
        }
    }


def _l3_contracts(root: Path) -> dict[str, dict[str, Any]]:
    return {
        "file_operation": {
            "available": True,
            "allowed_action_levels": ["L3"],
            "required_receipt_fields": ["path_metadata", "before_hash", "after_hash", "lane_id", "gate_result_id"],
            "allowed_substeps": ["replace_text_file", "append_text_file"],
            "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit", "credential"],
        },
        "reversible_workspace": {
            "available": True,
            "allowed_action_levels": ["L3"],
            "required_receipt_fields": ["path_metadata", "before_hash", "after_hash", "lane_id", "gate_result_id"],
            "allowed_workspace_root": str(root / "workspace_root"),
            "allowed_workspace_subdir": "work",
            "max_file_bytes": 4096,
            "max_patch_bytes": 2048,
            "allow_overwrite": True,
        },
    }


def _browser_contracts() -> dict[str, dict[str, Any]]:
    receipt_fields = ["receipt_id", "lane_id", "gate_result_id", "forbidden_surface_absent"]
    return {
        "browser": {
            "available": True,
            "allowed_action_levels": ["L4"],
            "required_receipt_fields": receipt_fields,
            "allowed_substeps": ["browser_read_public_page", "browser_prepare_plan", "browser_semantic_extract"],
            "forbidden_substeps": ["submit", "login", "upload", "download", "credential", "javascript"],
        },
        "browser_readonly": {
            "available": True,
            "allowed_domains": ["example.com"],
            "allowed_schemes": ["https"],
            "required_receipt_fields": receipt_fields,
        },
        "browser_preparation": {
            "available": True,
            "required_receipt_fields": receipt_fields,
            "max_candidate_targets": 4,
            "max_proposed_steps": 4,
        },
        "browser_semantic_extraction": {
            "available": True,
            "required_receipt_fields": receipt_fields,
            "max_evidence_cards": 6,
            "max_claims_per_source": 4,
        },
    }


def _l2_candidate() -> dict[str, Any]:
    return {
        "proposal_id": "proposal_l2",
        "source_role_id": "planner",
        "artifact_kind": "file_operation_candidate",
        "action_level_candidate": "L2",
        "authority_class": "needs_gate",
        "risk_class": "low",
        "budget_estimate": {"action_count": 1, "artifact_bytes": 32},
        "evidence_refs": ["ev_l2"],
        "receipt_refs": ["receipt_l2"],
        "expected_outcome": "Create a local generated report.",
        "rollback_posture": "delete generated artifact with tombstone",
        "user_review_required": False,
        "safe_summary": "Create a local generated report.",
        "target_relative_path": "reports/closed-loop.md",
        "content": "# Closed Loop\n\nLocal artifact.",
        "action_kind": "create_generated_report",
    }


def _l3_candidate(before_hash: str) -> dict[str, Any]:
    return {
        "proposal_id": "proposal_l3",
        "source_role_id": "planner",
        "artifact_kind": "file_operation_candidate",
        "action_level_candidate": "L3",
        "authority_class": "needs_gate",
        "risk_class": "medium",
        "budget_estimate": {"action_count": 1, "patch_bytes": 16},
        "evidence_refs": ["ev_l3"],
        "receipt_refs": ["receipt_l3"],
        "expected_outcome": "Replace one local text file reversibly.",
        "rollback_posture": "restore previous text from before snapshot",
        "user_review_required": False,
        "safe_summary": "Replace one local text file reversibly.",
        "target_relative_path": "docs/state.md",
        "content": "after\n",
        "before_hash": before_hash,
        "action_kind": "replace_text_file",
    }


def _browser_candidate(kind: str, proposal_id: str, evidence_ref: str) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "source_role_id": "researcher",
        "artifact_kind": "browser_step_candidate",
        "browser_organ_kind": kind,
        "action_level_candidate": "L4",
        "authority_class": "needs_user_review",
        "risk_class": "medium",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": [evidence_ref],
        "receipt_refs": [f"receipt_{kind}"],
        "expected_outcome": f"Run {kind} as untrusted browser perception data.",
        "rollback_posture": "no external mutation; discard receipt",
        "user_review_required": False,
        "safe_summary": f"Run {kind} without external mutation.",
        "requested_url": "https://example.com/research",
        "objective_summary": "Collect public page evidence.",
        "validity_scope": "mission_closed_loop:web",
        "semantic_focus": ["pricing", "case_study"],
        "candidate_goal": "Prepare non-executing browser evidence plan.",
    }


def _workspace_file(root: Path, content: str = "before\n") -> tuple[Path, str]:
    path = root / "workspace_root" / "work" / "docs" / "state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path, text_hash(content)


def _event_types(result: Any) -> list[AgentEventType]:
    return [event.event_type for event in result.trace]


def _phase_pairs(result: Any) -> list[tuple[AgentPhase | None, AgentPhase | None]]:
    return [(event.phase_before, event.phase_after) for event in result.trace]


def test_default_off_exact_regression_no_dispatch_or_organ_execution(tmp_path: Path) -> None:
    env = _envelope()
    user_input = _dispatch_payload(
        action_candidates=[_l2_candidate()],
        authority=_local_authority(["L2"]),
        organ_contracts=_l2_contracts(tmp_path),
    )

    result = AgentRuntime(project_root=tmp_path).run(env, user_input, evidence_refs=["ev_l2"])

    assert result.success is True
    assert result.final_phase is AgentPhase.COMPLETED
    assert result.organ_dispatch_result is None
    assert result.memory_feedback_path == "NOT_STARTED"
    assert result.replan_ready is False
    assert result.automatic_replan_executed is False
    assert AgentEventType.ORGAN_DISPATCH_COMPLETED not in _event_types(result)
    assert AgentEventType.ORGAN_DISPATCH_SKIPPED not in _event_types(result)
    assert not (tmp_path / "generated_root").exists()


def test_enabled_gate_rejection_blocks_before_executor(tmp_path: Path) -> None:
    env = _envelope()
    result = AgentRuntime(project_root=tmp_path, organ_execution_config=_local_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[_l2_candidate()],
            authority={},
            organ_contracts=_l2_contracts(tmp_path),
        ),
        evidence_refs=["ev_l2"],
    )

    dispatch = result.organ_dispatch_result
    assert dispatch is not None
    assert dispatch.candidate_results[0].status.value == "gate_rejected"
    assert dispatch.candidate_results[0].execution_result is None
    assert not (tmp_path / "generated_root").exists()


def test_enabled_l2_success_dispatches_executes_receipts_and_finalgate(tmp_path: Path) -> None:
    env = _envelope()
    result = AgentRuntime(project_root=tmp_path, organ_execution_config=_local_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[_l2_candidate()],
            authority=_local_authority(["L2"]),
            organ_contracts=_l2_contracts(tmp_path),
        ),
        evidence_refs=["ev_l2"],
    )

    dispatch = result.organ_dispatch_result
    assert dispatch is not None
    candidate = dispatch.candidate_results[0]
    assert candidate.status.value == "executed"
    assert candidate.execution_result is not None
    assert candidate.execution_result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert candidate.execution_result.receipt is not None
    assert candidate.execution_result.finalgate_certificate is not None
    assert Path(candidate.execution_result.executor_result_summary["artifact_path"]).exists()


def test_enabled_l3_success_dispatches_reversible_receipt_and_finalgate(tmp_path: Path) -> None:
    target, before_hash = _workspace_file(tmp_path)
    env = _envelope()

    result = AgentRuntime(project_root=tmp_path, organ_execution_config=_local_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[_l3_candidate(before_hash)],
            authority=_local_authority(["L3"]),
            organ_contracts=_l3_contracts(tmp_path),
            available_evidence_refs=["ev_l3"],
        ),
        evidence_refs=["ev_l3"],
    )

    dispatch = result.organ_dispatch_result
    assert dispatch is not None
    execution = dispatch.candidate_results[0].execution_result
    assert execution is not None
    assert execution.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert execution.receipt.before_hash == before_hash
    assert execution.receipt.after_hash is not None
    assert execution.finalgate_certificate is not None
    assert target.read_text(encoding="utf-8") == "after\n"


def test_enabled_browser_readonly_preparation_and_semantic_extraction(tmp_path: Path) -> None:
    fetcher = FakeBrowserReadOnlyFetcher()
    env = _envelope()
    candidates = [
        _browser_candidate("browser_readonly", "proposal_browser_readonly", "ev_browser_readonly"),
        _browser_candidate("browser_preparation", "proposal_browser_preparation", "ev_browser_preparation"),
        _browser_candidate("browser_semantic_extraction", "proposal_browser_semantic", "ev_browser_semantic"),
    ]

    result = AgentRuntime(
        project_root=tmp_path,
        organ_execution_config=_browser_config(),
        browser_fetcher=fetcher,
    ).run(
        env,
        _dispatch_payload(
            action_candidates=candidates,
            authority=_browser_authority(),
            organ_contracts=_browser_contracts(),
            available_evidence_refs=["ev_browser_readonly", "ev_browser_preparation", "ev_browser_semantic"],
        ),
        evidence_refs=["ev_browser_readonly", "ev_browser_preparation", "ev_browser_semantic"],
    )

    dispatch = result.organ_dispatch_result
    assert dispatch is not None
    executed_organs = [candidate.execution_result.organ_kind for candidate in dispatch.candidate_results if candidate.execution_result]
    assert executed_organs == ["browser_readonly", "browser_preparation", "browser_semantic_extraction"]
    assert fetcher.calls == ["https://example.com/research"]
    assert all(candidate.execution_result.execution_effect == "none" for candidate in dispatch.candidate_results if candidate.execution_result)
    assert "browser_submit" not in str(dispatch.model_dump(mode="json")).lower()
    dumped = str(dispatch.model_dump(mode="json")).lower()
    assert "credential_access" not in dumped
    assert "api_key" not in dumped
    assert "bearer " not in dumped


def test_memory_feedback_honesty_is_prepared_not_fake_closed(tmp_path: Path) -> None:
    env = _envelope()
    result = AgentRuntime(project_root=tmp_path, organ_execution_config=_local_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[_l2_candidate()],
            authority=_local_authority(["L2"]),
            organ_contracts=_l2_contracts(tmp_path),
        ),
        evidence_refs=["ev_l2"],
    )

    assert result.organ_dispatch_result is not None
    assert result.memory_feedback_path == "PREPARED"
    assert result.memory_feedback_refs
    assert result.automatic_replan_executed is False


def test_replan_ready_packet_is_prepared_without_automatic_replan(tmp_path: Path) -> None:
    env = _envelope()
    result = AgentRuntime(project_root=tmp_path, organ_execution_config=_local_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[_l2_candidate()],
            authority=_local_authority(["L2"]),
            organ_contracts=_l2_contracts(tmp_path),
        ),
        evidence_refs=["ev_l2"],
    )

    assert result.replan_ready is True
    assert result.automatic_replan_executed is False
    assert result.replan_packet is not None
    assert result.replan_packet["status"] == "PREPARED"


def test_no_l4_l5_l6_l7_or_forbidden_surface_execution(tmp_path: Path) -> None:
    env = _envelope()
    dangerous = _browser_candidate("browser_readonly", "proposal_danger", "ev_browser_readonly")
    dangerous.update(
        {
            "action_level_candidate": "L5",
            "browser_submit": True,
            "credential": True,
            "api_call": True,
            "desktop_action": True,
            "shell": True,
            "channel_send": True,
        }
    )

    result = AgentRuntime(project_root=tmp_path, organ_execution_config=_browser_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[dangerous],
            authority=_browser_authority(),
            organ_contracts=_browser_contracts(),
            available_evidence_refs=["ev_browser_readonly"],
        ),
        evidence_refs=["ev_browser_readonly"],
    )

    dispatch = result.organ_dispatch_result
    assert dispatch is not None
    assert dispatch.status.value in {"bridge_failed", "all_rejected", "no_candidates"}
    assert not any(candidate.execution_result for candidate in dispatch.candidate_results)


def test_provider_backend_model_override_is_rejected_through_dispatch(tmp_path: Path) -> None:
    env = _envelope()
    candidate = _l2_candidate()
    candidate["safe_summary"] = "provider_override should be rejected"

    result = AgentRuntime(project_root=tmp_path, organ_execution_config=_local_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[candidate],
            authority=_local_authority(["L2"]),
            organ_contracts=_l2_contracts(tmp_path),
        ),
        evidence_refs=["ev_l2"],
    )

    dispatch = result.organ_dispatch_result
    assert dispatch is not None
    assert not any(candidate_result.execution_result for candidate_result in dispatch.candidate_results)
    assert "override" not in str(result.llm_decision_cycle or {}).lower()


def test_phase_order_enabled_and_skipped_when_disabled(tmp_path: Path) -> None:
    env = _envelope()
    enabled = AgentRuntime(project_root=tmp_path, organ_execution_config=_local_config()).run(
        env,
        _dispatch_payload(
            action_candidates=[_l2_candidate()],
            authority=_local_authority(["L2"]),
            organ_contracts=_l2_contracts(tmp_path),
        ),
        evidence_refs=["ev_l2"],
    )
    disabled = AgentRuntime(project_root=tmp_path / "disabled").run(
        env.model_copy(update={"id": "mission_closed_loop_disabled"}),
        _dispatch_payload(
            action_candidates=[_l2_candidate()],
            authority=_local_authority(["L2"]),
            organ_contracts=_l2_contracts(tmp_path / "disabled"),
        ),
        evidence_refs=["ev_l2"],
    )

    assert (AgentPhase.EXECUTING, AgentPhase.ORGAN_DISPATCHING) in _phase_pairs(enabled)
    assert (AgentPhase.ORGAN_DISPATCHING, AgentPhase.ARTIFACT_REVIEWING) in _phase_pairs(enabled)
    assert (AgentPhase.EXECUTING, AgentPhase.ORGAN_DISPATCHING) not in _phase_pairs(disabled)
    assert disabled.organ_dispatch_result is None
    assert disabled.mission_result is not None
    assert disabled.mission_result.state.status is MissionStatus.COMPLETED
