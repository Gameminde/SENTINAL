# Sentinel Product Nervous System Integration V1

## Pack 1A Authority And Request Integrity Fix Report

Date: 2026-06-19

Base commit: `398d357f945370e251baef5638a6f37f06e5eee0`

Scope:

- Complete executable-authority provenance for the new product route.
- Make `MissionExecutionRequest` immutable and synchronize its state through `MissionRunStore` events.

Explicit non-goals:

- Pack 2 was not started.
- RuntimeHost CLI or desktop startup wiring was not changed.
- AgentRuntime, OrganDispatcher, coordinator dispatch, search/report lanes, provider code, and Pack 2 event bridge were not modified.
- No provider call was made.
- No push was made.

## Verdict

`PACK_1A_AUTHORITY_AND_REQUEST_INTEGRITY_FIX = LOCAL_COMMIT_CANDIDATE`

The focused product-route gaps identified after Pack 0 + Pack 1 are closed locally:

- Executable authority now binds a typed approval scope hash, policy hash, authority summary hash, envelope hash, and immutable lineage record hash.
- Policy may restrict approved authority but cannot broaden it.
- Authority renewal uses deterministic latest-version conflict checks and immutable version lineage.
- Mission execution requests are immutable prepared artifacts.
- Request lifecycle state is derived from canonical mission events instead of mutable request status rewrites.

## Files Changed

- `sentinel-control/services/sentinel-core/sentinel/operator/authority_issuer.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/mission_lifecycle_service.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/kernel.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/cockpit.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_authority_issuer.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_mission_lifecycle_service.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_runtime_host_pack1.py`
- `sentinel-control/docs/reviews/SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_PACK1A_AUTHORITY_AND_REQUEST_INTEGRITY_FIX_REPORT.md`

## Authority Provenance Matrix

| Provenance field | Owner | Persistence surface | Integrity behavior |
| --- | --- | --- | --- |
| Approval scope hash | `MissionAuthorityApprovalScope` | `MissionAuthorityEnvelopeRecord.authority_approval_scope_hash` and issue event metadata | Stable hash over sanitized approval scope |
| Policy hash | `MissionAuthorityPolicy` | `MissionAuthorityEnvelopeRecord.policy_hash` and issue/renew event metadata | Stable hash over sanitized policy |
| Authority summary hash | `MissionAuthoritySummary` | `MissionAuthorityEnvelopeRecord.authority_summary_hash` | Stable hash over approved mission summary |
| Envelope hash | `MissionAuthorityEnvelope` | `MissionAuthorityEnvelopeRecord.envelope_hash` | Stable hash over sanitized executable envelope |
| Lineage record hash | `MissionAuthorityEnvelopeRecord.record_hash` | Authority envelope record artifact | Verified on load/list; tamper raises hash mismatch |
| Revocation hash | `MissionAuthorityRevocationRecord.revocation_hash` | Revocation artifact and event metadata | Binds mission id, envelope id, and envelope version |

## Approval Scope Model

`MissionAuthorityApprovalScope` represents the user-approved executable boundary for the product route:

- `allowed_systems`
- `allowed_tools`
- `allowed_actions`
- `forbidden_actions`
- `allowed_paths`
- `allowed_domains`
- `allowed_accounts`
- `allowed_data_types`
- `mission_type`
- `mode`
- `max_duration_minutes`
- `max_actions`
- `max_cost_usd`
- `max_recipients`
- `browser_v3_authority_grants`
- `credential_grants`

The approval scope remains data-only:

- `data_not_authority = true`
- `authority_effect = none`
- `can_grant_authority = false`
- `can_execute = false`

## Restrictive Intersection Rules

Executable envelope computation now follows restrictive semantics:

