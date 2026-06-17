# Real Model Read-Only Operator Production Spine V1 - Pre-Implementation Design

Date: 2026-06-18

Repository: `C:\Users\youcefcheriet\sentinal`

Status: design checkpoint only. No runtime implementation is claimed by this
document.

## Purpose

The next proof Sentinel needs is not another isolated real-model laboratory
run. The next proof is one complete read-only user mission through the real
Sentinel production spine.

Target chain:

```text
normal operator entry
-> explicit UserModelContract
-> MissionKernel creates mission
-> MissionAuthorityEnvelope grants read-only scope
-> AgentRuntime / PowerRuntime bridge receives a proposal
-> Gate validates the proposal
-> governed read-only capability executes
-> certified telemetry records state
-> receipt is emitted
-> FinalGate certifies terminal truth
-> replay reconstructs without re-execution
```

## Non-Goals

Do not implement this pack by calling:

```text
sentinel.operator.real_model_certification
sentinel.operator.self_exploration_read_only
sentinel.operator.interactive_exploration_read_only
sentinel.operator.mutation_transport_micro_certification
```

Those modules are experimental evidence. They may inspire mechanisms but must
not become the production entry.

Do not start:

- a new provider experiment;
- a new Stage B protocol;
- mutation/coding;
- browser live expansion;
- desktop/voice/channel expansion;
- Security Testing special authority;
- Wave 2;
- UX implementation.

## Existing Spine To Reuse

Observed existing surfaces:

| Surface | Existing path |
|---|---|
| Normal CLI/operator model contract loading | `sentinel.cli`, `sentinel.operator.cockpit`, `sentinel.operator.conversation` |
| Explicit model contract | `sentinel.agent.model_contract.UserModelContract` |
| Product model client / adapter | `sentinel.operator.model_client`, `sentinel.operator.llm_adapter` |
| Provider execution | `sentinel.agent.model_execution.*` |
| Mission lifecycle | `sentinel.operator.kernel.MissionKernel` |
| Authority envelope | `sentinel.mission.models.MissionAuthorityEnvelope` |
| Runtime bridge | `sentinel.operator.agent_bridge`, `sentinel.operator.power_bridge` |
| Agent runtime | `sentinel.agent.runtime.AgentRuntime` |
| Telemetry | `sentinel.telemetry.TelemetryKernel` |
| Receipts and evidence | model execution receipts, workflow receipts, organ receipts |
| FinalGate | `sentinel.agent.final_gate.CoreFinalGate` and organ-specific FinalGate surfaces |
| Replay | `sentinel.operator.replay`, workflow/daemon/organ replay builders |

The design must reuse these surfaces.

## Canonical Entry Point

V1 uses one exact public/operator entry:

```text
sentinel.operator.cockpit.LLMLiveOperatorCockpit.handle(text)
```

This is the canonical natural-language entry because it is already suitable for
future desktop-app use:

```text
connect explicit model
submit natural-language mission
draft mission and authority summary
operator confirms start
MissionKernel creates/enqueues mission
operator can ask status/pause/resume/kill
```

The V1 production-spine runner may add a bound execution component after mission
enqueue, but it must remain downstream of the cockpit-created mission. It must
not expose a separate experimental CLI, and it must not call the laboratory
modules directly.

Forbidden entries:

```text
sentinel.operator.self_exploration_read_only
sentinel.operator.interactive_exploration_read_only
sentinel.operator.real_model_certification
sentinel.operator.mutation_transport_micro_certification
```

## Required Multi-Turn Loop

V1 must be multi-turn, not a single-shot report wrapper.

Required loop:

```text
LLMLiveOperatorCockpit.handle(user_text)
-> OperatorConversationEngine.handle_user_message(...)
-> OperatorLLMConversationAdapter.complete(...)
-> explicit UserModelContract request
-> MissionKernel.create_mission(...)
-> MissionKernel.enqueue(...)
-> ReadOnlyProductionSpineSession starts for mission_id/run_id
-> model decision turn
-> proposal correlated to mission_id/run_id
-> Gate validates one bounded action
-> read-only capability executes
-> telemetry event emitted
-> evidence refs recorded
-> action receipt emitted
-> observation returned to model context
-> next model decision turn
-> terminal report proposal
-> independent oracle result attached
-> terminal mission FinalGate exactly once
-> replay view built without provider/tool re-execution
```

