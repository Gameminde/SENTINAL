from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.agent.organs.safety_scanner import parse_evidence_bool
from sentinel.agent.model_execution.redaction import text_hash


NOW = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
MISSION_ID = "mission_browser_neural_remediation"


def test_authority_bool_rejects_non_literal_authority_values() -> None:
    from sentinel.agent.organs.safety_scanner import parse_authority_bool

    assert parse_authority_bool(True, field_name="allow_login") is True
    assert parse_authority_bool(False, field_name="allow_login") is False
    for value in ("true", "yes", "1", 1, 0, None, [], {}):
        with pytest.raises(ValueError, match="authority_boolean_must_be_literal"):
            parse_authority_bool(value, field_name="allow_login")


def test_evidence_bool_is_separate_and_does_not_authorize_power() -> None:
    from sentinel.agent.organs.safety_scanner import parse_authority_bool

    assert parse_evidence_bool("false", field_name="capture_screenshot", default=True) is False
    assert parse_evidence_bool("yes", field_name="capture_screenshot", default=False) is True
    with pytest.raises(ValueError, match="authority_boolean_must_be_literal"):
        parse_authority_bool("yes", field_name="allow_download")


def test_organ_dispatch_rejects_string_authority_flags() -> None:
    import sentinel.agent.organs.organ_dispatch as dispatch

    envelope = _mission(allowed_actions=["browser_session_open", "browser_login_credential_session"])
    candidate = {
        "browser_organ_kind": "browser_login_credential_session",
        "url": "https://example.com/login",
        "session_id": "bsess_1",
        "username_credential_ref_id": "cred_user",
        "password_credential_ref_id": "cred_pass",
        "allow_login": "yes",
    }
    request = dispatch._build_browser_login_request(
        raw_candidate=candidate,
        mission_id=envelope.id,
        organ_contracts={
            "browser_login_credential_session_broker": {
                "allowed_domains": ["example.com"],
                "username_credential_ref_id": "cred_user",
                "password_credential_ref_id": "cred_pass",
                "allow_login": False,
            }
        },
        authority_envelope=envelope,
        prior_candidate_results=[],
    )

    assert request is None


def test_v3_controlled_runner_rejects_string_authority_bool() -> None:
    from sentinel.organs.browser.controlled_runner import parse_browser_authority_bool_arg

    assert parse_browser_authority_bool_arg(True, field_name="allow_cross_origin", default=False) is True
    with pytest.raises(ValueError, match="authority_boolean_must_be_literal"):
        parse_browser_authority_bool_arg("on", field_name="allow_cross_origin", default=False)


def test_l2_success_requires_post_write_readback_hash(tmp_path: Path) -> None:
    from sentinel.agent.organs.local_artifact_executor import L2LocalArtifactAttemptStatus, L2LocalArtifactExecutor

    request = _l2_request(tmp_path, content="verified report\n")
    result = L2LocalArtifactExecutor().execute(request)

    assert result.attempt_status is L2LocalArtifactAttemptStatus.CREATED
    assert result.artifact_hash == text_hash("verified report\n")
    assert result.receipt.artifact_hash == text_hash("verified report\n")


def test_l2_write_mismatch_blocks_without_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import sentinel.agent.organs.local_artifact_executor as l2

    monkeypatch.setattr(l2, "_readback_text_hash", lambda _path: "wrong-hash")
    result = l2.L2LocalArtifactExecutor().execute(_l2_request(tmp_path, content="expected\n"))

    assert result.attempt_status is l2.L2LocalArtifactAttemptStatus.BLOCKED
    assert result.status is l2.L2LocalArtifactExecutorStatus.BLOCKED
    assert result.execution_effect == "none"
    assert result.receipt.rejection_reason == "artifact_write_verification_failed"


def test_l3_success_requires_post_write_readback_hash(tmp_path: Path) -> None:
    from sentinel.agent.organs.reversible_workspace_executor import (
        L3ReversibleWorkspaceExecutor,
        L3WorkspaceAttemptStatus,
    )

    request = _l3_request(tmp_path, content="new state\n")
    result = L3ReversibleWorkspaceExecutor().execute(request)

    assert result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
    assert result.after_hash == text_hash("new state\n")
    assert result.receipt.after_hash == text_hash("new state\n")


