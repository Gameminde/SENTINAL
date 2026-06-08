# MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1 Lock Report

Recorded at: 2026-06-08

## Verdict

```text
MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1 = LOCKED
previous_phase = OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1_LOCKED
next_phase = PRODUCTION_MISSION_DAEMON_AND_PROACTIVE_SCHEDULER_V1
roadmap_doctrine = product power under provable authority
```

Sentinel now has a governed local Worker Fleet foundation. A mission can spawn
bounded child workers whose authority is a strict subset of the parent
`MissionAuthorityEnvelope`, whose outputs are typed evidence packets, and whose
results are merged, rejected, or surfaced as conflicts under telemetry and
replay.

## What Was Reused

Existing Sentinel components reused:

```text
MissionKernel
MissionRunStore
DurableWorkflowStore
TelemetryKernel
TelemetryStore
MissionAuthorityEnvelope
Persistent memory refs as context-only data
PowerRuntime and AgentRuntime boundaries
receipt refs
FinalGate certificate refs
operator replay patterns
shared redaction and safety scanners
```

The implementation extends the current runtime spine. It does not create a
parallel mission runtime, a parallel authority model, a parallel telemetry
store, or a new execution surface.

## AgentLab Mechanisms Harvested

AgentLab was used as source-only reference.

```text
Hermes / DeerFlow / OpenJarvis:
  multi-agent decomposition, task graphs, worker coordination, verify loops

Microsoft Agent Framework / JARVIS:
  durable task lifecycle, checkpoint visibility, cancellation semantics

gptme / Agent Zero:
  background task ergonomics and operator-visible progress

oh-my-pi:
  minimized structured worker results, hash-anchored state, typed outputs

OpenClaw:
  broad role inspiration only
```

What was not copied:

```text
no vendor runtime
no vendor bridge
no vendor code
no dependency install
no account or service connection
no provider fallback/AUTO
```

All implementation was rewritten Sentinel-native.

## Runtime Added

```text
WorkerFleetRuntime
WorkerFleetConfig
WorkerRole
WorkerExecutionMode
WorkerTask
WorkerTaskGraph
WorkerSpawnRequest
ChildAuthorityEnvelope
WorkerBudget
WorkerDeadline
WorkerScope
WorkerExecutionContext
WorkerResultContract
WorkerEvidencePacket
WorkerResult
WorkerMergeDecision
WorkerConflictRecord
WorkerFleetRun
WorkerFleetReplayView
WorkerFleetReplayBuilder
```

## Authority Inheritance

Certified worker chain:

```text
parent MissionAuthorityEnvelope
-> child authority derivation
-> child budget/deadline/tool/path/domain scope
-> worker execution context
-> typed worker result
-> evidence refs / receipt refs / FinalGate refs
-> aggregator merge/reject/conflict
```

Closed:

```text
child authority is strict subset of parent = CLOSED
worker authority expansion = BLOCKED
worker root authority inheritance = BLOCKED
worker-created worker spawning = BLOCKED in V1
provider/backend/model override = BLOCKED
worker memory as authority = BLOCKED
worker receipt as authority = BLOCKED
worker FinalGate as future permission = BLOCKED
direct organ bypass from worker context = BLOCKED
```

## Merge And Replay

Worker results are not blindly merged. The aggregator verifies:

```text
result contract identity
worker/task identity
budget/deadline
required evidence refs
receipt refs when required
FinalGate refs when required
authority expansion fields
provider/model override fields
raw secret persistence
conflicting outputs by conflict key
```

Outcomes:

```text
MERGED
REJECTED
NEEDS_RETRY
NEEDS_REPLAN
NEEDS_OPERATOR_CHECKPOINT
CONFLICT
```

Replay reconstructs worker spawn, child authority, worker outputs, merge
decisions, conflicts, telemetry refs, memory refs, receipt refs, and FinalGate
refs without re-executing actions.

## Telemetry And Certified Mode

Worker Fleet requires verified local telemetry in Certified Sentinel Mode.