| Dimension | Rule |
| --- | --- |
| Allowed systems/tools/paths/domains/accounts/data types | Approval scope intersection policy |
| Allowed actions | Mission summary intersection approval scope intersection policy |
| Forbidden actions | Mission summary union approval scope union policy |
| Numeric budgets | Minimum of approval and policy |
| Expiry | Issued time plus minimum approved/policy duration |
| Browser grants | Included only when the exact sanitized grant appears in both approval and policy |
| Credential grants | Included only when the exact sanitized grant appears in both approval and policy |
| Mission title/objective | Derived from mission record because these are descriptive identity, not executable power |

Absent approval fields default to empty, disabled, or the most restrictive safe value. Policy cannot silently populate executable authority absent from the approval scope.

## Authority Lineage Behavior

Implemented lineage invariants:

- Loaded envelope records verify their own record hash.
- `list_records()` verifies every loaded record hash and sorts deterministically by version, issue time, and envelope id.
- Renewal requires:
  - `previous_envelope_ref`
  - `expected_current_envelope_ref`
  - the current latest record to match the expected envelope
  - previous envelope to match the expected current envelope
- Stale renewal attempts raise `mission_authority_envelope_conflict`.
- Renewing a revoked envelope raises `mission_authority_envelope_revoked`.
- Renewing an expired envelope raises `mission_authority_envelope_expired`.
- Cross-mission or missing envelope references raise a domain error instead of leaking filesystem errors.
- Revocation records bind:
  - `mission_id`
  - `revoked_envelope_ref`
  - `revoked_envelope_version`
  - `revocation_hash`

Envelope records are never mutated during renewal or revocation.

## Sanitized Issued Envelope Example

```json
{
  "mission_id": "mission_<redacted>",
  "version": 1,
  "authority_approval_scope_hash": "hash:<approval_scope>",
  "authority_summary_hash": "hash:<summary>",
  "policy_hash": "hash:<policy>",
  "envelope_hash": "hash:<envelope>",
  "allowed_systems": ["local_workspace"],
  "allowed_tools": ["read_only_observation"],
  "allowed_actions": ["list_directory", "read_file_segment"],
  "forbidden_actions": ["write_file", "shell", "archive_report"],
  "allowed_paths": ["."],
  "max_actions": 4,
  "max_duration_minutes": 15,
  "browser_v3_authority_grants": ["grant present only in approval and policy"],
  "credential_grants": []
}
```

## Immutable MissionExecutionRequest

`MissionExecutionRequest` is now an immutable prepared request artifact:

```json
{
  "request_id": "mission_exec_req_<redacted>",
  "mission_id": "mission_<redacted>",
  "capability_id": "read_only_research",
  "operation": "inspect_repository",
  "parameter_hash": "hash:<safe_parameters>",
  "workspace_ref": "snapshot:<ref>",
  "model_contract_ref": "model_contract:<ref>",
  "authority_envelope_ref": "authority_envelope_<redacted>",
  "prepared": true,
  "request_hash": "hash:<request>"
}
```

No mutable request `status` field is used.

## Product Route Ordering

The new lifecycle route writes in this order:

```text
MissionRecord(DRAFT)
-> authority envelope issued
-> immutable MissionExecutionRequest persisted
-> mission_execution_request_prepared event
-> MissionKernel.enqueue(..., metadata.execution_request_id)
-> mission_queued event
-> daemon queue entry
```

The mission is not enqueued until authority issuance, request persistence, and request-prepared event persistence have succeeded.

## Request State Derivation Algorithm

`MissionLifecycleService.derive_request_state()` derives state from the immutable request and canonical events:

| Evidence | Derived state |
| --- | --- |
| `mission_execution_request_claimed` for request id | `CLAIMED` |
| Else `mission_queued` for request id | `QUEUED` |
| Else `mission_execution_request_prepared` and mission still `DRAFT` | `ORPHANED_PREPARED` |
| Else `mission_execution_request_prepared` and mission is not `DRAFT` | `PREPARED` |
| Else request artifact only | `PREPARED` |

Reserved future states:

- `COMPLETED`
- `BLOCKED`

Pack 1A does not implement normal execution closeout; later packs own completion/blocking transitions.

