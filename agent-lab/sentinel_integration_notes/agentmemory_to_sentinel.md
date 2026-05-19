# AgentMemory To Sentinel Integration Notes

Date: 2026-05-19

Source audit: `agent-lab/audits/agentmemory_static_memory_audit.md`

## Strategic Takeaway

AgentMemory confirms Sentinel's memory lab direction:

```text
Memory is not truth.
Memory is not authority.
Memory is a scoped epistemic witness state.
Receipts are measurements.
Evidence is bound proof.
Gates are law.
FinalGate is certification boundary.
```

The vendor is powerful because it treats memory as a runtime layer rather than a
single summary file. Sentinel should absorb that lesson while keeping a stricter
authority firewall.

## Sentinel-Native Rewrite

### Minimal Epistemic Memory Bridge

The first implementation should not be a full memory server. It should be a
small internal bridge that accepts safe role-loop and proposal receipts, then
produces:

- `SafeFeedbackSignal`;
- `LivingMissionMemoryEntry`;
- `LivingMissionMemorySnapshot`;
- replayable memory update receipts.

Fields should include:

- `memory_id`;
- `mission_id`;
- `source_class`;
- `source_id`;
- `source_scope`;
- `validity_scope`;
- `claim_status`;
- `confidence`;
- `variance`;
- `created_at`;
- `observed_at`;
- `expires_at`;
- `evidence_refs`;
- `receipt_refs`;
- `contradiction_refs`;
- `authority_effect = none`;
- `execution_effect = none`;
- `safe_summary`.

### Hot Context Slots

Borrow AgentMemory's slot idea, but make slots Sentinel-native:

- `mission_objective`;
- `active_constraints`;
- `root_authority_summary`;
- `delegated_lane_summary`;
- `risk_posture`;
- `current_evidence`;
- `open_questions`;
- `operator_preferences`;
- `recent_finalgate_results`.

Slots should be pinned context, not proof and not permission.

### Retrieval Roadmap

Use a staged retrieval sequence:

1. lexical search plus metadata filters;
2. safe access tracking;
3. local embeddings after DLP and fixtures;
4. graph retrieval after provenance and contradiction tests;
5. reranking after score transparency exists.

Retrieval score can guide attention. It cannot promote claim status by itself.

### Temporal Mission Graph

Build a mission graph only after the minimal bridge is stable. Candidate edge
types:

- `mission -> requires -> capability`;
- `capability -> gated_by -> authority_gate`;
- `proposal -> cites -> evidence`;
- `proposal -> blocked_by -> risk`;
- `receipt -> measures -> action_result`;
- `memory_claim -> contradicted_by -> evidence`;
- `user_correction -> supersedes -> inferred_memory`;
- `lesson -> informs -> role_contract`.

Every edge must carry provenance, confidence, validity window, and
contradiction refs.

### Replay As Flight Recorder

Sentinel should use the replay pattern to reconstruct:

- role loop sequence;
- proposal artifact creation;
- verifier results;
- gate decisions;
- budget use;
- memory updates;
- FinalGate outcomes.

Replay must be based on safe receipts, not raw prompt or provider response.

## What To Keep From AgentMemory

- typed memory strata;
- observe first, derive later;
- deterministic compression default;
- working memory slots;
- version/supersession/TTL;
- hybrid retrieval architecture;
- graph and temporal validity concepts;
- lessons/routines as reusable proposal aids;
- replay/timeline reconstruction;
- retention scoring and access logs;
- privacy and audit as first-class features.

## What To Reject Or Redesign

- default-open auth;
- broad REST/MCP memory tool surfaces;
- direct memory-as-prompt injection;
- raw prompt/tool/provider/response persistence;
- arbitrary file compression/import APIs;
- LLM graph extraction as ground truth;
- destructive deletion without pre-delete tombstone;
- memory routines that directly execute;
- provider/model settings being inferred from memory.

## Required Sentinel Invariants

- Memory cannot grant Root Authority.
- Memory cannot expand `MissionAuthorityEnvelope`.
- Memory cannot create delegated operational lanes.
- Memory cannot approve execution.
- Memory cannot unlock credentials.
- Memory cannot override provider, backend, or model.
- Memory cannot bypass user review.
- Memory cannot bypass FinalGate.
- Memory cannot turn repeated unsupported claims into truth.
- Memory cannot convert a blocked action into an allowed action.
- Memory cannot mutate prompts, code, tests, policy, runtime, organs, providers,
  or `.env`.

## Implementation Recommendation

Proceed with the reduced Approach 2 from the memory lab:

```text
Minimal Epistemic Memory Bridge
with confidence, variance, TTL, source class, scope,
contradiction tracking, user-correction precedence,
duplicate-source suppression, and no-authority firewall.
```

Do not implement:

- external memory server;
- AgentMemory dependency bridge;
- MCP memory tools;
- direct context injection;
- broad agent history import;
- auto-running routines;
- organ execution from memory.

## First Tests To Write

- `test_memory_retrieval_is_data_not_instruction`
- `test_memory_cannot_grant_root_authority`
- `test_memory_cannot_create_delegated_lane`
- `test_memory_cannot_approve_execution`
- `test_memory_cannot_override_provider_backend_model`
- `test_raw_prompt_response_reasoning_key_rejected_before_memory_persist`
- `test_self_generated_receipts_do_not_satisfy_evidence_requirement`
- `test_duplicate_same_source_does_not_increase_confidence`
- `test_user_correction_supersedes_inferred_memory`
- `test_contradictions_survive_retrieval`
- `test_expired_memory_returns_historical_only`
- `test_slot_pinning_affects_recall_not_truth`
- `test_graph_edge_confidence_does_not_grant_authority`
- `test_replay_rebuilds_memory_snapshot_from_safe_receipts`

## Bottom Line

AgentMemory proves that memory is a force multiplier for agents, but Sentinel's
version must be more epistemic, more scoped, more auditable, and more hostile to
hidden authority channels.

The power to take:

```text
continuous memory -> retrieval -> feedback -> better reasoning
```

The boundary to preserve:

```text
memory improves cognition, never authority.
```