```text
telemetry unavailable/disabled/tampered = worker fleet blocked
worker_spawn_requested = CLOSED
worker_spawn_blocked = CLOSED
worker_started = CLOSED
worker_completed = CLOSED
worker_failed = CLOSED
worker_killed = CLOSED
worker_timeout = CLOSED
worker_budget_exhausted = CLOSED
worker_authority_derived = CLOSED
worker_authority_rejected = CLOSED
worker_result_submitted = CLOSED
worker_result_merged = CLOSED
worker_result_rejected = CLOSED
worker_conflict_detected = CLOSED
worker parallel efficiency metric = CLOSED
worker conflict rate metric = CLOSED
worker completion rate metric = CLOSED
worker useful minutes metric = CLOSED
worker cost metric = CLOSED
worker retry rate metric = CLOSED
worker merge success rate metric = CLOSED
```

Telemetry remains data. It does not execute, grant authority, unlock
credentials, persist raw prompts, persist raw provider responses, persist raw
reasoning, or become future permission.

## Memory Integration

Workers can carry scoped memory context refs and return memory feedback refs
inside the typed evidence packet. Memory remains context only.

Blocked:

```text
cross-mission authority expansion through memory
worker-generated authority
memory poisoning as permission
raw secret persistence
raw prompt/provider response persistence
```

## Workflow Integration

If a `workflow_id` is supplied in a worker spawn request metadata and a
`DurableWorkflowStore` is provided, Worker Fleet records a checkpoint through
the existing workflow store with receipt, FinalGate, and memory refs.

This is an optional bridge into the existing durable workflow spine, not a new
workflow runtime.

## Self-Audit

Reviewed axes:

```text
direct organ bypass = CLOSED
direct shell/API/channel execution bypass = CLOSED
authority inheritance = CLOSED
worker-as-authority = BLOCKED
memory-as-authority = BLOCKED
receipt-as-authority = BLOCKED
FinalGate-as-future-permission = BLOCKED
telemetry bypass = CLOSED for Certified Mode
raw secret persistence = BLOCKED
raw credential persistence = BLOCKED
raw prompt/provider response/reasoning persistence = BLOCKED
docs overclaim = CLOSED
vendor runtime integration = NOT_STARTED
new actuator family = NOT_STARTED
provider fallback/AUTO = NOT_APPROVED
```

Bug found and fixed:

```text
worker exception blocked_reason originally included raw exception text
fix: persisted blocked_reason is class-only, safe event summary is class-only
test: worker exception path does not persist raw exception or secret
```

## Verification

Targeted Worker Fleet tests:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_mission_worker_fleet_authority_inheritance_v1.py -q -p no:cacheprovider
```

Relevant regression slices passed:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_mission_worker_fleet_authority_inheritance_v1.py sentinel-control/services/sentinel-core/tests/test_observability_telemetry_and_product_power_metrics_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_and_automatic_replan_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_replan_gauntlet_v1.py -q -p no:cacheprovider

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_integrations_v1.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_models_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_mission_kernel_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_cockpit_flow_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_power_runtime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_agentruntime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_replay_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_product_gauntlet_v0.py -q -p no:cacheprovider

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_sentinel_power_runtime_v0.py sentinel-control/services/sentinel-core/tests/test_power_fabric_orchestration_demo.py sentinel-control/services/sentinel-core/tests/test_agent_runtime.py sentinel-control/services/sentinel-core/tests/test_brain_to_organ_runtime_closed_loop.py sentinel-control/services/sentinel-core/tests/test_agent_event_bus.py sentinel-control/services/sentinel-core/tests/test_agent_core_final_gate.py sentinel-control/services/sentinel-core/tests/test_agent_evidence_chain.py sentinel-control/services/sentinel-core/tests/test_delegated_action_gate_model_v0.py sentinel-control/services/sentinel-core/tests/test_gate_sequence_integration.py sentinel-control/services/sentinel-core/tests/test_gate_sequence_runtime_wiring.py -q -p no:cacheprovider

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
```

## Honest Limits

```text
same-process worker foundation only
no production daemon service
no multi-process worker lease yet
no proactive scheduler yet
no durable credential vault
no payment/spend/trading
no desktop/channel/voice expansion
no provider fallback/AUTO
no new actuator family
```

## Next Phase

```text
PRODUCTION_MISSION_DAEMON_AND_PROACTIVE_SCHEDULER_V1
```