## Failure State Matrix

| Failure point | Expected invariant | Focused proof |
| --- | --- | --- |
| Authority scope validation failure | No request artifact, no enqueue | `test_lifecycle_does_not_enqueue_when_authority_issuance_fails` |
| Authority artifact persistence failure | No issued event, no authority record | `test_authority_artifact_persistence_failure_does_not_emit_issued_event` |
| Authority record tamper | Load fails with hash mismatch | `test_loaded_authority_record_hash_is_verified` |
| Request artifact persistence failure | Mission remains `DRAFT`, no request, no prepared event, no queue | `test_lifecycle_request_persistence_failure_leaves_no_request_or_enqueue` |
| Request-prepared event persistence failure | Request artifact remains `PREPARED`, no queue | `test_lifecycle_request_prepared_event_failure_does_not_enqueue` |
| MissionKernel enqueue failure | Mission remains `DRAFT`; request is `ORPHANED_PREPARED`; no queued state | `test_lifecycle_does_not_mark_request_queued_when_enqueue_fails` |
| Daemon claim failure | Request remains `QUEUED`; no request-claimed event | `test_runtime_host_daemon_claim_failure_does_not_mark_request_claimed` |
| Stale renewal | Renewal rejected with conflict | `test_renewal_rejects_stale_revoked_or_expired_lineage` |
| Revoked renewal | Renewal rejected as revoked | `test_renewal_rejects_stale_revoked_or_expired_lineage` |
| Expired renewal | Renewal rejected as expired | `test_renewal_rejects_stale_revoked_or_expired_lineage` |
| Cross-mission envelope ref | Domain error; no revocation write | `test_cross_mission_envelope_reference_is_rejected` |

Ordered writes are not claimed as an atomic transaction. Partial artifacts remain visible and are reconciled through deterministic state derivation.

## RuntimeHost And Cockpit Scope

Pack 1A did not modify RuntimeHost application startup wiring.

Preserved Pack 1 behavior:

- `SentinelRuntimeHost.start()` starts daemon supervision.
- `SentinelRuntimeHost.shutdown()` stops daemon supervision.
- Cockpit remains a client when injected with `MissionLifecycleService`.
- Daemon deterministic pickup still stops at the injected/fake workflow boundary for Pack 1.

No CLI, desktop, or production app startup was wired.

## Focused Validation

Commands run from `C:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core` unless noted.

```text
py -3.13 -m pytest -q tests/operator/test_authority_issuer.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py
```

Result:

```text
17 passed
```

```text
py -3.13 -m pytest -q tests/operator/test_workflow_bridge_factory_pack1.py tests/operator/test_runtime_connection_registry.py tests/operator/test_mission_execution_coordinator.py tests/test_llm_live_operator_mission_kernel_v0.py tests/operator/test_authority_issuer.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py
```

Result:

```text
51 passed
```

```text
py -3.13 -O -m pytest -q tests/operator/test_authority_issuer.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py
```

Result:

```text
17 passed
1 expected pytest optimized-mode assertion warning
```

```text
py -3.13 -m compileall -q sentinel
```

Result:

```text
PASS
```

```text
git diff --check
```

Result:

```text
PASS
```

Targeted scans over changed files found no raw credential, raw prompt, raw response, raw reasoning, provider key persistence, provider-native tools, direct organ bypass, or provider fallback/AUTO introduction. Benign matches were existing enum/parameter words such as `AUTONOMOUS` and `fallback` in conversation-state handling.

## Remaining Limits

- RuntimeHost application startup remains intentionally not wired.
- Pack 2 event bridge was not started.
- Existing legacy/internal paths are not migrated by Pack 1A.
- Normal request `COMPLETED` and `BLOCKED` derivation is reserved for later execution integration packs.
- Ordered writes expose partial artifacts through deterministic state views; they are not represented as atomic transactions.

## Final Local Status

Pack 1A is ready for one local commit after verification. The final commit hash is recorded in the assistant response after commit creation.
