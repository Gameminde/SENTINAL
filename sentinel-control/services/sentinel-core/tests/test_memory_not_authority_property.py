"""Task 2.4 / Requirement 2 (Memory-not-Authority Multi-Phase Enforcement).

Adversarial property tests that prove the Memory-not-Authority invariant
(F-A3.4) is enforced at every phase boundary wired in
:meth:`AgentRuntime.run`.

Validates:
    * **CP-2.1 (Memory Isolation):**
      ``∀ phase_boundary P, ∀ memory_item M: capabilities_after(P, with M)
      ⊆ envelope.allowed_actions``
    * **CP-2.2 (No Hidden Policy):** the set of actions considered by action
      selection is determined only by the authority envelope captured at
      run entry, never by context/memory introduced later.

These tests are adversarial: they construct synthetic memory items and
mutated contexts that *try* to smuggle extra capability or a drifted
envelope past the phase boundary re-check installed by Task 2.2 / 2.3.
The contract is that ``Supervisor.assert_context_did_not_expand_authority``
(and, end-to-end, ``AgentRuntime.run``) MUST raise
:class:`InvariantViolation` — or, at the runtime level, return a
``final_phase == AgentPhase.BLOCKED`` result whose ``escalation_reason``
carries the offending boundary label.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from sentinel.agent import (
    AgentContext,
    AgentPhase,
    AgentRuntime,
    InvariantViolation,
    ReviewFinding,
    Supervisor,
)
from sentinel.agent.capability_selector import capabilities_from_actions
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


# ---------------------------------------------------------------------------
# Envelope / context fixtures — mirror the patterns used by
# ``tests/test_final_gate_terminality.py`` and ``tests/test_agent_runtime.py``.
# Duplicated intentionally per the task brief ("do NOT duplicate
# conftest.py fixtures" — i.e., keep the helper local to this test module).
# ---------------------------------------------------------------------------

SAFE_ACTIONS: list[str] = [
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

FORBIDDEN_ACTIONS: list[str] = [
    "send_email",
    "run_shell_command",
    "browser_submit_form",
    "credential_access",
]

# Capabilities an adversary might try to smuggle in. None of these derive
# from SAFE_ACTIONS via ``capabilities_from_actions``.
ADVERSARIAL_CAPABILITIES: list[str] = [
    "run_shell_command_capability",
    "send_email_capability",
    "credential_access_capability",
    "public_web_form_submit",  # would require "browser_form_submit" action
    "browser_research",  # would require browser_read/render action
]


def _envelope(**overrides: Any) -> MissionAuthorityEnvelope:
    data: dict[str, Any] = {
        "user_id": "user_001",
        "mission_type": MissionType.GTM,
        "mission_title": "Memory-not-Authority adversarial test",
        "mission_objective": "Prove phase-boundary re-checks detect drift.",
        "success_criteria": ["Trace exists", "Run completes"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": list(SAFE_ACTIONS),
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def _context_for(
    envelope: MissionAuthorityEnvelope,
    *,
    available_capabilities: list[str] | None = None,
) -> AgentContext:
    caps = (
        list(available_capabilities)
        if available_capabilities is not None
        else capabilities_from_actions(list(envelope.allowed_actions))
    )
    return AgentContext(
        mission=envelope,
        user_input={},
        evidence_refs=[],
        memory_items=[],
        constraints=[
            "mission_type=gtm",
            "memory_is_context_not_authority",
        ],
        available_capabilities=caps,
        available_tools=list(envelope.allowed_tools),
        world_model_refs=["mission_authority", "memory_not_authority"],
        summary=envelope.mission_title,
    )


# ---------------------------------------------------------------------------
# Test 1 — Adversarial Hypothesis property over context capability expansion
# ---------------------------------------------------------------------------


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(
    allowed_actions=st.lists(
        st.sampled_from(SAFE_ACTIONS),
        min_size=1,
        max_size=len(SAFE_ACTIONS),
        unique=True,
    ),
    extra_action=st.sampled_from(FORBIDDEN_ACTIONS),
    adversarial_capability=st.sampled_from(ADVERSARIAL_CAPABILITIES),
)
def test_adversarial_context_capability_expansion_property(
    allowed_actions: list[str],
    extra_action: str,
    adversarial_capability: str,
) -> None:
    """**Validates: CP-2.1 (Memory Isolation)**

    For any non-empty subset of the safe-actions pool, constructing an
    ``AgentContext`` whose ``available_capabilities`` contains a capability
    not derivable from ``allowed_actions`` MUST cause
    ``Supervisor.assert_context_did_not_expand_authority`` to raise
    :class:`InvariantViolation` with a message carrying the supplied
    ``boundary_name``.

    The ``extra_action`` is a forbidden action the adversary would love to
    have — it serves as a reminder in the generated state that the capability
    set under test genuinely lives outside the authority envelope, even
    though only ``adversarial_capability`` is injected into the context.
    """
    envelope = _envelope(allowed_actions=list(allowed_actions))
    derived = set(capabilities_from_actions(list(allowed_actions)))

    # The Hypothesis strategy may pick an adversarial capability that,
    # although never derived from ``SAFE_ACTIONS`` below, happens to coincide
    # with one derivable from a concrete subset. Guard against that so the
    # property only covers the adversarial (non-derivable) case it claims
    # to cover. ``extra_action`` is only referenced in the assertion context
    # to make the state-of-attack explicit (see docstring).
    assert extra_action not in allowed_actions
    if adversarial_capability in derived:
        pytest.skip(
            "Generated capability happened to be derivable from this "
            "allowed_actions subset; not an adversarial sample."
        )

    context = _context_for(
        envelope,
        available_capabilities=[*derived, adversarial_capability],
    )

    with pytest.raises(InvariantViolation) as excinfo:
        Supervisor().assert_context_did_not_expand_authority(
            context,
            envelope=envelope,
            original_allowed_actions=tuple(allowed_actions),
            boundary_name="t5_adversarial",
        )

    assert "t5_adversarial" in str(excinfo.value), (
        f"boundary_name must be prefixed to the violation message; got "
        f"{excinfo.value!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — End-to-end runtime detects allowed_actions drift in context.mission
# ---------------------------------------------------------------------------


def test_runtime_boundary_detects_allowed_actions_drift(tmp_path) -> None:
    """**Validates: CP-2.1 (Memory Isolation) end-to-end.**

    Monkeypatch ``ContextBuilder.build`` so the returned ``AgentContext``
    carries a *mutated* envelope whose ``allowed_actions`` has been widened
    beyond the original envelope's ``allowed_actions``. Then call
    ``runtime.run`` and assert the run is blocked with an
    ``escalation_reason`` that identifies the Memory-not-Authority boundary.

    Implementation note: ``MissionAuthorityEnvelope`` is a pydantic model so
    we use ``model_copy(update=...)`` to produce the widened copy, and
    assign it via ``AgentContext.model_copy(update={"mission": ...})``
    because ``AgentContext`` holds a reference to the mission envelope.
    ``InvariantViolation`` raised from inside the main ``try:`` block is
    caught by the existing ``except Exception`` handler in ``run`` and
    converted to a ``final_phase=BLOCKED`` result routed through
    ``_apply_final_gate`` (F-A3.11).
    """
    runtime = AgentRuntime(project_root=tmp_path)
    envelope = _envelope()

    original_build = runtime.context_builder.build

    def _drifted_build(
        env: MissionAuthorityEnvelope,
        *,
        user_input: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
        memory_items: list[dict[str, Any]] | None = None,
    ) -> AgentContext:
        context = original_build(
            env,
            user_input=user_input,
            evidence_refs=evidence_refs,
            memory_items=memory_items,
        )
        # Adversarial: produce a mutated envelope that tries to add a
        # forbidden action. Pydantic models are not frozen here but we
        # avoid in-place mutation for clarity — ``model_copy`` is the
        # idiomatic way to construct a modified copy.
        mutated_envelope = env.model_copy(
            update={
                "allowed_actions": [*env.allowed_actions, "run_shell_command"],
            }
        )
        return context.model_copy(update={"mission": mutated_envelope})

    runtime.context_builder.build = _drifted_build  # type: ignore[method-assign]

    result = runtime.run(
        envelope,
        {"idea": "Allowed-actions drift attack"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    # The drift is caught at the first phase boundary that runs after
    # CONTEXT_BUILDING — i.e. context_building_to_orienting (T2).
    # Whichever boundary fires, the escalation_reason must carry a
    # recognizable boundary prefix.
    assert result.final_phase == AgentPhase.BLOCKED, (
        f"Expected BLOCKED, got {result.final_phase}; "
        f"escalation_reason={result.escalation_reason!r}"
    )
    assert result.escalation_reason is not None
    known_boundaries = {
        "context_building_to_orienting",
        "orienting_to_method_selecting",
        "method_selecting_to_capability_selecting",
        "capability_selecting_to_tool_selecting",
        "tool_selecting_to_hypothesis_verifying",
        "hypothesis_verifying_to_action_scoring",
        "effort_routing_to_planning",
        "plan_reviewing_to_executing",
        "repairing_to_executing",
    }
    assert any(b in result.escalation_reason for b in known_boundaries), (
        "escalation_reason must identify which Memory-not-Authority "
        f"boundary caught the drift; got {result.escalation_reason!r}"
    )
    # Task 1 invariant: the returned result is terminally certified.
    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True


# ---------------------------------------------------------------------------
# Test 3 — Repair re-entry (T21) detects memory/authority drift
# ---------------------------------------------------------------------------


def test_repair_reentry_boundary_detects_memory_authority_drift(tmp_path) -> None:
    """**Validates: CP-2.1 (Memory Isolation) at the repair re-entry boundary.**

    Target: the T21 boundary (``repairing_to_executing``). The test forces
    the runtime into the REPAIR_ALLOWED branch (mirroring the repair-pressure
    fixture pattern from ``test_final_gate_terminality.py``) and then
    contaminates ``context.available_capabilities`` *inside* the first
    ``worker_coordinator.run_mission_worker`` invocation. The re-entry into
    EXECUTING then triggers the T21 boundary check, which must fire.

    We also set ``review_loop.review_worker_result`` to return a single
    ``critical`` finding on the first call, which keeps repair_pressure in
    the (0.25, 0.85) REPAIR_ALLOWED band (POWER mode gives
    ``max_repair_cycles=2`` so the budget bonus is present).

    Assertions:
        * result.final_phase == AgentPhase.BLOCKED
        * result.escalation_reason contains "repairing_to_executing"
        * earlier boundaries (T2..T5) did not catch it — the violation
          specifically fires at T21
        * result.final_gate_certification.accepted is True
    """
    runtime = AgentRuntime(project_root=tmp_path)
    envelope = _envelope()

    # --- 1. Force one critical review finding to drive REPAIR_ALLOWED ---
    original_review = runtime.review_loop.review_worker_result
    review_calls = {"n": 0}

    def _review_with_one_critical(worker_result):  # type: ignore[no-untyped-def]
        review_calls["n"] += 1
        # Consume the real review to preserve side-effects (none today,
        # but future-proof) and then override.
        original_review(worker_result)
        if review_calls["n"] == 1:
            return [
                ReviewFinding(
                    code="forced_repair_pressure",
                    severity="critical",
                    message="Force REPAIR_ALLOWED for T21 boundary test.",
                )
            ]
        return []

    runtime.review_loop.review_worker_result = _review_with_one_critical  # type: ignore[method-assign]

    # --- 2. Contaminate context.available_capabilities inside the first
    # worker invocation, AFTER the T5 boundary passes but BEFORE the
    # T21 re-entry check.
    original_worker = runtime.worker_coordinator.run_mission_worker
    worker_calls = {"n": 0}

    def _worker_that_leaks_capability(context, event_bus, *, plan=None):  # type: ignore[no-untyped-def]
        worker_calls["n"] += 1
        result = original_worker(context, event_bus, plan=plan)
        if worker_calls["n"] == 1:
            # In-place mutation of the ``available_capabilities`` list held
            # by the context object flowing through ``AgentRuntime.run``.
            # This simulates memory or a worker side-channel contaminating
            # the cognitive state with a capability outside the authority.
            context.available_capabilities.append(  # type: ignore[attr-defined]
                "run_shell_command_capability"
            )
        return result

    runtime.worker_coordinator.run_mission_worker = (  # type: ignore[method-assign]
        _worker_that_leaks_capability
    )

    result = runtime.run(
        envelope,
        {"idea": "T21 repair re-entry drift attack"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    # Behavior assertions.
    assert result.final_phase == AgentPhase.BLOCKED, (
        f"Expected BLOCKED at T21 after contamination; got "
        f"{result.final_phase}; escalation_reason="
        f"{result.escalation_reason!r}"
    )
    assert result.escalation_reason is not None
    assert "repairing_to_executing" in result.escalation_reason, (
        "T21 (repairing_to_executing) must be named in the escalation "
        f"reason; got {result.escalation_reason!r}. This proves the "
        "violation fired at the repair re-entry boundary, not earlier."
    )
    # Earlier boundaries must NOT claim this violation — if any of them had,
    # the worker would never have been called and ``worker_calls['n']``
    # would be 0.
    assert worker_calls["n"] >= 1, (
        "First mission worker must have executed (otherwise the drift was "
        "caught too early to prove T21 coverage)."
    )
    # Task 1 invariant: terminal certification is still accepted.
    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True


# ---------------------------------------------------------------------------
# Test 4 — Legacy call path (no envelope / no original_allowed_actions) works
# ---------------------------------------------------------------------------


def test_legacy_context_building_call_still_works() -> None:
    """Backward-compat path: ``assert_context_did_not_expand_authority``
    called with no ``envelope`` and no ``original_allowed_actions`` kwargs
    MUST still enforce the capability-derivation invariant.

    Part (a): clean context passes.
    Part (b): contaminated context fails via the legacy derivation check
    (no boundary_name prefix, since none was provided).
    """
    envelope = _envelope()

    # (a) Clean context — every available_capability derives from
    # envelope.allowed_actions.
    clean_context = _context_for(envelope)
    Supervisor().assert_context_did_not_expand_authority(clean_context)

    # (b) Contaminated context — available_capabilities carries a
    # capability not derivable from envelope.allowed_actions.
    tainted_caps = [
        *capabilities_from_actions(list(envelope.allowed_actions)),
        "run_shell_command_capability",
    ]
    tainted_context = _context_for(
        envelope,
        available_capabilities=tainted_caps,
    )
    with pytest.raises(InvariantViolation):
        Supervisor().assert_context_did_not_expand_authority(tainted_context)


# ---------------------------------------------------------------------------
# Test 5 — Hypothesis property over envelope mutations
# ---------------------------------------------------------------------------


_ALLOWED_ACTION_POOL = st.sampled_from(SAFE_ACTIONS)


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(
    original_allowed_actions=st.sets(
        _ALLOWED_ACTION_POOL, min_size=1, max_size=len(SAFE_ACTIONS)
    ),
    mutated_allowed_actions=st.sets(
        _ALLOWED_ACTION_POOL, min_size=1, max_size=len(SAFE_ACTIONS)
    ),
)
def test_memory_not_authority_property(
    original_allowed_actions: set[str],
    mutated_allowed_actions: set[str],
) -> None:
    """**Validates: CP-2.1 (Memory Isolation), CP-2.2 (No Hidden Policy).**

    Mutating the envelope's ``allowed_actions`` mid-run MUST be detected by
    ``Supervisor.assert_context_did_not_expand_authority`` whenever the
    mutated set is not a subset of the original set. When it IS a subset
    (authority being narrowed, never widened), the check MUST pass.

    Capabilities are pinned to those derived from
    ``original_allowed_actions`` so the only mutation under test is the
    envelope's action set.
    """
    original_list = sorted(original_allowed_actions)
    original_envelope = _envelope(allowed_actions=original_list)
    mutated_envelope = original_envelope.model_copy(
        update={"allowed_actions": sorted(mutated_allowed_actions)}
    )
    context = _context_for(
        mutated_envelope,
        available_capabilities=capabilities_from_actions(original_list),
    )

    def _call() -> None:
        Supervisor().assert_context_did_not_expand_authority(
            context,
            envelope=mutated_envelope,
            original_allowed_actions=tuple(original_list),
            boundary_name="property_boundary",
        )

    if mutated_allowed_actions.issubset(original_allowed_actions):
        # Subset: no expansion, invariant holds.
        _call()
    else:
        # Widening: the mutated envelope escaped the original authority.
        with pytest.raises(InvariantViolation) as excinfo:
            _call()
        assert "property_boundary" in str(excinfo.value), (
            "boundary_name must be prefixed to the violation message; got "
            f"{excinfo.value!r}"
        )
