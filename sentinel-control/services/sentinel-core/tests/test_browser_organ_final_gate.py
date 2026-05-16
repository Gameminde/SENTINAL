"""Task 5.2-C parity tests for the organ-side browser FinalGate module.

Validates that :class:`sentinel.organs.browser.final_gate.BrowserOrganChecksModule`
emits the same 14 browser FinalGate checks as the legacy
:class:`sentinel.agent.final_gate_registry.BrowserChecksModule`, in the same
order, with byte-equivalent payloads. Also enforces the organ-layering
contract (no ``sentinel.agent.browser.*`` imports from the new module).

Task 5.2-C does NOT change the default registry — the legacy
``BrowserChecksModule`` is still the one registered by ``default_registry()``.
This test proves the organ-side alternative is a drop-in replacement so
that a future wave can swap ownership without regressing behavior.
"""

from __future__ import annotations

import ast
import pathlib
from typing import Any

import pytest

from sentinel.agent import AgentRuntime, CoreFinalGate
from sentinel.agent.final_gate_registry import (
    BrowserChecksModule,
    CoreChecksModule,
    FinalGateRegistry,
    _ProjectScopeTailModule,
)
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs.browser.final_gate import (
    BrowserOrganChecksModule,
    BrowserOrganFinalGate,
)
from sentinel.shared.enums import MissionMode, MissionType


_ORGAN_FINAL_GATE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "sentinel"
    / "organs"
    / "browser"
    / "final_gate.py"
)