def test_l3_write_mismatch_blocks_and_attempts_safe_rollback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import sentinel.agent.organs.reversible_workspace_executor as l3

    calls = {"count": 0}
    real_readback = l3._readback_text_hash

    def racing_readback(path: Path) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "wrong-hash"
        return real_readback(path)

    monkeypatch.setattr(l3, "_readback_text_hash", racing_readback)
    result = l3.L3ReversibleWorkspaceExecutor().execute(_l3_request(tmp_path, content="new state\n"))

    assert result.attempt_status is l3.L3WorkspaceAttemptStatus.BLOCKED
    assert result.status is l3.L3WorkspaceExecutorStatus.BLOCKED
    assert result.rollback_attempted is True
    assert result.rollback_success is True
    assert result.receipt.rejection_reason == "workspace_write_verification_failed"


def test_l3_rollback_receipt_separates_attempted_and_success(tmp_path: Path) -> None:
    from sentinel.agent.organs.reversible_workspace_executor import (
        L3ReversibleWorkspaceExecutor,
        L3WorkspaceAttemptStatus,
    )

    executor = L3ReversibleWorkspaceExecutor()
    result = executor.execute(_l3_request(tmp_path, content="new state\n"))
    rollback = executor.rollback(result, rollback_reason="test rollback")

    assert rollback.attempt_status is L3WorkspaceAttemptStatus.ROLLBACK_COMPLETED
    assert rollback.rollback_attempted is True
    assert rollback.rollback_success is True
    assert rollback.restored_hash == result.before_hash


def test_credential_grant_max_use_count_is_atomic() -> None:
    from sentinel.organs.credentials.foundation import CredentialAccessDecision
    from sentinel.organs.credentials.foundation import evaluate_credential_access

    grant = _credential_grant(max_use_count=1)

    def _attempt(index: int):
        return evaluate_credential_access(_credential_access_request(request_id=f"creq_{index}"), [grant], current_time=NOW)

    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(_attempt, range(8)))

    allowed = [receipt for receipt in receipts if receipt.decision is CredentialAccessDecision.ALLOWED_METADATA_ONLY]
    denied = [receipt for receipt in receipts if receipt.decision is not CredentialAccessDecision.ALLOWED_METADATA_ONLY]
    assert len(allowed) == 1
    assert len(denied) == 7
    assert grant.used_count == 1
    assert all("credential_grant_use_count_exhausted" in receipt.reasons for receipt in denied)


def test_download_candidate_cannot_weaken_executable_policy(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import BrowserFileQuarantineContract

    with pytest.raises(ValueError, match="forbid_executables_cannot_be_disabled"):
        BrowserFileQuarantineContract(
            mission_id=MISSION_ID,
            allowed_domains=["example.com"],
            approved_upload_root=str(tmp_path / "uploads"),
            approved_download_quarantine_root=str(tmp_path / "downloads"),
            allow_download=True,
            forbid_executables=False,
        )


def test_download_effective_max_bytes_is_minimum(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import BrowserFileQuarantineContract

    contract = BrowserFileQuarantineContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        approved_upload_root=str(tmp_path / "uploads"),
        approved_download_quarantine_root=str(tmp_path / "downloads"),
        allow_download=True,
        max_file_bytes=5_000_000,
        candidate_max_file_bytes=100,
    )

    assert contract.max_file_bytes == 5_000_000
    assert contract.candidate_max_file_bytes == 100
    assert contract.effective_max_file_bytes == 100


def test_session_sanitizer_called_on_close_failure_and_close_all(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    sanitizer = _RecordingSessionSanitizer()
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        backend=_FakeBrowserSessionBackend(),
        session_sanitizer=sanitizer,
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.CLICK],
        max_steps=5,
    )

    opened = manager.open_session(BrowserSessionRequest(mission=_mission(), url="https://example.com", contract=contract))
    closed = manager.close_session(BrowserSessionRequest(mission=_mission(), url="https://example.com", contract=contract, session_id=opened.session_id))
    failed = manager.close_session(BrowserSessionRequest(mission=_mission(), url="https://example.com", contract=contract, session_id="missing"))
    opened_again = manager.open_session(BrowserSessionRequest(mission=_mission(), url="https://example.com", contract=contract))
    manager.close_all()

    assert closed.accepted is True
    assert failed.accepted is False
    assert sanitizer.calls["close"] >= 1
    assert sanitizer.calls["failure"] >= 1
    assert sanitizer.calls["close_all"] >= 1
    combined = f"{closed.model_dump(mode='json')} {failed.model_dump(mode='json')} {opened_again.model_dump(mode='json')}"
    assert "raw-cookie-value" not in combined
    assert "raw-token-value" not in combined


