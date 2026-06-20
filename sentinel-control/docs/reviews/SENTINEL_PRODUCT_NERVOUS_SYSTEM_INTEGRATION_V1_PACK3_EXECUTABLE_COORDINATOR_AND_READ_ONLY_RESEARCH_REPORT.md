# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# Pack 3 Executable Coordinator Dispatcher And Read-Only Research Report

## Verdict

`PACK_3_EXECUTABLE_COORDINATOR_DISPATCHER_AND_READ_ONLY_RESEARCH_ROUTE` proved the first deterministic executable product vertical slice for exactly one capability:

```text
capability_id = read_only_research
operation = inspect_repository
adapter_id = read_only_research_adapter
```

`PACK_3_1_REAL_MODEL_WIRING_AND_PROOF_CLOSEOUT_FIX` then closes the focused Pack 3 gap: governed LLM product mode now injects provider-backed read-only exploration and report clients from the explicit `UserModelContract`, and dispatcher completion is gated on persisted proof verification rather than trusted refs.

No browser, desktop, channel, credential, finance, voice, memory, or additional capability surface was connected. No real provider call was made in Pack 3.1.

## Before Product Call Graph

```text
CLI / cockpit
-> SentinelRuntimeHost
-> MissionLifecycleService
-> immutable MissionExecutionRequest
-> daemon claim
-> placeholder / deterministic pump boundary
```

Before Pack 3, the coordinator was data-only route selection and runtime connections described maturity, but no product route executed an adapter through a dispatcher.

Before Pack 3.1, Pack 3 had a deterministic vertical slice, but governed LLM product mode still used deterministic Pack 3 execution clients after cockpit mission interpretation. A real provider could understand the cockpit mission while not controlling exploration or the final report lane.

## After Product Call Graph

```text
CLI / application
-> validated UserModelContract
-> cockpit mission understanding
-> SentinelRuntimeHost
-> read-only provider execution factories
-> MissionLifecycleService
-> immutable MissionExecutionRequest
-> daemon claim
-> MissionExecutionCoordinator.decide()
-> persisted MissionExecutionDecision
-> UnifiedExecutionDispatcher
-> explicit adapter registry
-> ReadOnlyResearchAdapter
-> ReadOnlyProductionSpineSession
-> ReadOnlyProviderDecisionClient
-> governed list_directory / read_file_segment / search_text / finish_exploration
-> separate ReadOnlyProviderReportClient lane
-> sanitized report artifact
-> read-only receipt / failed-attempt evidence
-> read-only FinalGate
-> dispatcher proof verification
-> dispatch closeout
-> MissionKernel terminal transition
-> replay without re-execution
```

## Provider-Backed Product Wiring

Governed LLM mode now uses the explicit contract already selected by `--model-contract`:

```text
CLI --model-contract
-> validated UserModelContract
-> OperatorCatalogModelClient
-> SentinelRuntimeHost factories
-> ReadOnlyProviderDecisionClient
-> ReadOnlyResearchAdapter
-> ReadOnlyProviderReportClient
```

The exploration lane and report lane are separate calls. The focused CLI test proves:

```text
cockpit model call
-> exploration_decision call
-> exploration_decision call
-> final_report call
```

All calls use the same explicit `user_model_contract_id` in the current Pack 3.1 product wiring proof. A future pack may support explicitly declared separate contracts, but Pack 3.1 does not silently select or override model identity.

Provider-backed read-only clients:

```text
use no provider-native tools
use no fallback / AUTO
use bounded timeout and output budgets
keep prompt text in memory only
strip provider wrapper / raw response / reasoning-like keys before typed validation
persist no raw prompt, raw provider response, raw reasoning, credential, or authorization header
```

Deterministic clients remain available only for deterministic tests, explicit injected local tests, and `DETERMINISTIC_TEST` behavior. `SentinelRuntimeHost(require_read_only_model_clients=True)` fails closed if either provider execution factory is missing.

## Component Classification

