# Sentinel Product Nervous System Integration V1

## Pack 2B.2 Live Mission Timeline Streaming Fix Report

Date: 2026-06-20

Base Pack 2B.2 commit: `90e0869851e5b92ef04ba32b93bc9a4c6cfd5f39`

Scope:

- Correct Pack 2B material execution visibility so product claims are backed by real canonical emitters, not projector-only mappings.
- Preserve the existing Sentinel spine: `OperatorAgentRuntimeBridge -> AgentRuntime -> EventBus -> OperatorAgentEventBridge -> MissionRunStore`.
- Stream `MissionTraceTimeline` material milestones synchronously while `MissionRunner` is still executing.
- Add a neutral mission-layer `MissionTraceEventSink` boundary without importing operator modules into `MissionRunner` or `MissionTraceTimeline`.
- Add honest worker outcome semantics and source-ref trust labels.
- Remove unsupported product visibility claims for source events that remain unproven in the canonical path.

Explicit non-goals:

- Pack 3 was not started.
- Coordinator dispatch, READ_ONLY_RESEARCH, search_text, browser product projection, memory product projection, and new execution powers were not implemented.
- No provider call was made.
- No push was made.

## Verdict

`PACK_2B_2_LIVE_MISSION_TIMELINE_STREAMING_FIX = LOCAL_COMMIT_CANDIDATE`

Pack 2B.2 closes the Pack 2B timing gap:

```text
AgentRuntime material source events
-> safe typed AgentExecutionEvent
-> OperatorAgentEventBridge
-> MissionRunStore

MissionTraceTimeline.emit(...)
-> source event appended and hash-linked
-> source timeline persisted when configured
-> injected MissionTraceEventSink.emit_mission_trace_event(...)
-> EventBus.project_mission_trace_event(...)
-> safe typed AgentExecutionEvent with source_ledger=mission_trace_timeline
-> OperatorAgentEventBridge
-> MissionRunStore
-> MissionRunner continues only after projection returns
```

Material observations remain data only. They do not complete missions, certify receipts, create authority, or bypass FinalGate.

MissionRunner material timeline visibility is now:

```text
LIVE_SYNCHRONOUS_PROJECTION
```

This is not atomic across ledgers. A source timeline event may already exist when product projection fails. The containment guarantee is that later timeline emits are latched closed before mutation, no later plan step starts after a live projection failure, and the operator bridge blocks product success.

## Visibility Classification

| Family | Classification | Evidence |
| --- | --- | --- |
| `worker_started` | `END_TO_END_PROVEN` | Real `AgentRuntime` calls real `WorkerCoordinator`; projected through `OperatorAgentRuntimeBridge` into `MissionRunStore`. |
| `worker_completed` | `END_TO_END_PROVEN` | Success and failure closures are tested through real `WorkerCoordinator`; outcome is explicit and non-authoritative. |
| `controlled_capability_executed` | `END_TO_END_PROVEN` | Real direct controlled local tool call emits through `LocalControlledCapabilityRunner` and projects into `MissionRunStore`. |
| `controlled_capability_rejected` | `CANONICAL_REACH_PROVEN` | Existing canonical runtime tests exercise rejection; Pack 2B.2 keeps the safe projection contract. |
| `artifact_captured` | `END_TO_END_PROVEN` | Real controlled local tool call captures an artifact through `ArtifactCaptureSandbox` and projects it. |
| `artifact_capture_rejected` | `CANONICAL_REACH_PROVEN` | Existing artifact/capability paths retain rejection events; product projection stays safe and non-authoritative. |
| `organ_dispatch_skipped` | `END_TO_END_PROVEN` | Real `AgentRuntime` with explicit organ-dispatch opt-in and no candidates projects a skip milestone. |
| `organ_dispatch_completed` | `CANONICAL_REACH_PROVEN` | Real emitter exists in `AgentRuntime`; Pack 2B.2 keeps mapping, but focused proof used the skipped branch. |
| `action_routed` | `LIVE_END_TO_END_PROVEN` | Real `MissionRunner` timeline `ACTION_ROUTED` is projected before the executor starts. |
| `action_executed` | `LIVE_END_TO_END_PROVEN` | Real `MissionRunner` timeline `ACTION_EXECUTED` for step N is visible before step N+1 starts. |
| `action_blocked` | `LIVE_END_TO_END_PROVEN` | Real executor failure produces sanitized `ACTION_BLOCKED`, projected before the next independent step. |
| `action_escalated` | `CANONICAL_REACH_PROVEN` | Real `MissionTraceTimeline` event type exists and is mapped; focused route/block tests cover the shared boundary. |
| `mission_runner_completed` | `LIVE_END_TO_END_PROVEN` | Real successful `MissionRunner` emits and projects `MISSION_COMPLETED` before `worker_completed`. |
| `mission_runner_failed` | `LIVE_END_TO_END_PROVEN` | Failed `MissionRunner` terminal projection occurs before failed worker closure when the runner returns a failed result. |
| `organ_receipt_recorded` | `NOT_CONNECTED` | Removed from Pack 2B product projection until canonical AgentRuntime organ receipt path is proven. |
| `artifact_capture_duplicate` | `PROJECTOR_ONLY` | Source event remains in `EventBus`; Pack 2B.2 does not claim product visibility without canonical reach proof. |
| `artifact_capture_index_written` | `PROJECTOR_ONLY` | Source event remains in `EventBus`; Pack 2B.2 does not claim product visibility without canonical reach proof. |
| browser source events | `NOT_CONNECTED` | Browser product visibility remains out of scope for Pack 2B.2. |
| memory source events | `NOT_CONNECTED` | Memory product visibility remains out of scope for Pack 2B.2. |