def test_pre_context_sweep_blocks_or_redacts_secret_like_payloads() -> None:
    from sentinel.agent.llm.context_pack import sweep_context_payload_for_secrets

    payload = {
        "authorization": "Bearer live-token-value",
        "api_key": "sk-live-value",
        "cookie": "sid=raw-cookie-value",
        "session_token": "sess_live_value",
        "env": "OPENAI_API_KEY=raw-env-value",
    }
    result = sweep_context_payload_for_secrets(payload)

    assert result.accepted is False
    rendered = str(result.sanitized_payload)
    assert "live-token-value" not in rendered
    assert "sk-live-value" not in rendered
    assert "raw-cookie-value" not in rendered
    assert "raw-env-value" not in rendered
    assert result.findings


def test_context_pack_rejects_secret_like_content_before_hashing() -> None:
    from sentinel.agent.llm.context_pack import ContextPack, ContextPackAuthorityBoundary

    with pytest.raises(ValueError, match="context_pack_secret_like_payload"):
        ContextPack(
            mission_id=MISSION_ID,
            mission_goal="Use public data. Authorization: Bearer live-token-value",
            authority_boundary=ContextPackAuthorityBoundary(allowed_domains=["example.com"]),
        )


def test_motor_proposal_known_gated_action_exposes_drop_reason() -> None:
    from sentinel.agent.browser.neural.models import stable_neural_hash
    from sentinel.agent.browser.neural.motor_proposal import (
        MotorProposalArtifact,
        diagnose_motor_proposal_artifact,
        motor_proposal_artifact_to_browser_step_candidate,
    )

    payload = {
        "proposal_artifact_id": "mprop_known_gated_login",
        "mission_id": MISSION_ID,
        "organ_kind": "browser_session_manager",
        "action_level": "L5",
        "target_ref": "target_login",
        "source_signal_refs": ["nsig_safe_1"],
        "source_evidence_refs": ["ev_login"],
        "required_authority": "L5_browser_operator",
        "risk_flags": [],
        "expected_receipt_type": "BrowserSessionReceipt",
        "verification_plan": {"expected": "receipt_and_finalgate_required"},
        "url": "https://example.com/login",
        "action_kind": "login",
        "allowed_domains": ["example.com"],
        "target_role": "button",
        "target_name": None,
        "text": None,
        "dispatch_required": True,
        "data_not_instruction": True,
    }
    hash_payload = dict(payload)
    hash_payload.pop("dispatch_required")
    hash_payload.pop("data_not_instruction")
    artifact = MotorProposalArtifact(**payload, artifact_hash=stable_neural_hash(hash_payload))

    diagnostic = diagnose_motor_proposal_artifact(artifact)
    assert motor_proposal_artifact_to_browser_step_candidate(artifact) is None
    assert diagnostic.accepted is False
    assert diagnostic.drop_reason == "known_browser_action_gated"


class _RecordingSessionSanitizer:
    def __init__(self) -> None:
        self.calls = {"close": 0, "failure": 0, "close_all": 0}

    def sanitize(self, *, session: object | None, reason: str) -> dict[str, object]:
        self.calls[reason] = self.calls.get(reason, 0) + 1
        return {
            "sanitized": True,
            "reason": reason,
            "cookie": "[REDACTED]",
            "token": "[REDACTED]",
        }


class _FakeBrowserSessionBackend:
    backend_kind = "fake_browser"

    def open_context(
        self,
        *,
        profile_dir: Path,
        url: str,
        timeout_ms: int,
        viewport_width: int,
        viewport_height: int,
    ):
        from sentinel.organs.browser.cloak_backend import BrowserEngineSession

        profile_dir.mkdir(parents=True, exist_ok=True)
        context = _FakeBrowserContext()
        page = _FakeBrowserPage(url=url, context=context)
        return BrowserEngineSession(backend_kind=self.backend_kind, context=context, page=page, profile_dir=profile_dir)


class _FakeBrowserContext:
    def __init__(self) -> None:
        self.closed = False
        self.cookies_cleared = 0
        self.permissions_cleared = 0

    def clear_cookies(self) -> None:
        self.cookies_cleared += 1

    def clear_permissions(self) -> None:
        self.permissions_cleared += 1

    def close(self) -> None:
        self.closed = True


class _FakeBrowserPage:
    def __init__(self, *, url: str, context: _FakeBrowserContext) -> None:
        self.url = url
        self.context = context

    def content(self) -> str:
        return "<html><body><button>Go</button></body></html>"

    def locator(self, selector: str):
        return _FakeLocator(selector)

    def screenshot(self, **_kwargs: Any) -> bytes:
        return b"fake-png"