| Component | Classification | Notes |
| --- | --- | --- |
| `MissionKernel` | REUSED | Owns authoritative mission status. |
| `MissionRunStore` | REUSED | Owns canonical event ordering and artifacts. |
| `MissionLifecycleService` | EXTENDED | Derives `DISPATCH_DECIDED`, `DISPATCH_RUNNING`, `COMPLETED`, and `BLOCKED` from dispatch events. |
| `MissionExecutionRequest` | REUSED | The dispatcher consumes the persisted immutable request; no second request model was added. |
| `MissionExecutionCoordinator` | EXTENDED | Data-only, hash-bound route decisions over the canonical request. |
| `UnifiedExecutionDispatcher` | EXTENDED | Owns adapter resolution, decision persistence, proof verification, dispatch closeout, and terminal handoff. |
| `ReadOnlyResearchAdapter` | EXTENDED | Wraps the existing read-only production spine. |
| `ReadOnlyProviderDecisionClient` | NEW | Provider-backed exploration lane built from the explicit `UserModelContract`. |
| `ReadOnlyProviderReportClient` | NEW | Separate provider-backed report lane built from the explicit `UserModelContract`. |
| `ReadOnlyProductionSpineSession` | EXTENDED | Supports `search_text`, `finish_exploration`, separate report lane, and proof-only mode for dispatcher ownership. |
| `SentinelRuntimeHost` | EXTENDED | Owns coordinator, dispatcher, adapter registry, and deterministic daemon pump; enforces provider execution factories in LLM mode. |
| `CLI cockpit route` | EXTENDED | Builds Pack 3 execution factories from the explicit model contract and reports dispatch status safely. |
| Other Sentinel capabilities | NOT_CONNECTED | Left as legacy/internal/not connected for later packs. |

## Coordinator Decision Contract

`MissionExecutionCoordinator` accepts the persisted `MissionExecutionRequest` and emits a serializable `MissionExecutionDecision` with:

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
request hash mismatch
decision hash mismatch
authority mission mismatch
authority ref mismatch
revoked or expired authority
decision persistence failure
adapter exception
adapter result correlation failure
persisted proof verification failure
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

## Authority Revalidation

The dispatcher independently verifies before adapter execution:

```text
request hash verifies
decision hash verifies
authority mission id matches request mission id
authority envelope ref matches request and decision
authority is not revoked
authority is not expired
```

`RuntimeHost.resolve_active()` remains defense in depth, but Pack 3.1 no longer relies on the host resolver alone.

## Adapter Proof Ownership

| Proof Surface | Owner | Dispatcher Behavior |
| --- | --- | --- |
| Successful read-only action receipts | Read-only spine | Loads, verifies, and relays refs only. |
| Failed action-attempt evidence | Read-only spine | Relays refs only. |
| Read-only FinalGate certificates | Read-only spine | Loads, verifies, and relays refs only on successful adapter routes. |
| Dispatch decision artifact | Dispatcher | Persists before adapter execution. |
| Dispatch terminal certificate | Dispatcher | Creates exactly one rejected terminal certificate for pre-adapter blocks or proof failures that lack a read-only FinalGate. |
| Dispatch closeout artifact | Dispatcher | Persists normalized result and terminal status. |
| Mission terminal transition | Dispatcher for Pack 3 route | Occurs after dispatch closeout and accepted proof or rejected terminal certificate. |

The adapter does not duplicate receipts, and the dispatcher does not create replacement successful FinalGate certificates.

## Proof Verification Contract

Mission completion requires a typed proof verification pass over persisted artifacts:

```text
every receipt ref exists
receipt hash verifies
receipt mission_id matches
at least one successful material observation receipt exists

report artifact exists
report hash verifies against persisted safe report
report mission_id matches
report evidence refs are known

FinalGate ref exists
certificate hash verifies
certificate mission_id matches
certificate accepted is true
certificate receipt refs match the validated receipt set
```

If proof verification fails, dispatch status becomes `BLOCKED`, MissionKernel does not become `COMPLETED`, and a stable safe failure code is written without raw artifact content.

## Pre-Adapter Terminal Certificate Contract

Pre-adapter blocks, including coordinator rejection, unknown adapter, capability mismatch, request-state mismatch, authority mismatch, inactive authority, and decision persistence failure, now close with one dispatcher-owned rejected terminal certificate:

```text
successful action receipts = 0
dispatcher terminal certificate accepted = false
dispatch closeout count = 1
MissionKernel = BLOCKED or FAILED
terminal MissionKernel transition count = 1
```

If the read-only spine has already produced a terminal FinalGate, the dispatcher relays and verifies it instead of creating another terminal certificate. Exactly one terminal certificate exists per dispatch route.

## Bounded `search_text`

The read-only spine supports bounded `search_text`:

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

Exploration decisions remain one-action read-only decisions. The final report is produced through `ReadOnlyReportClient` or `ReadOnlyProviderReportClient` after `finish_exploration`, not parsed as an action decision.

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

The Pack 3 end-to-end fixture observes:

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

Blocked pre-adapter routes observe no `mission_dispatch_started` event and still produce one dispatch closeout plus one rejected dispatcher terminal certificate.

## Terminal Closeout Rules

```text
coordinator decision != execution success
dispatcher success != mission success
adapter return != mission success
report generated != mission success
```

`MissionKernel` reaches `COMPLETED` only after request correlation, dispatch closeout, required receipt verification, report artifact verification, and accepted FinalGate verification. Blocked routes end with `BLOCKED`, no fabricated successful receipt, one terminal certificate, one dispatch closeout, and one MissionKernel terminal transition.

Focused terminal-count proof:

```text
success:
  dispatch decisions = 1
  dispatch started events = 1
  dispatch closeouts = 1
  terminal certificates = 1
  terminal MissionKernel events = ["mission_completed"]

pre-adapter block:
  dispatch decisions = 1
  dispatch started events = 0
  dispatch closeouts = 1
  terminal certificates = 1
  successful receipts = 0
  terminal MissionKernel events = ["mission_blocked"]
```

## Replay Proof

Pack 3.1 keeps replay as reconstruction only. The focused replay test captures counters before and after `MissionReplayBuilder.build()` and proves zero deltas for:

```text
coordinator calls
exploration decision client calls
report client calls
MissionRunStore events
receipt writes
failed-attempt writes
report artifact writes
FinalGate writes
dispatch decision writes
dispatch closeout writes
dispatcher terminal certificate writes
MissionKernel status
timeline verification
```

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
-> dispatcher proof verification
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

Focused validation for the final Pack 3.1 commit:

```text
py -3.13 -m pytest -q tests\operator\test_product_nervous_system_pack3.py tests\test_cli_runtime_host_product_wiring_pack1b.py
25 passed

py -3.13 -m pytest -q tests\operator\test_mission_execution_coordinator.py tests\operator\test_runtime_connection_registry.py tests\operator\test_runtime_host_pack1.py tests\operator\test_mission_lifecycle_service.py tests\test_production_mission_daemon_and_scheduler_v1.py
33 passed

py -3.13 -m pytest -q tests\test_real_model_read_only_operator_production_spine_v1.py tests\operator\test_agent_runtime_event_bridge_pack2a.py tests\test_mission_kernel.py tests\test_low_risk_execution_finalgate_receipts.py tests\test_llm_live_operator_replay_v0.py
PASS; quiet output printed progress dots but no final numeric count.

py -3.13 -O -m pytest -q tests\operator\test_product_nervous_system_pack3.py tests\test_cli_runtime_host_product_wiring_pack1b.py tests\operator\test_mission_execution_coordinator.py tests\operator\test_runtime_host_pack1.py tests\operator\test_mission_lifecycle_service.py tests\test_real_model_read_only_operator_production_spine_v1.py tests\test_llm_live_operator_replay_v0.py
PASS; quiet output printed progress dots plus the expected Python -O pytest warning.

py -3.13 -m compileall -q sentinel\operator\read_only_model_clients.py sentinel\operator\unified_execution_dispatcher.py sentinel\operator\runtime_host.py sentinel\cli.py
PASS

git diff --check
PASS; only Windows LF-to-CRLF working-copy warnings were printed.

targeted provider-material / secret / fallback / AUTO / provider-native-tool / direct-bypass scans
PASS; hits were limited to defensive deny-list keys, tests asserting non-persistence, and documentation statements.
```

No real provider call was made.
