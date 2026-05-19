# Memory Implementation Readiness Checklist

Status: docs/spec lock candidate

## Purpose

This checklist defines what must exist before implementing
`ROLE_LOOP_RECEIPTS_AND_FEEDBACK_MEMORY_BRIDGE`.

Until these checks are satisfied, memory implementation should remain blocked.

## Recommended Implementation Scope

Proceed with reduced Approach 2 only:

```text
Minimal Epistemic Memory Engine
```

Allowed next implementation:

- typed memory entries;
- typed feedback signals;
- memory safety scanner;
- memory snapshot;
- confidence and variance fields;
- TTL and scope fields;
- contradiction refs;
- source class and source lineage;
- no-authority firewall;
- role-loop result optional memory bridge output.

Forbidden in next implementation:

- broad LivingMissionMemory retrieval ranking;
- Brain live society wiring;
- AgentRuntime default behavior change;
- organ execution;
- delegated operational lanes;
- provider expansion;
- fallback routing;
- AUTO model routing;
- policy mutation;
- `.env` access;
- credential access.

## Required Tests Before Merge

### Authority And Execution

- memory cannot grant Root Authority;
- memory cannot expand `MissionAuthorityEnvelope`;
- memory cannot approve execution;
- memory cannot create delegated operational lanes;
- memory cannot unlock credentials;
- memory cannot bypass user review;
- memory cannot bypass FinalGate;
- memory cannot convert blocked action into allowed action;
- memory snapshot has `authority_effect = none`;
- memory snapshot has `execution_effect = none`.

### Raw Leakage

- memory rejects raw prompt fields;
- memory rejects raw provider response fields;
- memory rejects raw reasoning/thinking fields;
- memory rejects raw key-like strings;
- memory rejects raw Bearer tokens;
- memory rejects hidden action payloads;
- memory receipts contain hashes and refs only.

### Epistemic Integrity

- stale memory TTL test;
- expired memory becomes historical context only;
- contradiction persistence test;
- unsupported claim cannot become verified by repetition;
- duplicate source confidence suppression test;
- self-generated evidence laundering test;
- source lineage dedupe test;
- source class ranking test;
- user correction precedence test;
- summary cannot outrank receipt test;
- current evidence beats stale memory test.

### Scope Safety

- mission scope mismatch downgrades memory;
- validity scope mismatch downgrades memory;
- provider/backend/model override rejected;
- memory from old phase cannot silently apply to current phase;
- user preference memory stays scoped unless explicitly promoted.

### Feedback Safety

- missing evidence creates feedback signal;
- invented evidence ref creates feedback signal;
- contradiction creates feedback signal;
- budget issue creates feedback signal;
- blocked intent creates feedback signal;
- self-improvement candidate is proposal-only;
- feedback cannot mutate prompts, code, tests, policy, runtime, organs, providers,
  credentials, or `.env`.

### Determinism And Replay

- identical sanitized inputs produce identical memory hashes;
- schema version is present;
- source receipt hashes are preserved;
- duplicate inputs do not create duplicate active memory;
- replay preserves contradiction and supersession status.

## Required Models

Future implementation should define:

- `FeedbackSignalKind`;
- `FeedbackSignalSeverity`;
- `FeedbackMemoryStatus`;
- `SafeFeedbackSignal`;
- `LivingMissionMemoryEntry`;
- `LivingMissionMemorySnapshot`;
- `MemoryBridgeInput`;
- `MemoryBridgeResult`;
- `MemorySafetyValidationResult`;
- `RoleLoopMemoryBridge`.

## Required Feedback Signal Kinds

Minimum signal kinds:

- `MISSING_EVIDENCE`;
- `INVENTED_EVIDENCE_REF`;
- `CONTRADICTION`;
- `RISK_FLAG`;
- `BUDGET_WASTE`;
- `BUDGET_EXHAUSTED`;
- `BLOCKED_INTENT`;
- `SUCCESSFUL_STRATEGY`;
- `USER_REVIEW_REQUIRED`;
- `SELF_IMPROVEMENT_CANDIDATE`;
- `STALE_MEMORY`;
- `USER_CORRECTION`;
- `DUPLICATE_SOURCE_SUPPRESSED`;
- `SELF_GENERATED_EVIDENCE_QUARANTINED`.

## Required Memory Snapshot Fields

The future `LivingMissionMemorySnapshot` must expose:

- `mission_id`;
- `loop_id`;
- `memory_entry_ids`;
- `feedback_signal_count`;
- `evidence_gap_count`;
- `contradiction_count`;
- `risk_flag_count`;
- `blocked_action_count`;
- `budget_issue_count`;
- `learned_pattern_count`;
- `expired_memory_count`;
- `duplicate_source_suppression_count`;
- `self_generated_evidence_quarantine_count`;
- `safe_summary`;
- `authority_effect = none`;
- `execution_effect = none`.

## Readiness Verdict

Implementation may start only after this lab spec is accepted.

Next pack should be:

```text
MINIMAL_EPISTEMIC_MEMORY_BRIDGE
```

It should implement only the reduced Approach 2 scope and must remain
non-authoritative, non-executing, provider-agnostic, and default-off.
