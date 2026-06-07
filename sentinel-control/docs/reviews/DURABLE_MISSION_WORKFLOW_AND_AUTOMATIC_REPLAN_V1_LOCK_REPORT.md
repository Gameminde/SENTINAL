# Durable Mission Workflow And Automatic Replan V1 Lock Report

Recorded: 2026-06-07

## Verdict

```text
DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1 = LOCKED
current_phase = DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1_LOCKED
previous_phase = PERSISTENT_SEMANTIC_MEMORY_V1_LOCKED
next_phase = MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1
```

Sentinel now has a restartable local workflow controller over the existing
MissionKernel and PowerRuntime. Automatic replan is the product default only
when the candidate is provably inside the unchanged MissionAuthorityEnvelope.
Replan is autonomy inside authority. Replan is not new authority.

## Existing Sentinel Components Reused

```text
MissionKernel and MissionRunStore = canonical lifecycle and run directory
MissionEvent timeline and MissionReplayBuilder = canonical event/replay spine
OperatorPowerRuntimeBridge = only PowerRuntime invocation path
OperatorAgentRuntimeBridge = public/default-off AgentRuntime boundary
SentinelPowerRuntimeV0 = only automatic replan execution engine
MissionAuthorityEnvelope = only authority source
PowerRuntime receipts and FinalGate refs = durable step proof
RoleLoop/Persistent Semantic Memory refs = context/evidence only
existing safety scanner and PowerMissionPlan validators = persistence firewall
```

No parallel mission store, event stream, authority model, runtime, or organ
dispatch path was created.

## Sentinel-Native Additions

```text
DurableWorkflowRecord
WorkflowAuthoritySnapshot
WorkflowStepState
WorkflowStepProof
WorkflowBranch
WorkflowCheckpoint
ResumeCursor
ReplanCandidate
ReplanDecision
ReplanExecutionGuard
DurableWorkflowStore
DurableMissionWorkflowRuntime
DurableWorkflowReplayBuilder
```

Workflow state is stored under the existing mission run directory:

```text
<run-root>/<mission-id>/workflow/
```

## Automatic Replan Proof

Automatic PowerRuntime replan executes only when every applicable guard passes:

```text
same mission id and latest verified checkpoint
same complete authority-envelope fingerprint
same mission objective hash
same action/organ/actuator/request-contract manifest
same risk lane or lower
same exact endpoint/path/recipient/merchant/asset/account scope
same bound executor contract
same provider/backend/model and optional model-contract hash
worst-case retry action count remains inside max_actions
action attempts reserved durably before execution
typed estimated step cost reserved before execution and charged at checkpoint
recipient count remains inside max_recipients
positive cost requires typed step cost proof and remaining budget
no L6/L7 or special-authority boundary
no credential-use boundary
no irreversible boundary
no memory/receipt/FinalGate/checkpoint-as-permission
```

Any failed guard creates an operator checkpoint/escalation without execution.
Mission kill, pause, expiry, revocation, and authority drift are rechecked
before each next PowerRuntime step.

Successful dependency completion requires a local proof record bound to the
workflow, mission, active branch, plan hash, step contract, result hash,
receipt refs, and FinalGate refs. A caller-supplied checkpoint with invented
refs cannot unlock a dependent step.

The public PowerRuntime operator bridge now fails closed without the current
MissionAuthorityEnvelope, rejects action/tool/system/target scope drift, and
accepts execution only through an explicit bound executor contract. It also
enforces the recipient ceiling and rejects target-like request keys that are
not part of the canonical, envelope-checkable request vocabulary. Revoked or
expired envelopes, cumulative mission action/cost exhaustion, hidden API
mutation methods, empty plans, and successful executor results without both
receipt and FinalGate refs fail closed before becoming durable success.

Mission records are hash-bound. Workflow verification includes the current
mission-record hash, mission event chain, and a prepared-event hash for every
durable checkpoint. A checkpoint cannot publish if its prepared event append
fails.

## Deliberate AgentRuntime Boundary

AgentRuntime remains available through its existing public/default-off bridge,
with mission identity binding and safe receipt/FinalGate/memory/replan refs.

Opaque AgentRuntime automatic replan is not executed in V1. It escalates with:

```text
agent_runtime_replan_requires_typed_plan
```

This avoids pretending that opaque continuation context proves exact action,
organ, target, risk, credential, and budget scope.

## Agent Lab Mechanisms Harvested

Source-only mechanisms informed the Sentinel-native rewrite:

```text
Microsoft Agent Framework / JARVIS = durable lifecycle and checkpoint thinking
Hermes / DeerFlow / OpenJarvis = long-running task continuation and replan loops
Agent Zero / gptme = visible background mission ergonomics
oh-my-pi = hash-anchored state and typed minimized results
```

No vendor code, runtime, dependency, account, service, or bridge was copied or
integrated.

## Self-Audit Findings Closed

An independent adversarial review reopened the initial completion claim. Its
reproductions were converted into failing tests before remediation. The lock
below reflects the hardened second pass, not the earlier optimistic state.

