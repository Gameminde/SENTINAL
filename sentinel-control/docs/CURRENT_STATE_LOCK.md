# Current State Lock

## Performance Runtime Foundation Closure - Phase A-F

Recorded at: 2026-05-16 16:45:28 +02:00

Branch: `main`

HEAD: `eddaecb` (`eddaecbb36a202fff18db12f40e41186d097eec3`)

Commit status: local `main` is ahead of `origin/main` by 1 commit.
`origin/main` currently points to `daa4625`
(`daa4625d93736523dcdc93afd3850aafedff6a35`).

Baseline A-E commit:

```text
7aaecb1 - baseline: lock performance runtime foundation phases A-E
```

Phase F commit:

```text
eddaecb - perf: add benchmark regression gates foundation
```

Current phase state:

```text
Phase A = LOCKED
Phase B = STRUCTURAL LOCK / PERFORMANCE CAVEATS
Phase C = STRUCTURAL LOCK / PARTIAL RUNTIME ADOPTION
Phase D = LOCKED
Phase E = LOCKED
Phase F = STRUCTURAL LOCK
```

Why Phase F is structural:

Phase F locked the benchmark/regression gate foundation:
`GoldenMission` definitions, `BenchmarkHarness.run`, gate evaluation,
Property 14 coverage, hot-path coverage registry, and the minimal
`CoreFinalGate.verify_performance_receipts(...)` helper. It is not a
production benchmark proof yet because real golden mission runners and CI
integration remain open.

Open backlog remains:

```text
P-B-PERF-01
P-B-PERF-02
P-C-RUNTIME-01
P-C-KEY-01
P-D-RUNTIME-01
P-D-BATCH-01
P-D-BROWSER-01
P-F-RUNNER-01
P-F-CI-01
```

Explicit closure statements:

```text
No new phase started.
Brain/Science research not started.
Consensus.ai research not started.
```

Date: 2026-05-10

## Sentinel Full System Audit — Decision Records

### Task 10 / F-A3.1 — InvariantChecker.check_authority

Decision: **Removed as live safety code; retained only as an
error-directed tombstone stub** that raises `NotImplementedError`.

The method name `InvariantChecker.check_authority` still exists in
`sentinel/agent/invariants.py` so any legacy caller fails loudly with
a diagnostic pointing at the canonical chokepoints. It does NOT
perform an authority check. The method was not physically deleted —
a future hard delete is acceptable once all external/integration
callers are migrated, but the tombstone is the current state.

Rationale:

* `InvariantChecker.check_authority` had zero production call sites.
  It duplicated the two-line check already performed by
  `sentinel.mission.scope_checker.MissionScopeChecker.is_in_scope`
  (invoked on every routed action by
  `sentinel.mission.risk.RiskRouter.route` → `AutonomyEngine.decide`).
* The router enforces a strictly stronger set of rules than
  `check_authority` did: forbidden-action matching,
  `BLACK_ZONE_ACTIONS` terms, path scope, revocation, expiry, budget,
  posture thresholds. Any action that passed `check_authority` but
  should have been blocked by these extra rules would have created a
  false sense of safety.
* Organ-scoped authority is enforced by
  `sentinel.organs.authority.OrganAuthorityEvaluator`.
* Memory-drift-based authority expansion is enforced by
  `InvariantChecker.check_memory_not_authority` +
  `check_capabilities_derive_from_authority` at nine cognitive phase
  boundaries (Task 2 / Requirement 2).
* Wiring `check_authority` as a belt-and-braces check before
  `AutonomyEngine.decide` would have duplicated the router's check
  one function-call earlier, using the live (possibly-mutated)
  envelope rather than `original_allowed_actions`, making it both
  redundant and weaker.

Canonical authority-enforcement chokepoints (post-tombstone):

1. `sentinel.mission.risk.RiskRouter.route` via
   `sentinel.mission.scope_checker.MissionScopeChecker.is_in_scope`
   (mission-level, always-on, every action).
2. `sentinel.organs.authority.OrganAuthorityEvaluator` (organ-level,
   for organ adapters).
3. `sentinel.agent.invariants.InvariantChecker.check_memory_not_authority`
   and `.check_capabilities_derive_from_authority` — the
   Memory-not-Authority drift check, run at every cognitive phase
   boundary against `original_allowed_actions` captured at run entry
   (Task 2).

Tombstone behavior:

* Calling `InvariantChecker().check_authority(envelope, action)`
  raises `NotImplementedError` with a message naming `RiskRouter`,
  `MissionScopeChecker`, and `OrganAuthorityEvaluator`.
* Zero production call sites exist (AST-verified by
  `test_check_authority_method_removed_and_no_production_call_sites_exist`).

Tests locking this decision live in
`tests/test_agent_invariants.py`:
`test_check_authority_decision_documented`,
`test_no_dead_safety_code_in_invariants`,
`test_check_authority_method_removed_and_no_production_call_sites_exist`,
`test_router_enforces_action_in_authority_as_canonical_chokepoint`.

### Audit Status Lock — post Task 6.5-A

Snapshot date: 2026-05-13

This section is the canonical audit status after Task 6.5-A landed.
It supersedes any earlier status report. Scope: the
`sentinel-full-system-audit` spec at
`.kiro/specs/sentinel-full-system-audit/`.

#### P0 — Pre-P6U Blockers: COMPLETE

| Task | Title | Outcome |
|------|-------|---------|
| 1 | FinalGate Runtime Integration | `CoreFinalGate.evaluate` now runs on every `AgentRuntime.run` exit path. `AgentRunResult.final_gate_certification` always carries an accepted certification; rejected intended results downgrade to BLOCKED and re-certify. `AgentBlockedError` if BLOCKED re-cert fails. |
| 2 | Memory-not-Authority Multi-Phase | Invariant re-invoked at 9 phase boundaries against `original_allowed_actions` captured at run entry. Supervisor validates both envelope and `context.mission.allowed_actions` drift. |
| 3 | Dry-Run ↔ Execution Crypto Binding | `OrganDryRunReceipt.action_payload_hash` auto-computed from `{action, preview}`. `OrganExecutionReceipt.started()` requires `execution_action_payload` kwarg and raises `ReceiptIntegrityError` on mismatch. TOCTOU window closed. |
| 4 | Reactive Kill-Switch | `MissionRunner._check_revocation` polls `envelope.revoked_at` and `CancellationToken.is_cancelled` before each plan step. `MissionKillSwitch.revoke` stamps `revoked_at` AND cancels the token. New `MissionStatus.REVOKED` terminal state. |
| 7 | Per-Append Trace Hash | `EventBus.append` now calls full O(n) chain re-verification BEFORE linking each new event. `TraceIntegrityError` raised immediately on any prior-event tampering. |

#### P1 / P2 — Structural Integrity and Hardening: COMPLETE

| Task | Title | Outcome |
|------|-------|---------|
| 13 | EventBus Primitives → Shared Layer | `AgentEventType`, `AgentPhase`, `AgentEvent`, `TraceIntegrityError`, `EventBus` moved to `sentinel/shared/events.py`. Agent-layer modules are re-export shims. Organs import directly from `sentinel.shared.events`. |
| 11 | CoreFinalGate Registry Decomposition | `FinalGateRegistry` + `FinalGateCheckModule` protocol. `CoreChecksModule` (24), `BrowserChecksModule` / `BrowserOrganChecksModule` (14), `_ProjectScopeTailModule` (1). Default registry uses `BrowserOrganChecksModule`. |
| 15 | Phase Self-Transition Guard | `can_transition` rejects absorbing→same-absorbing. `AgentState.transition` raises `InvalidPhaseTransition` (subclass of `ValueError` for backward compat). No production path attempts absorbing self-transition. |
| 14 | ImprovementProposal Approval Token | `approved_by_human_id: str \| None` + `@model_validator` rejects `status="approved"` without a non-empty token. Belt-and-braces `InvariantChecker.check_improvement_proposals` for reconstituted proposals. |
| 12 | Structured BrowserOperatorRouteRejected | Replaces `ValueError(f"browser_operator_route_rejected:{reason}")` with a structured exception carrying `reason`, `context`, `original_exception`. Subclasses `ValueError` for legacy `except ValueError` compat. Stack trace preserved via `raise ... from`. |
| 8 | DecisionFrameVerifier Mandatory Params | `required_evidence_refs` and `known_receipt_ids` are keyword-only and required (no defaults; explicit `None` also rejected). Silent-skip eliminated. |
| 9 + 9-A | Sanitizer Property Tests + Safety Sanity | `SECRET_PATTERNS` expanded from 2 to 13 with OpenAI/Stripe/AWS/GitHub/Google/Slack/JWT/PEM/DB-URL/Bearer/Authorization coverage. Trailing-boundary bug on `-`-ending tokens fixed (lookaround anchors). Performance bounded (<2s/1MB benign). 22 false-positive tests prove non-over-redaction. Canonical sanitizer documented; sibling domain sanitizers left untouched. |
| 10 | `check_authority` Tombstone | See the Task 10 / F-A3.1 decision record above. Live body replaced with `NotImplementedError` stub; zero production call sites; canonical chokepoints documented. |
| 6 | GateSequence + 6.5-A Runtime Wiring | `GateSequence` enforces SPINE_01 §5 seven-gate ordering with short-circuit on any non-PASS verdict. `RiskRouter.route_via_sequence` adapter runs the sequence then delegates to legacy `route()`; `AutonomyEngine.decide` routes through the adapter by default. `RISK_ROUTE_DECIDED` payload preserved byte-for-byte. `GateSequenceRoutingError` fires on sequence/router verdict drift. |

