# Sentinel Product Nervous System Ownership Contracts V1

Status: frozen for `SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1` Pack 0 and Pack 1.

This contract defines product-level ownership for new Sentinel runtime paths. It does not claim that older internal paths are migrated merely because they are classified.

## Canonical Ownership

- `MissionKernel` owns authoritative product mission status.
- `MissionRunStore` owns canonical mission event ordering.
- `AgentRuntime` and `MissionRunner` states are subordinate execution states.
- The cockpit owns user approval through `MissionAuthoritySummary`.
- `MissionAuthorityEnvelopeIssuer` owns executable authority creation.
- The coordinator owns serializable route policy.
- The dispatcher owns execution and live adapter resolution.
- Existing surfaces retain explicit receipt and FinalGate ownership.
- Bridges normalize and relay references; they do not duplicate proof.
- Memory writes are opt-in and policy-controlled.

## Authority And Execution Order

New product mission creation must follow this governed lifecycle:

```text
cockpit approval
-> MissionRecord
-> MissionAuthorityEnvelopeIssuer
-> MissionExecutionRequest persistence
-> enqueue
-> daemon pickup / dispatcher handoff
```

No new product path may enqueue before executable authority is issued and the `MissionExecutionRequest` is persisted.

## Legacy Compatibility

Existing direct internal access is temporarily classified as `LEGACY_INTERNAL`. This classification is descriptive only. It is not proof of migration and it does not grant new authority.

Allowed route classifications:

- `PRODUCTION_ROUTE`: new governed product path through RuntimeHost and lifecycle service.
- `LEGACY_INTERNAL`: existing internal path retained for compatibility during migration.
- `TEST_ONLY`: test harness or fixture path.
- `DISABLED`: known non-production or intentionally inactive path.

All new product paths must use `SentinelRuntimeHost` and `MissionLifecycleService`.

## Bridge Law

Runtime bridges may translate and relay references between existing runtime surfaces. They must not mint authority, duplicate proof ownership, or create independent receipt / FinalGate systems.

## Memory Law

Memory can store safe summaries only when a policy explicitly opts in. Memory cannot approve missions, create authority, enqueue execution, or become proof.
