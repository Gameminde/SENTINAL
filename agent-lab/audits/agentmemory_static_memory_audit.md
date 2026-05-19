# AgentMemory Static Memory Audit

Date: 2026-05-19

Source: https://github.com/rohitg00/agentmemory

Local source: `agent-lab/vendors/agentmemory/source`

Audited commit: `68fddd418e1bbcc41d32a1c61b7a78d91eb7c4dc`

Execution status: source audit only. No install, no server start, no MCP client
connection, no provider call, no real account connection, no key usage.

## Verdict

AgentMemory is one of the most useful memory specimens in Agent Lab so far, but
it must not be adopted as a trusted Sentinel substrate.

The strongest ideas to harvest are:

- typed memory strata instead of one flat summary blob;
- hook/event capture before derivation;
- deterministic compression as a safe default;
- working memory slots and pinned hot context;
- hybrid retrieval with transparent scoring;
- temporal graph and relation modeling;
- access tracking, retention scoring, TTL, supersession, and versioning;
- replay/timeline reconstruction;
- lessons, routines, checkpoints, and self-reflection loops.

The most dangerous ideas to reject or rewrite are:

- default-open auth when no secret is configured;
- direct memory injection into model prompts without a strict data/instruction
  boundary;
- raw observation capture that can contain prompts, tool inputs, tool outputs,
  assistant responses, images, and secrets;
- remote/API file read and rewrite surfaces;
- LLM-extracted memory or graph facts becoming treated as truth;
- destructive delete paths where audit can happen after deletion;
- monolithic MCP/API tool surfaces exposed to agents.

Sentinel should harvest the memory operating model, not the runtime.

## Audit Scope

Read-only inspection covered:

- `README.md`
- `GOVERNANCE.md`
- `src/types.ts`
- `src/functions/remember.ts`
- `src/functions/search.ts`
- `src/functions/context.ts`
- `src/functions/working-memory.ts`
- `src/functions/slots.ts`
- `src/functions/retention.ts`
- `src/functions/auto-forget.ts`
- `src/functions/checkpoints.ts`
- `src/functions/replay.ts`
- `src/functions/privacy.ts`
- `src/functions/audit.ts`
- `src/functions/hybrid-search.ts` and related retrieval modules through source
  map/search inspection
- `src/functions/graph.ts`
- `src/functions/temporal-graph.ts`
- REST/API and MCP surfaces in `src/triggers/api.ts` and `src/mcp/server.ts`
- OpenClaw and Hermes integration surfaces through source search.

The upstream `DESIGN.md` was intentionally not used as a memory architecture
source; it appears to describe a visual design system rather than the memory
runtime.

## System Shape

AgentMemory is a local-first memory runtime for coding agents. Its advertised
model is:

```text
agent hook events
-> raw observations
-> compressed observations
-> memories / summaries / lessons / graph nodes
-> search / context injection / replay / viewer
```

It integrates through hooks, MCP, REST APIs, and direct host plugins. The same
memory server can serve multiple agent hosts.

For Sentinel, the important lesson is not "add another memory server." The
lesson is that memory must become an operating layer with capture, derivation,
retrieval, retention, replay, and governance as separate phases.

## Strong Mechanisms To Harvest

### 1. Typed Memory Strata

AgentMemory separates sessions, raw observations, compressed observations,
durable memories, summaries, lessons, slots, graph nodes, graph edges, actions,
and checkpoints. See `src/types.ts:1`, `src/types.ts:29`,
`src/types.ts:44`, `src/types.ts:81`, `src/types.ts:222`,
`src/types.ts:352`, `src/types.ts:397`, `src/types.ts:435`,
`src/types.ts:667`, and `src/types.ts:843`.

Sentinel adaptation:

- Keep the concept.
- Rewrite as Sentinel-native `MissionObservation`, `MissionMemory`,
  `MissionMemoryClaim`, `MissionMemorySlot`, `MissionMemoryRelation`,
  `MissionCheckpoint`, and `MissionReplayEvent`.