## Before And After Execution Visibility Graph

Before Pack 2B.2:

```text
AgentRuntime EventBus
-> projector mapping
-> MissionRunStore

MissionRunner MissionTraceTimeline
-> MissionRunner completes
-> WorkerCoordinator iterates returned trace_events
-> product sees timeline after the run
```

After Pack 2B.2:

```text
OperatorAgentRuntimeBridge
-> AgentRuntime
-> real EventBus source emitters
-> AgentExecutionEvent.from_agent_event()
-> OperatorAgentEventBridge
-> MissionRunStore

MissionRunner
-> MissionTraceTimeline
-> MissionTraceEventSink.emit_mission_trace_event()
-> WorkerCoordinator EventBus live timeline adapter
-> EventBus.project_mission_trace_event()
-> AgentExecutionEvent.from_mission_trace_event()
-> OperatorAgentEventBridge
-> MissionRunStore
-> MissionRunner continues to the next material action
```

## Worker Outcome Semantics

`WORKER_COMPLETED` is no longer presented as certified success.

Mapping:

```text
payload.success == true
-> activity_outcome = succeeded
-> safe_summary = "Agent worker lifecycle closed successfully."

payload.success == false
-> activity_outcome = failed
-> safe_summary = "Agent worker lifecycle closed with failure."

payload.success unavailable
-> activity_outcome = closed_unknown
-> safe_summary = "Agent worker lifecycle closed with unknown outcome."
```

Only the allowlisted boolean `success` is read from the source payload. Raw worker results, exception text, worker instructions, paths, targets, and payload contents are not projected.

## MissionTraceTimeline Bridge Contract

Shared boundary:

```text
MissionTraceEventSink.emit_mission_trace_event(mission_trace_event)
```

The canonical WorkerCoordinator route supplies a tiny adapter:

```text
_EventBusMissionTraceEventSink
-> EventBus.project_mission_trace_event(...)
```

This path:

- projects only safe typed timeline events;
- uses `source_ledger = mission_trace_timeline`;
- preserves source event id, source sequence, source logical time, source hash, mission id, and safe action refs;
- never appends to the AgentRuntime source ledger;
- never imports `MissionRunStore`, `MissionKernel`, or operator modules into `MissionRunner` or `MissionTraceTimeline`;
- latches projection failure through `MissionTraceProjectionError` and the existing `AGENT_EVENT_SPINE_PERSISTENCE_FAILED` bridge path.

Projected timeline families:

```text
ACTION_ROUTED -> action_routed
ACTION_EXECUTED -> action_executed
ACTION_BLOCKED -> action_blocked
ACTION_ESCALATED -> action_escalated
MISSION_COMPLETED -> mission_runner_completed
MISSION_FAILED -> mission_runner_failed
```

Blocked from timeline projection:

```text
raw action arguments
targets
paths
URLs
executor output
exception text
review payloads
prompts
provider output
reasoning
credentials
authorization data
```

## Source Ref Trust Contract

Every projected material event carries:

```text
ref_verification_status = unverified_source_refs
```

Pack 2B.2 validates only:

- source event correlation;
- source event hash/sequence/logical-time anchors;
- safe ref grammar and family splitting;
- product observation ordering.

Pack 2B.2 does not verify that referenced artifacts, receipts, or evidence objects exist. FinalGate, proof closeout, and replay remain responsible for proof verification.

No Pack 2B.2 ref can mark an action, worker, runtime, or mission successful.

## Ordering And Failure Behavior

Preserved:

```text
MissionRunStore sequence = total product observation order
source ledger + source sequence = per-ledger source order
gaps are accepted
duplicate/decreasing source sequence is rejected
projection failure is critical
source ledger latches after projection failure
bridge blocks safely on material projection failure
```

Sequence tracking remains scoped to each `OperatorAgentEventBridge` invocation and source ledger.

Live ordering proven for the governed WorkerCoordinator route:

