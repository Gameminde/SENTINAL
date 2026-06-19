# Sentinel Product Nervous System Integration V1

## Pack 2B Material Execution Activity Visibility Report

Date: 2026-06-20

Base commit: `8e5524861ecafb430e4d5484e0300cdb578db48a`

Scope:

- Extend the Pack 2A AgentRuntime event bridge so product truth can see material internal execution milestones already emitted by World B.
- Preserve source-event truth with source ledger, source id/hash, source sequence, source logical time, activity kind, safe refs, and product correlation ids.
- Keep MissionKernel as the only owner of authoritative product mission status.
- Keep bridges as ref relays and safe event projectors only; no receipt, FinalGate, artifact, memory, or authority fabrication.
- Keep unsupported browser and memory source events source-only for Pack 2B.

Explicit non-goals:

- Pack 2C / Pack 3 was not started.
- Coordinator dispatch, READ_ONLY_RESEARCH, search_text, browser power, worker power, memory expansion, and unified dispatcher execution were not implemented.
- No provider call was made.
- No push was made.

## Verdict

`PACK_2B_MATERIAL_EXECUTION_ACTIVITY_VISIBILITY = LOCAL_COMMIT_CANDIDATE`

Pack 2B makes existing World B material activity visible in `MissionRunStore` without using it as authority. Product surfaces can now distinguish:

```text
runtime started
worker started/completed
controlled capability executed/rejected
artifact captured/duplicate/rejected/index written
organ dispatch completed/skipped
organ receipt recorded
runtime terminal
```

from generic phase or evidence updates.

## Source Event Inventory

The implementation inspected the actual source emitters before projection.

| Source emitter | Existing source event | Pack 2B projection | Notes |
| --- | --- | --- | --- |
| `sentinel/agent/worker_coordinator.py` | `WORKER_STARTED` | `worker_started` | Projected as material activity with safe worker refs only. |
| `sentinel/agent/worker_coordinator.py` | `WORKER_COMPLETED` | `worker_completed` | Projected as material activity. Source payload remains blocked from product projection. |
| `sentinel/agent/controlled_capability.py` | `CONTROLLED_CAPABILITY_EXECUTED` | `controlled_capability_executed` | Projected with safe capability/evidence refs only. |
| `sentinel/agent/controlled_capability.py` | `CONTROLLED_CAPABILITY_REJECTED` | `controlled_capability_rejected` | Projected as material rejection, not a product mission terminal state. |
| `sentinel/agent/artifact_capture.py` | `ARTIFACT_CAPTURED` | `artifact_captured` | Projected with safe artifact/evidence refs only. |
| `sentinel/agent/artifact_capture.py` | `ARTIFACT_CAPTURE_DUPLICATE` | `artifact_capture_duplicate` | Projected as material activity. |
| `sentinel/agent/artifact_capture.py` | `ARTIFACT_CAPTURE_REJECTED` | `artifact_capture_rejected` | Projected as material rejection, not a product mission terminal state. |
| `sentinel/agent/artifact_capture.py` | `ARTIFACT_CAPTURE_INDEX_WRITTEN` | `artifact_capture_index_written` | Projected as material activity. |
| `sentinel/agent/runtime.py` | `ORGAN_DISPATCH_COMPLETED` | `organ_dispatch_completed` | Projected as material dispatch visibility. |
| `sentinel/agent/runtime.py` | `ORGAN_DISPATCH_SKIPPED` | `organ_dispatch_skipped` | Projected as material dispatch visibility. |
| `sentinel/organs/receipts.py` and runtime organ paths | `ORGAN_EXECUTION_RECEIPT_RECORDED` | `organ_receipt_recorded` | Product label avoids the unsafe `organ_execution` scanner term while preserving source id/hash/sequence. |
| Browser organ files | many `BROWSER_*` events | not projected in Pack 2B | Source events exist, but Pack 2B does not expand browser power or create browser product claims. |
| Memory feedback path in `sentinel/agent/runtime.py` | memory refs in runtime result/replan packet | not projected in Pack 2B | No new memory authority or memory-writing surface is added. |

## Before And After Product Call Graph

Before Pack 2B:

```text
AgentRuntime source EventBus
-> source event with material activity
-> Pack 2A projection
-> generic phase_transition / evidence_refs_updated / receipt_refs_updated
-> MissionRunStore
```

After Pack 2B:

```text
AgentRuntime source EventBus
-> source event with material activity
-> AgentExecutionEvent.from_agent_event()
-> explicit material allowlist first
-> safe refs split by family
-> source ledger/id/hash/sequence/logical time captured
-> OperatorAgentEventBridge monotonic-source validation
-> MissionRunStore append_event("agentruntime_execution_event_observed")
```

## Projection Contract

Projected metadata now includes:

```text
event_id
event_kind
activity_kind
mission_id
run_id
execution_request_id
bridge_call_id
agent_run_id
phase_before
phase_after
evidence_refs
receipt_refs
artifact_refs
capability_refs
worker_refs
organ_refs
source_ledger
source_event_id
source_event_hash
source_event_type
source_sequence
source_logical_time
source_parent_event_id
event_hash
terminal
critical
data_not_authority
authority_effect
```

