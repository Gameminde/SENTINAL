# Sentinel Product Nervous System Integration V1 — Pack 0 + Pack 1 Report

Status: local implementation candidate, Pack 0 + Pack 1 only.

No provider call was executed. Pack 2 was not started. This pack does not claim full production-spine migration for legacy paths.

## Ownership Contract

Frozen contract: `sentinel-control/services/sentinel-core/sentinel/operator/OWNERSHIP_CONTRACTS.md`.

Core ownership:

- `MissionKernel` owns authoritative product mission status.
- `MissionRunStore` owns canonical event ordering.
- `AgentRuntime` and `MissionRunner` are subordinate execution states.
- Cockpit owns user approval through `MissionAuthoritySummary`.
- `MissionAuthorityEnvelopeIssuer` owns executable authority creation.
- Coordinator owns serializable route policy.
- Dispatcher owns execution and live adapter resolution.
- Existing receipt and FinalGate surfaces retain proof ownership.
- Bridges normalize and relay refs; they do not duplicate proof.
- Memory writes are opt-in and policy-controlled.
- Existing direct internal paths are classified `LEGACY_INTERNAL`, not migrated by declaration.
- New product paths must use `SentinelRuntimeHost` and `MissionLifecycleService`.

## Before / After Product Call Graph

Before Pack 1:

```text
Cockpit
-> MissionKernel.create_mission
-> MissionKernel.enqueue
-> daemon/runtime paths discover mission state later
```

After Pack 1 product route:

```text
SentinelRuntimeHost.start()
-> host owns MissionKernel / MissionAuthorityEnvelopeIssuer / MissionLifecycleService / MissionDaemonRuntime
-> Cockpit client calls MissionLifecycleService
-> MissionRecord
-> MissionAuthorityEnvelopeIssuer issues immutable envelope record
-> MissionExecutionRequest persisted and hash-bound
-> MissionKernel.enqueue
-> MissionDaemonRuntime enqueue metadata includes execution_request_id
-> deterministic host.pump_daemon_once() proves daemon claim/pickup
```

Legacy compatibility:

```text
Existing direct MissionKernel and MissionRunStore paths remain LEGACY_INTERNAL or TEST_ONLY.
They are not claimed as migrated by Pack 1.
```

## Authority Lineage Schema

Implemented in `sentinel.operator.authority_issuer`:

```text
MissionAuthorityEnvelopeRecord
  envelope_id
  version
  mission_id
  previous_envelope_ref
  authority_summary_hash
  policy_hash
  issued_at
  expires_at
  revocation_ref
  envelope_hash
  record_hash
```

Lineage:

```text
Envelope v1 issued
-> renewal creates Envelope v2 with previous_envelope_ref = v1
-> revocation creates separate immutable MissionAuthorityRevocationRecord
-> active resolver rejects revoked or expired latest envelope
```

Revocation does not mutate existing envelope records. The regression test asserts that a revoked v2 record still reloads with `revocation_ref is None`.

## Sanitized Issued Envelope Example

```json
{
  "envelope_id": "authority_envelope_<redacted>",
  "version": 1,
  "mission_id": "mission_<redacted>",
  "previous_envelope_ref": null,
  "authority_summary_hash": "sha256:<summary>",
  "policy_hash": "sha256:<policy>",
  "expires_at": "2026-06-19T12:00:00Z",
  "envelope_hash": "sha256:<envelope>",
  "record_hash": "sha256:<record>"
}
```

## No Authority Expansion Proof

`MissionAuthorityEnvelopeIssuer` enforces:

- `MissionAuthoritySummary.allowed_actions` must be non-empty.
- Summary allowed actions must be a subset of policy allowed actions.
- Summary allowed actions must not intersect summary or policy forbidden actions.
- Envelope allowed actions are copied from the approved summary, not expanded from the policy.
- Envelope forbidden actions are the union of summary and policy forbidden actions.

Focused proof:

- `test_issuer_creates_hash_bound_envelope_record_without_scope_expansion`
- `test_issuer_rejects_summary_action_outside_policy`
- `test_renewal_creates_new_lineage_record_and_revocation_is_immutable`

## Persisted MissionExecutionRequest

Implemented in `sentinel.operator.mission_lifecycle_service`:

```text
MissionExecutionRequest
  request_id
  mission_id
  capability_id
  operation
  parameter_hash
  workspace_ref
  model_contract_ref
  authority_envelope_ref
  status
  request_hash
```

Sanitized example:

```json
{
  "request_id": "mission_exec_req_<redacted>",
  "mission_id": "mission_<redacted>",
  "capability_id": "read_only_research",
  "operation": "inspect_repository",
  "parameter_hash": "sha256:<safe-redacted-parameters>",
  "workspace_ref": "snapshot:host",
  "model_contract_ref": "model_contract:host",
  "authority_envelope_ref": "authority_envelope_<redacted>",
  "status": "queued",
  "request_hash": "sha256:<request>"
}
```

## Enqueue Ordering Proof

`MissionLifecycleService.create_mission()` performs:

```text
MissionRecord creation
-> MissionAuthorityEnvelopeIssuer.issue()
-> MissionExecutionRequest persisted
-> mission_execution_request_persisted event
-> request status updated to QUEUED
-> MissionKernel.enqueue()
-> daemon enqueue metadata includes execution_request_id
```

