# Sentinel Product Nervous System Integration V1

## Pack 1B RuntimeHost Product Wiring Report

Date: 2026-06-20

Base commit: `675a5c81b03c445eff87ecd2aaf2848072efdffa`

Scope:

- Wire exactly one non-test product startup path: the existing Sentinel CLI/operator cockpit entrypoint.
- Prove CLI/application entry now owns one `SentinelRuntimeHost`, starts it, injects `host.lifecycle` into `LLMLiveOperatorCockpit`, accepts only an explicit typed `MissionAuthorityApprovalScope` for governed mission starts, creates the mission through the lifecycle service, persists authority and request before enqueue, pumps daemon pickup once, then shuts the host down deterministically.
- Keep legacy direct-kernel cockpit behavior available only through explicit `--legacy-internal-direct` and classify it as `LEGACY_INTERNAL`.

Explicit non-goals:

- Pack 2 was not started.
- AgentRuntime event visibility was not implemented.
- Coordinator dispatch, search/report capabilities, provider calls, desktop wiring, and background daemon supervision were not added.
- No provider call was made.
- No push was made.

## Verdict

`PACK_1B_RUNTIME_HOST_PRODUCT_WIRING = LOCAL_COMMIT_CANDIDATE`

The CLI cockpit product route now uses the Pack 1 RuntimeHost/lifecycle spine. The old direct route is no longer the silent default for governed starts.

## Product Entrypoint Wired

Wired entrypoint:

```text
sentinel.cli.main()
-> _run_cockpit_command()
-> SentinelRuntimeHost(run_root=...)
-> host.start()
-> LLMLiveOperatorCockpit(..., lifecycle_service=host.lifecycle, authority_approval_scope=...)
-> cockpit.handle(...)
-> MissionLifecycleService.create_mission(...)
-> host.pump_daemon_once(mission_id)
-> host.shutdown()
```

CLI flags added to `cockpit` and `chat`:

```text
--authority-scope <path>
--legacy-internal-direct
```

`--authority-scope` must point to an explicit `MissionAuthorityApprovalScope` JSON object. Missing scope does not fall back to the legacy route. It reaches the lifecycle-backed cockpit and blocks before `MissionRecord` creation.

`--legacy-internal-direct` explicitly selects the old direct-kernel cockpit route and labels turns with:

```json
{
  "internal_access_classification": "legacy_internal",
  "production_runtime_host_used": false
}
```

## Before And After Call Graph

Before Pack 1B:

```text
sentinel.cli.main()
-> _run_cockpit_command()
-> LLMLiveOperatorCockpit(run_root=...)
-> MissionKernel constructed inside cockpit
-> cockpit.handle("start")
-> MissionKernel.create_mission()
-> MissionKernel.enqueue()
```

After Pack 1B product route:

```text
sentinel.cli.main()
-> _run_cockpit_command()
-> explicit authority scope file parsed into MissionAuthorityApprovalScope
-> SentinelRuntimeHost(run_root=...)
-> host.start()
-> LLMLiveOperatorCockpit(lifecycle_service=host.lifecycle, authority_approval_scope=scope)
-> cockpit.handle("start")
-> MissionLifecycleService.create_mission()
-> MissionRecord(DRAFT)
-> MissionAuthorityEnvelopeIssuer.issue()
-> immutable MissionExecutionRequest persisted
-> mission_execution_request_prepared event
-> MissionKernel.enqueue()
-> daemon queue entry
-> host.pump_daemon_once(mission_id)
-> mission_execution_request_claimed event
-> daemon_tick_completed at no-workflow boundary
-> host.shutdown()
```

## Explicit Approval Input Contract

The CLI adapter rejects non-object JSON and requires these keys to be present before it constructs `MissionAuthorityApprovalScope`:

```text
user_id
allowed_systems
allowed_tools
allowed_actions
forbidden_actions
allowed_paths
allowed_domains
allowed_accounts
allowed_data_types
browser_v3_authority_grants
credential_grants
max_duration_minutes
max_actions
max_cost_usd
```

Sanitized test approval example:

```json
{
  "user_id": "operator_user",
  "allowed_systems": ["local_workspace"],
  "allowed_tools": ["read_only_observation"],
  "allowed_actions": ["research", "draft"],
  "forbidden_actions": ["payment", "send_email", "credential_access", "shell", "write_file"],
  "allowed_paths": ["."],
  "allowed_domains": [],
  "allowed_accounts": [],
  "allowed_data_types": [],
  "browser_v3_authority_grants": [],
  "credential_grants": [],
  "max_duration_minutes": 15,
  "max_actions": 4,
  "max_cost_usd": 0.0
}
```