class _FakeLocator:
    def __init__(self, selector: str) -> None:
        self.selector = selector

    def inner_text(self, **_kwargs: Any) -> str:
        return "Go"

    def count(self) -> int:
        return 0

    def nth(self, _index: int):
        return self

    def get_attribute(self, _name: str, **_kwargs: Any) -> str | None:
        return None

    def input_value(self, **_kwargs: Any) -> str:
        return ""


def _mission(**updates: Any):
    from sentinel.mission.models import MissionAuthorityEnvelope
    from sentinel.shared.enums import MissionMode, MissionType

    data = {
        "id": MISSION_ID,
        "user_id": "user_remediation",
        "mission_type": MissionType.RESEARCH_SUMMARY,
        "mission_title": "Browser neural remediation",
        "mission_objective": "Verify remediation locks.",
        "success_criteria": ["locks pass"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace", "public_web"],
        "allowed_tools": ["browser_session_l5_live"],
        "allowed_actions": ["browser_session_open", "browser_session_observe", "browser_session_interact", "browser_session_close"],
        "forbidden_actions": ["browser_submit_form", "payment", "shell", "desktop_action"],
        "allowed_domains": ["example.com"],
        "allowed_paths": ["data/generated_projects"],
        "max_actions": 20,
        "max_cost_usd": 0.0,
    }
    data.update(updates)
    return MissionAuthorityEnvelope(**data)


def _l2_contract(tmp_path: Path):
    from sentinel.agent.organs.local_artifact_executor import L2ExecutorContract

    return L2ExecutorContract(
        mission_id="mission_l2_remediation",
        lane_id="lane_l2",
        gate_result_id="gate_l2",
        allowed_workspace_root=str(tmp_path / "generated_root"),
        allowed_artifact_subdir="artifacts",
        max_artifact_bytes=4096,
        allow_overwrite=False,
        allow_rollback_cleanup=True,
        receipt_required=True,
        tombstone_required_for_cleanup=True,
        finalgate_posture_required=True,
        execution_enabled_for_l2=True,
        contract_version="l2-local-artifact-v0",
    )


def _l2_lane():
    from sentinel.agent.organs.delegated_action_gate import (
        DelegatedActionAuthorityClass,
        DelegatedActionLane,
        DelegatedActionLevel,
        DelegatedActionReceiptRequirement,
        DelegatedActionRiskClass,
        OrganProposalKind,
    )

    return DelegatedActionLane(
        lane_id="lane_l2",
        mission_id="mission_l2_remediation",
        source_candidate_id="candidate_l2",
        organ_kind=OrganProposalKind.FILE_OPERATION,
        action_level=DelegatedActionLevel.L2,
        allowed_substeps=["create_generated_report"],
        forbidden_substeps=["send", "network", "api", "shell", "browser_submit"],
        authority_class=DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        risk_class=DelegatedActionRiskClass.LOW,
        budget_limit={"remaining_action_count": 2, "remaining_artifact_bytes": 4096},
        credential_scope="none",
        evidence_refs=["ev_l2"],
        receipt_refs=["receipt_gate_l2"],
        receipt_contract=DelegatedActionReceiptRequirement(
            required_receipt_fields=["artifact_hash", "path_metadata", "lane_id", "gate_result_id"],
            receipt_refs=["receipt_gate_l2"],
            receipt_contract_hash="receipt_contract_hash_l2",
        ),
        revocation_rule="lane can be revoked before local artifact execution",
        rollback_posture="delete generated artifact with tombstone",
        user_review_requirement="not_required_for_l2_local_artifact",
        FinalGate_checks=["local_only", "artifact_hash_present", "no_external_mutation"],
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
        ttl_seconds=1800,
    )


def _l2_request(tmp_path: Path, *, content: str):
    from sentinel.agent.organs.local_artifact_executor import L2LocalArtifactActionKind, L2LocalArtifactRequest

    return L2LocalArtifactRequest(
        mission_id="mission_l2_remediation",
        source_candidate_id="candidate_l2",
        action_kind=L2LocalArtifactActionKind.CREATE_GENERATED_REPORT,
        target_relative_path="report.md",
        content=content,
        metadata={"title": "safe report"},
        contract=_l2_contract(tmp_path),
        delegated_lane=_l2_lane(),
        budget_estimate={"artifact_bytes": len(content.encode("utf-8")), "action_count": 1},
        current_time=NOW,
    )


def _l3_contract(tmp_path: Path):
    from sentinel.agent.organs.reversible_workspace_executor import L3ExecutorContract

    return L3ExecutorContract(
        mission_id="mission_l3_remediation",
        lane_id="lane_l3",
        gate_result_id="gate_l3",
        allowed_workspace_root=str(tmp_path / "workspace_root"),
        allowed_workspace_subdir="work",
        max_file_bytes=4096,
        max_patch_bytes=2048,
        allow_overwrite=True,
        allow_delete=False,
        tombstone_required_for_delete=True,
        rollback_required=True,
        rollback_must_be_tested_before_mutation=True,
        receipt_required=True,
        finalgate_posture_required=True,
        execution_enabled_for_l3=True,
        contract_version="l3-reversible-workspace-v0",
    )


def _l3_lane():
    from sentinel.agent.organs.delegated_action_gate import (
        DelegatedActionAuthorityClass,
        DelegatedActionLane,
        DelegatedActionLevel,
        DelegatedActionReceiptRequirement,
        DelegatedActionRiskClass,
        OrganProposalKind,
    )

    return DelegatedActionLane(
        lane_id="lane_l3",
        mission_id="mission_l3_remediation",
        source_candidate_id="candidate_l3",
        organ_kind=OrganProposalKind.FILE_OPERATION,
        action_level=DelegatedActionLevel.L3,
        allowed_substeps=["replace_text_file"],
        forbidden_substeps=["send", "network", "api", "shell", "browser_submit"],
        authority_class=DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        risk_class=DelegatedActionRiskClass.MEDIUM,
        budget_limit={"remaining_action_count": 2, "remaining_patch_bytes": 2048},
        credential_scope="none",
        evidence_refs=["ev_l3"],
        receipt_refs=["receipt_gate_l3"],
        receipt_contract=DelegatedActionReceiptRequirement(
            required_receipt_fields=["before_hash", "after_hash", "path_metadata", "lane_id", "gate_result_id"],
            receipt_refs=["receipt_gate_l3"],
            receipt_contract_hash="receipt_contract_hash_l3",
        ),
        revocation_rule="lane can be revoked before reversible local workspace execution",
        rollback_posture="restore previous text content from before snapshot",
        user_review_requirement="not_required_for_l3_reversible_workspace",
        FinalGate_checks=["local_only", "before_hash", "after_hash", "rollback_ready"],
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
        ttl_seconds=1800,
    )


def _l3_request(tmp_path: Path, *, content: str):
    from sentinel.agent.organs.reversible_workspace_executor import L3WorkspaceActionKind, L3WorkspaceRequest

    target = tmp_path / "workspace_root" / "work" / "docs" / "state.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    before_content = "old state\n"
    target.write_text(before_content, encoding="utf-8")
    return L3WorkspaceRequest(
        mission_id="mission_l3_remediation",
        source_candidate_id="candidate_l3",
        action_kind=L3WorkspaceActionKind.REPLACE_TEXT_FILE,
        target_relative_path="docs/state.md",
        content=content,
        before_hash=text_hash(before_content),
        metadata={"title": "safe reversible edit"},
        contract=_l3_contract(tmp_path),
        delegated_lane=_l3_lane(),
        budget_estimate={"patch_bytes": len(content.encode("utf-8")), "action_count": 1},
        current_time=NOW,
    )


def _credential_grant(**updates: Any):
    from sentinel.agent.organs.delegated_action_gate import DelegatedActionLevel
    from sentinel.organs.credentials.foundation import CredentialGrant

    data = {
        "grant_id": "credgrant_atomic",
        "mission_id": MISSION_ID,
        "credential_ref_id": "cred_ref_atomic",
        "allowed_organs": ["browser_login_credential_session"],
        "allowed_action_levels": [DelegatedActionLevel.L6],
        "domain_scope": ["example.com"],
        "action_scope": ["browser_login"],
        "max_use_count": 1,
        "receipt_refs": ["receipt_credential"],
    }
    data.update(updates)
    return CredentialGrant(**data)


def _credential_access_request(**updates: Any):
    from sentinel.agent.organs.delegated_action_gate import DelegatedActionLevel
    from sentinel.organs.credentials.foundation import CredentialAccessRequest

    data = {
        "request_id": "creq_atomic",
        "mission_id": MISSION_ID,
        "credential_ref_id": "cred_ref_atomic",
        "organ_kind": "browser_login_credential_session",
        "action_level": DelegatedActionLevel.L6,
        "domain": "example.com",
        "action": "browser_login",
        "receipt_refs": ["receipt_request"],
    }
    data.update(updates)
    return CredentialAccessRequest(**data)
