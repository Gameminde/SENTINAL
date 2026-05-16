"""Task 1.5 / Requirement 1 (FinalGate Runtime Integration, finding F-A3.11).

Determinism tests for ``CoreFinalGate.evaluate``.

These tests enforce the correctness property:

    CP-1.2 (FinalGate Determinism):
        ∀ inputs: CoreFinalGate.evaluate(inputs) = CoreFinalGate.evaluate(inputs)

The same ``AgentRunResult`` — whether evaluated multiple times by the same
``CoreFinalGate`` instance or by multiple fresh instances — must always
produce structurally identical ``CoreFinalGateResult`` objects (comparing
every field via ``model_dump()``, including all nested ``CoreGateCheck``
entries and their ``details`` payloads).

If determinism fails here it would indicate:

- A check reads wall-clock time or a random source.
- A check depends on dict/set iteration order that is not canonicalised.
- A check has unreported mutable global state.

**Validates: Requirement 1 (CP-1.2 FinalGate Determinism)**
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings, strategies as st

from sentinel.agent import AgentRuntime, CoreFinalGate
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


# ---------------------------------------------------------------------------
# Envelope / run factories — mirror ``tests/test_final_gate_terminality.py``
# and ``tests/test_agent_core_final_gate.py`` so the fixture shape matches
# the canonical COMPLETED run used elsewhere in the suite.
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


def _envelope(**overrides: Any) -> MissionAuthorityEnvelope:
    data: dict[str, Any] = {
        "user_id": "user_001",
        "mission_type": MissionType.GTM,
        "mission_title": "Final gate determinism test",
        "mission_objective": "Exercise CoreFinalGate.evaluate idempotency.",
        "success_criteria": ["Trace exists", "Run completes"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": list(SAFE_ACTIONS),
        "forbidden_actions": [
            "send_email",
            "run_shell_command",
            "browser_submit_form",
            "credential_access",
        ],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def _completed_run(tmp_path: Path):
    """A normal terminal COMPLETED run, used as the shared input fixture.

    We deliberately reuse the SAME ``AgentRunResult`` across every evaluate()
    invocation — the purpose of determinism tests is to prove that calling
    ``evaluate`` repeatedly on a fixed input produces a fixed output.
    """
    return AgentRuntime(project_root=tmp_path).run(
        _envelope(),
        {"idea": "Sentinel SPINE determinism"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )


# ---------------------------------------------------------------------------
# Test 1: same instance, N=3 evaluations
# ---------------------------------------------------------------------------


def test_final_gate_evaluate_is_deterministic_same_instance(tmp_path):
    """Calling ``evaluate`` three times on the SAME ``CoreFinalGate``
    instance with the same ``AgentRunResult`` produces structurally equal
    verdicts.

    Structural equality is measured via ``model_dump()`` across the full
    nested tree (``accepted``, every ``CoreGateCheck`` in ``checks``, each
    check's ``name``, ``kind``, ``passed``, ``message``, and ``details``).
    """
    result = _completed_run(tmp_path)
    gate = CoreFinalGate()

    verdicts = [gate.evaluate(result) for _ in range(3)]

    baseline = verdicts[0].model_dump()
    for index, verdict in enumerate(verdicts[1:], start=1):
        assert verdict.model_dump() == baseline, (
            f"CoreFinalGate.evaluate returned a different verdict on call "
            f"{index + 1} from the same instance. Determinism is violated."
        )


# ---------------------------------------------------------------------------
# Test 2: three fresh instances, one shared input
# ---------------------------------------------------------------------------


def test_final_gate_evaluate_is_deterministic_across_instances(tmp_path):
    """Calling ``evaluate`` once on each of three FRESH ``CoreFinalGate``
    instances with the same ``AgentRunResult`` produces structurally equal
    verdicts.

    This rules out hidden instance-level mutable state that could diverge
    verdicts across independently-constructed gate objects.
    """
    result = _completed_run(tmp_path)

    verdicts = [CoreFinalGate().evaluate(result) for _ in range(3)]

    baseline = verdicts[0].model_dump()
    for index, verdict in enumerate(verdicts[1:], start=1):
        assert verdict.model_dump() == baseline, (
            f"CoreFinalGate.evaluate returned a different verdict from "
            f"instance {index + 1} (fresh construction). Determinism is "
            f"violated across instances."
        )


# ---------------------------------------------------------------------------
# Test 3: Hypothesis property — determinism across generated run contexts
# ---------------------------------------------------------------------------


_SAFE_TITLES = st.sampled_from(
    [
        "Determinism property mission A",
        "Determinism property mission B",
        "SPINE property-test determinism",
        "Final-gate determinism coverage",
    ]
)

_SAFE_MODES = st.sampled_from([MissionMode.SAFE, MissionMode.POWER])

_EVIDENCE_REFS = st.lists(
    st.sampled_from(["ev_direct", "ev_wtp", "ev_scope", "ev_001"]),
    min_size=0,
    max_size=3,
    unique=True,
)

_IDEAS = st.sampled_from(
    [
        "Sentinel SPINE",
        "Property-based final-gate determinism",
        "Small safe mission idea",
        "Determinism coverage mission",
    ]
)


@settings(
    max_examples=6,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(
    title=_SAFE_TITLES,
    mode=_SAFE_MODES,
    max_actions=st.integers(min_value=5, max_value=20),
    evidence_refs=_EVIDENCE_REFS,
    idea=_IDEAS,
)
def test_final_gate_determinism_property(
    tmp_path, title, mode, max_actions, evidence_refs, idea
):
    """**Validates: Requirement 1 (CP-1.2 FinalGate Determinism)**

    For any valid run context generated by the strategy, running
    ``AgentRuntime`` once to obtain an ``AgentRunResult`` and then
    evaluating that result with two FRESH ``CoreFinalGate`` instances
    must produce structurally identical verdicts (``model_dump()`` equal).
    """
    env = _envelope(
        mission_title=title,
        mode=mode,
        max_actions=max_actions,
    )

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {"idea": idea},
        evidence_refs=list(evidence_refs),
    )

    verdict_a = CoreFinalGate().evaluate(result)
    verdict_b = CoreFinalGate().evaluate(result)

    assert verdict_a.model_dump() == verdict_b.model_dump(), (
        "CoreFinalGate.evaluate produced different verdicts for two "
        "fresh instances evaluating the same run result. Determinism "
        "is violated."
    )


# ---------------------------------------------------------------------------
# Test 4: determinism also holds when ``allowed_project_root`` is passed
# ---------------------------------------------------------------------------


def test_final_gate_determinism_includes_allowed_project_root(tmp_path):
    """``evaluate(result, allowed_project_root=...)`` is deterministic.

    The additional ``_project_scope`` check appended when
    ``allowed_project_root`` is provided must itself be deterministic, and
    the combined verdict (now including that extra check) must match
    across repeated calls.
    """
    result = _completed_run(tmp_path)
    gate = CoreFinalGate()

    verdict_1 = gate.evaluate(result, allowed_project_root=tmp_path)
    verdict_2 = gate.evaluate(result, allowed_project_root=tmp_path)

    assert verdict_1.model_dump() == verdict_2.model_dump(), (
        "CoreFinalGate.evaluate is non-deterministic when "
        "allowed_project_root is supplied."
    )

    # Also verify across fresh instances to rule out instance-level state.
    verdict_3 = CoreFinalGate().evaluate(result, allowed_project_root=tmp_path)
    assert verdict_1.model_dump() == verdict_3.model_dump(), (
        "CoreFinalGate.evaluate is non-deterministic across fresh "
        "instances when allowed_project_root is supplied."
    )