_SAFE_ACTIONS = [
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
        "user_id": "user_browser_parity",
        "mission_type": MissionType.GTM,
        "mission_title": "Browser organ final-gate parity test",
        "mission_objective": "Prove BrowserOrganChecksModule parity.",
        "success_criteria": ["Trace exists", "Run completes"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": list(_SAFE_ACTIONS),
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


def _run(tmp_path: pathlib.Path):
    return AgentRuntime(project_root=tmp_path).run(
        _envelope(),
        {"idea": "Browser organ final-gate parity"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )


# ---------------------------------------------------------------------------
# 1. Same 14 check names.
# ---------------------------------------------------------------------------


_EXPECTED_BROWSER_CHECK_NAMES = [
    "browser_capability_receipts",
    "browser_interaction_dry_run_contract",
    "browser_interaction_execution_contract",
    "browser_public_lifecycle_contract",
    "browser_reliability_supervisor_contract",
    "browser_v25_observation_and_operator_contract",
    "browser_v3_form_submit_contract",
    "browser_v3_download_quarantine_contract",
    "browser_v3_upload_authorized_contract",
    "browser_v3_private_session_contract",
    "browser_v3_login_authority_contract",
    "browser_v3_cookie_storage_contract",
    "browser_v3_js_evaluate_sandboxed_contract",
    "browser_v3_har_body_capture_contract",
]


def test_browser_organ_final_gate_emits_same_14_check_names_as_browser_checks_module(tmp_path):
    result = _run(tmp_path)
    legacy = BrowserChecksModule().checks(result)
    organ = BrowserOrganChecksModule().checks(result)

    legacy_names = [c.name for c in legacy]
    organ_names = [c.name for c in organ]

    assert len(organ_names) == 14
    assert organ_names == _EXPECTED_BROWSER_CHECK_NAMES
    assert organ_names == legacy_names


# ---------------------------------------------------------------------------
# 2. Same check order (already covered by test 1 equality, but explicit).
# ---------------------------------------------------------------------------


def test_browser_organ_final_gate_order_matches_browser_checks_module(tmp_path):
    result = _run(tmp_path)
    legacy_order = [c.name for c in BrowserChecksModule().checks(result)]
    organ_order = [c.name for c in BrowserOrganChecksModule().checks(result)]
    assert legacy_order == organ_order


# ---------------------------------------------------------------------------
# 3. Byte-equivalent verdicts (full ``model_dump`` equality per-check).
# ---------------------------------------------------------------------------


def test_browser_organ_final_gate_verdicts_match_existing_browser_checks_module(tmp_path):
    result = _run(tmp_path)
    legacy = [c.model_dump() for c in BrowserChecksModule().checks(result)]
    organ = [c.model_dump() for c in BrowserOrganChecksModule().checks(result)]
    assert organ == legacy
    # Sanity: each check has the full CoreGateCheck payload.
    for check in organ:
        assert set(check.keys()) >= {"name", "kind", "passed", "message", "details"}
        assert isinstance(check["passed"], bool)


# ---------------------------------------------------------------------------
# 4. Organ-layering: no ``sentinel.agent.browser.*`` imports.
# ---------------------------------------------------------------------------


def test_browser_organ_final_gate_uses_no_agent_browser_imports():
    """AST-scan: the new module must NOT import from
    ``sentinel.agent.browser.*``. Importing sibling types from
    ``sentinel.agent.final_gate`` (``CoreGateCheck``, ``CoreGateCheckKind``)
    is allowed — they are shared pydantic result types, not part of
    ``CoreFinalGate``'s private surface.
    """
    source = _ORGAN_FINAL_GATE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_ORGAN_FINAL_GATE_PATH))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.startswith("sentinel.agent.browser"):
                offenders.append(
                    f"line {node.lineno}: from {node.module} import ..."
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("sentinel.agent.browser"):
                    offenders.append(
                        f"line {node.lineno}: import {alias.name}"
                    )
    assert offenders == [], (
        "sentinel.organs.browser.final_gate must not import from "
        "sentinel.agent.browser.*. Offending imports:\n"
        + "\n".join(f"  {x}" for x in offenders)
    )


def test_browser_organ_final_gate_does_not_import_core_final_gate():
    """Task 5.2-C3: after Wave C3 inlines the check bodies, the organ
    module must NOT import the :class:`CoreFinalGate` class (either at
    top level or via lazy local imports inside function bodies). Sibling
    types ``CoreGateCheck`` and ``CoreGateCheckKind`` from
    ``sentinel.agent.final_gate`` ARE allowed (they are the shared
    pydantic result types every FinalGate module emits).

    Enforcement:
      * AST walk: for every ``from sentinel.agent.final_gate import ...``
        and every ``import sentinel.agent.final_gate ...`` node (whether
        top-level or nested inside a function), assert ``CoreFinalGate``
        is NOT among the imported names or aliases.
      * Also confirm the substring ``CoreFinalGate`` does not appear
        anywhere in the module source as a dotted reference
        (``agent.final_gate.CoreFinalGate`` or ``_Gate =``-style
        aliasing).
    """
    source = _ORGAN_FINAL_GATE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_ORGAN_FINAL_GATE_PATH))

    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "sentinel.agent.final_gate":
                for alias in node.names:
                    if alias.name == "CoreFinalGate":
                        offenders.append(
                            f"line {node.lineno}: from sentinel.agent.final_gate "
                            f"import CoreFinalGate"
                        )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sentinel.agent.final_gate.CoreFinalGate":
                    offenders.append(
                        f"line {node.lineno}: import {alias.name}"
                    )
        elif isinstance(node, ast.Attribute):
            # Catch attribute access like ``sentinel.agent.final_gate.CoreFinalGate``
            # or ``final_gate.CoreFinalGate`` even when the base module is imported.
            if node.attr == "CoreFinalGate":
                offenders.append(
                    f"line {node.lineno}: attribute access ...CoreFinalGate"
                )
        elif isinstance(node, ast.Name):
            # Bare references to the name ``CoreFinalGate`` in code (e.g. an
            # alias assignment ``_Gate = CoreFinalGate``) — only flag if it's
            # being loaded, not if it's a string/docstring (walk doesn't hit
            # those).
            if node.id == "CoreFinalGate":
                offenders.append(
                    f"line {node.lineno}: bare reference to CoreFinalGate"
                )

    assert offenders == [], (
        "sentinel.organs.browser.final_gate must not import "
        "CoreFinalGate (the class). Offenders:\n"
        + "\n".join(f"  {x}" for x in offenders)
    )