#### Task 5 — Browser Legacy Surface Consolidation: STRUCTURAL LOCK

See the dedicated "Task 5 / Wave D Structural Lock" section below for
the full lock record. Summary: all 17 browser execution files are
organ-side; agent-side paths are shims; production FinalGate uses
`BrowserOrganChecksModule`; receipt runtime adoption deferred to
post-audit backlog.

**Completed sub-tasks** (incremental waves, each reviewed before
proceeding):

* `5.1` Inventory — 39 files catalogued across authority / execution /
  receipt / utility / test-only categories with migration plan.
* `5.2-A` Utilities migrated to `sentinel/organs/browser/` with shims:
  `pdf`, `screenshot`, `observability`, `cdp_ax`, `dom_snapshot`,
  `ui_observation`, `visual_observation`, `accessibility_snapshot`,
  `extraction`, `url_guard`.
* `5.2-B1` `models.py` migrated with shim.
* `5.2-B2` `v3_authority.py` migrated with shim.
* `5.2-B3` `interaction_dry_run.py` migrated with shim.
* `5.3` `BrowserOrganChecksModule` (name `"browser_organ"`) owns the 14
  browser FinalGate checks in `sentinel/organs/browser/final_gate.py`
  with zero `CoreFinalGate` delegation and zero
  `sentinel.agent.browser.*` imports. Byte-equivalence with the
  legacy `BrowserChecksModule` preserved.
* `5.4` Default `FinalGateRegistry` registers
  `BrowserOrganChecksModule`; `CoreFinalGate` still emits the same
  39-check result from a fresh process.

**Wave D completed.** All 17 executor/adapter/orchestrator files
migrated to `sentinel/organs/browser/`. See the "Task 5 / Wave D
Structural Lock" section below for the full lock record.

#### Last verified test summaries — from Wave D final run

```
D2 checkpoint: 81 passed
D3 checkpoint: 81 passed
D4 checkpoint: 87 passed
D5 full regression: 192 passed
Final self-review targeted battery: 146 passed
Full suite: 100% reached (pytest teardown hang, zero failures)
```

Earlier tasks contributed additional per-task regression batteries
(Task 8: 31 passed; Task 9/9-A: 39 passed; Task 10: 36 passed; Task
12: 90 passed; Task 14: 37 passed; Task 15: 47 passed; Task 6/6.5-A:
145 passed). Those numbers reflect isolated runs at the time each
task landed; the Wave D summary above is the most recent cross-layer
re-confirmation.

#### Follow-ups explicitly **not** started

* Hard physical deletion of the `check_authority` tombstone stub —
  acceptable once all external/integration callers are migrated; not
  attempted here.
* Production replacement of `RiskRouter.route()` with a pure
  sequence-driven router — not in scope; the Task 6.5-A adapter
  wires the sequence additively while preserving the legacy route
  contract and the `RISK_ROUTE_DECIDED` timeline payload.

### Task 5 / Wave D Structural Lock — accepted with documented transitions

Lock date: 2026-05-13

**Lock type:** STRUCTURAL LOCK — not full `OrganExecutionReceipt`
runtime adoption.

**What is locked:**

* All 17 browser execution/adapter/orchestrator files now live under
  `sentinel/organs/browser/` with organ-side imports
  (`sentinel.shared.events`, `sentinel.organs.browser.*`).
* `sentinel/agent/browser/` paths are backward-compatibility shims
  that re-export from the organ-side canonical modules. Class identity
  is preserved across both paths.
* Production default `FinalGateRegistry` uses
  `BrowserOrganChecksModule` (name `"browser_organ"`). The 14 browser
  FinalGate checks are owned by the organ module with zero
  `CoreFinalGate` delegation.
* `BrowserChecksModule` remains only as a deprecated parity/test
  reference. It is NOT in the production registry.
* `CoreFinalGate._browser_*` static methods remain only as deprecated
  test-reachable helpers. They are NOT called by the production
  FinalGate path.
* `wrap_browser_execution_receipt` exists in
  `sentinel/organs/browser/receipt_wrapper.py`, is tested (12 tests),
  and is available for executor adoption — but is NOT yet called by
  any executor runtime path.
* `P3H_ALLOWED_EXECUTION_INTENT_VALUES` in `organs/browser/final_gate.py`
  is deduplicated — derives from the organ-side
  `interaction_execution.P3H_ALLOWED_EXECUTION_INTENTS`.

**Spec corrections accepted:**

* **5.7:** Documented deprecation notice in module docstring satisfies
  this audit. Runtime `DeprecationWarning` deferred until internal
  callers migrate.
* **5.9:** Original literal "≤20 checks" replaced with: "CoreFinalGate
  SHALL NOT own organ-specific checks; cross-organ core checks remain
  as the safety baseline." Current baseline: 24 core checks +
  project-scope tail; all 14 browser checks owned by
  `BrowserOrganChecksModule`. CP-5.2 (FinalGate Delegation) satisfied.

**Documented cross-layer imports (organ → agent):**

* `sentinel.agent.artifact_capture` — pure utility (7 organ files)
* `sentinel.agent.evidence_ranker.sanitize_*` — pure utility
  (`navigation_l6.py`, pre-existing)
* `sentinel.agent.final_gate.CoreGateCheck/CoreGateCheckKind` —
  shared pydantic result types (`final_gate.py`, TYPE_CHECKING only
  for `AgentRunResult`)
* `sentinel.agent.action_engine` — cognitive bridge
  (`operator_runtime.py`)
* `sentinel.agent.browser.perception_adapter` — cognitive bridge
  intentionally kept in agent (`operator_runtime.py`)
* `sentinel.agent.perception` — cognitive bridge
  (`operator_runtime.py`)
* `sentinel.agent.tool_call_protocol` — cognitive bridge
  (`controlled_runner.py`, `operator_runtime.py`)

**Post-audit Browser Runtime Adoption Backlog:**

1. Wire `wrap_browser_execution_receipt` into executor boundary once
   `OrganDryRunReceipt`, `OrganAuthorityEnvelope`, and
   `OrganKillSwitch` are present at the call site.
2. Migrate parity tests from `BrowserChecksModule` /
   `CoreFinalGate._browser_*` to `BrowserOrganChecksModule`.
3. Remove `BrowserChecksModule` after tests migrate.
4. Remove `CoreFinalGate._browser_*` static helpers after tests
   migrate.
5. Rewrite 3 production shim imports (`final_gate.py`,
   `action_engine.py`, `tool_intent_compiler.py`) to
   `sentinel.organs.browser.*`.
6. Move `artifact_capture` and `evidence_ranker` sanitizer utilities
   to `sentinel/shared/` layer.
7. Export Wave D modules from `sentinel.organs.browser.__init__` when
   agent-side shims retire.

---

### Sentinel Full System Audit — CLOSED

Closure date: 2026-05-13

#### 1. Audit scope

This spec (`.kiro/specs/sentinel-full-system-audit/`) was an
**audit/closure spec** — its purpose was to surface, prioritize, and
fix architectural findings from the P6R5 code-grounded review before
P6U readiness. It is NOT a continuation roadmap and no new organ
should be started inside this spec. Any follow-up work must be opened
in a new spec.

#### 2. Completed blockers (15 tasks, all closed)

| Task | Title | Priority | Status |
|------|-------|----------|--------|
| 1 | FinalGate Runtime Integration | P0 Critical | ✓ Complete |
| 2 | Memory-not-Authority Multi-Phase | P0 High | ✓ Complete |
| 3 | Dry-Run ↔ Execution Cryptographic Binding | P0 High | ✓ Complete |
| 4 | Reactive Kill-Switch Interruption | P0 High | ✓ Complete |
| 7 | Per-Append Trace Hash Verification | P1 Medium | ✓ Complete |
| 13 | EventBus Primitives → Shared Layer | P1 Low | ✓ Complete |
| 11 | CoreFinalGate Registry Decomposition | P1 Medium | ✓ Complete |
| 5 | Browser Legacy Surface Consolidation | P1 High | ✓ STRUCTURAL LOCK |
| 6 | GateSequence + Runtime Wiring | P1 Medium | ✓ Complete |
| 15 | Phase Self-Transition Guard | P2 Low | ✓ Complete |
| 14 | ImprovementProposal Approval Token | P2 Low | ✓ Complete |
| 12 | MissionRunner Exception Reform | P2 Medium | ✓ Complete |
| 8 | DecisionFrameVerifier Mandatory Params | P2 Medium | ✓ Complete |
| 9 | Sanitizer Property Tests + 9-A Sanity | P2 Medium | ✓ Complete |
| 10 | `check_authority` Tombstone Decision | P2 Medium | ✓ Complete |

