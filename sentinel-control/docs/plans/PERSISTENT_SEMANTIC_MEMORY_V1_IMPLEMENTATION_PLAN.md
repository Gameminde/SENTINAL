# Persistent Semantic Memory V1 Implementation Plan

Baseline HEAD: `073174456f661e1fbdd2d2382b032a582374c765`

Canonical roadmap: `SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md`

## Scope

Implement, audit, remediate, test, document, commit, and push only
`PERSISTENT_SEMANTIC_MEMORY_V1`.

## Task 1 - Core Models And Sanitizer

Test first:

- durable record carries provenance, namespace, hashes, and no-authority flags;
- unsafe control fields are rejected;
- secret-like summaries are redacted before persistence;
- namespace ownership and mission scope are validated.

Implement:

- `sentinel/memory/models.py`
- `sentinel/memory/sanitizer.py`
- `sentinel/memory/__init__.py`

## Task 2 - Durable Store And Indexes

Test first:

- records survive process/service restart;
- path is explicit and database initialization is deterministic;
- content hash corruption is quarantined;
- FTS lexical search and fallback are deterministic;
- local semantic vectors rank related wording;
- entity and contradiction indexes preserve links;
- duplicate lineage/content does not inflate confidence.

Implement:

- `sentinel/memory/indexes.py`
- `sentinel/memory/store.py`

Use SQLite and standard-library-only deterministic vectors.

## Task 3 - Ingest, Retrieve, Rank

Test first:

- ingest existing `LivingMissionMemoryEntry`;
- hybrid scoring is visible and deterministic;
- mission/user/entity/procedure scope rules prevent leakage;
- expired, superseded, contradictory, and historical records remain visible
  only under their explicit contracts;
- retrieval result stays data-not-instruction and authority-neutral.

Implement:

- `sentinel/memory/service.py`
- `sentinel/memory/retrieval.py`

## Task 4 - Expiry, Deletion, Utility

Test first:

- expiry removes active recall;
- delete writes tombstone before content removal;
- deleted content is absent after restart;
- utility delta is computed from explicit metrics;
- utility does not mutate records or authority.

Implement:

- `sentinel/memory/lifecycle.py`
- `sentinel/memory/utility.py`

## Task 5 - Existing-System Integrations

Test first:

- Brain recall adapter returns existing `LivingMissionMemoryEntry` contracts;
- Brain still routes recalled entries through `SafeMemoryRetriever`;
- MissionKernel records safe memory retrieval refs in the existing timeline;
- Cockpit optional recall is default-off and surfaces safe refs/context only;
- no direct organ/runtime execution path is introduced.

Implement:

- `sentinel/memory/integration.py`
- minimal optional changes to Brain, Cockpit, MissionKernel, and exports.

## Task 6 - Phase Gauntlet

Create end-to-end tests for:

- restart durability and cross-session recall;
- mission and user isolation;
- entity/procedure cross-mission continuity;
- memory poisoning and prompt injection;
- stale, expired, contradictory, superseded, and deleted memory;
- raw secret/prompt/provider/reasoning exclusion;
- no authority/provider/budget/execution effects;
- measurable utility delta.

## Task 7 - Targeted Regressions

Run:

```text
tests/test_persistent_semantic_memory_v1.py
tests/test_persistent_semantic_memory_integrations_v1.py
tests/test_persistent_semantic_memory_gauntlet_v1.py
tests/test_llm_minimal_epistemic_memory_bridge.py
tests/test_llm_safe_memory_retrieval_v0.py
tests/test_llm_role_loop_to_memory_bridge_integration.py
tests/test_brain_cognition_loop_wiring.py
tests/test_llm_live_operator_mission_kernel_v0.py
tests/test_llm_live_operator_cockpit_flow_v0.py
tests/test_memory_not_authority_property.py
tests/test_memory_not_authority_bias.py
```

Also run compileall and `git diff --check`.

## Task 8 - Exhaustive Self-Audit And Remediation

Audit:

- authority drift and memory-as-authority;
- provider/model/budget/permission mutation;
- direct organ/runtime bypass;
- raw secret/credential/prompt/provider/reasoning persistence;
- SQL injection, path misuse, corruption, tamper handling;
- cross-user and cross-mission leakage;
- deletion/expiry truth;
- utility-score truth laundering;
- concurrency and deterministic behavior;
- docs and runtime maturity overclaim.

Fix all P0/P1 and serious P2 findings before lock.

## Task 9 - Truth Docs, Lock Report, Commit, Push

Update:

- `README.md`
- `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- `sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md`
- relevant memory roadmap docs

Create:

- `sentinel-control/docs/reviews/PERSISTENT_SEMANTIC_MEMORY_V1_LOCK_REPORT.md`

Final truth:

```text
current_phase = PERSISTENT_SEMANTIC_MEMORY_V1_LOCKED
previous_phase = SENTINEL_EXHAUSTIVE_SELF_AUDIT_AND_MASTER_ROADMAP_LOCKED
next_phase = DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1
```

Stage only intended files, commit, push `origin/main`, verify local HEAD equals
remote HEAD, and stop without starting the next phase.
