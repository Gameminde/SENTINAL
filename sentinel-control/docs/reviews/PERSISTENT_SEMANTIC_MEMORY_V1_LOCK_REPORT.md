# Persistent Semantic Memory V1 Lock Report

Recorded at: 2026-06-07

## Verdict

```text
PERSISTENT_SEMANTIC_MEMORY_V1 = CLOSED
current_phase = PERSISTENT_SEMANTIC_MEMORY_V1_LOCKED
previous_phase = SENTINEL_EXHAUSTIVE_SELF_AUDIT_AND_MASTER_ROADMAP_LOCKED
next_phase = DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1
recommendation = GO / scoped to the next canonical roadmap phase
```

Persistent Semantic Memory V1 gives Sentinel durable, scoped cognitive
continuity without creating a second authority path. It extends the existing
`RoleLoopMemoryBridge` and safe in-process memory contracts rather than
replacing them.

## Runtime Connection Map

```text
AgentRuntime
-> RoleLoopMemoryBridge
-> optional PersistentMemoryIngestAdapter
-> PersistentSemanticMemoryService
-> DurableMemoryStore

Cockpit / Brain
-> optional PersistentMemoryRecallAdapter
-> scoped hybrid retrieval
-> existing safe context contracts

MissionKernel
-> safe retrieval refs and query hash
-> existing hash-chained mission timeline
```

## Authority And Data Flow

```text
MissionAuthorityEnvelope.user_id
-> requester/owner binding
-> namespace-scoped ingest and retrieval

memory record / hit / utility result
-> data_not_instruction = true
-> authority_effect = none
-> execution_effect = none
-> cannot approve execution, unlock credentials, create lanes, or override model/provider
```

Memory remains context only. It cannot become authority, execution permission,
provider selection, budget, policy, receipt-as-authority, or
FinalGate-as-future-permission.

## Components Added

```text
sentinel/memory/models.py
sentinel/memory/sanitizer.py
sentinel/memory/indexes.py
sentinel/memory/store.py
sentinel/memory/service.py
sentinel/memory/integration.py
sentinel/memory/utility.py
```

Implemented:

- local SQLite durable store with WAL, busy timeout, and secure-delete hygiene;
- mission, user, entity, procedure, and same-user shared namespaces;
- FTS5 lexical retrieval with deterministic fallback;
- deterministic local hashed-token semantic scoring;
- entity, procedure, contradiction, and supersession indexes;
- provenance-linked trust classes with injected validation for elevated trust;
- deterministic explainable hybrid ranking;
- expiry, historical visibility, deletion tombstones, and deletion receipts;
- optional Brain and cockpit recall;
- MissionKernel retrieval timeline refs;
- optional AgentRuntime write-through from `RoleLoopMemoryBridge`;
- callable memory utility evaluator.

## Runtime Maturity Truth

```text
durable local memory store = LIVE_RUNTIME / local SQLite
typed ingestion and retrieval = LIVE_RUNTIME
AgentRuntime RoleLoopMemoryBridge write-through = LIVE_RUNTIME / optional default-off
Brain durable recall = LIVE_RUNTIME / optional default-off
Cockpit durable recall = LIVE_RUNTIME / optional default-off
MissionKernel retrieval timeline refs = LIVE_RUNTIME
memory utility evaluator = RUNTIME_LIBRARY / not automatically invoked
large-scale vector backend = NOT_STARTED
encrypted-at-rest memory store = NOT_STARTED
automatic memory curation/compaction = NOT_STARTED
```

## Exhaustive Audit Findings And Remediation

Independent security, logic, algorithm, integration, and documentation reviews
found no P0.

Closed findings:

```text
CROSS_USER_BRAIN_RECALL = CLOSED
CROSS_USER_INGEST_POISONING = CLOSED
CALLER_DECLARED_TRUST_LAUNDERING = CLOSED
KNOWN_SEMANTIC_PROMPT_INJECTION = CLOSED
ACTIVE_HISTORICAL_RECALL = CLOSED
COMMON_SECRET_PATTERN_PERSISTENCE = CLOSED
SEMANTIC_CANDIDATE_STARVATION = CLOSED
MUTABLE_VECTOR_TAMPER_INFLUENCE = CLOSED
CONCURRENT_SUPERSESSION_REVERSE_LINK_RACE = CLOSED
DIRECT_TYPED_UNSAFE_METADATA_INGEST = CLOSED
RECALL_FAILURE_PROPAGATION = CLOSED
INVALID_TRUST_CLASS_FAILURE = CLOSED
PROCEDURE_INDEX_DELETE_CLEANUP = CLOSED
COCKPIT_RETRIEVAL_TIMELINE_REF = CLOSED
EXPIRY_IDEMPOTENCE = CLOSED
FTS_SCORE_DIRECTION = CLOSED
LOW_TRUST_PROJECTION_OVERCLAIM = CLOSED
DELETION_FORENSIC_OVERCLAIM = CLOSED
```