Every turn must reuse:

```text
same mission_id
same run_id
same explicit UserModelContract
same frozen fixture identity
same MissionAuthorityEnvelope or a valid narrowed descendant
```

Every model/tool call must check before and after:

```text
kill state
revocation state
authority expiry
deadline
model-call budget
tool-call budget
token budget
certified telemetry state
mission terminal state
```

If any check fails after a provider response but before parsing, the response is
discarded as terminal/blocked metadata, not counted as an invalid model
decision.

## Minimal Mission Shape

Use a fresh read-only repository fixture, not Sentinel itself.

Mission:

```text
Inspect a frozen repository snapshot.
Explain its architecture.
Trace one complete execution path.
Identify one verified inconsistency.
Produce an evidence-linked report.
```

Rules:

- no write authority;
- no shell mutation;
- no provider-native tools;
- no hidden file hints;
- no precomputed solution;
- no direct experimental harness call;
- no raw prompt/response/reasoning persistence;
- no memory-generated authority;
- no receipt/FinalGate-as-permission.

## Production-Spine Components To Add Or Bind

V1 should add the smallest possible binding layer:

```text
ReadOnlyOperatorMissionRequest
ReadOnlyOperatorMissionPolicy
ReadOnlyOperatorDecision
ReadOnlyOperatorAction
ReadOnlyOperatorObservation
ReadOnlyOperatorEvidenceRef
ReadOnlyOperatorReport
ReadOnlyOperatorReceipt
ReadOnlyOperatorReplayView
```

Names may follow local conventions, but the concepts must exist.

Important: these are not a new runtime. They are typed request/result wrappers
around existing MissionKernel, authority, AgentRuntime/PowerRuntime, telemetry,
receipt, FinalGate, and replay surfaces.

## No Parallel Runtime Ownership

New read-only operator types are adapters only. They may not own parallel
mission lifecycle, authority, dispatch, telemetry, receipt, FinalGate, or replay.

| Proposed V1 concept | Existing production surface it adapts |
|---|---|
| `ReadOnlyOperatorMissionRequest` | `LLMLiveOperatorCockpit.handle(...)` + `MissionKernel.create_mission(...)` |
| `ReadOnlyOperatorMissionPolicy` | `MissionAuthorityEnvelope` + existing budget/deadline policies |
| `ReadOnlyOperatorDecision` | `OperatorLLMDecisionResult` / model execution decision metadata |
| `ReadOnlyOperatorAction` | Existing Gate + AgentRuntime/PowerRuntime bridge action request |
| `ReadOnlyOperatorObservation` | Existing governed tool result/evidence envelope |
| `ReadOnlyOperatorEvidenceRef` | Existing evidence/artifact ref discipline |
| `ReadOnlyOperatorReport` | Terminal mission result payload, not authority |
| `ReadOnlyOperatorReceipt` | Existing receipt/evidence chain surfaces |
| `ReadOnlyOperatorReplayView` | Existing replay builders; no re-execution |

If an existing model can be safely extended, prefer that over adding a new
parallel abstraction.

## Allowed Actions

V1 read-only actions:

```text
list_directory
read_file_segment
search_text
search_symbol
inspect_git_metadata
finish_with_report
checkpoint
```

Every action must be:

- scoped to frozen fixture root;
- authorized by read-only MissionAuthorityEnvelope;
- validated before execution;
- recorded with telemetry;
- linked to evidence;
- reflected in a receipt;
- replayable without re-execution.

## Blocked Actions

```text
write_file
apply_patch
delete_file
move_file
run_shell_mutating
network_call
desktop_action
browser_live_action
credential_access
provider_switch
fallback/AUTO
provider-native tool call
```

## Gate And FinalGate Semantics

Use three distinct levels:

```text
per-action Gate validation
per-action receipt/evidence validation
terminal mission FinalGate exactly once
```

Do not mark each read action as terminal mission success.

Per-action Gate validates:

- mission/run correlation;
- authority scope;
- frozen fixture boundary;
- allowed action enum;
- read-only nature;
- kill/revocation/expiry/deadline/budget state;
- certified telemetry availability.