Regression proof:

```text
event_types.index("mission_authority_envelope_issued")
< event_types.index("mission_execution_request_persisted")
< event_types.index("mission_queued")
```

Failure proof:

```text
authority issuance failure leaves the record in DRAFT
and no mission_queued event is emitted.
```

## RuntimeHost Behavior

`SentinelRuntimeHost` owns:

- `MissionKernel`
- `MissionAuthorityEnvelopeIssuer`
- `MissionLifecycleService`
- `MissionDaemonRuntime`
- connection registry and coordinator infrastructure needed by later packs
- shared telemetry/configuration dependency roots

Behavior:

- `start()` starts daemon supervision and is idempotent.
- `shutdown()` stops daemon supervision and is deterministic.
- `status()` exposes started/stopped state, daemon availability, connection count, and active mission count.
- `lifecycle` is the product path for new cockpit mission starts.

## Cockpit-As-Client Proof

`LLMLiveOperatorCockpit` accepts an optional `MissionLifecycleService`.

When supplied:

```text
cockpit start
-> lifecycle_service.create_mission(...)
-> authority envelope and execution request are persisted before enqueue
```

When not supplied:

```text
existing direct kernel path remains available as legacy compatibility
```

## Daemon Production Caller And Deterministic Pickup Proof

`SentinelRuntimeHost.pump_daemon_once(mission_id)` proves:

```text
latest persisted MissionExecutionRequest is loaded
active authority is resolved
daemon lease is claimed
request status becomes CLAIMED
daemon.tick(...) is called deterministically
```

The test proves the daemon queue metadata carries the `execution_request_id` and that `daemon_lease_claimed` is appended.

Pack 1 intentionally stops at deterministic workflow boundary pickup. AgentRuntime connection belongs to later packs.

## Workflow Bridge Factory Proof

`DurableMissionWorkflowRuntime` now accepts:

```text
power_bridge_factory: Callable[[MissionKernel], OperatorPowerRuntimeBridge] | None
```

Default behavior remains unchanged:

```text
power_bridge_factory or (lambda kernel: OperatorPowerRuntimeBridge(kernel))
```

The focused test injects a factory bridge and verifies `run_power_tick()` uses the injected bridge with the expected mission id and `update_mission_status=False`.

## Files Changed

Pack 0 / Pack 1 files:

- `sentinel-control/services/sentinel-core/sentinel/operator/OWNERSHIP_CONTRACTS.md`
- `sentinel-control/services/sentinel-core/sentinel/operator/authority_issuer.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/legacy_classification.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/mission_lifecycle_service.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/cockpit.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/kernel.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/workflow_runtime.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_authority_issuer.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_mission_lifecycle_service.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_runtime_host_pack1.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_workflow_bridge_factory_pack1.py`

Coordinator / registry infrastructure included for Pack 1 host ownership:

- `sentinel-control/services/sentinel-core/sentinel/operator/runtime_connections.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/mission_execution_coordinator.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_runtime_connection_registry.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_mission_execution_coordinator.py`

## Validation

Focused Pack 1:

```text
py -3.13 -m pytest -q tests/operator/test_authority_issuer.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py tests/operator/test_workflow_bridge_factory_pack1.py
8 passed
```

Near regression slice:

```text
py -3.13 -m pytest -q tests/operator/test_authority_issuer.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py tests/operator/test_workflow_bridge_factory_pack1.py tests/operator/test_runtime_connection_registry.py tests/operator/test_mission_execution_coordinator.py tests/test_llm_live_operator_cockpit_flow_v0.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_production_mission_daemon_and_scheduler_v1.py tests/test_durable_mission_workflow_and_automatic_replan_v1.py
88 passed
```

Read-only / capability regression slice:

```text
py -3.13 -m pytest -q tests/test_real_model_read_only_operator_production_spine_v1.py tests/test_capability_registry.py tests/test_p6_external_organ_foundry.py
94 passed
```

Optimized mode:

```text
py -3.13 -O -m pytest -q tests/operator/test_authority_issuer.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py tests/operator/test_workflow_bridge_factory_pack1.py tests/operator/test_runtime_connection_registry.py tests/operator/test_mission_execution_coordinator.py
17 passed
```

Static checks:

```text
py -3.13 -m compileall -q sentinel
PASS

git diff --check
PASS with LF-to-CRLF warnings only
```

Safety scans:

```text
secret/provider material scan: no real secret found; fixture sk-unit-secret appears only in existing test assertions
raw prompt/response/reasoning scan: no persistence introduced
fallback/AUTO scan: only existing ReplanDecision.AUTO_EXECUTE enum and textual no-fallback doctrine found
direct bypass scan: only doctrine text, tests, and legitimate MissionAuthorityEnvelope construction found
```

## Explicit Non-Goals

Not implemented in Pack 0 + Pack 1:

- AgentRuntimeEventBridge
- unified dispatcher execution
- `READ_ONLY_RESEARCH` adapter
- new `search_text` capability
- separate final-report lane
- unified capability catalog
- unified replay
- memory expansion
- surface adapters

## Final Pack Verdict

`SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1` Pack 0 + Pack 1 is locally implemented as a candidate for review.

No provider call. No push. No score change. Pack 2 not started.