- Every durable entry must have source class, scope, TTL, confidence, variance,
  claim status, evidence refs, receipt refs, contradiction refs, authority
  effect `none`, and execution effect `none`.

### 2. Observe First, Derive Later

The capture path records session/tool events first and derives memory afterward.
This is visible in `src/functions/observe.ts` and the hook payload types in
`src/types.ts`.

Sentinel adaptation:

- Keep the measurement-first shape.
- Raw provider prompt/response/reasoning and secrets still cannot become
  durable Sentinel metadata.
- Store safe observations and hashes, not raw prompts or hidden execution
  payloads.
- Derived memory must be rebuildable from safe receipts and evidence.

### 3. Deterministic Compression As Default

AgentMemory has a zero-LLM synthetic compression path and treats LLM compression
as optional. Source references include `src/functions/observe.ts:223`,
`src/functions/observe.ts:234`, `src/functions/compress.ts:67`, and config
flags in `src/config.ts`.

Sentinel adaptation:

- Keep deterministic compression as the default.
- LLM enrichment may propose labels or hypotheses, but those labels stay
  `CLAIMED` or `INFERRED` until evidence-bound verification supports them.

### 4. Versioning, Supersession, TTL

`mem::remember` creates durable memories with strength, version, parent,
supersedes, related IDs, source observation IDs, and `forgetAfter` TTL. Source:
`src/functions/remember.ts:12`, `src/functions/remember.ts:72`,
`src/functions/remember.ts:83`, `src/functions/remember.ts:93`,
`src/functions/remember.ts:141`.

Sentinel adaptation:

- Keep TTL, supersession, and version history.
- Never delete phase-lock evidence silently.
- Prefer tombstones, archived historical context, and explicit supersession over
  hard delete for governance-critical memory.

### 5. Working Memory Slots

AgentMemory has pinned slots and working context that are budgeted and ranked.
References include `src/types.ts:222`, `src/functions/slots.ts:13`,
`src/functions/slots.ts:169`, `src/functions/working-memory.ts:25`,
`src/functions/working-memory.ts:100`, and `src/functions/working-memory.ts:209`.

Sentinel adaptation:

- Add scoped slots such as `mission_objective`, `operator_preferences`,
  `active_constraints`, `risk_posture`, `authority_lane`, `current_evidence`,
  and `open_questions`.
- Slots are context aids only. They cannot grant authority or approve execution.
- Pinning affects retrieval priority, not truth or permission.

### 6. Hybrid Retrieval

AgentMemory combines lexical, vector, and graph retrieval, with reciprocal rank
fusion and optional reranking. References include `README.md:745`,
`src/state/hybrid-search.ts:22`, `src/state/hybrid-search.ts:80`,
`src/state/hybrid-search.ts:197`, and `src/state/reranker.ts:34`.

Sentinel adaptation:

- Start with BM25 plus typed metadata filters and source scopes.
- Add local embeddings after DLP and deterministic fixtures exist.
- Add graph retrieval after provenance/confidence is first-class.
- Keep score components visible. Retrieval score is not truth.

### 7. Query Expansion And Smart Search

AgentMemory includes query expansion, compact/expanded smart search, and access
tracking. References include `src/functions/query-expansion.ts:5`,
`src/functions/smart-search.ts:12`, `src/functions/search.ts:164`, and
`test/smart-search.test.ts:171`.

Sentinel adaptation:

- Use query expansion to find evidence gaps and related receipts.
- Mark expanded queries as generated retrieval hypotheses.
- Do not let query expansion add new claims to memory without source refs.

### 8. Temporal Graph

AgentMemory models graph nodes, edges, temporal validity, old edge history, and
temporal queries. References include `src/types.ts:352`,
`src/types.ts:397`, `src/functions/graph.ts:82`,
`src/functions/graph-retrieval.ts:41`, `src/functions/temporal-graph.ts:152`,
and `src/functions/temporal-graph.ts:277`.

