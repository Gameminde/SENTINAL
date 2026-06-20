# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# Pack 3 Executable Coordinator Dispatcher And Read-Only Research Report

## Verdict

`PACK_3_EXECUTABLE_COORDINATOR_DISPATCHER_AND_READ_ONLY_RESEARCH_ROUTE` is locally implemented for one capability:

```text
capability_id = read_only_research
operation = inspect_repository
adapter_id = read_only_research_adapter
```

No browser, desktop, channel, credential, finance, voice, memory, or provider surface was connected in this pack.

## Before Product Call Graph

```text
CLI / cockpit
-> SentinelRuntimeHost
-> MissionLifecycleService
-> immutable MissionExecutionRequest
-> daemon claim
-> placeholder / deterministic pump boundary
```

The coordinator existed as data-only route selection, and runtime connections described maturity, but no Pack 3 product route executed an adapter through a dispatcher.

## After Product Call Graph

```text
CLI / application
-> SentinelRuntimeHost
-> MissionLifecycleService
-> immutable MissionExecutionRequest
-> daemon claim
-> MissionExecutionCoordinator.decide()
-> persisted MissionExecutionDecision
-> UnifiedExecutionDispatcher
-> explicit adapter registry
-> ReadOnlyResearchAdapter
-> ReadOnlyProductionSpineSession
-> list_directory / read_file_segment / search_text / finish_exploration
-> separate ReadOnlyReportClient lane
-> sanitized report artifact
-> read-only receipt / failed-attempt evidence
-> read-only FinalGate
-> dispatch closeout
-> MissionKernel terminal transition
-> replay without re-execution
```

## Component Classification

| Component | Classification | Notes |
| --- | --- | --- |
| `MissionKernel` | REUSED | Owns authoritative mission status. |
| `MissionRunStore` | REUSED | Owns canonical event ordering and artifacts. |
| `MissionLifecycleService` | EXTENDED | Derives `DISPATCH_DECIDED`, `DISPATCH_RUNNING`, `COMPLETED`, `BLOCKED` from dispatch events. |
| `MissionExecutionRequest` | REUSED | The dispatcher consumes the persisted immutable request; no second request model was added. |
| `MissionExecutionCoordinator` | EXTENDED | Data-only, hash-bound route decisions over the canonical request. |
| `UnifiedExecutionDispatcher` | NEW | Owns live adapter resolution, decision persistence, dispatch closeout, and terminal handoff. |
| `ReadOnlyResearchAdapter` | NEW | Wraps the existing read-only production spine. |
| `ReadOnlyProductionSpineSession` | EXTENDED | Adds `search_text`, `finish_exploration`, separate report lane, and optional proof-only mode for dispatcher ownership. |
| `RuntimeHost` | EXTENDED | Owns coordinator, dispatcher, adapter registry, and deterministic daemon pump. |
| `CLI cockpit route` | EXTENDED | Reports dispatch status/adapter safely when the host pumps a mission. |
| Other Sentinel capabilities | NOT_CONNECTED | Left as legacy/internal/not connected for later packs. |

## Coordinator Decision Contract

`MissionExecutionCoordinator` now accepts the persisted `MissionExecutionRequest` and emits a serializable `MissionExecutionDecision` with:

```text
decision_id
mission_id
execution_request_id
capability_id
operation
route
adapter_id
authority_envelope_ref
connection_profile_hash
rejection_reason
decision_hash
data_not_authority = true
can_execute = false
```

The decision contains no live bridge, runtime instance, callable, open file, provider client, credential, full parameters, or raw user text. It is data only and cannot grant authority.

Example route:

```json
{
  "status": "routed",
  "capability_id": "read_only_research",
  "operation": "inspect_repository",
  "route": "agent_runtime",
  "adapter_id": "read_only_research_adapter",
  "can_execute": false
}
```

## Dispatcher Adapter Registry

`UnifiedExecutionDispatcher` persists the coordinator decision before adapter execution, then resolves exactly one adapter from `UnifiedExecutionAdapterRegistry`.

Fail-closed cases include:

```text
coordinator rejection
unknown adapter
adapter id mismatch
capability mismatch
operation mismatch
request state mismatch
authority ref mismatch
adapter exception
adapter result correlation failure
```

No silent fallback to legacy workflow, direct kernel execution, PowerRuntime, another adapter, AUTO routing, or provider-native tools was added.

## Request-State Mapping

Request state is derived from canonical events:

```text
mission_execution_request_prepared -> PREPARED
mission_queued -> QUEUED
mission_execution_request_claimed -> CLAIMED
mission_dispatch_decision_persisted -> DISPATCH_DECIDED
mission_dispatch_started -> DISPATCH_RUNNING
mission_dispatch_closeout_persisted(status=completed) -> COMPLETED
mission_dispatch_closeout_persisted(status=blocked/failed) -> BLOCKED
```

The immutable request artifact is not rewritten.

## Authority Validation

The dispatcher validates that the active authority envelope reference matches the request and decision before adapter execution. The read-only adapter then relies on the existing spine and Gate behavior for allowed actions. Revoked or expired authority blocks before dispatch.

## Adapter Proof Ownership