Per-action receipt/evidence records:

- action id;
- mission/run id;
- authority envelope ref;
- input refs;
- output evidence refs;
- snapshot/fixture identity;
- telemetry refs;
- safe result summary;
- failure or block reason.

Terminal FinalGate validates once:

- mission/run correlation across all turns;
- authority validity throughout the mission;
- certified telemetry continuity;
- complete action receipts;
- evidence-reference integrity;
- report grounding;
- budget/deadline compliance;
- forbidden-action count is zero;
- independent oracle result exists;
- replay completeness;
- replay performs no action, tool, or provider call.

## Fake-Model Gate Before Real Model

Before any real provider call:

| Gate | Expected result |
|---|---|
| Fake model completes read-only mission through production spine | PASS |
| Wrong authority tries read action | BLOCKED |
| Write/mutation requested | BLOCKED |
| Kill before action | BLOCKED |
| Revocation before action | BLOCKED |
| Authority expiry before action | BLOCKED |
| Telemetry unavailable | FAIL_CLOSED |
| Receipt missing | FinalGate rejects |
| Replay built | no re-execution |
| Raw prompt/response/reasoning scan | zero persistence |
| Duplicate evidence loop | counted as nonproductive or blocked |

Required deterministic scenarios:

```text
successful multi-turn read-only mission
wrong authority
write request
kill before model response
kill before action
revocation between turns
authority expiry between turns
telemetry unavailable
provider/model error
duplicate action/evidence
deadline exhaustion
missing action receipt
wrong mission/run receipt
terminal report with unsupported claims
FinalGate rejection
replay without model/tool re-execution
```

Only after all gates pass should a single real-model run be considered.

## Real-Model Gate

Exactly one real-model read-only mission may run after local gates pass.

It must freeze:

```text
mission fixture hash
UserModelContract hash
provider/backend/model identifiers
endpoint hash
policy hash
budget
deadline
allowed actions
oracle
```

Success requires:

```text
mission created normally
explicit model contract used
model proposed only legal read-only actions
runtime executed only through production path
telemetry stayed certified
evidence refs matched observations
receipt chain complete
FinalGate accepted only if proof complete
replay reconstructed without provider/tool re-execution
independent oracle accepted report utility and claims
```

Model self-report is not evidence.

## Failure Taxonomy

Classify failure as exactly one primary category:

```text
MODEL_CAPABILITY
PROVIDER_TRANSPORT
MODEL_CONTRACT
MISSION_KERNEL
AUTHORITY_GATE
RUNTIME_BRIDGE
TELEMETRY_CERTIFICATION
READ_ONLY_TOOLING
EVIDENCE_GROUNDING
RECEIPT_CHAIN
FINALGATE
REPLAY
ORACLE
BUDGET_OR_DEADLINE
UNKNOWN
```

Also classify scope:

```text
GENERIC_SYSTEM_FINDING
MODEL_SPECIFIC_BEHAVIOR
PROVIDER_SPECIFIC_BEHAVIOR
FIXTURE_SPECIFIC
UNKNOWN_REQUIRES_MORE_EVIDENCE
```

## Report And Truth Rules

One successful run may prove:

```text
REAL_MODEL_PRODUCTION_SPINE_READ_ONLY_MISSION = FIRST_EVIDENCE
```

It must not automatically prove:

```text
Wave 1 complete
production ready
score increase
browser/coding/desktop/voice readiness
```

Scores remain unchanged until predefined corpus and holdout thresholds pass.

## Immediate Implementation Order

1. Add read-only production-spine request/result models.
2. Add fake model adapter or deterministic model coordinator fixture that uses
   the same product interfaces.
3. Bind MissionKernel + read-only authority + AgentRuntime/PowerRuntime.
4. Add read-only repository fixture tools behind Gate.
5. Emit receipts and FinalGate refs for every material action.
6. Add replay builder that reconstructs without action/provider calls.
7. Add adversarial local tests.
8. Run local gates.
9. Stop before real provider call unless explicitly approved.

## Final Boundary

This pack is the bridge from lab intelligence to product intelligence. Its
discipline is simple:

```text
model thinks
Sentinel owns mission, authority, action, proof, and memory
```

If that chain is broken, the pack is not complete.
