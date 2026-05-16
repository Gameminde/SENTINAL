"""Final-gate check registry.

Task 11 / Requirement 11 — CoreFinalGate Decomposition.

Splits the ~38 monolithic checks previously coded directly inside
:meth:`sentinel.agent.final_gate.CoreFinalGate.evaluate` into a registry of
:class:`FinalGateCheckModule` instances. The registry preserves:

* **Deterministic order** — modules are evaluated in registration order,
  and each module emits its checks in a fixed order.
* **Behavioral equivalence** — the default registry (core + browser) calls
  the same static check methods on :class:`CoreFinalGate` that the old
  monolithic ``evaluate`` method called, in the same order. No check is
  added, removed, or reordered.
* **Open-closed extension** — new organ-specific modules can be appended
  via :meth:`FinalGateRegistry.register` without modifying the core
  registry or :class:`CoreFinalGate`.

Task 5 (Browser Legacy Consolidation) will later replace
:class:`BrowserChecksModule` with an organ-side
``BrowserOrganFinalGate`` adapter. At that time, ``CoreChecksModule``
stays unchanged and this registry becomes the sole extension surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sentinel.agent.final_gate import CoreFinalGateResult, CoreGateCheck
    from sentinel.agent.models import AgentRunResult


@runtime_checkable
class FinalGateCheckModule(Protocol):
    """Protocol for a cohesive group of FinalGate checks.

    A module must expose:
      * ``name`` — a stable identifier (e.g. ``"core"``, ``"browser"``).
      * ``checks(result, allowed_project_root)`` — returns the ordered list
        of :class:`CoreGateCheck` results for this module's domain.

    Implementers SHOULD be stateless so that
    :meth:`CoreFinalGate.evaluate` remains deterministic (Task 1 / CP-1.2).
    """

    name: str

    def checks(
        self,
        result: "AgentRunResult",
        *,
        allowed_project_root: Path | None = None,
    ) -> list["CoreGateCheck"]:
        ...


class FinalGateRegistry:
    """Ordered container of :class:`FinalGateCheckModule` instances.

    Invariants:
      * modules are evaluated in registration order
      * ``register`` raises :class:`ValueError` on duplicate module names
      * ``evaluate_all`` concatenates every module's checks and builds a
        :class:`CoreFinalGateResult` with ``accepted = all(c.passed for c in checks)``
    """

    __slots__ = ("_modules",)

    def __init__(self, modules: list[FinalGateCheckModule] | None = None) -> None:
        self._modules: list[FinalGateCheckModule] = []
        for module in modules or []:
            self.register(module)

    def register(self, module: FinalGateCheckModule) -> "FinalGateRegistry":
        existing_names = {m.name for m in self._modules}
        if module.name in existing_names:
            raise ValueError(
                f"FinalGateRegistry already contains a module named {module.name!r}."
            )
        self._modules.append(module)
        return self

    @property
    def modules(self) -> tuple[FinalGateCheckModule, ...]:
        return tuple(self._modules)

    def evaluate_all(
        self,
        result: "AgentRunResult",
        *,
        allowed_project_root: Path | None = None,
    ) -> "CoreFinalGateResult":
        # Local import to avoid a circular import at module-load time —
        # ``final_gate.py`` imports this module to wire the default
        # registry.
        from sentinel.agent.final_gate import CoreFinalGateResult

        checks: list = []
        for module in self._modules:
            checks.extend(module.checks(result, allowed_project_root=allowed_project_root))
        return CoreFinalGateResult(
            accepted=all(check.passed for check in checks),
            checks=checks,
        )


# ---------------------------------------------------------------------------
# CoreChecksModule — cross-organ checks that remain in the core gate.
# ---------------------------------------------------------------------------


class CoreChecksModule:
    """The 25 cross-organ checks that are intrinsic to :class:`CoreFinalGate`.

    These checks observe properties that span multiple organs or apply to
    the cognitive runtime itself (trace integrity, budget, posture,
    receipt agreement, authority-expansion, mission-archive consistency,
    LLM P3Y context-pack, artifact paths, and the optional project-scope
    check when ``allowed_project_root`` is provided).

    The actual check logic lives in static methods on
    :class:`CoreFinalGate`. This module delegates to them in the exact
    order used by the pre-Task-11 monolithic ``evaluate`` so behavior
    equivalence is guaranteed by construction.
    """

    name = "core"

    def checks(
        self,
        result: "AgentRunResult",
        *,
        allowed_project_root: Path | None = None,
    ) -> list["CoreGateCheck"]:
        from sentinel.agent.final_gate import CoreFinalGate as _Gate

        # ``_success_event_contract`` and ``_success_evidence_contract``
        # are instance methods that read class-level constants
        # (``SUCCESS_REQUIRED_EVENTS``/``SUCCESS_REQUIRED_EVIDENCE``).
        # ``_evidence_chains_trace_bound`` is a classmethod-style helper
        # (``@staticmethod``). Instantiate a gate once per call so the
        # instance methods resolve correctly.
        _gate_instance = _Gate()

        checks: list = [
            _Gate._trace_present(result),
            _Gate._trace_mission_consistency(result),
            _Gate._runtime_certification(result),
            _Gate._state_replay(result),
            _Gate._phase_contract(result),
            _Gate._tool_policy_decisions_trace_bound(result),
            _Gate._selected_tools_are_policy_eligible(result),
            _Gate._non_selected_tools_stay_out(result),
            _Gate._learning_is_human_approved(result),
            _Gate._mission_trace_integrity(result),
            _Gate._mission_result_consistency(result),
            _Gate._mission_results_archive(result),
            _Gate._global_action_budget(result),
            _Gate._active_plan_matches_mission_trace(result),
            _Gate._evidence_chains_trace_bound(result),
            _gate_instance._success_event_contract(result),
            _gate_instance._success_evidence_contract(result),
            _Gate._success_artifact_contract(result),
            _Gate._artifact_paths_are_relative(result),
            _Gate._execution_posture_matches_authority(result),
            _Gate._mission_risk_route_decisions(result),
            _Gate._controlled_capability_receipts(result),
            _Gate._llm_context_pack_and_tool_intent_contract(result),
            _Gate._mission_artifact_receipts(result),
        ]
        # NOTE: the project-scope check is emitted by
        # ``_ProjectScopeTailModule`` AFTER the browser module, not here,
        # to preserve the pre-Task-11 end-of-list ordering.
        return checks


# ---------------------------------------------------------------------------
# BrowserChecksModule — 14 browser-specific checks.
#
# Task 5 (Browser Legacy Consolidation) will later replace this with an
# organ-side ``BrowserOrganFinalGate`` adapter. For Task 11 we just route
# the checks through a module so the core gate no longer embeds them.
# ---------------------------------------------------------------------------


class BrowserChecksModule:
    name = "browser"

    def checks(
        self,
        result: "AgentRunResult",
        *,
        allowed_project_root: Path | None = None,
    ) -> list["CoreGateCheck"]:
        from sentinel.agent.final_gate import CoreFinalGate as _Gate

        return [
            _Gate._browser_capability_receipts(result),
            _Gate._browser_interaction_dry_run_contract(result),
            _Gate._browser_interaction_execution_contract(result),
            _Gate._browser_public_lifecycle_contract(result),
            _Gate._browser_reliability_supervisor_contract(result),
            _Gate._browser_v25_observation_and_operator_contract(result),
            _Gate._browser_v3_form_submit_contract(result),
            _Gate._browser_v3_download_quarantine_contract(result),
            _Gate._browser_v3_upload_authorized_contract(result),
            _Gate._browser_v3_private_session_contract(result),
            _Gate._browser_v3_login_authority_contract(result),
            _Gate._browser_v3_cookie_storage_contract(result),
            _Gate._browser_v3_js_evaluate_sandboxed_contract(result),
            _Gate._browser_v3_har_body_capture_contract(result),
        ]


def default_registry() -> FinalGateRegistry:
    """Default registry — core module first, then browser module.

    Matches the pre-Task-11 check order: 24 core checks, then 14 browser
    checks, then the conditional ``_project_scope`` check (emitted
    within ``CoreChecksModule`` when ``allowed_project_root`` is
    provided). Changing this function's output would change
    :meth:`CoreFinalGate.evaluate` behavior, so keep it stable.

    Task 5.2-C2 (Browser Legacy Consolidation, Wave C default-registry
    substitution pilot). The browser module slot now holds
    :class:`sentinel.organs.browser.final_gate.BrowserOrganChecksModule`
    — the organ-side module produced in Task 5.2-C. The legacy
    :class:`BrowserChecksModule` remains defined above for reference and
    parity tests; it is no longer the production module.

    ``BrowserOrganChecksModule`` is imported lazily inside this function
    to avoid any chance of circular import at module-load time between
    ``sentinel.agent.final_gate_registry`` and the organ-side module
    (which already delegates to ``CoreFinalGate`` static methods).

    Note on ordering: the old monolithic ``evaluate`` appended the
    project-scope check AT THE END (after all browser checks). We
    preserve that by keeping the project-scope check inside
    ``CoreChecksModule`` but the default registry below registers
    modules as ``[core, browser]``, which means ``_project_scope`` is
    emitted within the core module (before browser). To preserve
    equivalence with the pre-Task-11 end-of-list ordering, we re-order:
    ``core-no-scope`` → ``browser`` → ``core-scope-tail``.

    We accomplish this with two module instances — ``CoreChecksModule``
    emits everything EXCEPT ``_project_scope``, and a tiny trailing
    module (``_ProjectScopeTailModule``) emits only the conditional
    project-scope check. Both are stateless. This keeps module
    boundaries clean while preserving the exact pre-Task-11 ordering.
    """
    # Lazy import: guards against any future circular-import regression
    # even though the current organ-side module only imports
    # ``sentinel.agent.final_gate`` lazily inside its ``checks()`` body.
    from sentinel.organs.browser.final_gate import BrowserOrganChecksModule

    return FinalGateRegistry(
        modules=[
            CoreChecksModule(),  # 24 core checks (project-scope NOT included here)
            BrowserOrganChecksModule(),  # 14 browser checks (organ-side owner)
            _ProjectScopeTailModule(),  # conditional project-scope check at the end
        ]
    )


# ---------------------------------------------------------------------------
# Internal: the project-scope check used to sit at the very end of the
# check list (after all browser checks). We carve it out of
# ``CoreChecksModule`` above and move it into a tiny trailing module so
# the default registry output is bit-exact with the pre-Task-11
# monolithic ``evaluate``.
# ---------------------------------------------------------------------------


class _ProjectScopeTailModule:
    name = "project_scope_tail"

    def checks(
        self,
        result: "AgentRunResult",
        *,
        allowed_project_root: Path | None = None,
    ) -> list["CoreGateCheck"]:
        if allowed_project_root is None:
            return []
        from sentinel.agent.final_gate import CoreFinalGate as _Gate

        return [
            _Gate._project_scope(result, Path(allowed_project_root).resolve())
        ]


__all__ = [
    "BrowserChecksModule",
    "CoreChecksModule",
    "FinalGateCheckModule",
    "FinalGateRegistry",
    "default_registry",
]