# ---------------------------------------------------------------------------
# 5. Registry substitution: swap BrowserChecksModule → BrowserOrganChecksModule
#    and prove the resulting ``CoreFinalGate`` verdict is byte-equivalent.
# ---------------------------------------------------------------------------


def test_core_final_gate_can_register_browser_organ_module_without_behavior_change(tmp_path):
    """Build an alternate :class:`FinalGateRegistry` that registers the
    organ-side browser module in place of the legacy one, and confirm
    ``CoreFinalGate`` emits a byte-equivalent verdict.

    **Post Task 5.2-C2:** the default registry ALREADY uses
    ``BrowserOrganChecksModule`` under the hood (swapped in by
    ``default_registry()``). This test remains valuable as an explicit
    proof of the drop-in equivalence — it constructs an alt registry
    that also uses the organ module and compares its verdict to the
    default. Both should agree because they use the same module.
    """
    result = _run(tmp_path)

    default_verdict = CoreFinalGate().evaluate(
        result, allowed_project_root=str(tmp_path)
    )

    alt_registry = FinalGateRegistry(
        modules=[
            CoreChecksModule(),
            BrowserOrganChecksModule(),
            _ProjectScopeTailModule(),
        ]
    )
    alt_verdict = CoreFinalGate(registry=alt_registry).evaluate(
        result, allowed_project_root=str(tmp_path)
    )

    assert alt_verdict.model_dump() == default_verdict.model_dump()
    assert alt_verdict.accepted is True
    assert [c.name for c in alt_verdict.checks] == [
        c.name for c in default_verdict.checks
    ]


# ---------------------------------------------------------------------------
# Bonus — confirm both exported identifiers refer to the same class.
# ---------------------------------------------------------------------------


def test_browser_organ_final_gate_aliases_point_to_same_class():
    assert BrowserOrganFinalGate is BrowserOrganChecksModule


# ---------------------------------------------------------------------------
# Bonus — module name is ``browser_organ`` (distinct from the legacy
# ``browser``) so the two can coexist in a registry during parity.
# ---------------------------------------------------------------------------


def test_browser_organ_module_has_distinct_registry_name():
    assert BrowserOrganChecksModule.name == "browser_organ"
    assert BrowserChecksModule.name == "browser"
    assert BrowserOrganChecksModule.name != BrowserChecksModule.name


# ---------------------------------------------------------------------------
# Bonus — registering both the legacy and organ modules in the same
# registry is permitted (they have distinct names) and yields the union
# of their checks. This is NOT how production will use them, but confirms
# the registry's duplicate-name guard doesn't reject the organ variant.
# ---------------------------------------------------------------------------


def test_registry_accepts_both_browser_modules_side_by_side(tmp_path):
    result = _run(tmp_path)
    registry = FinalGateRegistry(
        modules=[
            CoreChecksModule(),
            BrowserChecksModule(),
            BrowserOrganChecksModule(),
            _ProjectScopeTailModule(),
        ]
    )
    verdict = CoreFinalGate(registry=registry).evaluate(
        result, allowed_project_root=str(tmp_path)
    )
    # Each browser check appears twice in the concatenated list.
    browser_check_name_counts: dict[str, int] = {}
    for check in verdict.checks:
        if check.name in _EXPECTED_BROWSER_CHECK_NAMES:
            browser_check_name_counts[check.name] = (
                browser_check_name_counts.get(check.name, 0) + 1
            )
    for name in _EXPECTED_BROWSER_CHECK_NAMES:
        assert browser_check_name_counts.get(name) == 2, (
            f"Expected 2 occurrences of {name} when both browser modules "
            f"are registered; got {browser_check_name_counts.get(name)}."
        )


