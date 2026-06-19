# Sentinel Product Nervous System Integration V1

## Pack 2A AgentRuntime Event Bridge Foundation Report

Date: 2026-06-20

Base commit: `3d4ae93362990a5af34a1d9b635d3438b12c4cca`

Scope:

- Project safe `AgentRuntime` execution events into the canonical `MissionRunStore` while `runtime.run()` is executing.
- Keep World B (`sentinel.agent` / `sentinel.shared`) independent from `MissionRunStore`, `MissionKernel`, and operator bridge imports.
- Keep product mission status owned by `MissionKernel`.
- Treat projected events as observations only: data, refs, hash anchors, and telemetry-friendly state, not authority.
- Fail closed when critical execution-event persistence or correlation fails.

Explicit non-goals:

- Pack 2B was not started.
- Coordinator dispatch was not implemented.
- MissionRunner organs were not connected.
- `READ_ONLY_RESEARCH`, `search_text`, final-report lane, unified capability catalog, and unified dispatcher execution were not added.
- No provider call was made.
- No push was made.

## Verdict

`PACK_2A_AGENT_RUNTIME_EVENT_BRIDGE_FOUNDATION = LOCAL_COMMIT_CANDIDATE`

Pack 2A adds the first product-visible AgentRuntime event spine. The operator product ledger can now see runtime execution progress in source order without reconstructing it from the final return object.

## Before And After Call Graph

Before Pack 2A:

```text
OperatorAgentRuntimeBridge.run()
-> AgentRuntime.run()
-> AgentRuntime local EventBus emits events internally
-> AgentRuntime returns AgentRunResult
-> OperatorAgentRuntimeBridge appends one final agentruntime_result
```

After Pack 2A:

```text
OperatorAgentRuntimeBridge.run()
-> create bridge_call_id / agent_run_id
-> OperatorAgentEventBridge(store, mission_id, run_id, request_id, ids)
-> AgentRuntime.run(... execution_event_sink=bridge ...)
-> AgentRuntime local EventBus.append(source AgentEvent)
-> AgentExecutionEvent.from_agent_event(...)
-> OperatorAgentEventBridge validates mission/run/request/source correlation
-> MissionRunStore.append_event("agentruntime_execution_event_observed")
-> AgentRuntime returns AgentRunResult
-> OperatorAgentRuntimeBridge appends final agentruntime_result
```

Backward compatibility:

```text
runtime.run(envelope, user_input)
```

is still used when a runtime does not accept `execution_event_sink`, preserving existing fake/injected runtime tests.

## Event Contract Added

Added `sentinel.shared.execution_events`:

```text
AgentExecutionEventKind
AgentExecutionEvent
ExecutionEventSink
```

Supported safe projection kinds:

```text
runtime_started
phase_transition
runtime_completed
runtime_blocked
runtime_failed
runtime_revoked
runtime_escalated
evidence_refs_updated
receipt_refs_updated
```

Safe metadata contains only:

```text
event ids
mission id
run id
execution request id
bridge call id
agent run id
phase before/after
evidence refs
receipt refs
source event id
source event hash
projection event hash
terminal/critical booleans
data-not-authority markers
```

Blocked from projection:

```text
source event payload
raw prompt
raw provider response
raw reasoning
credentials
authorization material
full tool arguments
file contents
```

## Sanitized Projected Event Example

```json
{
  "event_type": "agentruntime_execution_event_observed",
  "safe_summary": "Agent entered execution phase.",
  "metadata": {
    "event_kind": "phase_transition",
    "mission_id": "mission_...",
    "run_id": "session_agent",
    "execution_request_id": "mission_exec_req_pack2a",
    "bridge_call_id": "agent_bridge_call_...",
    "agent_run_id": "agent_run_...",
    "phase_before": "initialized",
    "phase_after": "executing",
    "evidence_refs": ["evidence:agent"],
    "receipt_refs": [],
    "source_event_id": "aev_...",
    "source_event_hash": "sha256...",
    "event_hash": "sha256...",
    "terminal": false,
    "critical": true,
    "data_not_authority": true,
    "authority_effect": "none"
  }
}
```

## State And Authority Review

Confirmed:

- `OperatorAgentEventBridge` never calls `MissionKernel.update_status`.
- Projected runtime events are appended as canonical `MissionRunStore` observation events only.
- Product terminality still comes from `OperatorAgentRuntimeBridge` interpreting `AgentRunResult` and then asking `MissionKernel` to transition, when `update_mission_status=True`.
- `AgentExecutionEvent` validates `data_not_authority=True`, `authority_effect="none"`, `can_grant_authority=False`, and `can_execute=False`.
- Event projection cannot create or expand `MissionAuthorityEnvelope`.

## Terminal Ordering And Deduplication

Implemented:

- At most one projected runtime terminal event per bridge call.
- A source event after a projected terminal event raises `AGENT_EVENT_SPINE_PERSISTENCE_FAILED`.
- Duplicate source event ids are rejected.
- Cross-mission source events are rejected.
- Correlation is checked for mission id, run id, execution request id, bridge call id, agent run id, source event id, and source event hash.

## Persistence Failure Behavior

Critical projection persistence failure blocks safely:

```text
blocked_reason = AGENT_EVENT_SPINE_PERSISTENCE_FAILED
```

The bridge records a sanitized `agentruntime_blocked` event and does not include raw exception text.

## Store Safety Adjustment

`MissionRunStore` and `MissionEvent` now allow a boolean metadata key:

```text
terminal
```

only for:

```text
event_type == "agentruntime_execution_event_observed"
```

This key means "AgentRuntime reached an absorbing runtime state"; it is not the shell/terminal action surface blocked by the shared safety scanner. All other metadata remains scanned normally.

## Files Changed

Created:

```text
sentinel-control/services/sentinel-core/sentinel/shared/execution_events.py
sentinel-control/services/sentinel-core/sentinel/operator/agent_event_bridge.py
sentinel-control/services/sentinel-core/tests/operator/test_agent_runtime_event_bridge_pack2a.py
sentinel-control/docs/reviews/SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_PACK2A_AGENT_RUNTIME_EVENT_BRIDGE_REPORT.md
```

Updated:

```text
sentinel-control/services/sentinel-core/sentinel/shared/events.py
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/agent_bridge.py
sentinel-control/services/sentinel-core/sentinel/operator/models.py
sentinel-control/services/sentinel-core/sentinel/operator/store.py
```

## Focused Tests

RED result before implementation:

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py
ERROR: ModuleNotFoundError: No module named 'sentinel.operator.agent_event_bridge'
```

GREEN results:

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py
6 passed

py -3.13 -m pytest -q tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/operator/test_agent_runtime_event_bridge_pack2a.py
19 passed

py -3.13 -m pytest -q tests/test_agent_trace_replay.py tests/test_shared_events_layering.py
12 passed

py -3.13 -O -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py tests/test_llm_live_operator_agentruntime_bridge_v0.py
19 passed

py -3.13 -m pytest -q tests/test_agent_runtime.py tests/test_agent_trace_replay.py tests/test_shared_events_layering.py
27 passed

py -3.13 -m pytest -q tests/test_observability_telemetry_and_product_power_metrics_v1.py tests/test_llm_live_operator_agentruntime_bridge_v0.py
19 passed

py -3.13 -m pytest -q tests/operator/test_runtime_host_pack1.py tests/operator/test_workflow_bridge_factory_pack1.py
6 passed

py -3.13 -m pytest -q tests/test_mission_kernel.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_llm_live_operator_replay_v0.py
69 passed

py -3.13 -m pytest -q tests/test_agent_core_final_gate.py tests/test_final_gate_terminality.py tests/test_final_gate_registry.py tests/test_final_gate_determinism.py
66 passed
```

One attempted command used stale file names and was replaced with actual repository test files:

```text
tests/operator/test_mission_lifecycle_service_pack1.py not found
tests/test_operator_replay.py not found
```

No provider tests or real model calls were run.

## Remaining Limits

- Pack 2A projects AgentRuntime event observations only.
- No production dispatcher execution is connected yet.
- No MissionRunner organ path is connected yet.
- No unified replay or capability catalog is implemented in this pack.
- Legacy paths classified by prior packs are not migrated by this pack.

## Next Pack

Next work remains Pack 2B or the next explicitly approved nervous-system integration slice. Pack 2A does not authorize coordinator dispatch, provider calls, browser expansion, or broader capability work.