```text
OBJECTIVE_DOUBLE_HASH_FALSE_REJECT = CLOSED
FULL_AUTHORITY_FINGERPRINT_DRIFT = CLOSED
STALE_CHECKPOINT_REPLAN = CLOSED
STEP_CONTRACT_RECOMBINATION = CLOSED
RETRY_ACTION_BUDGET_UNDERCOUNT = CLOSED
ACTION_BUDGET_PRE_EXECUTION_RESERVATION = CLOSED
TYPED_ESTIMATED_COST_RESERVATION_AND_DEBIT = CLOSED
SAME_DOMAIN_ENDPOINT_EXPANSION = CLOSED
CASE_DISTINCT_PATH_EXPANSION = CLOSED
POWER_BRIDGE_TARGET_SCOPE_BYPASS = CLOSED
POWER_BRIDGE_NONCANONICAL_TARGET_KEY_BYPASS = CLOSED
POWER_BRIDGE_RECIPIENT_BUDGET_BYPASS = CLOSED
POWER_BRIDGE_REVOKED_OR_EXPIRED_ENVELOPE = CLOSED
POWER_BRIDGE_CUMULATIVE_MISSION_ACTION_COST_BUDGET = CLOSED
POWER_BRIDGE_HIDDEN_API_MUTATION = CLOSED
POWER_BRIDGE_EMPTY_PLAN_FALSE_SUCCESS = CLOSED
POWER_BRIDGE_SUCCESS_WITHOUT_STRUCTURAL_PROOF = CLOSED
UNBOUND_EXECUTOR_CONTRACT = CLOSED
EXECUTOR_BINDING_CRYPTOGRAPHIC_AUTHENTICATION = DEFERRED / trusted same-process boundary
COMPOUND_IRREVERSIBLE_MARKER_BYPASS = CLOSED
L6_L7_SPECIAL_AUTHORITY_AUTO_REPLAN = CLOSED / escalates
CREDENTIAL_SCOPE_UNPROVEN = CLOSED / escalates
OPAQUE_AGENTRUNTIME_AUTO_REPLAN = CLOSED / escalates
MODEL_CONTRACT_DRIFT = CLOSED
POSITIVE_COST_WITHOUT_TYPED_PROOF = CLOSED / escalates
KILL_OR_REVOCATION_BETWEEN_STEPS = CLOSED
OPERATOR_PAUSE_AUTO_RESUME = CLOSED
REPLAN_AFTER_KILL_BRANCH_CREATION = CLOSED
MISSION_RECORD_TAMPER_RESURRECTION = CLOSED
EXPLICIT_OPERATOR_PAUSE_AUTO_RESUME = CLOSED
EMPTY_REPLAN_FALSE_COMPLETION = CLOSED
MALFORMED_WORKFLOW_RECORD_EXCEPTION_LEAK = CLOSED
CHECKPOINT_REPLAY_ORDER = CLOSED
FORGED_CHECKPOINT_PROOF_AS_PERMISSION = CLOSED
BRANCH_CHECKPOINT_CRASH_WINDOW = CLOSED / checkpoint-first fail-closed transition
TAMPER_REHASH_LAUNDERING = CLOSED
MALFORMED_CHECKPOINT_REPLAY = CLOSED
GENERIC_WORKFLOW_RECORD_AUTHORITY_OR_BUDGET_REWRITE = CLOSED
CURRENT_BRANCH_REWRITE_OUTSIDE_CHECKPOINT_TRANSITION = CLOSED
POWER_BRIDGE_EXCEPTION_RAW_LEAK = CLOSED
INVALID_POWER_EXECUTOR_RESULT_CRASH = CLOSED
SAME_PROCESS_DUPLICATE_TICK_EXECUTION = CLOSED
MISSION_LIFECYCLE_TRANSITION_RACE = CLOSED / local-process lock
EVENT_APPEND_DURABILITY = CLOSED / flush + fsync
CHECKPOINT_PREPARED_EVENT_BINDING = CLOSED
RAW_SECRET_LIKE_WORKFLOW_PERSISTENCE = CLOSED
RAW_SECRET_LIKE_AGENTEVIDENCE_REF_PERSISTENCE = CLOSED
OAUTH_SESSION_COOKIE_API_KEY_SECRET_FORMS = CLOSED
```

## Tests And Checks

```text
dedicated durable workflow/replan and bridge gauntlet = 112 passed
targeted cockpit/memory/AgentRuntime/Gate/FinalGate/PowerRuntime regressions = 359 passed
operator safety/kernel/replay impact slice = 61 passed
python compileall sentinel = passed
git diff --check = passed
modified-file secret scan = no finding
provider override/fallback/AUTO/direct-dispatch boundary scan = no finding
```

The final verification pass is rerun after documentation updates before any
completion claim.

## Honest Limits

```text
workflow/proof hashes = unkeyed corruption/non-rehashing tamper detection
local proof ledger cannot provide cryptographic authenticity against a writer able to rewrite every local file
bound executor contract = trusted same-process injection boundary, not cryptographic backend authentication
receipt/FinalGate refs = structurally required for success but not cryptographically authenticated by this V1 layer
duplicate-tick lock = same-process only, not a production multi-process lease
typed estimated step cost is charged conservatively; actual provider billing reconciliation is not implemented
opaque AgentRuntime automatic replan = blocked until typed plan proof exists
external side effects cannot be made transactionally atomic by a local checkpoint
checkpoint/record/event append is fail-closed but not one atomic multi-file transaction
crash after durable action/cost reservation can require operator intervention
kill/revocation is checked between steps but cannot interrupt an already-running actuator call
production daemon/heartbeat/dead-letter recovery = not started
worker fleet and child-authority inheritance = next phase
```

## Boundaries Preserved

```text
new actuator family = none
direct organ execution = none
new provider fallback/AUTO routing = none
raw credential storage or use = none
payment/account/trading/security/desktop/channel connector power = none
vendor runtime integration = none
```