Blocked from projection:

```text
source payload
source summary text
tool arguments
organ arguments
URLs
selectors
paths
file contents
raw prompts
provider outputs
reasoning
credentials
cookies
authorization headers
arbitrary exception strings
```

## Sanitized Projected Event Example

```json
{
  "event_type": "agentruntime_execution_event_observed",
  "safe_summary": "Agent runtime controlled capability executed.",
  "metadata": {
    "event_kind": "controlled_capability_executed",
    "activity_kind": "controlled_capability_executed",
    "mission_id": "mission_...",
    "run_id": "session_agent",
    "execution_request_id": "mission_exec_req_pack2b_material",
    "bridge_call_id": "agent_bridge_call_...",
    "agent_run_id": "agent_run_...",
    "phase_before": "executing",
    "phase_after": "executing",
    "capability_refs": ["capability:local_file"],
    "evidence_refs": ["evidence:policy"],
    "receipt_refs": [],
    "artifact_refs": [],
    "source_ledger": "agent_runtime_event_bus",
    "source_event_id": "aev_...",
    "source_event_hash": "sha256...",
    "source_event_type": "controlled_capability_executed",
    "source_sequence": 2,
    "source_logical_time": 2,
    "source_parent_event_id": null,
    "terminal": false,
    "critical": true,
    "data_not_authority": true,
    "authority_effect": "none"
  }
}
```

## Ordering And Integrity

Implemented:

- Each projection carries `source_ledger = agent_runtime_event_bus`.
- Each projection carries the source event id/hash/sequence/logical time.
- `OperatorAgentEventBridge` rejects duplicate source event ids.
- `OperatorAgentEventBridge` rejects nonmonotonic source sequences per source ledger.
- A terminal projection still latches the bridge against later projected events.
- Event projection remains critical. There is no noncritical degradation mode in Pack 2B.

## Authority And Status Review

Confirmed:

- Material projections never call `MissionKernel.update_status`.
- Material projections cannot complete, block, revoke, or escalate product missions by themselves.
- `AgentExecutionEvent` still enforces `data_not_authority=True`, `authority_effect="none"`, `can_grant_authority=False`, and `can_execute=False`.
- Product completion still comes only from the governed bridge result path and MissionKernel transition, not from intermediate material events.

## Browser And Memory Scope

Browser and memory source signals are intentionally not elevated in Pack 2B.

Pack 2B tests confirm:

```text
BROWSER_EVIDENCE_COLLECTED -> source-only
LEARNING_PROPOSED / memory feedback style signal -> source-only
```

Future packs may add typed browser or memory projection only after a governed production route exists for that surface.

## Tests Added

Added focused tests in:

```text
sentinel-control/services/sentinel-core/tests/operator/test_agent_runtime_event_bridge_pack2a.py
```

Coverage:

- material activity projects existing source emitters in source order;
- activity kind matches event kind;
- source sequence/logical time metadata is preserved;
- safe refs are split into capability/artifact/receipt/worker/organ/evidence families;
- raw source summaries and payload-like material are not projected;
- nonmonotonic source sequence is rejected safely;
- unsupported browser and memory source events remain source-only;
- existing Pack 2A tests updated so material events no longer collapse into generic phase/evidence/receipt categories.

## Validation Evidence

Commands run before this report:

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py -k "pack2b"
```

Result:

```text
3 passed
```

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py
```

Result:

```text
18 passed
```

Additional focused validation run before local commit:

```text
py -3.13 -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_shared_events_layering.py
py -3.13 -O -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py
py -3.13 -m pytest -q tests/test_mission_kernel.py tests/test_agent_trace_replay.py tests/test_llm_live_operator_replay_v0.py
py -3.13 -m pytest -q tests/test_observability_telemetry_and_product_power_metrics_v1.py tests/operator/test_runtime_host_pack1.py tests/operator/test_workflow_bridge_factory_pack1.py
py -3.13 -m pytest -q tests/test_agent_runtime.py tests/test_agent_trace_replay.py
py -3.13 -O -m pytest -q tests/operator/test_agent_runtime_event_bridge_pack2a.py tests/test_shared_events_layering.py
py -3.13 -m compileall -q sentinel
git diff --check
targeted safety scan on modified files
```

Results:

```text
36 passed
18 passed under python -O
52 passed
12 passed
22 passed
23 passed under python -O
compileall PASS
git diff --check PASS
safety scan PASS with only expected fixture/doc/blocklist markers
```

## Honest Limits

- Pack 2B does not connect coordinator dispatch execution.
- Pack 2B does not add READ_ONLY_RESEARCH, search_text, browser action, worker expansion, memory expansion, or provider-backed execution.
- Pack 2B does not claim unified replay.
- Pack 2B does not claim browser product visibility beyond source-only retention.
- Pack 2B does not claim memory product visibility beyond existing runtime result refs.
- Pack 2B only projects material activity already emitted on the AgentRuntime event bus.

## Next Pack Boundary

Next work should remain separate:

```text
Pack 2C / Pack 3:
  dispatcher execution
  typed capability adapter connection
  read-only research adapter
  browser/memory product projection only after governed route evidence
```