Executable authority is still computed by restrictive intersection:

```text
MissionAuthoritySummary
AND explicit MissionAuthorityApprovalScope
AND MissionAuthorityPolicy
```

Policy can narrow, but it cannot silently broaden absent approval.

## RuntimeHost Ownership Proof

The product route constructs one host per CLI invocation and calls:

```text
host.start()
try:
    cockpit work
finally:
    host.shutdown()
```

Focused tests prove:

- one host instance is constructed for the product invocation;
- `start()` is called once;
- the cockpit turn metadata carries `runtime_host_lifecycle_ref`;
- host shutdown occurs after success;
- host shutdown occurs after cockpit exception;
- host shutdown occurs after daemon pickup failure;
- no duplicate host or daemon owner is created for one invocation.

Automatic background supervision remains not implemented. Pack 1B uses only deterministic `host.pump_daemon_once(mission_id)`.

## Deterministic Pickup Proof

After a successful governed start, the product route calls:

```text
host.pump_daemon_once(mission_id)
```

The focused test confirms:

- latest execution request exists;
- request state derives as `CLAIMED`;
- `mission_execution_request_claimed` is present;
- daemon queue status becomes `RUNNING`;
- `daemon_tick_completed` is present;
- tick result reports `executed = false`, matching the Pack 1 workflow boundary with no workflow id supplied.

If pickup fails, the CLI returns a safe typed error:

```text
sentinel cockpit: daemon_pickup_failed:<ExceptionClass>
```

No legacy fallback occurs, and the request remains `QUEUED` with no claimed event.

## Failure Behavior

| Failure point | Product route behavior |
| --- | --- |
| Host construction failure | Returns `runtime_host_construction_failed:<class>`; no fallback |
| Host start failure | Returns `runtime_host_start_failed:<class>`; shutdown attempted; no fallback |
| Missing approval scope at mission start | Lifecycle-backed cockpit returns `explicit_authority_approval_scope_required`; no `MissionRecord` |
| Approval-scope parse/validation failure | Returns `authority_scope_invalid:<safe code>`; no mission |
| Lifecycle mission creation failure | Returns `cockpit_product_route_failed:<class>`; shutdown in finally |
| Daemon pickup failure | Returns `daemon_pickup_failed:<class>`; request not claimed; shutdown in finally |
| Cockpit/application exception | Returns `cockpit_product_route_failed:<class>`; shutdown in finally |

## Remaining Legacy Routes

The old direct-kernel cockpit path remains only by explicit CLI flag:

```text
--legacy-internal-direct
```

Classification:

```text
LEGACY_INTERNAL
```

This classification is descriptive. It is not proof that the path migrated to the product route, and it grants no new authority.

Other CLI/browser/power-lab routes were not migrated in Pack 1B.

## Tests And Checks

Focused tests run:

```text
py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py
Result: 6 passed
```

Affected CLI plus new product wiring:

```text
py -3.13 -m pytest -q tests/test_llm_live_operator_cockpit_cli_v0.py tests/test_cli_runtime_host_product_wiring_pack1b.py
Result: 19 passed
```

Pack 1 core regressions:

```text
py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py tests/test_llm_live_operator_cockpit_cli_v0.py tests/operator/test_runtime_host_pack1.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_authority_issuer.py
Result: 40 passed
```

Adjacent coordinator/bridge slices:

```text
py -3.13 -m pytest -q tests/operator/test_mission_execution_coordinator.py tests/operator/test_runtime_connection_registry.py tests/operator/test_workflow_bridge_factory_pack1.py
Result: 10 passed
```

Python optimized mode:

```text
py -3.13 -O -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py tests/test_llm_live_operator_cockpit_cli_v0.py tests/operator/test_runtime_host_pack1.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_authority_issuer.py
Result: 40 passed
Note: pytest emitted the expected Python -O assertion warning.
```

Additional final checks are recorded in the final response for this pack.

## Files Created Or Updated

- `sentinel-control/services/sentinel-core/sentinel/cli.py`
- `sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py`
- `sentinel-control/services/sentinel-core/tests/test_llm_live_operator_cockpit_cli_v0.py`
- `sentinel-control/docs/reviews/SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_PACK1B_RUNTIME_HOST_PRODUCT_WIRING_REPORT.md`

## Honest Limits

- Pack 2 is not started.
- AgentRuntime and final capability execution are not connected to this product path yet.
- RuntimeHost still uses deterministic manual daemon pumping, not automatic background supervision.
- The CLI is the only product entrypoint wired in Pack 1B.
- Desktop, voice, provider, browser expansion, search/report lanes, and unified dispatcher work are unchanged.