| Proof Surface | Owner | Dispatcher Behavior |
| --- | --- | --- |
| Successful read-only action receipts | Read-only spine | Relays refs only. |
| Failed action-attempt evidence | Read-only spine | Relays refs only. |
| Read-only FinalGate certificates | Read-only spine | Relays refs only. |
| Dispatch decision artifact | Dispatcher | Persists before adapter execution. |
| Dispatch closeout artifact | Dispatcher | Persists normalized result and terminal status. |
| Mission terminal transition | Dispatcher for Pack 3 route | Occurs after dispatch closeout and accepted FinalGate. |

The adapter does not duplicate receipts, and the dispatcher does not create replacement FinalGate certificates.

## Bounded `search_text`

The read-only spine now supports bounded `search_text`:

```text
snapshot-root bounded
read-only
literal substring search
query length max 80 chars
file inspection max 80 files
match max 40
safe excerpt max 240 chars
deterministic path ordering
no symlink follow
sensitive/excluded paths blocked
no shell or subprocess execution
```

Example safe observation shape:

```json
{
  "path": ".",
  "query_hash": "hash",
  "matches": [
    {"path": "src/commands.py", "line": 1, "excerpt_hash": "hash", "safe_excerpt": "def register_commands(...)"}
  ]
}
```

## Separate Report Lane

Exploration decisions remain one-action read-only decisions. The final report is produced through `ReadOnlyReportClient` after `finish_exploration`, not parsed as an action decision.

Report validation requires:

```text
nonempty report
known evidence refs only
no unsupported mutation/external action claim
at least one useful observation
safety scan pass
report artifact hash verification
```

The persisted report is a sanitized product artifact, not a raw provider response. No provider wrapper, raw prompt, raw reasoning, credential, or authorization header is persisted.

## Live Event Sequence

The Pack 3 end-to-end fixture observed:

```text
mission_execution_request_claimed
mission_dispatch_decision_persisted
mission_dispatch_started
read_only_spine_session_started
read_only_spine_action_receipted
read_only_report_generation_started
read_only_report_generation_completed
read_only_spine_finalgate_certified
mission_dispatch_closeout_persisted
mission_completed
```

## Terminal Closeout Rules

```text
coordinator decision != execution success
dispatcher success != mission success
adapter return != mission success
report generated != mission success
```

`MissionKernel` reaches `COMPLETED` only after dispatch closeout, required receipt refs, report artifact validation, and accepted FinalGate. Blocked routes end with `BLOCKED`, rejected FinalGate, no fabricated successful receipt, and one product terminal path.

## Replay Proof

Pack 3 uses existing replay builder behavior. The focused end-to-end test records event count before replay, builds replay, and verifies event count is unchanged and `reexecuted_actions` is false.

Replay does not call the coordinator, dispatcher, adapter, runtime, model, tool, report lane, receipt writer, FinalGate writer, or MissionKernel transitions.

## Local End-To-End Mission

Fixture mission:

```text
Inspect a disposable repository.
Map its major packages.
Find where command registration occurs.
Identify one architecture risk.
Produce an evidence-linked technical report.
```

Path proven:

```text
RuntimeHost
-> lifecycle
-> request
-> daemon pump
-> coordinator
-> dispatcher
-> read-only adapter
-> list/search/read
-> report lane
-> receipts
-> FinalGate
-> MissionKernel completed
-> replay no-reexecution
```

Workspace mutation check passed with the original fixture files and directories unchanged.

## Remaining Legacy / Not Connected Routes

```text
browser = NOT_CONNECTED
desktop = NOT_CONNECTED
channels = NOT_CONNECTED
credentials = NOT_CONNECTED
finance = NOT_CONNECTED
voice = NOT_CONNECTED
memory write expansion = NOT_CONNECTED
multi-surface unified replay = NOT_CONNECTED
legacy direct internal paths = LEGACY_INTERNAL / TEST_ONLY as previously classified
```

## Validation

Focused tests run:

```text
py -3.13 -m pytest -q tests/operator/test_product_nervous_system_pack3.py
7 passed

py -3.13 -m pytest -q tests/operator/test_mission_execution_coordinator.py tests/operator/test_runtime_host_pack1.py tests/test_cli_runtime_host_product_wiring_pack1b.py
16 passed

py -3.13 -m pytest -q tests/test_real_model_read_only_operator_production_spine_v1.py tests/operator/test_agent_runtime_event_bridge_pack2a.py tests/test_mission_kernel.py tests/test_llm_live_operator_replay_v0.py
passed

py -3.13 -O -m pytest -q tests/operator/test_product_nervous_system_pack3.py tests/operator/test_mission_execution_coordinator.py tests/operator/test_runtime_host_pack1.py tests/test_cli_runtime_host_product_wiring_pack1b.py
23 passed

py -3.13 -m pytest -q tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_connection_registry.py
12 passed

py -3.13 -m pytest -q tests/operator/test_product_nervous_system_pack3.py tests/operator/test_mission_execution_coordinator.py tests/operator/test_runtime_host_pack1.py tests/test_cli_runtime_host_product_wiring_pack1b.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_connection_registry.py
35 passed
```
No real provider call was made.
