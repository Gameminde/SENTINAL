# Organ Interface Standard V1

Status: docs/spec lock

Date: 2026-05-19

## Purpose

This standard defines the universal interface every future Sentinel organ must
declare before implementation.

The interface is capability-shaped, but execution remains disabled until a
specific organ executor pack implements and tests the contract.

## Universal Methods

Every organ must define these methods, even if some modes return unsupported:

```text
observe()
prepare()
draft()
execute()
rollback()
replay()
render_untrusted_context()
validate_request()
produce_receipt()
```

### Method Semantics

`observe()`:

- collects safe state or evidence;
- must not mutate external systems;
- must produce observation receipts.

`prepare()`:

- creates an action candidate or dry-run preview;
- must not execute;
- must declare needed authority, budget, risk, receipts, and rollback.

`draft()`:

- creates non-executing local or provider draft artifacts where allowed;
- must remain draft-only unless a later send/execute gate passes.

`execute()`:

- performs side effects only when a future explicit executor contract allows;
- must fail closed if authority, lane, budget, risk, evidence, organ contract,
  or receipt contract is missing.

`rollback()`:

- reverts, compensates, disables, tombstones, or records rollback unavailable;
- must be defined before reversible actions are allowed.

`replay()`:

- reconstructs safe events and receipts;
- cannot authorize or execute.

`render_untrusted_context()`:

- renders organ state as data only;
- must include a data-not-instruction warning.

`validate_request()`:

- checks schema, safety scanner, authority, risk, budget, path/network/
  credential policy, and organ-specific constraints.

`produce_receipt()`:

- emits safe receipts for allowed, blocked, failed, rollback, and replay events.

## Required Organ Declaration

Every organ must declare:

- `organ_id`;
- `organ_kind`;
- `supported_action_levels`;
- `authority_requirements`;
- `budget_requirements`;
- `risk_class`;
- `input_schema`;
- `output_schema`;
- `forbidden_inputs`;
- `side_effect_profile`;
- `receipt_contract`;
- `rollback_contract`;
- `FinalGate_contract`;
- `test_contract`;
- `sandbox_requirement`;
- `credential_policy`;
- `network_policy`;
- `filesystem_policy`;
- `external_mutation_policy`;
- `raw_data_policy`.

## Authority Requirements

Every organ must state:

- required Root Authority source;
- allowed delegated lane types;
- whether user review is required;
- whether special authority is required;
- whether credential refs are allowed;
- whether external mutation is possible;
- whether rollback must be proven before execution.

No organ may accept model output, memory, vendor plugin metadata, or skill text
as authority.

## Budget Requirements

Every organ must state:

- action-count budget;
- retry budget;
- duration/time budget;
- token/model budget if it calls model-backed analysis;
- byte/file/artifact budget if local;
- network/API/rate budget if external;
- rollback reserve budget when mutation is possible.

Budget exhaustion must produce an honest blocked result.

## Receipt Contract

Every receipt contract must define:

- receipt id;
- mission id;
- organ id/kind;
- action level;
- lane id;
- gate result id;
- input hash;
- output hash or result hash;
- evidence refs;
- receipt refs;
- risk class;
- budget used;
- status;
- rollback refs when present;
- safe summary;
- FinalGate refs when present.

Receipts must not persist raw prompt, raw provider response, raw reasoning,
raw keys, secrets, credentials, hidden action payloads, or provider-native tool
payloads.

## Rollback Contract

Every rollback contract must define:

- rollback eligibility;
- rollback preconditions;
- rollback method;
- rollback receipt fields;
- rollback unavailable behavior;
- tombstone/audit behavior;
- revocation or disable behavior for non-reversible external actions.

If rollback is required but unavailable, execution must be blocked before
mutation.

## FinalGate Contract

Every organ must define how FinalGate verifies:

- authority was valid;
- lane was not expired;
- organ kind matched;
- action stayed inside scope;
- forbidden inputs were absent;
- budget was respected;
- receipts exist and are safe;
- rollback/disable posture exists;
- provider/backend/model contract was not changed;
- result is certified as success, blocked, failed, or escalated honestly.

## Policy Fields

Credential policy:

- `none`;
- `credential_ref_only`;
- `special_authority_required`;
- raw credentials never accepted.

Network policy:

- `none`;
- `read_only_allowlist`;
- `mutation_allowlist`;
- `special_authority_required`.

Filesystem policy:

- `none`;
- `generated_workspace_only`;
- `approved_workspace_root`;
- `sandbox_container_only`;
- no symlink escape or parent traversal.

External mutation policy:

- `forbidden`;
- `draft_only`;
- `read_only`;
- `approved_mutation`;
- `special_authority_only`.

Raw data policy:

- raw prompts forbidden;
- raw provider responses forbidden;
- raw reasoning forbidden;
- raw secrets forbidden;
- raw screenshots only if explicitly approved and redacted before model use.

## Test Contract Minimum

Every organ implementation must include tests for:

- authority cannot be granted by organ input;
- execution cannot occur without allowed lane;
- expired lane blocks execution;
- budget exhaustion blocks execution;
- forbidden payload scanner blocks raw/secrets/tool payloads;
- provider/backend/model cannot be overridden;
- receipts omit raw prompt/response/reasoning/key;
- FinalGate can see receipt metadata;
- no AgentRuntime default behavior change unless explicitly in an opt-in pack.