Sentinel adaptation:

- Keep a mission graph, but every edge must carry provenance, evidence refs,
  confidence, validity window, and contradiction refs.
- Graph extraction by an LLM is a proposed graph, not proof.
- Old edges must survive as history; do not smooth contradictions away.

### 9. Lessons, Preferences, Routines

AgentMemory contains lessons, routines, slots, and preferences as reusable memory
forms. References include `src/functions/lessons.ts:7`,
`test/lessons.test.ts:94`, `src/functions/routines.ts:8`,
and `test/routines.test.ts:59`.

Sentinel adaptation:

- Keep lessons as scoped memory with confidence damping.
- Preferences require source class and scope. User corrections outrank inferred
  preferences.
- Routines should become proposal templates only until explicit execution lanes
  exist.

### 10. Checkpoints And Replay

AgentMemory supports replay, timeline import, checkpoints, action state, and
snapshot-like restore. References include `README.md:370`,
`src/functions/replay.ts:261`, `src/replay/jsonl-parser.ts:93`,
`src/replay/timeline.ts:103`, `src/functions/checkpoints.ts:8`,
`src/functions/checkpoints.ts:132`, `src/functions/snapshot.ts:39`, and
`src/functions/snapshot.ts:156`.

Sentinel adaptation:

- Build mission replay as a flight recorder for role loops, proposal artifacts,
  gates, receipts, memory updates, and FinalGate results.
- Checkpoints should be authority-neutral markers: they can block/resume planned
  work, but they cannot approve execution.
- Restore must be bounded by workspace roots and audited.

### 11. Retention Scoring And Auto-Forget

AgentMemory has retention scoring, access logs, decay, hot/warm/cold tiers,
dry-run eviction, and auto-forget. References include
`src/functions/retention.ts:80`, `src/functions/retention.ts:122`,
`src/functions/retention.ts:246`, `src/functions/retention.ts:291`,
`src/functions/auto-forget.ts:24`, `src/functions/auto-forget.ts:40`,
and `src/functions/auto-forget.ts:118`.

Sentinel adaptation:

- Keep retention scoring.
- Archive or tombstone governance-critical entries instead of deleting them.
- Retention should prefer "less visible" over "gone" for uncertain or
  audit-relevant entries.
- Access frequency must not convert a claim into truth.

### 12. Audit And Privacy Surfaces

AgentMemory contains privacy redaction, sensitive path checks, and audit records.
References include `src/functions/privacy.ts:5`, `src/functions/privacy.ts:22`,
`test/privacy.test.ts:5`, `src/functions/audit.ts:9`,
`src/functions/audit.ts:34`, and `test/remember-forget-audit.test.ts:48`.

Sentinel adaptation:

- Keep the idea of redaction and audit.
- Strengthen it: DLP before persistence, no raw prompt/response/reasoning/key,
  pre-delete immutable audit, and export privilege checks.

## Dangerous Patterns Sentinel Must Avoid

### 1. Default-Open Auth

`checkAuth` returns allow when no secret is configured. The middleware also
continues when no secret exists. See `src/triggers/api.ts:34` and
`src/triggers/api.ts:64`.

Sentinel decision: reject. Memory APIs must not default open. Local development
can have a clearly marked unauthenticated mode only when loopback-only,
disabled by default for sensitive operations, and visible in receipts.

### 2. Memory Injection Without Hard Boundary

`mem::context` renders memory into an agent context block. It includes pinned
slots, project profile, lessons, summaries, and observations. See
`src/functions/context.ts:114` and `src/functions/context.ts:226`.

Sentinel decision: modify. Memory retrieved into prompts must be treated as
untrusted data, quoted or encoded, provenance-labelled, and blocked from
instruction authority.

