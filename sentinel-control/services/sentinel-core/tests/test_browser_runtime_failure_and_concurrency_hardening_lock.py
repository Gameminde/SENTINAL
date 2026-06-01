from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.organs import runtime_execution as runtime_execution_module
from sentinel.agent.organs.delegated_action_gate import DelegatedActionGateDecision
from sentinel.agent.organs.organ_dispatch import OrganDispatcher, OrganDispatchStatus
from sentinel.agent.organs.proposal_bridge import OrganProposalBridge, OrganProposalBridgeInput
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionStatus,
    execute_organ_runtime_request,
)

from test_brain_to_organ_runtime_closed_loop import (
    NOW,
    _envelope,
    _l2_candidate,
    _l2_contracts,
    _local_authority,
    _local_config,
)
from test_browser_runtime_unification_l6_login_file_js_dispatch_lock import (
    LOGIN_HTML,
    MISSION_ID,
    PASS_REF,
    PASSWORD_VALUE,
    URL,
    USER_REF,
    _gate,
    _mission,
    _open_request,
    _runtime_config,
)
from test_delegated_action_gate_model_v0 import _budget, _decide


def _login_runtime_request() -> OrganRuntimeExecutionRequest:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionContract,
        BrowserLoginCredentialSessionRequest,
    )

    gate = _gate(DelegatedActionLevel.L6)
    return OrganRuntimeExecutionRequest(
        mission_id=MISSION_ID,
        action_level=DelegatedActionLevel.L6,
        organ_kind="browser_login_credential_session_broker",
        authority_envelope=_mission(),
        gate_result=gate,
        delegated_lane=gate.lane,
        browser_login_request=BrowserLoginCredentialSessionRequest(
            mission=_mission(),
            url=URL,
            session_id="runtime_existing_session",
            contract=BrowserLoginCredentialSessionContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                username_credential_ref_id=USER_REF,
                password_credential_ref_id=PASS_REF,
                allow_login=True,
            ),
            username_target_name="Email",
            password_target_name="Password",
            submit_target_name="Sign in",
        ),
    )


def test_browser_session_manager_cache_has_thread_lock_and_reuses_single_manager(tmp_path: Path) -> None:
    assert hasattr(runtime_execution_module, "_BROWSER_SESSION_MANAGERS_LOCK")
    assert runtime_execution_module._BROWSER_SESSION_MANAGERS_LOCK is not None

    config = _runtime_config(tmp_path, browser_document_fixtures={URL: LOGIN_HTML}, browser_persist_sessions=True)
    gate = _gate(DelegatedActionLevel.L5)
    request = OrganRuntimeExecutionRequest(
        mission_id=MISSION_ID,
        action_level=DelegatedActionLevel.L5,
        organ_kind="browser_session_manager",
        authority_envelope=_mission(),
        gate_result=gate,
        delegated_lane=gate.lane,
        browser_session_request=_open_request(),
    )

    def get_manager_identity() -> int:
        _, manager = runtime_execution_module._browser_session_manager_for_runtime(request, config)
        return id(manager)

    with ThreadPoolExecutor(max_workers=16) as pool:
        manager_ids = list(pool.map(lambda _: get_manager_identity(), range(64)))

    assert len(set(manager_ids)) == 1


def test_browser_l5_l6_special_runtime_requires_persisted_session_continuity(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path, browser_document_fixtures={URL: LOGIN_HTML}, browser_persist_sessions=False)

    result = execute_organ_runtime_request(_login_runtime_request(), config=config)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "browser_persist_sessions_required_for_l5_l6_special_authority"
    assert result.receipt is None
    assert result.finalgate_certificate is None


def test_browser_executor_exception_returns_sanitized_receipt_and_finalgate(tmp_path: Path, monkeypatch: Any) -> None:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionBrokerL6,
    )

    def raise_with_secret(self: BrowserLoginCredentialSessionBrokerL6, request: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"browser crashed with {'Bear'}{'er'} {PASSWORD_VALUE}")

    monkeypatch.setattr(BrowserLoginCredentialSessionBrokerL6, "execute", raise_with_secret)
    config = _runtime_config(tmp_path, browser_document_fixtures={URL: LOGIN_HTML}, browser_persist_sessions=True)

    result = execute_organ_runtime_request(_login_runtime_request(), config=config)
    dumped = result.model_dump_json()

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason is not None
    assert result.blocked_reason.startswith("browser_login_credential_session_broker_executor_exception")
    assert result.receipt is not None
    assert result.receipt.blocked_reason == result.blocked_reason
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.certified is True
    assert result.trace.receipt_hash is not None
    assert result.trace.certificate_hash is not None
    assert "RuntimeError" in dumped
    assert PASSWORD_VALUE not in dumped
    assert "Bear" + "er " not in dumped


def test_gate_prioritizes_missing_authority_over_budget_exhausted() -> None:
    result = _decide(authority={}, budget=_budget(remaining_action_count=0))

    assert result.decision is DelegatedActionGateDecision.AUTHORITY_EXTENSION_REQUIRED


def test_organ_dispatch_correlates_raw_candidate_by_source_proposal_id_when_bridge_reorders(tmp_path: Path) -> None:
    alpha = {
        **_l2_candidate(),
        "proposal_id": "proposal_alpha",
        "target_relative_path": "reports/alpha.md",
        "content": "alpha content",
    }
    beta = {
        **_l2_candidate(),
        "proposal_id": "proposal_beta",
        "target_relative_path": "reports/beta.md",
        "content": "beta content",
    }
    raw_candidates = [alpha, beta]
    bridge_result = OrganProposalBridge().build(
        OrganProposalBridgeInput(
            mission_id="mission_dispatch_correlation",
            proposal_artifacts=raw_candidates,
            current_time=NOW,
        )
    )
    assert [candidate.source_proposal_id for candidate in bridge_result.candidates] == [
        "proposal_alpha",
        "proposal_beta",
    ]

    class ReorderingBridge:
        def build(self, bridge_input: OrganProposalBridgeInput) -> Any:
            return bridge_result.model_copy(update={"candidates": list(reversed(bridge_result.candidates))})

    dispatcher = OrganDispatcher()
    dispatcher._bridge = ReorderingBridge()  # type: ignore[assignment]

    result = dispatcher.dispatch(
        mission_id="mission_dispatch_correlation",
        action_candidates=raw_candidates,
        config=_local_config(),
        authority=_local_authority(),
        authority_envelope=_envelope("mission_dispatch_correlation"),
        budget={
            "remaining_action_count": 4,
            "remaining_retries": 1,
            "remaining_tokens": 100_000,
            "organ_budget_units": {"file_operation": 4},
        },
        available_evidence_refs=["ev_l2"],
        organ_contracts=_l2_contracts(tmp_path),
    )

    assert result.status is OrganDispatchStatus.COMPLETED
    first = result.candidate_results[0].execution_result
    assert first is not None
    assert first.executor_result_summary["artifact_path"].endswith("reports\\beta.md") or first.executor_result_summary[
        "artifact_path"
    ].endswith("reports/beta.md")
    beta_path = tmp_path / "generated_root" / "artifacts" / "reports" / "beta.md"
    assert beta_path.read_text(encoding="utf-8") == "beta content"
