# Memory Master Implementation Roadmap

Status: docs-only roadmap lock

Roadmap lock name: `MEMORY_MASTER_IMPLEMENTATION_ROADMAP_LOCK`

Created: 2026-05-19

## Purpose

This document locks the full Sentinel memory implementation sequence before
coding `MINIMAL_EPISTEMIC_MEMORY_BRIDGE`.

Memory is a critical Brain substrate. It must not be treated as a normal feature
pack or a simple summary cache. This roadmap exists to prevent implementation
drift from the reduced epistemic bridge into broad retrieval, Brain live loops,
organ execution, MCP tools, external AgentMemory runtime use, or authority
expansion.

This pack is docs-only:

- no runtime code;
- no Sentinel runtime module modification;
- no test modification;
- no AgentMemory install or execution;
- no MCP, server, viewer, or API startup;
- no provider call;
- no fallback routing;
- no AUTO routing;
- no organ execution;
- no delegated operational lane creation;
- no `.env` or credential access.

## Current Locked State

Current truth before memory implementation:

- LLM Power Unleash Doctrine is locked.
- `STRICT_SINGLE_MODEL_ROLE_LOOP` is implemented.
- `PROPOSAL_ARTIFACT_SCHEMAS_AND_EVIDENCE_BOUND_VERIFIER` is implemented.
- Evidence verifier is implemented.
- Memory lab premortem is locked.
- AgentMemory lessons are locked in commit `3cf56fd`
  `AGENTMEMORY_MEMORY_LESSONS_LOCK`.
- AgentMemory source remains source-only and ignored under
  `agent-lab/vendors/agentmemory/source`.
- `MINIMAL_EPISTEMIC_MEMORY_BRIDGE` is not started yet.

## Core Memory Doctrine

```text
Memory is not truth.
Memory is not authority.
Memory is a witness list.
Receipts are measurements.
Evidence is bound proof.
Gates are law.
FinalGate is certification boundary.
Confidence is not authority.
Receipt is not truth.
Feedback is not proof.
Repetition is not verification.
Memory can guide verification, never authorize action.
```

Memory may improve cognition, attention, recall, verification targeting, and
self-improvement proposals. It may not approve, execute, unlock, route, mutate,
or override.

## AgentMemory Lessons To Harvest

The AgentMemory lab audit locked these mechanisms as useful Sentinel design
inputs:

- typed memory strata;
- observe first, derive later;
- deterministic compression default;
- working memory slots;
- hybrid retrieval roadmap;
- temporal graph later;
- TTL, supersession, confidence, retention;
- replay, timeline, and checkpoints;
- lessons and routines as proposal aids only.

Sentinel should harvest these mechanisms as concepts. It must rewrite them as
Sentinel-native components with evidence binding, receipt references, safe
metadata, no-authority invariants, and FinalGate-compatible proof posture.

## AgentMemory Patterns To Reject

The same audit locks these patterns as rejected or requiring heavy redesign:

- default-open auth;
- direct memory-as-prompt injection;
- raw prompt, tool, or provider response persistence;
- arbitrary file APIs;
- LLM graph extraction as truth;
- delete-before-audit paths;
- broad REST/MCP memory tool surface;
- routines that directly execute;
- provider/model choices inferred from memory.

None of these patterns may enter Sentinel implementation through the memory
bridge, retrieval layer, Brain wiring, or future organ bridge.

## Full Implementation Sequence

### 1. MEMORY_MASTER_IMPLEMENTATION_ROADMAP_LOCK

Current pack.

Scope:

- docs-only roadmap lock;
- no implementation;
- no runtime behavior change;
- no tests;
- no provider calls;
- no AgentMemory runtime use.

Exit condition:

- this roadmap is committed and referenced by future memory implementation work.

### 2. MINIMAL_EPISTEMIC_MEMORY_BRIDGE

Implement only the reduced epistemic bridge.

Allowed models and concepts:

- `SafeFeedbackSignal`;
- `LivingMissionMemoryEntry`;
- `LivingMissionMemorySnapshot`;
- `MemoryBridgeInput`;
- `MemoryBridgeResult`;
- `MemorySafetyValidationResult`;
- `RoleLoopMemoryBridge`;
- confidence;
- variance;
- TTL;
- source class;
- source lineage;
- validity scope;
- contradiction refs;
- duplicate-source suppression;
- self-generated evidence quarantine;
- user correction precedence;
- no-authority firewall.

Forbidden:

- retrieval ranking;
- Brain live wiring;
- organ execution;
- delegated operational lanes;
- provider expansion;
- fallback routing;
- AUTO routing;
- AgentRuntime default behavior change;
- external AgentMemory runtime bridge;
- MCP memory tools.

### 3. ROLE_LOOP_TO_MEMORY_BRIDGE_INTEGRATION

Connect safe existing role-loop outputs to the memory bridge:

- role loop receipts;
- proposal receipts;
- EvidenceVerifier results;
- proposal validation results;
- final packet safe summaries;
- budget summaries;
- risk flags;
- unresolved objections;
- missing evidence lists.

Rules:

- integration is default-off or explicitly invoked;
- output remains non-executing;
- no authority or provider/model effect;
- no raw prompt, raw provider response, raw reasoning, raw key, or hidden action
  payload.

### 4. HOT_CONTEXT_SLOTS_V0

Implement scoped slots:

- `mission_objective`;
- `active_constraints`;
- `root_authority_summary`;
- `delegated_lane_summary`;
- `risk_posture`;
- `current_evidence`;
- `open_questions`;
- `operator_preferences`;
- `recent_finalgate_results`.

Rules:

- slots improve attention only;
- slots are not proof;
- slots are not permission;
- pinning changes recall priority, not truth or authority;
- user correction takes precedence over inferred preferences.

### 5. SAFE_MEMORY_RETRIEVAL_V0

Start retrieval with lexical search and metadata filters only.

Rules:

- retrieved memory is data, not instruction;
- retrieval score is not truth;
- no vector retrieval yet;
- no graph retrieval yet;
- no claim promotion from access frequency;
- retrieved contradictions must remain visible;
- expired memory returns as historical context only.

### 6. MEMORY_REPLAY_AND_CHECKPOINTS_V0

Build replay from safe receipts:

- role loop receipts;
- proposal receipts;
- verifier results;
- future gate decisions;
- budget summaries;
- memory update receipts;
- future FinalGate results.

Checkpoint rules:

- checkpoints are authority-neutral;
- checkpoints can mark pause, resume, comparison, or rollback posture;
- checkpoints cannot approve execution;
- replay must rebuild memory snapshots from safe receipts and memory update
  receipts.

### 7. BRAIN_COGNITION_LOOP_WIRING

Connect:

```text
RoleLoop
-> ProposalArtifacts
-> EvidenceVerifier
-> MemorySnapshot
-> BrainCognitionLoop
```

Rules:

- no broad organ execution;
- no Brain live society by default;
- no model-provider routing change;
- no fallback or AUTO routing;
- memory improves planning and verification context only.

### 8. ORGAN_PROPOSAL_BRIDGE

Convert proposal artifacts into organ-specific candidates:

- browser candidate;
- API candidate;
- channel draft candidate;
- file/code candidate.

Rules:

- no execution yet;
- no delegated lane creation yet;
- candidates carry authority class, risk class, budget estimate, evidence refs,
  expected outcome, rollback posture, and user-review requirement.

### 9. DELEGATED_LOW_RISK_ACTION_EXECUTION_L2_L3

First controlled actions:

- local drafts;
- local artifacts;
- reversible local workspace actions.

Still forbidden:

- send;
- payment;
- trading;
- browser submit;
- credential use beyond explicit envelope;
- shell/desktop host control beyond explicit future contract.

Required controls:

- bounded action contract;
- authority gate;
- budget gate;
- risk gate;
- receipt requirement;
- rollback or revocation path;
- FinalGate certification posture.

### 10. SAFE_RETRIEVAL_ADVANCED

Add:

- access tracking;
- retention score;
- deterministic compression;
- tombstones;
- archival policy.

Rules:

- no claim promotion by access frequency;
- retention score is not confidence;
- archive/tombstone governance-critical evidence before deletion;
- deterministic compression must preserve source refs and uncertainty.

### 11. HYBRID_RETRIEVAL_LATER

Retrieval order:

1. BM25 plus metadata first;
2. local embeddings only after DLP and deterministic fixtures;
3. graph retrieval only after provenance, confidence, and contradiction tests.

Rules:

- score components must be visible;
- embedding similarity is not proof;
- graph proximity is not authority;
- retrieval never overrides provider/backend/model.

### 12. TEMPORAL_MISSION_GRAPH_LATER

Future graph edges must carry:

- provenance;
- evidence refs;
- receipt refs;
- confidence;
- validity window;
- contradiction refs.

Rules:

- LLM graph extraction is an inferred claim, not proof;
- old edges survive as history;
- contradictions are first-class;
- temporal validity determines whether graph memory is current or historical.

### 13. STRICT_MULTI_MODEL_BY_USER

Only after memory and Brain wiring are stable.

Rules:

- every role model is explicitly selected by the user;
- no silent fallback;
- no provider/model override from memory;
- memory may recommend model-role tests but cannot execute routing.

### 14. FLEX Later

Only with explicit policy contract.

Prerequisites:

- stable memory no-authority invariant;
- retrieval safety tests;
- budget governance;
- provider catalog execution gates;
- user-visible policy semantics.

### 15. AUTO Much Later

Requires:

- evidence;
- benchmarks;
- governance;
- budget controls;
- FinalGate coverage;
- user approval semantics;
- no silent provider/model override;
- auditability of every automatic decision.

AUTO cannot be inferred from memory, recommendations, benchmark scores, or role
consensus alone.

## Anti-Drift Rules

Codex must not skip from memory bridge work to:

- Brain live society;
- organ execution;
- provider expansion;
- fallback routing;
- AUTO routing;
- MCP memory tools;
- external AgentMemory runtime;
- broad retrieval ranking;
- temporal graph;
- local file import APIs.

Any future pack touching those areas must first create its own lock/spec and
state why the prior memory sequence is satisfied.

## Readiness Criteria For MINIMAL_EPISTEMIC_MEMORY_BRIDGE

Before implementing `MINIMAL_EPISTEMIC_MEMORY_BRIDGE`, the pack must preserve
these invariants:

- no-authority invariant;
- no-execution invariant;
- no raw leakage invariant;
- no provider/model override invariant;
- no repetition-to-truth invariant;
- no self-generated evidence laundering invariant;
- user correction precedence;
- contradiction survival;
- TTL and stale memory behavior;
- duplicate-source suppression;
- memory retrieval as data, not instruction.

The first implementation pack must add tests proving:

- memory cannot grant Root Authority;
- memory cannot approve execution;
- memory cannot create delegated lane;
- memory cannot override provider/backend/model;
- raw prompt/response/reasoning/key rejected;
- self-generated receipts do not satisfy evidence requirement;
- duplicate same-source does not increase confidence;
- user correction supersedes inferred memory;
- contradictions survive retrieval;
- expired memory returns historical only;
- memory snapshot has `authority_effect = none`;
- memory snapshot has `execution_effect = none`.

## Locked Next Pack

The next recommended pack is:

```text
MINIMAL_EPISTEMIC_MEMORY_BRIDGE
```

It must implement only the reduced Approach 2 bridge and remain non-authoritative,
non-executing, provider-agnostic, default-off or explicitly invoked, and
compatible with the existing role loop, proposal artifact, evidence verifier,
budget, and FinalGate posture.