### 3. Raw Observation Leakage

`RawObservation` includes tool inputs, tool outputs, user prompts, assistant
responses, raw payloads, and image data in `src/types.ts:29`. Hooks and observe
paths can capture broad payloads.

Sentinel decision: reject raw persistence. Store safe summaries, receipt refs,
hashes, redaction status, and evidence IDs. Raw prompt, provider response,
reasoning, keys, and hidden action payloads remain non-durable.

### 4. Arbitrary Local File Surfaces

REST paths include file compression and replay import by path. See
`src/triggers/api.ts:410`, `src/functions/compress-file.ts:107`,
`src/functions/compress-file.ts:150`, `src/triggers/api.ts:473`, and
`src/functions/replay.ts:305`.

Sentinel decision: reject as agent-callable API. Any future file memory import
must be workspace-root allowlisted, local-only, user-approved for sensitive
paths, and dry-run auditable.

### 5. Destructive Delete Before Durable Audit

Some deletion/retention paths delete data and then record audit or summarize
audit after the operation. References include `src/functions/remember.ts:153`,
`src/functions/retention.ts:370`, `src/functions/audit.ts:31`, and
`src/functions/governance.ts:21`.

Sentinel decision: modify. Pre-delete audit and tombstone first, then mutate.
Failures must not erase the proof trail.

### 6. LLM-Derived Graph As Truth

Temporal graph extraction uses an LLM prompt path. See
`src/functions/temporal-graph.ts:157` and
`src/functions/temporal-graph.ts:183`.

Sentinel decision: modify. LLM graph output is an inferred claim graph.
Evidence verifier and contradiction tracker decide status. Graph confidence does
not grant authority.

### 7. Monolithic Agent Tool Surface

AgentMemory exposes a broad set of MCP/API functions. The README describes more
than 50 tools, and `src/index.ts` registers a large function family.

Sentinel decision: reject broad memory tool exposure. Sentinel memory should
have narrow internal interfaces, explicit caller contracts, and test-only
replacement paths.

## Premortem: How AgentMemory Patterns Could Break Sentinel

### Memory-As-Authority Re-Entry

Risk: retrieved "lessons" or "routines" are interpreted as permission.

Sentinel control:

- memory has `authority_effect = none`;
- gates read mission authority from Root Authority and Delegated Operational
  Authority only;
- role consensus, lesson confidence, graph confidence, and recall frequency
  cannot approve execution.

### Receipt Trust Laundering

Risk: a self-generated observation becomes a memory, then a future verifier uses
it as proof.

Sentinel control:

- self-generated receipts can support continuity but cannot satisfy independent
  evidence requirements alone;
- every claim tracks source class and independence class;
- repeated same-source observations do not increase confidence.

### Prompt Injection Through Memory

Risk: a stored memory says "ignore prior policy" and gets injected into the role
loop as if it were instruction.

Sentinel control:

- memory retrieval returns data blocks, not instructions;
- role prompts explicitly treat memory as untrusted observations;
- scanner rejects authority expansion, provider/model override, credential
  access, and hidden action payloads.

### Stale Evidence Resurrection

Risk: old workspace state, old user preference, old provider status, or old
mission scope is revived as current truth.

Sentinel control:

- TTL and validity scope are mandatory;
- expired memory becomes historical context only;
- user corrections supersede inferred memory while preserving audit trail;
- retrieval includes contradiction and supersession metadata.

### Duplicate Confidence Inflation

Risk: the same idea repeated across summaries, lessons, graph nodes, and slots
appears independently supported.

Sentinel control:

- confidence updates are grouped by source lineage;
- same-source duplicates increase familiarity, not truth;
- independent evidence is required for support upgrades.

## Sentinel Concepts To Add

### MissionObservation

Safe, redacted event or measurement. It can reference hashes and receipts, but
not raw prompts, raw provider responses, raw reasoning, or keys.

### MissionMemoryClaim