# ---------------------------------------------------------------------------
# Task 5.2-C2 — default registry substitution pilot.
#
# The default registry produced by ``default_registry()`` now registers
# ``BrowserOrganChecksModule`` (name=``browser_organ``) in place of the
# legacy ``BrowserChecksModule`` (name=``browser``). These tests pin the
# substitution and guard the circular-import contract.
# ---------------------------------------------------------------------------


def test_default_registry_uses_browser_organ_module():
    """Task 5.2-C2: the default registry module list contains the
    organ-side ``BrowserOrganChecksModule``.
    """
    from sentinel.agent.final_gate_registry import default_registry

    registry = default_registry()
    module_names = [module.name for module in registry.modules]
    assert "browser_organ" in module_names
    # The organ module occupies slot index 1 — the "browser" slot.
    assert module_names == ["core", "browser_organ", "project_scope_tail"]
    browser_slot = registry.modules[1]
    assert isinstance(browser_slot, BrowserOrganChecksModule)


def test_default_registry_no_longer_uses_browser_checks_module():
    """Task 5.2-C2: the legacy ``BrowserChecksModule`` (name=``browser``) is
    no longer in the default registry module list. It remains importable
    and usable for parity/reference, but production no longer registers it.
    """
    from sentinel.agent.final_gate_registry import default_registry

    registry = default_registry()
    assert "browser" not in [module.name for module in registry.modules]


def test_core_final_gate_default_registry_still_emits_same_39_checks(tmp_path):
    """Task 5.2-C2: ``CoreFinalGate().evaluate(...)`` with the new default
    registry still produces the exact 39-check verdict the monolithic gate
    produced before Task 11: 24 core + 14 browser + 1 project_scope.

    Check ordering and names are identical to the pre-substitution default
    registry (proved bit-exact by the Task 11 equivalence suite).
    """
    result = _run(tmp_path)
    verdict = CoreFinalGate().evaluate(result, allowed_project_root=str(tmp_path))

    assert verdict.accepted is True
    names = [c.name for c in verdict.checks]
    assert len(names) == 39

    # Browser checks (14) appear in the expected slot between core and project_scope.
    core_names = [c.name for c in CoreChecksModule().checks(result)]
    assert names[: len(core_names)] == core_names
    assert names[len(core_names) : len(core_names) + 14] == _EXPECTED_BROWSER_CHECK_NAMES
    assert names[-1] == "project_scope"


def test_fresh_process_import_core_final_gate_no_circular_import():
    """Task 5.2-C2: ``CoreFinalGate`` imports cleanly in a brand-new Python
    process. Guards against any circular-import regression introduced by
    ``default_registry()`` referencing ``sentinel.organs.browser.final_gate``.

    Uses a subprocess so module caches from other tests do not mask a real
    cycle.
    """
    import subprocess
    import sys

    script = (
        "from sentinel.agent.final_gate import CoreFinalGate; "
        "gate = CoreFinalGate(); "
        "print(gate.__class__.__name__)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"Fresh-process CoreFinalGate import failed.\n"
        f"stdout: {completed.stdout!r}\n"
        f"stderr: {completed.stderr!r}"
    )
    assert "CoreFinalGate" in completed.stdout


def test_browser_checks_module_remains_available_for_reference():
    """Task 5.2-C2: the legacy ``BrowserChecksModule`` remains importable
    (for parity tests) even though the default registry no longer uses it.
    It must still produce the same 14 checks as the organ module.
    """
    from sentinel.agent.final_gate_registry import BrowserChecksModule as _Legacy

    assert _Legacy.name == "browser"
    legacy = _Legacy()
    organ = BrowserOrganChecksModule()
    # Both modules are still usable alongside the default registry.
    # Parity covered by test_browser_organ_final_gate_verdicts_match_existing_browser_checks_module.
    assert legacy.name != organ.name
    assert legacy.name == "browser"
    assert organ.name == "browser_organ"
