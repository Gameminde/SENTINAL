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

Pack 2A.1 correction:

```text
PACK_2A_1_MANDATORY_VISIBILITY_AND_EVENT_TRUTH_FIX = LOCAL_COMMIT_CANDIDATE
```

Pack 2A.1 tightens the event spine truth contract:

- production/governed `OperatorAgentRuntimeBridge` routes require explicit event-sink support by default;
- the read-only production spine internal runtime now accepts the sink and emits source start/terminal events instead of relying on legacy mode;
- sink-disabled execution is available only through explicit `LEGACY_EXPLICITLY_DISABLED` mode and is classified `TEST_ONLY` or `LEGACY_INTERNAL`;
- custom runtimes accepting only `**kwargs` are not treated as sink-capable;
- projected summaries are deterministic and are not copied from source `AgentEvent.summary`;
- unsupported source events are retained in World B but are not projected into product truth;
- source and operator ledgers are not atomic: a source event may already exist when projection fails, but the World B ledger latches that failure and rejects every later append before source mutation;
- every Pack 2A projection is critical. Noncritical degradation behavior is intentionally not claimed in this pack.

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

Pack 2A original backward compatibility:

```text
runtime.run(envelope, user_input)
```

Pack 2A.1 correction:

```text
runtime.run(envelope, user_input)
```

is no longer used silently on governed routes. It is allowed only when the caller explicitly constructs:

```text
projection_mode = LEGACY_EXPLICITLY_DISABLED
```

Remaining sink-disabled route classifications:

```text
LEGACY_INTERNAL:
  old/internal callers may use explicit LEGACY_EXPLICITLY_DISABLED while being migrated.

TEST_ONLY:
  older fake runtime tests that do not model AgentRuntime event projection use explicit LEGACY_EXPLICITLY_DISABLED.

CUSTOM_EXPLICIT:
  custom runtimes may run only if they either expose the explicit execution_event_sink parameter or opt into explicit legacy mode outside product routes.

DISABLED:
  implicit signature fallback and **kwargs-only sink inference are disabled.
```

## Event Contract Added

Added `sentinel.shared.execution_events`:

```text
AgentExecutionEventKind
AgentExecutionEvent
ExecutionEventSink
```

Supported safe projection allowlist:

```text
agent_initialized -> runtime_started
known terminal AgentEvent -> matching runtime terminal kind
validated phase_before != phase_after -> phase_transition
safe receipt refs present -> receipt_refs_updated
safe evidence refs present -> evidence_refs_updated
otherwise -> no product projection
```

Unknown source events no longer default to `phase_transition`.

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
  "safe_summary": "Agent runtime phase changed from initialized to executing.",
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
- A source event after a source terminal event is rejected by `EventBus` before source mutation.
- A critical projection failure leaves the already-appended source event intact, latches World B, and rejects every later source append before mutation.
- Duplicate source event ids are rejected.
- Cross-mission source events are rejected.
- Correlation is checked for mission id, run id, execution request id, bridge call id, agent run id, source event id, and source event hash.

## Persistence Failure Behavior

Critical projection persistence failure blocks safely:

```text
blocked_reason = AGENT_EVENT_SPINE_PERSISTENCE_FAILED
```

The bridge records a sanitized `agentruntime_blocked` event and does not include raw exception text.

Noncritical degradation:

```text
not implemented in Pack 2A.1
```

All projected Pack 2A event kinds are truthfully marked critical. This avoids a false noncritical/critical distinction until a real degraded projection path is designed and tested.

## Deterministic Summary And Ref Safety

Pack 2A.1 no longer projects source summary text. Summaries are constructed only from trusted projection kind and validated phase enums:

```text
runtime_started -> "Agent runtime started."
phase_transition -> "Agent runtime phase changed from <before> to <after>."
receipt_refs_updated -> "Agent runtime receipt references were updated."
evidence_refs_updated -> "Agent runtime evidence references were updated."
runtime_failed -> "Agent runtime reached failed terminal state."
```

Evidence and receipt refs are bounded and sanitized before projection:

```text
max refs per kind = 8
max ref length = 80
allowed grammar = [A-Za-z][A-Za-z0-9_.:-]{0,79}
blocked markers include URLs, paths, whitespace, query strings, authorization, tokens, secrets, raw_prompt, raw_response, provider_response, and reasoning
unsafe refs are omitted from the projection
```

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
sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py
sentinel-control/services/sentinel-core/sentinel/operator/models.py
sentinel-control/services/sentinel-core/sentinel/operator/store.py
```

Pack 2A.1 additionally updated focused compatibility tests:

```text
sentinel-control/services/sentinel-core/tests/operator/test_agent_runtime_event_bridge_pack2a.py
sentinel-control/services/sentinel-core/tests/test_llm_live_operator_agentruntime_bridge_v0.py
sentinel-control/services/sentinel-core/tests/test_observability_telemetry_and_product_power_metrics_v1.py
sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_replan_gauntlet_v1.py
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

Pack 2A.1 focused GREEN results:

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_shared_events_layering.py
PASS

py -3.13 -m pytest -q tests/test_mission_kernel.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_agent_trace_replay.py tests/test_llm_live_operator_replay_v0.py
PASS

py -3.13 -O -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py tests/test_llm_live_operator_agentruntime_bridge_v0.py
PASS

py -3.13 -m pytest -q tests/test_real_model_read_only_operator_production_spine_v1.py
PASS

py -3.13 -m pytest -q tests/test_durable_mission_workflow_replan_gauntlet_v1.py
PASS

py -3.13 -m pytest -q tests/test_observability_telemetry_and_product_power_metrics_v1.py tests/test_llm_live_operator_agentruntime_bridge_v0.py
PASS

py -3.13 -m pytest -q tests/test_agent_runtime.py tests/test_agent_trace_replay.py tests/test_shared_events_layering.py
PASS

py -3.13 -m pytest -q tests/operator/test_runtime_host_pack1.py tests/operator/test_workflow_bridge_factory_pack1.py
PASS

py -3.13 -m compileall -q sentinel
PASS

git diff --check
PASS
```

## Remaining Limits

- Pack 2A projects AgentRuntime event observations only.
- No production dispatcher execution is connected yet.
- No MissionRunner organ path is connected yet.
- No unified replay or capability catalog is implemented in this pack.
- Legacy paths classified by prior packs are not migrated by this pack.

## Next Pack

Next work remains Pack 2B or the next explicitly approved nervous-system integration slice. Pack 2A does not authorize coordinator dispatch, provider calls, browser expansion, or broader capability work.
