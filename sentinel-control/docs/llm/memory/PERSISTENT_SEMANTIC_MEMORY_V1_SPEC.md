# Persistent Semantic Memory V1 Specification

Status: implementation specification

Canonical phase: `PERSISTENT_SEMANTIC_MEMORY_V1`

## Purpose

Persistent Semantic Memory V1 gives Sentinel durable cognitive continuity
across sessions and missions without creating a new authority source or a
parallel memory system.

The phase extends the existing memory chain:

```text
RoleLoopMemoryBridge
-> LivingMissionMemoryEntry
-> PersistentSemanticMemoryService
-> scoped hybrid retrieval
-> Brain / Cockpit / MissionKernel context and refs
```

The existing `RoleLoopMemoryBridge`, hot context slots, safe retrieval
contracts, memory replay, and mission timeline remain canonical.

## Product Contract

Memory may:

- remember safe facts, preferences, outcomes, entities, and procedures;
- retrieve relevant scoped context;
- expose provenance, contradictions, expiry, and supersession;
- propose useful context to Brain and the live operator cockpit;
- measure whether recall improved a mission outcome.

Memory may not:

- grant or expand authority;
- approve execution;
- create delegated lanes;
- unlock credentials;
- change provider, backend, or model;
- change budgets or permissions;
- call organs or runtime executors;
- persist raw prompts, provider responses, reasoning, credentials, or secrets.

## Sentinel-Native Architecture

```text
MemoryIngestor
MemorySanitizer
MemoryRecord
MemoryProvenance
MemoryNamespace
DurableMemoryStore
LexicalIndex
SemanticIndex
EntityIndex
ContradictionIndex
MemoryRetriever
MemoryRanker
MemoryExpiryAndDeletion
MemoryUtilityEvaluator
```

The durable store is local SQLite. Lexical retrieval uses SQLite FTS5 when
available. Semantic retrieval uses a deterministic local hashed-token vector,
so V1 adds no provider, network, model, or dependency surface.

## Namespace And Visibility Rules

Every record belongs to exactly one namespace:

| Namespace | Visibility |
| --- | --- |
| `mission` | Only the same user and mission |
| `user` | Same user across missions |
| `entity` | Same user and an explicitly requested entity |
| `procedure` | Same user and an explicitly requested procedure |
| `shared` | Same user only in V1 |

Other mission namespaces are never silently recalled. Cross-mission
continuity must be expressed as `user`, `entity`, or `procedure` memory.

## Durable Record Contract

Every `MemoryRecord` contains:

- stable record and content hashes;
- namespace and owner user;
- source class, source ID, lineage ID, and trust class;
- source and validity scopes;
- created, observed, and optional expiry timestamps;
- evidence and receipt references;
- contradiction, supersession, and reverse-supersession references;
- entity references;
- claim status, confidence, variance, and safe summary;
- `authority_effect = none`, `execution_effect = none`,
  `data_not_instruction = true`.

Tombstone and deletion timestamps live in the separate durable
`MemoryTombstone` and deletion receipt contracts rather than in every active
record.

## Ingestion Contract

1. Accept existing `LivingMissionMemoryEntry` objects or explicit safe records.
2. Redact secret-like text before persistence.
3. Reject raw prompt/provider/reasoning/control fields.
4. Reject memory that attempts to behave as an instruction or authority.
5. Validate namespace ownership and mission scope.
6. Compute deterministic content and record hashes. Semantic vectors are
   derived again from the verified safe summary at retrieval time.
7. Persist the record and update lexical, entity, procedure, contradiction,
   and scoped supersession indexes atomically.
8. Duplicate lineage/content does not increase confidence or truth status.

## Retrieval Contract

Retrieval is:

- scoped by owner user and namespace;
- deterministic for the same store/query/time;
- budgeted by `max_hits` and candidate limit;
- explainable through visible score components;
- hybrid across lexical, semantic, entity, freshness, and provenance signals;
- contradiction- and historical-aware;
- returned as untrusted data, never instruction or proof.

Retrieval score affects attention only. It never changes claim status,
confidence, authority, provider selection, budget, or execution permission.

## Expiry And Deletion Contract

- Expired records become retained historical records and are removed from
  active lexical retrieval.
- Delete writes a durable tombstone/audit event before active content removal.
- Deleted content is no longer retrievable.
- Safe proof metadata and hashes survive deletion.
- Governance-critical evidence/receipt references remain as safe hashes/refs,
  not raw content.
- SQLite `secure_delete` and WAL checkpointing are best-effort hygiene.
  `MemoryDeletionReceipt.forensic_erasure_guaranteed` is always false.

## Integration Contract

### Brain

An optional `PersistentMemoryRecallAdapter` retrieves scoped records and
converts them back into existing `LivingMissionMemoryEntry` objects. Brain
continues to use `SafeMemoryRetriever`; durable memory does not bypass it.

### Live Operator Cockpit

The cockpit may receive a safe recall summary and retrieval refs. Recalled
content remains labeled untrusted and cannot become a command or authority.
Persistent memory is optional and default-off when no service/user scope is
supplied.

### MissionKernel

MissionKernel records safe retrieval refs and query hashes in the existing
hash-chained mission timeline. It does not treat memory refs as permission.

### AgentRuntime Write-Through

An optional `PersistentMemoryIngestAdapter` writes the existing
`RoleLoopMemoryBridge` output through the durable ingestion contract.
Write-through is default-off, binds the requester to
`MissionAuthorityEnvelope.user_id`, and fails safely without changing the
mission authority result.

## Utility Evaluation

`MemoryUtilityEvaluator` is a callable V1 library that compares explicit
baseline and recalled outcomes using completion, intervention, and evidence
metrics. It is not automatically wired to mission outcomes. The result is an
evaluation record only. Utility scores cannot mutate authority, claim truth,
or routing.

## Failure Posture

- malformed or unsafe ingest: reject, persist safe rejection hash only;
- unavailable FTS5: deterministic bounded lexical fallback;
- corrupt record/hash mismatch: quarantine from retrieval;
- scope mismatch: exclude;
- expired/tombstoned record: exclude from active retrieval;
- integration failure: continue without durable recall and expose safe status;
- no provider fallback, no hidden model call, no direct execution.

## V1 Residual Limits

- SQLite stores sanitized safe summaries locally but does not encrypt them at
  rest.
- Record hashes detect corruption and non-rehashing tamper. They are unkeyed
  and do not protect against an attacker who already has arbitrary database
  write access and can recompute hashes.
- Semantic retrieval performs a deterministic bounded local scan. A future
  admitted vector backend is required for large-scale collections.
- Prompt-injection screening blocks known unsafe patterns and low-trust
  records are excluded from cockpit prompt context. This is defense in depth,
  not a proof that every semantic injection phrase can be recognized.
- Logical deletion is proven by a tombstone and active-content removal;
  forensic erasure from all filesystem snapshots and backups is not claimed.

## Acceptance Gauntlet

The phase is not locked until tests prove:

- durable recall survives service restart;
- lexical, semantic, entity, contradiction, and provenance ranking works;
- mission/user/entity/procedure namespaces do not leak;
- stale, expired, superseded, deleted, malicious, and contradictory memory is
  handled visibly and safely;
- secret-like input is redacted or rejected before persistence;
- memory cannot alter authority, provider, model, budget, or execution;
- Brain, Cockpit, and MissionKernel integrations remain optional and bounded;
- utility evaluation measures outcome deltas without changing runtime state.