#### 3. Final verdict

**The `sentinel-full-system-audit` spec can be CLOSED.**

* All 15 parent tasks are resolved (14 fully complete + 1 structural
  lock with accepted spec corrections and documented transitions).
* The browser execution surface is structurally organ-side — all 17
  executor/adapter/orchestrator files live under
  `sentinel/organs/browser/` with clean layering.
* Receipt-runtime adoption (wiring `wrap_browser_execution_receipt`
  into executor call sites) remains in the post-audit backlog. It
  does not block P6U readiness.
* Any further work on this codebase must be opened in a **new spec**.
  This spec is closed and should not be reopened.

#### 4. Next Spec Seed Backlog

The following items are explicitly NOT done inside this audit. They
are seeds for future specs:

**Browser Runtime Adoption** (post-audit backlog from Task 5):
1. Wire `wrap_browser_execution_receipt` into
   `controlled_runner` / `operator_runtime` / executor boundary once
   `OrganDryRunReceipt`, `OrganAuthorityEnvelope`, and
   `OrganKillSwitch` are present at the call site.
2. Migrate parity tests from `BrowserChecksModule` /
   `CoreFinalGate._browser_*` to `BrowserOrganChecksModule`.
3. Remove `BrowserChecksModule` after tests migrate.
4. Remove `CoreFinalGate._browser_*` static helpers after tests
   migrate.

**Shared Utility Extraction:**
5. Move `sentinel.agent.artifact_capture` to `sentinel/shared/`.
6. Move `sentinel.agent.evidence_ranker.sanitize_context_text` /
   `sanitize_context_payload` to `sentinel/shared/sanitizer.py`.

**Import Rewrite:**
7. Rewrite 3 production shim imports (`final_gate.py`,
   `action_engine.py`, `tool_intent_compiler.py`) to
   `sentinel.organs.browser.*`.
8. Export Wave D modules from `sentinel.organs.browser.__init__` when
   agent-side shims retire.

**P6U and Beyond:**
9. P6U API Authenticated Read L6 — the next phase in the roadmap.
10. Later organs roadmap (capital, desktop L7, channel L7, etc.).

#### 5. Testing summary

**Wave D final run (most recent cross-layer confirmation):**

```
D2 checkpoint:                     81 passed
D3 checkpoint:                     81 passed
D4 checkpoint:                     87 passed
D5 full regression:               192 passed
Final self-review targeted battery: 146 passed
Full suite: 100% reached (zero failures visible; final summary
  line unavailable due to known PowerShell teardown hang on
  Windows — the process reaches [100%] with all dots passing
  but pytest's post-test teardown blocks indefinitely in the
  piped output stream. This is a test-runner environment issue,
  not a test failure.)
```