```text
worker_started
-> live action_routed
-> live action_executed / action_blocked / action_escalated
-> live mission_runner_completed / mission_runner_failed
-> worker_completed
```

Failure containment:

| Failure point | Source event state | Later action behavior | Product result |
| --- | --- | --- | --- |
| `ACTION_ROUTED` projection fails | `ACTION_ROUTED` may exist in source timeline | executor is not invoked | bridge returns blocked with `AGENT_EVENT_SPINE_PERSISTENCE_FAILED` |
| `ACTION_EXECUTED` projection fails | current action already executed and source event may exist | no later plan step starts | bridge returns blocked with `AGENT_EVENT_SPINE_PERSISTENCE_FAILED` |
| later timeline emit after projection failure | rejected before source mutation | no new source event | stable mission trace projection failure |

No rollback is claimed for an action whose `ACTION_EXECUTED` event describes work that already completed.

## Sanitized Examples

Worker success closure:

```json
{
  "event_kind": "worker_completed",
  "activity_outcome": "succeeded",
  "safe_summary": "Agent worker lifecycle closed successfully.",
  "source_ledger": "agent_runtime_event_bus",
  "ref_verification_status": "unverified_source_refs",
  "data_not_authority": true,
  "authority_effect": "none"
}
```

MissionRunner action execution:

```json
{
  "event_kind": "action_executed",
  "activity_outcome": "succeeded",
  "source_ledger": "mission_trace_timeline",
  "action_refs": ["action:..."],
  "ref_verification_status": "unverified_source_refs",
  "data_not_authority": true,
  "authority_effect": "none"
}
```

Blocked action:

```json
{
  "event_kind": "action_blocked",
  "activity_outcome": "blocked",
  "source_ledger": "mission_trace_timeline",
  "safe_summary": "Mission runner action blocked.",
  "ref_verification_status": "unverified_source_refs"
}
```

## Authority And Status Review

Confirmed:

- Material observations never call `MissionKernel.update_status`.
- Worker/step/organ completion does not directly mutate product mission status.
- Product completion still requires the bridge closeout path and FinalGate.
- `AgentExecutionEvent` remains `data_not_authority=True`, `authority_effect="none"`, `can_grant_authority=False`, and `can_execute=False`.
- Browser and memory visibility remain out of scope.

## Tests Added Or Updated

Focused coverage in:

```text
sentinel-control/services/sentinel-core/tests/operator/test_agent_runtime_event_bridge_pack2a.py
```

Pack 2B.2 proof coverage:

- real `OperatorAgentRuntimeBridge -> AgentRuntime -> WorkerCoordinator -> EventBus -> MissionRunStore`;
- neutral `MissionTraceEventSink` injection into `MissionTraceTimeline`;
- `action_routed` visible before executor invocation;
- `action_executed` visible before the next plan step;
- `action_blocked` visible before the next independent plan step;
- `mission_runner_completed` visible before `worker_completed`;
- no post-run duplicate relay;
- projection failure on `ACTION_ROUTED` prevents executor invocation;
- projection failure on `ACTION_EXECUTED` prevents later steps;
- source event remains in `MissionTraceTimeline` when projection fails;
- projection-failure latch rejects later emits before mutation;
- product mission cannot become completed after live projection failure;
- successful worker closure projects `activity_outcome=succeeded`;
- failed worker closure projects `activity_outcome=failed`, not success;
- real controlled capability execution projects material activity;
- real artifact capture projects material activity;
- real organ dispatch skipped projects material activity;
- real `MissionTraceTimeline` action routed/executed/completed projects safely;
- real blocked action projects without raw exception text;
- unsupported projector-only families remain source-only;
- source refs carry `unverified_source_refs`;
- MissionKernel status is not mutated by intermediate observations;
- replay tests continue to prove no runtime/tool/store-write deltas.

## Validation Evidence

Commands run during Pack 2B.2:

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py -k "pack2b2"
```

Result:

```text
8 passed
```

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py
```

Result:

```text
32 passed
```

Additional focused validations are recorded in the final response for the local commit.

## Honest Limits

- `organ_dispatch_completed` remains canonical-reach-proven, while focused end-to-end proof used the skipped branch.
- `controlled_capability_rejected` and `artifact_capture_rejected` remain canonical-reach-proven from existing source paths, not re-proven as the central Pack 2B.2 happy path.
- `organ_receipt_recorded` is not claimed as product-visible in Pack 2B.2.
- Duplicate artifact capture and index-written source events are not claimed as product-visible in Pack 2B.2.
- Browser and memory product projection remain excluded.
- Unified dispatcher execution and Pack 3 are not implemented.

## Next Pack Boundary

Next work remains separate:

```text
Pack 3:
  coordinator dispatch execution
  typed capability adapter connection
  read-only research adapter
  browser/memory product projection only after governed route evidence
```
