from __future__ import annotations

import inspect


def test_squad_roles_are_views_over_neurons() -> None:
    from sentinel.agent.browser.neural import BrowserNeuralOperatorSquad, BrowserSquadRoleKind, NeuronKind

    squad = BrowserNeuralOperatorSquad.default(mission_id="mission_squad", authority_envelope_id="env_1")
    role = squad.role(BrowserSquadRoleKind.SCOUT)

    assert NeuronKind.BROWSER_OBSERVATION in role.allowed_neuron_kinds
    assert role.data_not_instruction is True
    assert role.authority_effect == "none"


def test_squad_agents_cannot_execute_directly() -> None:
    from sentinel.agent.browser.neural import BrowserNeuralOperatorSquad

    squad = BrowserNeuralOperatorSquad.default(mission_id="mission_squad", authority_envelope_id="env_1")

    for role in squad.roles:
        assert role.can_execute is False
        assert role.can_call_organ_directly is False
        assert role.can_call_runtime_execution is False
        assert role.can_access_credentials is False


def test_operator_role_emits_motor_proposal_only() -> None:
    from sentinel.agent.browser.neural import BrowserNeuralOperatorSquad, BrowserSquadRoleKind

    squad = BrowserNeuralOperatorSquad.default(mission_id="mission_squad", authority_envelope_id="env_1")
    output = squad.role_output(
        BrowserSquadRoleKind.OPERATOR,
        source_signal_refs=["nsig_plan"],
        summary="prepare motor proposal",
        proposal_artifact_refs=["mprop_1"],
    )

    assert output.role_kind is BrowserSquadRoleKind.OPERATOR
    assert output.proposal_artifact_refs == ["mprop_1"]
    assert output.can_execute is False
    assert output.authority_effect == "none"


def test_verifier_boundary_and_recovery_roles_cannot_grant_authority() -> None:
    from sentinel.agent.browser.neural import BrowserNeuralOperatorSquad, BrowserSquadRoleKind

    squad = BrowserNeuralOperatorSquad.default(mission_id="mission_squad", authority_envelope_id="env_1")

    for kind in (BrowserSquadRoleKind.VERIFIER, BrowserSquadRoleKind.BOUNDARY, BrowserSquadRoleKind.RECOVERY):
        output = squad.role_output(kind, source_signal_refs=["nsig_1"], summary="role observation")
        assert output.can_grant_authority is False
        assert output.can_approve_future_execution is False
        assert output.execution_effect == "none"


def test_boundary_role_detects_auth_payment_captcha_without_bypass() -> None:
    from sentinel.agent.browser.neural import BrowserNeuralOperatorSquad, BrowserSquadRoleKind

    squad = BrowserNeuralOperatorSquad.default(mission_id="mission_squad", authority_envelope_id="env_1")
    output = squad.boundary_check("login checkout captcha page", source_signal_refs=["nsig_1"])

    assert output.role_kind is BrowserSquadRoleKind.BOUNDARY
    assert {"auth_wall", "payment_boundary", "captcha_boundary"}.issubset(set(output.risk_flags))
    assert output.can_execute is False


def test_squad_uses_one_authority_envelope() -> None:
    from sentinel.agent.browser.neural import BrowserNeuralOperatorSquad

    squad = BrowserNeuralOperatorSquad.default(mission_id="mission_squad", authority_envelope_id="env_1")

    assert {role.authority_envelope_id for role in squad.roles} == {"env_1"}
    assert squad.authority_envelope_id == "env_1"


def test_squad_trace_replayable_from_ledger(tmp_path) -> None:
    from sentinel.agent.browser.neural import BrowserNeuralOperatorSquad, BrowserSquadRoleKind
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    ledger = BrowserNeuralReceiptLedger(tmp_path / "squad-ledger.jsonl")
    squad = BrowserNeuralOperatorSquad.default(mission_id="mission_squad", authority_envelope_id="env_1")
    output = squad.role_output(BrowserSquadRoleKind.SCOUT, source_signal_refs=["nsig_1"], summary="scout saw page")
    squad.record_output(ledger, workflow_id="wf_squad", run_id="run_1", output=output)

    replay = ledger.replay()

    assert replay[0].refs["role_output_id"] == output.output_id
    assert replay[0].refs["authority_envelope_id"] == "env_1"


def test_no_squad_module_imports_browser_backends_or_runtime_execution() -> None:
    import sentinel.agent.browser.neural.squad as squad

    source = inspect.getsource(squad)

    assert "from sentinel.agent.organs.runtime_execution" not in source
    assert "BrowserSessionManagerL5Live" not in source
    assert "BrowserLoginCredentialSessionBrokerL6" not in source
    assert "playwright" not in source.lower()