Important controls:

- requester identity is mandatory and must match the namespace owner;
- AgentRuntime binds recall/write-through ownership to the mission envelope;
- elevated trust requires an injected provenance reference validator;
- untrusted/inferred memory projects as unknown with bounded confidence;
- historical, expired, and superseded memory is excluded from active recall;
- prompt context excludes low-trust/historical records and is scanned again;
- semantic vectors are recomputed from verified summaries at retrieval;
- scoped supersession uses `BEGIN IMMEDIATE` and rejects cross-scope targets;
- recall and write-through failures produce safe hashes/status instead of
  breaking or expanding runtime authority.

## Residual Risks And Honest Limits

```text
UNKEYED_RECORD_HASH = ACCEPTED_V1_LIMIT
SQLITE_SAFE_SUMMARIES_NOT_ENCRYPTED_AT_REST = ACCEPTED_V1_LIMIT
FORENSIC_ERASURE_NOT_GUARANTEED = ACCEPTED_V1_LIMIT
SEMANTIC_SCAN_LINEAR_AT_V1_SCALE = ACCEPTED_V1_LIMIT
PROMPT_INJECTION_SCREENING_HEURISTIC = ACCEPTED_V1_LIMIT
UTILITY_EVALUATOR_NOT_AUTOMATICALLY_WIRED = ACCEPTED_V1_LIMIT
```

An attacker with arbitrary SQLite write access can rewrite payloads and
recompute the unkeyed record hash. V1 therefore proves local corruption and
non-rehashing tamper detection, not cryptographic authenticity against a
database writer.

## Files Created

```text
sentinel-control/docs/llm/memory/PERSISTENT_SEMANTIC_MEMORY_V1_SPEC.md
sentinel-control/docs/plans/PERSISTENT_SEMANTIC_MEMORY_V1_IMPLEMENTATION_PLAN.md
sentinel-control/docs/reviews/PERSISTENT_SEMANTIC_MEMORY_V1_LOCK_REPORT.md
sentinel-control/services/sentinel-core/sentinel/memory/__init__.py
sentinel-control/services/sentinel-core/sentinel/memory/indexes.py
sentinel-control/services/sentinel-core/sentinel/memory/integration.py
sentinel-control/services/sentinel-core/sentinel/memory/models.py
sentinel-control/services/sentinel-core/sentinel/memory/sanitizer.py
sentinel-control/services/sentinel-core/sentinel/memory/service.py
sentinel-control/services/sentinel-core/sentinel/memory/store.py
sentinel-control/services/sentinel-core/sentinel/memory/utility.py
sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_v1.py
sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_integrations_v1.py
sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_gauntlet_v1.py
```

## Files Updated

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel/agent/brain/cognition_loop.py
sentinel/agent/runtime.py
sentinel/operator/cockpit.py
sentinel/operator/conversation.py
sentinel/operator/kernel.py
sentinel/operator/llm_frame.py
sentinel/shared/safety_scanner.py
tests/test_brain_native_candidate_source_and_memory_feedback_lock.py
tests/test_browser_final_capability_lock.py
```

## Tests And Checks

Targeted verification:

```text
Persistent Semantic Memory V1 core/integration/gauntlet = 60 passed
Brain/AgentRuntime closed-loop regressions = 59 passed
Cockpit/kernel/operator regressions = 51 passed
Existing memory and memory-not-authority regressions = 150 passed
Browser final capability truth regression = 5 passed
ArtifactRefStore isolated performance rerun = passed / p95 0.810 ms
python -m compileall -q sentinel = exit code 0
git diff --check = clean
```

Full-suite verification:

```text
py -3.13 -m pytest -p no:cacheprovider
Result: 2381 passed, 3 skipped
```

The first full-suite run exposed one transient disk benchmark miss and one
stale browser roadmap-current-phase assertion. The benchmark passed in
isolation, and the stale test was repaired to preserve browser completion as
historical truth while recognizing Persistent Semantic Memory V1 as the
current phase.

## Boundaries Preserved

```text
new execution surface added = false
vendor runtime integrated = false
vendor code copied = false
provider fallback/AUTO added = false
direct organ bypass added = false
raw credential storage added = false
raw prompt/provider response/reasoning persistence added = false
memory-as-authority added = false
next roadmap phase started = false
```

## Next Recommended Phase

```text
DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1
```

That phase is not started by this lock.