**Per-task regression batteries (at time of each task's landing):**

| Task | Tests |
|------|------:|
| Task 6 + 6.5-A | 145 |
| Task 12 | 90 |
| Task 15 | 47 |
| Task 9 / 9-A | 39 |
| Task 14 | 37 |
| Task 10 | 36 |
| Task 8 | 31 |

**Total unique test files created during this audit:** 12 new test
files covering property tests, integration tests, layering invariants,
and structural guards.

#### 6. Post-audit backlog status

**NOT done. NOT started. NOT claimed as complete.**

The 10 items in the "Next Spec Seed Backlog" above are explicitly
deferred. They must be opened in a new spec with their own
requirements, design, and tasks before implementation begins.

---

## Phase

```text
current_phase = P6T_B_FULL_LOCKED
previous_phase = P6T_A_FULL_LOCKED
next_phase = P6U_API_AUTHENTICATED_READ_L6
```

P6T-B Browser Controlled Navigation L6 Implementation is accepted as full
locked. It promotes the existing Sentinel browser capability to controlled
navigation L6 without creating a new browser organ.

P6T-B implements:

```text
BrowserNavigationAuthority
BrowserNavigationAdapter
BrowserNavigationBudget
BrowserNavigationTimeoutPolicy
BrowserNavigationReceipt
BrowserNavigationResult
BrowserFailureReceipt
BrowserPageEvidenceCard
BrowserNavigationDiffSummary
BrowserLinkCandidateRef
BrowserActionCandidateRef
BrowserNavigationDecisionFrameSlice
BrowserNavigationFinalGate
BrowserNavigationKillSwitch
BrowserNavigationCapabilityScanner
BrowserNavigationReceiptAdapter
BrowserNavigationActionKernel
BrowserNavigationPreview
BrowserRiskRouter
BrowserSchemeClassifier
BrowserQuarantineSandboxPolicy
BrowserSandboxAuthority
BrowserSandboxInspectionReceipt
BrowserSandboxNetworkPolicy
BrowserSandboxArtifactStore
BrowserSandboxEscapeGuard
SuspiciousUrlEvidenceCard
BrowserSandboxDecisionFrameSlice
```

P6T-B source-binding refs:

```text
openclaw_browser_action_kernel
cloakbrowser_power_classification
jarvis_permission_lifecycle
browser_use_action_registry_crosscheck
cua_browser_tool_boundary_crosscheck
chrome_devtools_mcp_cdp_shape_crosscheck
hermes_browser_output_pruning
sentinel_p6r_decision_frame
```

P6T-B route model:

```text
NORMAL_NAVIGATION = http/https allowlisted public domain read-only navigation
QUARANTINE_SANDBOX_INSPECTION = file/javascript/data/local/private/suspicious redirect
PROPOSAL_ONLY = chrome/devtools/profile/login/form/upload/download/account-affecting actions
BLACK_LANE_BLOCK = credential theft, fake identity, KYC bypass, captcha bypass,
                   stealth abuse, malware, fraud/payment abuse
```

P6T-B normal navigation can fetch/read allowlisted public pages, verify redirect
chains, emit deterministic navigation receipts, emit compact page evidence
cards, emit link/action candidate refs, and produce P6R-compatible browser
decision-frame slices.

Suspicious URL schemes are not permanently rejected capabilities. They are
denied from normal navigation, classified by `BrowserSchemeClassifier`, and
routed by `BrowserRiskRouter` to sandbox/proposal/block according to authority,
objective, and risk.

P6T-B does not add login/session mutation, form submit, upload/download
automation, payment/checkout, publishing/posting/sending, arbitrary JavaScript
execution, stealth/captcha/bypass, browser profile takeover, personal/default
browser profile connection, credential secret access, browser power expansion
beyond controlled navigation, vendor runtime bridge, vendor code copy, or
authority expansion.

## P6T-B Verification

```text
P6T-B targeted tests = 35 passed
P6C browser organ neighbor tests = 11 passed
P6R/P6Q context economy neighbor tests = 26 passed
P6M reality activation neighbor tests = 8 passed
full sentinel-core tests = not run by instruction
```

```bash
python -m pytest tests/test_p6_browser_controlled_navigation_l6.py -v --tb=short
python -m pytest tests/test_p6_browser_organ_contract.py -v --tb=short
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```

P6T-B required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/browser/navigation_l6.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/misuse_classifier.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_browser_controlled_navigation_l6.py
sentinel-control/docs/organs/P6T_B_BROWSER_CONTROLLED_NAVIGATION_L6_SCORECARD.md
sentinel-control/docs/organs/P6T_B_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6U go condition:

```text
P6U may start only as authenticated read-only API L6 through scoped credential
refs, rate-limit ledger, allowed vendor/endpoint authority, API response
receipts, credential-ref receipts, P6R context discipline, and no mutation API.
```

## Audit Correction — FinalGate Runtime Integration

Date: 2026-05-11

`CoreFinalGate` is now invoked from inside `AgentRuntime.run`. It is no longer
a post-hoc external verification step. Finding F-A3.11 from the
sentinel-full-system-audit spec (Axis 3.9) is closed.

Runtime integration contract:

```text
AgentRuntime.__init__ constructs self._final_gate = CoreFinalGate().
AgentRuntime.run routes every return AgentRunResult(...) through
self._apply_final_gate(result) before returning to the caller.
Every exit path is covered: COMPLETED, BLOCKED, ESCALATED, FAILED, REVOKED.
Every returned AgentRunResult carries final_gate_certification: a
CoreFinalGateResult with accepted=True.
```

Rejection downgrade semantics:

```text
If CoreFinalGate.evaluate rejects the intended result, the runtime downgrades
it to an AgentRunResult with status=BLOCKED.
The names of the failed checks are preserved as diagnostic text in
escalation_reason with the prefix "final_gate_rejected:".
The downgraded BLOCKED result is re-evaluated by CoreFinalGate and attached
with an accepted certification before being returned.
If the downgraded BLOCKED result also fails certification, AgentBlockedError
is raised. The runtime never returns an uncertified result.
```

Correctness properties now enforced by tests:

```text
CP-1.1 FinalGate Terminality = tests/test_final_gate_terminality.py
CP-1.2 FinalGate Determinism = tests/test_final_gate_determinism.py
```

Prior audit-surfaced claim that "FinalGate is only invoked externally in
tests" no longer holds. The runtime owns the terminal certification step.

## Prior P6T-A Phase

P6T-A Browser AgentLab Power Binding remains accepted as full locked. It splits
Browser Controlled Navigation L6 into a binding phase and an implementation
phase, following the same pattern as Desktop L6.

P6T-A binds Browser L6 to:

```text
OpenClaw first: browser action surface, gateway/action kernel,
approval/preview, scanner, tool schema discipline
CloakBrowser: browser power classification, detection, reliability, session,
fingerprint lessons
JARVIS: sidecar/browser awareness and permission lifecycle where relevant
browser-use / Cua / Chrome DevTools MCP: public cross-check for browser and
computer-use patterns
Hermes: browser output pruning and context compression
P6R: compact page evidence and decision-frame discipline
```

P6T-A does not add code or runtime powers.

## P6T-A Verification

```text
P6T-A docs verification = git diff --check clean
code tests = not run; docs-only binding phase
```

## Prior P6S-B Phase

P6S-B Desktop Workspace L6 Implementation remains accepted as full locked. It
promotes the existing desktop workspace capability into real scoped L6 local
workspace operations without adding broad host control.

P6S-B implements:

```text
DesktopWorkspaceAuthority
WorkspaceOperationAdapter
WorkspaceOperationBudget
WorkspaceTimeoutPolicy
WorkspaceMutationScope
PathContainmentProofRef
WorkspaceRollbackRef
DesktopWorkspaceKillSwitch
WorkspaceCostTrace
DesktopWorkspaceL6Receipt
DesktopWorkspaceL6Result
WorkspaceFailureReceipt
WorkspaceDiffSummary
WorkspaceContextCard
DesktopDecisionFrameSlice
WorkspaceActionKernel
WorkspaceCapabilityScanner
DesktopWorkspaceL6FinalGate
WorkspaceReceiptAdapter
```

P6S-B real scoped workspace actions:

```text
list_dir
read_file
write_file
create_folder
```

P6S-B requires scoped root authority, P6S-A source-binding refs, path
containment proof refs, deterministic receipts, rollback refs for mutation,
compact workspace context cards, Desktop decision-frame slices, kill switch,
and FinalGate compatibility.

P6S-B preserves P6R context discipline:

```text
raw workspace content may be returned to the local caller
raw workspace content is not placed in receipts or decision frames
receipt refs and content hashes travel in the LLM-facing context
workspace trees are compact summaries, not raw dumps
```

P6S-B does not add Code/Shell harvest, a new organ family, full host control,
shell/process execution, live screenshot/clipboard, desktop click/type/key,
sidecar admin mutation, vendor runtime bridging, vendor code copy, browser power
expansion, payment/spend runtime, trading runtime, credential secret access, or
authority expansion.

## P6S-B Verification

```text
P6S-B targeted tests = 9 passed
P6L desktop sidecar neighbor tests = 14 passed
P6M reality activation neighbor tests = 8 passed
full sentinel-core tests = not run by instruction
```

## Prior P6S-A Phase

P6S-A Desktop AgentLab Power Binding remains accepted as full locked. It binds
Desktop Workspace L6 to the strongest relevant AgentLab mechanisms before any
Desktop L6 implementation code starts.

P6S-A source order:

```text
JARVIS first: sidecar, enrollment, RPC registry, desktop awareness, approval,
audit, revocation
OpenJarvis second: budget, timeout, local execution discipline, cost routing
OpenClaw third: action kernel, manifest, scanner, preview, approval surface
Hermes fourth: context quarantine, compression, prompt discipline
Sentinel existing implementation last: P6K/P6L/P6M/P6P/P6R promotion base
```

P6S-A locks this doctrine:

```text
Sentinel must surpass audited agents, not imitate them.
Desktop L6 is not a fresh organ and not a generic file helper.
Desktop L6 is a Sentinel-native promotion of AgentLab power plus Brain L4,
P6R context discipline, receipts, rollback, authority, and FinalGate.
```

P6S-A does not start Desktop L6 implementation, Code/Shell harvest, a new organ
family, full host control, shell/process execution, screenshot/clipboard live,
vendor runtime bridging, vendor code copy, or authority expansion.

## P6S-A Verification

```text
P6S-A docs verification = git diff --check clean
full sentinel-core tests = not run; docs-only binding phase
```

## Prior P6R5 Phase

P6R5 Sentinel Cognitive Mechanics Review remains accepted as full locked. It
formally reviews Sentinel as a mathematical, physical, algorithmic, and
real-world thinking/action system before Desktop Workspace L6, then grounds
that review in P6Q/P6R code behavior.

P6R5 verdict:

```text
Sentinel is a promising but incomplete future-grade architecture.
It is not architecture theater.
It is not yet proven as a full future-grade operator.
```

P6R5 locks this model:

```text
S_t = mission state + authority + workspace + beliefs + receipts + organs +
      user-selected model contract + blockers + traces

a_t = argmax expected_progress + expected_information_gain
      - token_cost - latency_cost - risk_cost - retry_cost

subject to:
  authority_allows = true
  risk <= allowed_risk
  receipt_integrity = true
  no_authority_expansion = true
  FinalGate = pass
```

P6R5 frames Sentinel as a feedback-control agent:

```text
sensors = organs and receipts
controller = Brain L4 + Context Engine + Authority + FinalGate
actuators = promoted organs
memory = workspace + beliefs + receipt graph + traces
energy = tokens + latency + dollars + risk
feedback = receipts + verifier + replay + FinalGate
```

P6R5 does not start Desktop Workspace L6, Code/Shell harvest, a new organ
family, runtime powers, external execution powers, or authority expansion.

## P6R5 Verification

```text
P6R5 docs verification = git diff --check clean
P6Q targeted tests = 9 passed
P6R targeted tests = 17 passed
P6M/P6O/P6P/P6L neighbor tests = 33 passed
full sentinel-core tests = not run by instruction
```

Command:

```bash
git diff --check -- sentinel-control/docs/research sentinel-control/docs/CURRENT_STATE_LOCK.md sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/11_PHASE_ROADMAP_P6_TO_P10.md
```

P6R5 required files:

```text
sentinel-control/docs/research/P6R5_SENTINEL_COGNITIVE_MECHANICS_REVIEW.md
sentinel-control/docs/research/P6R5_MATH_PHYSICS_ALGORITHM_MODEL.md
sentinel-control/docs/research/P6R5_AGENT_LOOP_FORMAL_SPEC.md
sentinel-control/docs/research/P6R5_FUTURE_OR_GENERIC_VERDICT.md
sentinel-control/docs/research/P6R5_FAILURE_MODES_AND_PROOF_GAPS.md
sentinel-control/docs/research/P6R5_CODE_GROUNDED_REVIEW_ADDENDUM.md
sentinel-control/docs/research/P6R5_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/11_PHASE_ROADMAP_P6_TO_P10.md
```

P6R5 code-grounded corrections:

```text
P6Q over-budget decision frames are measured and flagged instead of capped.
P6R compression checks specific required evidence refs when provided.
P6R verifier can validate receipt refs against a known receipt graph.
AuthorityCardBuilder removes allowed/forbidden overlap with forbidden winning.
Decision-frame sanitization covers dict keys as well as values.
```

Locked P6R5 go condition:

```text
P6S may start only if Desktop Workspace L6 uses P6R decision frames from the
beginning and never dumps raw workspace trees/files/diffs into the LLM.
```

## Prior P6R Phase

P6R Subquadratic Agent Context Engine Prototype is accepted as full locked. It
turns P6Q context economy measurements into compact LLM decision frames that
preserve authority, critical evidence refs, blockers, selected tools, and
receipt replay integrity while keeping exact receipts outside the prompt.

P6R locks these internal models and components:

```text
ContextNeedEstimator
ReceiptGraphRetriever
EvidenceRanker
StateCardBuilder
AuthorityCardBuilder
ToolSurfaceRouter
PromptBudgetAllocator
LLMDecisionFrame
DecisionFrameVerifier
DecisionFrameHash
ContextCompressionResult
```

P6R decision frames include:

```text
mission card
authority card
progress card
top-k evidence
selected tool surface only
current blockers
next decision options
required output schema
receipt refs, not raw receipts
```

P6R excludes raw receipts, raw files, raw browser pages, raw API outputs, raw
channel messages, raw tool schemas, debate transcripts, historical state, and
secret-like material by default.

P6R does not start Desktop Workspace L6, Code/Shell harvest, a new organ
family, external execution powers, or authority expansion.

## P6R Verification

```text
P6R targeted tests = 17 passed
P6Q neighbor tests = 9 passed
full sentinel-core tests = not run by instruction
```

Commands:

```bash
python -m pytest tests/test_p6_subquadratic_agent_context_engine.py -v --tb=short
python -m pytest tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
```

P6R required files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/context_engine.py
sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py
sentinel-control/services/sentinel-core/sentinel/agent/receipt_retriever.py
sentinel-control/services/sentinel-core/sentinel/agent/evidence_ranker.py
sentinel-control/services/sentinel-core/sentinel/agent/state_cards.py
sentinel-control/services/sentinel-core/sentinel/agent/tool_surface_router.py
sentinel-control/services/sentinel-core/sentinel/agent/prompt_budget.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_subquadratic_agent_context_engine.py
sentinel-control/docs/research/P6R_SUBQUADRATIC_AGENT_CONTEXT_ENGINE_SCORECARD.md
sentinel-control/docs/research/P6R_DECISION_FRAME_SPEC.md
sentinel-control/docs/research/P6R_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6R findings:

```text
The user-selected model remains authoritative.
Sentinel optimizes prompt exposure for that selected model.
Raw evidence remains exact and replayable outside the prompt.
The LLM sees a compact decision frame, not a raw mission dump.
Tool surfaces are minimized to relevant authorized tools.
Missing critical evidence causes verifier failure.
Over-budget frames are reported as over budget rather than capped.
Secret-like content is redacted from stored decision-frame cards, not only from
prompt rendering.
```

## Prior P6Q Phase

P6Q Context Token And Model Economy Frontier remains accepted as full locked. It
turns P6Q0 research into measurable token/context/model-cost pressure reports
before building the P6R context engine.

P6Q locks these internal models:

```text
UserModelContract
ModelCostProfile
ModelCapabilityProfile
ContextBudgetPolicy
QualityExpectationContract
TokenLedger
TokenLedgerEntry
ContextPressureReport
ToolSchemaTokenReport
ReceiptTokenReport
OrganOutputTokenReport
DecisionFrameCostProjection
ContextModeComparison
```

P6Q compares:

```text
naive_full_context
summary_context
subquadratic_decision_frame
```

P6Q does not start Desktop Workspace L6, Code/Shell harvest, a new organ
family, external execution powers, or authority expansion.

## P6Q Verification

```text
P6Q targeted tests = 9 passed
full sentinel-core tests = not run by instruction
```

Command:

```bash
python -m pytest tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
```

P6Q required files:

```text
sentinel-control/services/sentinel-core/sentinel/agent/model_contract.py
sentinel-control/services/sentinel-core/sentinel/agent/model_cost.py
sentinel-control/services/sentinel-core/sentinel/agent/token_ledger.py
sentinel-control/services/sentinel-core/sentinel/agent/context_pressure.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_p6_context_token_model_economy_frontier.py
sentinel-control/docs/research/P6Q_CONTEXT_TOKEN_AND_MODEL_ECONOMY_FRONTIER_SCORECARD.md
sentinel-control/docs/research/P6Q_CONTEXT_PRESSURE_REPORT.md
sentinel-control/docs/research/P6Q_MODEL_COST_PROJECTION_REPORT.md
sentinel-control/docs/research/P6Q_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6Q findings:

```text
The user chooses the model.
Sentinel optimizes context for the selected model.
Model prices and context lengths are configurable profiles.
Receipts remain exact outside the prompt.
P6R must construct compact LLM decision frames using P6Q measurements.
Over-budget decision frames are reported truthfully before compression and
cost projection uses the measured frame size.
```

## Prior P6Q0 Phase

P6Q0 AgentLab Frontier Deep Research remains accepted as full locked. It
confirmed that AgentLab is the deep source, GitHub trends are cross-check only,
and Context/Token/Model Economy must precede Desktop Workspace L6.

P6Q0 required files:

```text
sentinel-control/docs/research/P6Q0_AGENTLAB_FRONTIER_DEEP_RESEARCH.md
sentinel-control/docs/research/P6Q0_AGENTLAB_POWER_TO_SENTINEL_REWRITE_MATRIX.md
sentinel-control/docs/research/P6Q0_CONTEXT_ECONOMY_FINDINGS.md
sentinel-control/docs/research/P6Q0_TRENDING_REPO_CROSS_CHECK.md
sentinel-control/docs/research/P6Q0_SENTINEL_REWRITE_BACKLOG.md
sentinel-control/docs/research/P6Q0_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/11_PHASE_ROADMAP_P6_TO_P10.md
```

Locked P6Q0 findings:

```text
AgentLab is the deep source.
GitHub trends are cross-check only.
The user chooses the model.
Sentinel optimizes context for the selected model.
Model prices and context lengths are configurable profiles.
Receipts remain exact outside the prompt.
The next implementation tranche is P6Q Context/Token/Model Economy Frontier.
```

## Prior P6P Phase

P6P Existing Organs Runtime Promotion Plan remains accepted as full locked. It
converted P6O gauntlet evidence into a deterministic L6 promotion plan for
existing organs only, with `desktop_workspace_l6` as the first runtime promotion
candidate after the context economy layer.

## Prior P6O Phase

P6O Existing Organs Real World Gauntlet remains accepted as full locked. It
pushes the existing P6M/P6N organs harder in repeated, combined, max-mode
scenarios before adding any new organ family.

## Prior P6N Phase

P6N Existing Organs Capability Frontier remains accepted as full locked. It
pushes the P6M-activated organs to their practical limits before adding any new
organ family.

## Prior P6M Phase

P6M Reality Activation for Existing Organs remains accepted as full locked. It
changes the direction from adding another organ family to making the already
created organs do scoped real work.

## Prior P6L Phase

P6L Desktop Sidecar Organ Implementation remains accepted as full locked. It
implements the Sentinel-native Desktop Sidecar Organ from the P6K JARVIS-first
harvest and blueprint.

## Prior P6K Phase

P6K Desktop AgentLab Harvest and Blueprint remains accepted as full locked. It
prevents Sentinel from building the Desktop Sidecar Organ from a generic
specification by harvesting JARVIS first, then OpenClaw and OpenJarvis, and
rewriting their desktop/sidecar mechanisms into Sentinel-native blueprint
models.

## Prior P6J1 Phase

P6J1 Power Surface Doctrine Reframe remains accepted as full locked. It corrects
the P6J vocabulary so Sentinel treats advanced browser, live API, channel,
credential, spend, trading, and sidecar surfaces as high-power operator
capabilities with promotion paths, not as capabilities to delete.

## Prior P6J Phase

P6J AgentLab Implementation Alignment remains accepted as full locked. It
verifies that every implemented P6C-P6I.6 organ maps to source-backed
AgentLab/vendor patterns and has a Sentinel-native rewrite, capability
classification, and promotion path.

## Prior P6I.6 Phase

P6I.6 TradingAgents Harvest remains accepted as full locked. It clones
TauricResearch/TradingAgents into AgentLab for static audit only, extracts its
multi-agent trading-desk patterns, and integrates them into Sentinel as
Sentinel-native internal trading cognition.

## Prior P6I.5 Phase

P6I.5 Capital Stack Hardening remains accepted as full locked. It hardens the
locked P6G/P6H/P6I capital stack after logic review by binding spend proposals
to real signal refs, capping sandbox budget reallocation, binding spend
kill-switches to the authority mission, blocking credential-ref overrides,
enforcing trading authority asset scope, enforcing max leverage, and broadening
profit-guarantee detection.

## Prior P6I Phase

P6I Trading Special Authority remains accepted as full locked. It defines
paper-first trading special authority, broker contracts, asset policy, position
sizing, max-loss policy, stop-loss policy, trade journal, paper trade provider,
and deterministic trading receipts.

## Prior P6H Phase

P6H Spend Runtime Limited remains accepted as full locked. It defines explicit
spend authority, spend requests, provider adapter interface, fake/sandbox
provider, spend receipts, subscription guard, refund/cancel path, and spend kill
switch.

P6H does not execute real payment providers, grant authority, add browser
execution, implement real trading runtime, account creation, credential access,
external API execution, channel send, sidecar execution, vendor runtime bridges,
vendor code copies, or silent authority expansion.

## P6H Verification

```text
targeted P6H tests = 10 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_spend_runtime_limited.py -v --tb=short
```

P6H required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/spend/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/spend/runtime.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_spend_runtime_limited.py
sentinel-control/docs/organs/P6H_SPEND_RUNTIME_LIMITED_SCORECARD.md
sentinel-control/docs/organs/P6H_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6H rules:

```text
Spend authority requires explicit budget, vendor, category, expiry, receipt, and
kill switch.
FakeSpendProvider creates sandbox receipts only.
Real provider interface exists but is disabled by default.
Budget overrun and single-transaction overrun are blocked.
Hidden subscriptions are blocked.
Explicit subscriptions require explicit authority and refund/cancel path.
Credential use is reference-only; raw credential material is blocked.
SpendReceipt cannot start real payment, access secrets, or expand authority.
```

## Prior P6G Phase

P6G Capital Operator Sandbox remains accepted as full locked. It defines
opportunity modeling, signal ledgers, adaptive operating envelopes, sandbox
budget reallocation, dynamic spend proposals, capital risk review, and
deterministic capital sandbox receipts without live spend.

P6G does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6G Verification

```text
targeted P6G tests = 9 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_capital_operator_sandbox.py -v --tb=short
```

P6G required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/capital/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/capital/sandbox.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_capital_operator_sandbox.py
sentinel-control/docs/organs/P6G_CAPITAL_OPERATOR_SANDBOX_SCORECARD.md
sentinel-control/docs/organs/P6G_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6G rules:

```text
Capital opportunities and planned Browser/API/Channel/Credential inputs are
modeled as sandbox references only.
SignalLedger records market, API, outreach, ROI, and risk signals.
Dynamic budget reallocation requires signal refs.
CapitalRiskReview flags profit guarantee claims.
DynamicSpendPolicy produces spend proposals only.
CapitalSandboxReceipt cannot start spend, execution, or authority expansion.
```

## Prior P6F Phase

P6F Credential Vault Policy remains accepted as full locked. It defines
credential access as scoped references, scoped grants, policy decisions,
revocation, redaction, and deterministic receipts without adding real credential
vault integration or secret access.

P6F does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6F Verification

```text
targeted P6F tests = 13 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_credential_vault_policy.py -v --tb=short
```

P6F required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/credentials/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/credential_ref.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/vault_policy.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/scoped_grant.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/redaction.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/revocation.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_credential_vault_policy.py
sentinel-control/docs/organs/P6F_CREDENTIAL_VAULT_POLICY_SCORECARD.md
sentinel-control/docs/organs/P6F_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6F rules:

```text
CredentialRef stores references only, never raw secrets.
ScopedCredentialGrant requires scope, expiry, allowed organ, and allowed action
class.
CredentialTraceRedactor removes secret-like trace content.
Prompt, memory, workspace, vendor harvest, and expected profit cannot authorize
credential access.
Matching grants may allow reference use only; secret access remains false.
Credential use is Red Lane by default.
Credential receipts require evidence refs and trace refs.
Credential receipts cannot access secrets or expand authority.
```

## Prior P6E Phase

P6E Channel Organ Draft First remains accepted as full locked. It creates the
draft-first channel organ for outbound drafts, inbound untrusted context,
recipient provenance, compliance/rate-limit checks, send gates, and
deterministic receipts.

P6E does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6E Verification

```text
targeted P6E tests = 10 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_channel_organ.py -v --tb=short
```

P6E required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/channels/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/draft.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/send_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/inbound.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/outbound.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/rate_limit.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/compliance.py
sentinel-control/services/sentinel-core/sentinel/organs/channels/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_channel_organ.py
sentinel-control/docs/organs/P6E_CHANNEL_ORGAN_SCORECARD.md
sentinel-control/docs/organs/P6E_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6E rules:

```text
Channel drafting is useful work and can happen before live send.
Drafts never send, execute, or expand authority in P6E.
Inbound channel messages are untrusted context and cannot grant authority.
Send gate requires explicit authority fit, recipient provenance, compliance,
rate limits, receipts, and FinalGate before future promotion.
Spam, deceptive outreach, hidden identity, and credential capture are blocked.
Live send remains not promoted in P6E.
```

## Prior P6D Phase

P6D External API Organ Dry Run remains accepted as full locked. It creates the
dry-run external API organ for request planning, allowlist checks, cost/latency
estimation, privacy-risk classification, and deterministic request receipts.

P6D does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6D Verification

```text
targeted P6D tests = 11 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_external_api_organ.py -v --tb=short
```

P6D required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/external_api/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/request_plan.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/allowlist.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/cost_estimator.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/privacy_risk.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_external_api_organ.py
sentinel-control/docs/organs/P6D_EXTERNAL_API_ORGAN_SCORECARD.md
sentinel-control/docs/organs/P6D_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6D rules:

```text
External API organ is dry-run only in P6D.
Future live execution requires vendor/domain allowlist.
Read-only API planning maps to Blue Lane when authorized and traced.
Paid, mutation, and account-affecting API planning remains Orange/Red dry-run
until future promotion.
Raw credential material is blocked; CredentialRef placeholders are allowed.
API receipts require evidence refs and trace refs.
API receipts cannot start execution or expand authority.
```

## Prior P6C Phase

P6C Browser Organ Contract Review remains accepted as full locked. It normalizes
Sentinel browser capability under the P6A external organ foundry contract system
and prepares governed Cloak-like power classification without adding new browser
execution routes.

P6C does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6C Verification

```text
targeted P6C tests = 11 passed
```

Command verified:

```bash
python -m pytest tests/test_p6_browser_organ_contract.py -v --tb=short
```

P6C required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/lanes.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/power_governor.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/misuse_classifier.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/reliability_profile.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/session_policy.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/fingerprint_risk.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/compliance_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/detection_bench.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_browser_organ_contract.py
sentinel-control/docs/organs/P6C_BROWSER_ORGAN_CONTRACT_REVIEW_SCORECARD.md
sentinel-control/docs/organs/P6C_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6C rules:

```text
Cloak-like browser powers are classified and governed, not discarded.
P5 is misuse-objective rejection, not capability deletion.
BrowserPowerGovernor may downgrade stronger power to the lowest needed safe
power.
Read-only public browsing maps to Blue Lane when authorized and traced.
Sensitive submit/form/click/login/upload actions remain dry-run/proposal unless
future promotion explicitly authorizes them.
P4 stealth-class browser power requires special authority.
Browser receipts require evidence refs and trace refs.
Browser receipts cannot start execution or expand authority.
```

## Prior P6B Phase

P6B Agent Lab Organ Harvest remains accepted as full locked. It turns forensic
evidence from Agent Lab and external source ledgers into deterministic,
machine-readable Sentinel organ harvest candidates.

P6B does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, external API execution, channel send, sidecar execution, vendor runtime
bridges, vendor code copies, or silent authority expansion.

## P6B Verification

```text
targeted P6B tests = 9 passed
P6A neighbor tests = 20 passed
event bus + P5L neighbor tests = 30 passed
full sentinel-core regression = 647 passed
```

Commands verified:

```bash
python -m pytest tests/test_p6_agent_lab_organ_harvest.py -v --tb=short
python -m pytest tests/test_p6_external_organ_foundry.py -v --tb=short
python -m pytest tests/test_agent_event_bus.py tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests -v --tb=short
```

P6B required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/vendor_harvest.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_agent_lab_organ_harvest.py
sentinel-control/docs/organs/P6B_AGENT_LAB_ORGAN_HARVEST_SCORECARD.md
sentinel-control/docs/organs/P6B_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6B harvest candidates:

```text
OpenClaw -> SentinelActionKernel
Hermes -> SentinelMemorySkillSpec
OpenJarvis -> SentinelCostRouter
JARVIS -> PermissionedSidecarManifest
financial-services -> FinancialProcedureGraph
CloakBrowser -> BrowserPowerGovernor
```

Locked P6B rules:

```text
Agent Lab harvests mechanisms, not vendor runtime.
P6B candidates are L2 Sentinel contract candidates only.
P6B does not register executable organs.
P6B does not grant authority.
P6B does not copy vendor code.
P6B does not bridge vendor runtime.
P6B preserves dangerous runtime surfaces as blocked findings.
VendorHarvestReference remains rewrite knowledge only.
```

## Autonomy/Risk Lane Doctrine

This doctrine corrects the interpretation of P6A safety. Sentinel must become
more autonomous inside explicit authority, not less autonomous.

```text
Green Lane:
local, reversible, low-risk actions; auto-execute when authorized.

Blue Lane:
external read-only or low-risk actions; auto-execute with trace when
authorized.

Orange Lane:
cost/account/message/API actions; execute inside explicit RootAuthorityEnvelope
and risk budget, without micro-approval for every small authorized action.

Red Lane:
trading, spend runtime, credentials, desktop/sidecar, stealth browser; require
special authority, caps, receipts, kill switch, and FinalGate.

Black Lane:
fraud, fake identity, KYC bypass, credential theft, illegal spam, unlawful
evasion, profit guarantees; always blocked as misuse objectives.
```

```text
blocked-by-default = not executable until promoted
blocked-by-default != forbidden forever
powerful-by-authority > safe-by-refusal
```

Risk is allowed only when user authority is explicit, risk budget exists, the
action class is promoted, receipts/replay exist, kill switch exists, and
FinalGate passes.

Risk is not allowed when it crosses root authority, hides cost or identity,
creates unapproved obligation, violates legal/compliance boundaries, or bypasses
policy.

## Prior P6A Phase

P6A External Organ Foundry remains accepted as full locked. It creates the
Sentinel-native contract layer for future external organs without adding real
external execution powers.

## P6A Verification

```text
targeted P6A tests = 20 passed
P5L integrated review tests = 23 passed
full sentinel-core regression = 638 passed
```

Commands verified:

```bash
python -m pytest tests/test_p6_external_organ_foundry.py -v --tb=short
python -m pytest tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests -v --tb=short
```

P6A required files:

```text
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/authority.py
sentinel-control/services/sentinel-core/sentinel/organs/contracts.py
sentinel-control/services/sentinel-core/sentinel/organs/dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/kill_switch.py
sentinel-control/services/sentinel-core/sentinel/organs/promotion_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/registry.py
sentinel-control/services/sentinel-core/sentinel/organs/replay.py
sentinel-control/services/sentinel-core/sentinel/organs/risk.py
sentinel-control/services/sentinel-core/tests/test_p6_external_organ_foundry.py
sentinel-control/docs/organs/P6A_EXTERNAL_ORGAN_FOUNDRY_SCORECARD.md
sentinel-control/docs/organs/P6A_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

Locked P6A rules:

```text
ExternalOrganContract requires authority mapping, risk profile schema,
dry-run receipt schema, execution receipt schema, trace/event compatibility,
kill-switch compatibility, source refs, and FinalGate compatibility.
VendorHarvestReference records rewrite knowledge only and cannot grant
authority.
Signals, workspace, memory, and expected profit cannot expand authority.
Payment/trading/account/credential action classes are blocked by default.
Dry-run-only organ authority cannot execute.
Execution-shaped receipts require explicit executable authority and untriggered
kill switch.
Receipts use deterministic hashes and replay rejects forged/mismatched records.
Promotion toward execution requires eval dataset, risk map, failure modes,
rollback/disable plan, receipt schema, kill switch, and FinalGate adapter.
```

## Prior Architecture Lock

The Sentinel A to Z architecture lock remains the project compass before P6
external organs. It records where Sentinel's powers are harvested from, why they
matter, how they are rewritten under Sentinel authority, which product workflows
use them, and which promotion levels must be passed before execution.

## Architecture A To Z Verification

```text
docs-only architecture lock = created
external source ledger = financial-services and CloakBrowser recorded
CloakBrowser powers = classified, not discarded
misuse objectives = blocked by Brain power governance
product workflow map = created
repo governance and dirty-tree policy = created
promotion ladder L0-L8 = created
runtime powers added = 0
vendor code copied = 0
```

Required files:

```text
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/00_README_PROJECT_COMPASS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/01_ORIGIN_AND_NORTH_STAR.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/02_AGENT_LAB_FORENSIC_EVIDENCE_INDEX.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/03_POWER_HARVEST_MAP.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/04_COMPARATIVE_ARCHITECTURE_ANALYSIS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/05_TRADEOFF_DECISION_LEDGER.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/06_SENTINEL_SYSTEM_ARCHITECTURE_A_TO_Z.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/07_DIRECTORY_AND_FILE_BLUEPRINT.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/08_ADVISORY_TO_EXECUTABLE_PROMOTION_LADDER.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/09_SIMULATION_AND_PREMORTEM_SCENARIOS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/10_PRESERVATION_CONSTRAINTS.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/11_PHASE_ROADMAP_P6_TO_P10.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/12_P6A_EXTERNAL_ORGAN_FOUNDRY_SPEC.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/13_ARCHITECTURE_LOCK_VERDICT.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/14_PRODUCT_WORKFLOW_MAP.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/15_REPO_GOVERNANCE_AND_DIRTY_TREE_POLICY.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/16_FINANCIAL_SERVICES_HARVEST_MAP.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/17_CLOAK_BROWSER_POWER_REVIEW.md
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/18_SOURCE_RESEARCH_LEDGER.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## Prior P5L Phase

P5L remains accepted as full locked. It integrates and hardens the Brain L4 stack
before P6 external organs. It does not execute external systems, grant authority,
add external powers, implement payment/spend runtime, trading runtime, account
creation, credential access, browser power expansion, or authority expansion.

## Verification

```text
targeted P5L tests = 23 passed
targeted full P5 suite with P5L = 102 passed
full sentinel-core regression = 618 passed
targeted P5K tests = 9 passed
targeted full P5 suite = 79 passed
full sentinel-core regression = 595 passed
targeted P5J tests = 6 passed
targeted P5I tests = 10 passed
targeted P5H tests = 7 passed
targeted P5G tests = 7 passed
targeted P5F tests = 6 passed
targeted P5E tests = 11 passed
targeted P5B/P5C/P5D neighbor tests = 23 passed
P5D.5 docs verification = diff check passed
targeted P5D tests = 11 passed
targeted P5B/P5C tests = 12 passed
```

Commands verified:

```bash
python -m pytest tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py tests/test_agent_society_manager.py tests/test_agent_global_workspace.py tests/test_agent_bayesian_belief_state.py tests/test_agent_adaptive_debate.py tests/test_agent_epistemic_action.py tests/test_agent_resourcefulness_engine.py tests/test_agent_skill_procedure_graph.py tests/test_agent_brainbench.py tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
python -m pytest tests -v --tb=short
python -m pytest tests/test_agent_brainbench.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py tests/test_agent_society_manager.py tests/test_agent_global_workspace.py tests/test_agent_bayesian_belief_state.py tests/test_agent_adaptive_debate.py tests/test_agent_epistemic_action.py tests/test_agent_resourcefulness_engine.py tests/test_agent_skill_procedure_graph.py tests/test_agent_brainbench.py -v --tb=short
python -m pytest tests -v --tb=short
python -m pytest tests/test_agent_skill_procedure_graph.py -v --tb=short
python -m pytest tests/test_agent_resourcefulness_engine.py -v --tb=short
python -m pytest tests/test_agent_epistemic_action.py -v --tb=short
python -m pytest tests/test_agent_adaptive_debate.py -v --tb=short
python -m pytest tests/test_agent_bayesian_belief_state.py -v --tb=short
python -m pytest tests/test_agent_global_workspace.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py tests/test_agent_society_manager.py -v --tb=short
git diff --check -- sentinel-control/docs/CURRENT_STATE_LOCK.md sentinel-control/docs/brain
python -m pytest tests/test_agent_society_manager.py -v --tb=short
python -m pytest tests/test_agent_mission_entropy.py tests/test_agent_count_controller.py -v --tb=short
```

Full sentinel-core was rerun after P5L and passed.

## P5L Required Files

These files are required to preserve the P5L full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/workspace.py
sentinel-control/services/sentinel-core/sentinel/agent/resourcefulness.py
sentinel-control/services/sentinel-core/sentinel/agent/brainbench.py
sentinel-control/services/sentinel-core/tests/test_agent_brain_l4_integrated_review.py
sentinel-control/services/sentinel-core/tests/test_agent_brain_l4_premortem_fixtures.py
sentinel-control/docs/brain/P5L_BRAIN_L4_INTEGRATED_REVIEW.md
sentinel-control/docs/brain/P5L_PREMORTEM_HARDENING_SCORECARD.md
sentinel-control/docs/brain/P5L_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5L Locked Doctrine

P5L certifies the Brain L4 stack as an integrated internal cognitive system.

It hardens these pre-mortem classes:

```text
over/under agent allocation
workspace fact pollution
belief confidence inflation
debate false positive/false negative routing
unsafe high-information action ranking
resourcefulness authority bypass
silent authority extension activation
partial success mislabeled as full success
skill procedure missing-authority execution recommendation
capital profit guarantee claims
dynamic spend changes without signal refs
dirty broadcast context leakage
role creation without first-principles purpose
missing or forged P5 trace events
```

P5L remains internal. It does not attach real-world execution organs.

## P5K Required Files

These files are required to preserve the P5K full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/brainbench.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_brainbench.py
sentinel-control/docs/brain/P5K_BRAINBENCH_SCORECARD.md
sentinel-control/docs/brain/P5K_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5K Locked Doctrine

`BrainBench` is evaluation only.

It produces:

```text
BrainBenchCase
BrainBenchReport
allocation_accuracy
belief_update_quality
debate_trigger_precision
information_gain_score
cost_efficiency
trace_integrity
negative authority-expansion cases
```

It may emit:

```text
BRAINBENCH_CASE_RUN
BRAINBENCH_REPORT_CREATED
```

BrainBench rejects forged L4 traces and authority-expansion attempts.

## P5J Required Files

These files are required to preserve the P5J full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/skill_procedure.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_skill_procedure_graph.py
sentinel-control/docs/brain/P5J_SKILL_PROCEDURE_GRAPH_SCORECARD.md
sentinel-control/docs/brain/P5J_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5J Locked Doctrine

`SkillProcedureGraph` is advisory only.

It produces:

```text
SkillProcedure
SkillProcedureMatch
ProcedurePrecondition
RequiredAuthority
CanonicalStep
SuccessProof
KnownFailureMode
```

It may emit:

```text
SKILL_PROCEDURE_MATCHED
```

Skill memory recommends procedures, but never grants authority or starts
execution.

## P5I Required Files

These files are required to preserve the P5I full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/resourcefulness.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_resourcefulness_engine.py
sentinel-control/docs/brain/P5I_RESOURCEFULNESS_ENGINE_SCORECARD.md
sentinel-control/docs/brain/P5I_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5I Locked Doctrine

`ResourcefulnessEngine` is advisory only.

It produces:

```text
ResourcefulnessDecision
DebrouilleLevel D0-D5
FallbackPlanSet
ToolSubstitutionDecision
PartialSuccessReport
AuthorityExtensionProposal
```

It may emit:

```text
RESOURCEFULNESS_ROUTED
FALLBACK_PLAN_CREATED
TOOL_SUBSTITUTION_PROPOSED
PARTIAL_SUCCESS_DECLARED
AUTHORITY_EXTENSION_PROPOSED
```

AuthorityExtensionProposal is proposal-only and cannot activate new authority.

## P5H Required Files

These files are required to preserve the P5H full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/epistemic_action.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_epistemic_action.py
sentinel-control/docs/brain/P5H_EPISTEMIC_ACTION_EVALUATOR_SCORECARD.md
sentinel-control/docs/brain/P5H_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5H Locked Doctrine

`EpistemicActionEvaluator` is advisory only.

It produces:

```text
EpistemicActionScore
expected_progress
expected_information_gain
risk_penalty
cost_penalty
authority_impact
total_action_value
```

It may emit:

```text
EPISTEMIC_ACTION_SCORED
```

Action value never authorizes execution. Unsafe high-information actions remain
blocked or proposal-only outside this evaluator.

## P5G Required Files

These files are required to preserve the P5G full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/adaptive_debate.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_adaptive_debate.py
sentinel-control/docs/brain/P5G_ADAPTIVE_DEBATE_SPARSE_MOA_SCORECARD.md
sentinel-control/docs/brain/P5G_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5G Locked Doctrine

`AdaptiveDebateRouter` is advisory only.

It produces:

```text
DebateRoute
DebateRolePlan
SparseMoAPlan
DebateAggregationPlan
unresolved_disputes
fan_in_limit
max_layers
max_debate_rounds
```

It may emit:

```text
DEBATE_ROUTED
MOA_LAYER_COMPLETED
DEBATE_AGGREGATED
```

Debate planning never executes agents, calls tools, or expands authority.

## P5F Required Files

These files are required to preserve the P5F full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/belief_state.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_bayesian_belief_state.py
sentinel-control/docs/brain/P5F_BAYESIAN_BELIEF_STATE_SCORECARD.md
sentinel-control/docs/brain/P5F_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5F Locked Doctrine

`BayesianBeliefState` is advisory only.

It produces:

```text
Belief
BeliefUpdate
EvidenceSupport
ContradictionSupport
belief_probability
belief_variance
posterior_update_reason
```

It may emit:

```text
BELIEF_STATE_UPDATED
```

Belief confidence informs cognition only. It never grants tools, actions, paths,
browser powers, payment powers, credentials, or authority.

## P5E Required Files

These files are required to preserve the P5E full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/workspace.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_global_workspace.py
sentinel-control/docs/brain/P5E_MISSION_GLOBAL_WORKSPACE_SCORECARD.md
sentinel-control/docs/brain/P5E_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5E Locked Doctrine

`MissionGlobalWorkspace` is the versioned shared cognition layer.

It produces:

```text
WorkspaceSnapshot
WorkspaceDelta
BroadcastSlice
WorkspaceFact
WorkspaceClaim
WorkspaceSignal
WorkspaceAgentOutput
WorkspaceOpenQuestion
WorkspaceRejectedClaim
```

It may emit:

```text
WORKSPACE_SNAPSHOT_CREATED
WORKSPACE_BROADCAST_PREPARED
WORKSPACE_DELTA_APPLIED
```

It stores facts, claims, questions, rejected claims, signal observations, and
agent outputs. It never grants tools, actions, paths, browser powers, payment
powers, credentials, or authority.

Rejected claims cannot be reintroduced as accepted facts.

Broadcast slices must be role-specific and minimized rather than dumping the
whole workspace.

## P5D.5 Required Files

These files are required to preserve the P5D.5 full lock:

```text
sentinel-control/docs/brain/P5D5_CAPITAL_OPERATOR_DOCTRINE.md
sentinel-control/docs/brain/P5D5_ADAPTIVE_OPERATING_ENVELOPE.md
sentinel-control/docs/brain/P5D5_SIGNAL_RESPONSIVE_SPEND_POLICY.md
sentinel-control/docs/brain/P5D5_LOCK_VERDICT.md
sentinel-control/docs/brain/P5A_BRAIN_L4_ROADMAP.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5D.5 Locked Doctrine

P5D.5 locks:

```text
RootAuthorityEnvelope = fixed user mandate boundaries
AdaptiveOperatingEnvelope = dynamic operating parameters inside root boundaries
SignalLedger = evidence for operating changes
BudgetReallocator = moves spend toward stronger signals without crossing authority
DynamicSpendPolicy = spend/hold/scale/cut/propose-extension doctrine
SpendDecisionTrace = reason, signal, risk, budget, receipt, and stop-condition proof
```

Core rule:

```text
Authority boundaries do not silently expand.
Operational allocation must adapt continuously inside those boundaries.
```

Current core still treats payment/spend/credential actions as blocked black-zone
actions. P5D.5 does not change runtime behavior.

If explicit spend authority is granted in a future runtime, Sentinel should be
able to act inside that authority rather than remain passive. Any action outside
root authority requires an `AuthorityExtensionProposal`.

## P5D Required Files

These files are required to preserve the P5D full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/agent_society.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/sentinel/agent/__init__.py
sentinel-control/services/sentinel-core/tests/test_agent_society_manager.py
sentinel-control/docs/brain/P5D_AGENT_SOCIETY_SCORECARD.md
sentinel-control/docs/brain/P5D_LOCK_VERDICT.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
```

## P5D Locked Doctrine

`AgentSocietyManager` is advisory only.

It consumes:

```text
AgentCountRoute
MissionEntropyEstimate
MissionAuthorityEnvelope
```

It produces deterministic outputs:

```text
AgentSocietyPlan
AgentRoleAssignment
AgentOutputContract
AgentRolePurpose
AgentSocietyPlanStatus
```

It may emit:

```text
AGENT_SOCIETY_PLANNED
AGENT_ROLE_ASSIGNED
```

Each role must map to at least one P5C.5 first-principles purpose:

```text
exploration
verification
aggregation
contradiction
cost control
context compression
authority-bound fallback
```

It must not grant:

```text
tools
actions
paths
browser powers
external systems
credentials
payments
channel sending
desktop control
```

It must not spawn agents and must not implement runtime multi-agent execution.

## P5C.5 Required Files

These files remain required to preserve the P5C.5 full lock:

```text
sentinel-control/docs/brain/P5C5_FIRST_PRINCIPLES_BRAIN_STACK.md
sentinel-control/docs/brain/P5C5_INFORMATION_THERMODYNAMICS_CONTRACT.md
sentinel-control/docs/brain/P5C5_ENTROPY_BUDGET_MODEL.md
sentinel-control/docs/brain/P5C5_MATH_TO_ALGORITHM_TRANSLATION.md
sentinel-control/docs/brain/P5C5_LOCK_VERDICT.md
```

## P5C Required Files

These files remain required to preserve the P5C full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/agent_count.py
sentinel-control/services/sentinel-core/tests/test_agent_count_controller.py
sentinel-control/docs/brain/P5C_AGENT_COUNT_SCORECARD.md
sentinel-control/docs/brain/P5C_LOCK_VERDICT.md
```

## P5B Required Files

These files remain required to preserve the P5B full lock:

```text
sentinel-control/services/sentinel-core/sentinel/agent/mission_entropy.py
sentinel-control/services/sentinel-core/tests/test_agent_mission_entropy.py
sentinel-control/docs/brain/P5B_MISSION_ENTROPY_SCORECARD.md
sentinel-control/docs/brain/P5B_LOCK_VERDICT.md
```

## Boundary

Do not stop the P5 sprint unless a hard blocker appears.

Do not start the next organ.

Do not add new browser powers.

Do not implement runtime multi-agent execution.

Do not implement payment/spend runtime.

Do not implement trading runtime.

Do not implement account creation.

Do not silently expand authority.