Epistemic claim with:

- `claim_status`;
- `source_class`;
- `source_id`;
- `source_scope`;
- `validity_scope`;
- `confidence`;
- `variance`;
- `evidence_refs`;
- `receipt_refs`;
- `contradiction_refs`;
- `expires_at`;
- `authority_effect = none`;
- `execution_effect = none`.

### MissionMemorySlot

Pinned scoped context for active mission operation. Slots improve attention,
not authority.

### MissionMemoryGraph

Temporal graph of mission entities, capabilities, gates, receipts, evidence,
risks, and lessons. Edges carry provenance and validity windows.

### MissionRetentionScore

Score for recall priority, storage tier, and compression/archival decisions.
Retention score must not become confidence.

### MissionReplay

Reconstructable timeline from safe role-loop receipts, proposal receipts,
gate decisions, budget summaries, evidence verdicts, memory updates, and
FinalGate outcomes.

### MissionCheckpoint

Authority-neutral milestone that can pause, resume, or compare mission state.
It cannot approve execution.

## Recommended Sentinel Test Suite

Add these tests before implementing a memory bridge:

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
- `test_memory_prompt_injection_is_quoted_and_non_authoritative`
- `test_retention_does_not_delete_lock_or_finalgate_evidence`
- `test_delete_writes_tombstone_before_removal`
- `test_replay_rebuilds_memory_snapshot_from_safe_receipts`
- `test_slot_pinning_affects_recall_not_truth`
- `test_graph_edge_confidence_does_not_grant_authority`

## Keep / Modify / Reject Matrix

| Mechanism | Sentinel decision | Reason |
| --- | --- | --- |
| Typed memory strata | Keep and rewrite | Good system separation, needs Sentinel epistemic fields |
| Hook/event capture | Keep and rewrite | Observe-first is powerful, raw fields must be redacted |
| Deterministic compression | Keep | Safe default for memory derivation |
| Optional LLM compression | Modify | LLM output is hypothesis, not truth |
| Working memory slots | Keep and rewrite | Strong attention primitive, no authority effect |
| Hybrid retrieval | Keep phased | Start BM25+metadata, add vectors/graph later |
| Temporal graph | Keep and rewrite | Valuable for causality and stale-state tracking |
| Lessons/preferences | Modify | Confidence and source scope required |
| Routines | Modify | Proposal templates only until lanes exist |
| Replay/timeline | Keep | Flight recorder shape aligns with receipts |
| Checkpoints | Keep and rewrite | Must stay authority-neutral |
| Retention/auto-forget | Modify | Archive/tombstone governance evidence |
| Privacy/audit | Keep and harden | Good direction, insufficient for Sentinel raw-leak rules |
| Default-open auth | Reject | Memory is sensitive control surface |
| Direct prompt injection | Reject as-is | Memory is untrusted data, not instruction |
| Arbitrary file API | Reject as-is | Too much local authority for a memory service |
| Monolithic MCP surface | Reject | Too broad for Sentinel authority model |
| LLM graph as proof | Reject | Extraction is inferred claim only |

## What Sentinel Should Build Next

The next Sentinel memory implementation should stay reduced and rigorous:

```text
Minimal Epistemic Memory Bridge
-> safe memory entries
-> feedback signals
-> source/scope/TTL/confidence/variance
-> contradiction tracking
-> no-authority firewall
-> replayable snapshots
```

Do not start broad memory server integration, third-party memory adapters,
MCP memory tools, browser/desktop organs, or self-modifying memory.

## Final Finding

AgentMemory shows how much power a real memory layer can give an agent:
continuity, recall, context selection, replay, lessons, routines, graph
navigation, and compounding feedback. It also demonstrates the central danger:
memory surfaces are close to the prompt, close to tools, and close to local
files. If those surfaces are not bounded, memory becomes a hidden authority
channel.

Sentinel should take the power, not the trust model.
