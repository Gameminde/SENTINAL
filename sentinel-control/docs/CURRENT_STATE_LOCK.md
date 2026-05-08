# Current State Lock

Date: 2026-05-09

## Phase

```text
current_phase = P6A_FULL_LOCKED
previous_phase = ARCHITECTURE_A_TO_Z_LOCKED
next_phase = P6B_AGENT_LAB_ORGAN_HARVEST
```

P6A External Organ Foundry is accepted as full locked. It creates the
Sentinel-native contract layer for future external organs without adding real
external execution powers.

P6A does not execute external systems, grant authority, add browser execution,
implement payment/spend runtime, trading runtime, account creation, credential
access, vendor runtime bridges, vendor code copies, or silent authority
expansion.

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
