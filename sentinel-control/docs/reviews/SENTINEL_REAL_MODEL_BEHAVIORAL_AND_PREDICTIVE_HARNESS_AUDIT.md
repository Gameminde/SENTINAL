# Sentinel Real-Model Behavioral And Predictive Harness Audit

Date: 2026-06-15

Verdict: V3_1_READY_WITH_ACCEPTED_LIMITATIONS

Scope: local-only behavioral and predictive audit before any additional real-model provider call.

No real provider call was executed during this audit.

## Evidence Preserved

The audit preserves the prior empirical run evidence without rewriting outcomes:

| Experiment | Oracle | Calls | Tokens | Duration | Key result |
| --- | --- | ---: | ---: | ---: | --- |
| Initial | PASS | 15 | 20594 | 210.36s | Correct but inefficient; 7 invalid structured outputs. |
| V1 | FAIL | 9 | 9795 | 75.25s | Provider continuity loss. |
| V2 | FAIL | 7 | 10827 | 87.88s | Structured protocol too restrictive; mutation never executed. |
| V3 | FAIL | 6 | 9252 | 75.54s | Control-to-mutation handoff failed; last two control outputs hit exact 901-token ceiling. |

## Full Loop Reviewed

Reviewed path:

```text
prompt/frame construction
-> model request
-> provider transport
-> response extraction
-> structured validation
-> repair
-> state transition
-> tool selection
-> tool execution
-> observation normalization
-> context update
-> replan
-> mutation handoff
-> artifact generation
-> artifact validation
-> material execution
-> oracle
-> receipts
-> FinalGate
-> replay
-> report counters
```

## Observed Failures Fixed

| Severity | Finding | Status | Fix |
| --- | --- | --- | --- |
| P1 | Provider adapter extracted JSON from prose/Markdown-like wrapper. | Fixed | `strict_json_only` request metadata now forces exact JSON parsing for certification; prose with embedded JSON becomes `raw_text_hash`. |
| P1 | Late model response after mission kill could still execute an action. | Fixed | Terminal guard added before provider call, after provider call, and before coding/browser action execution. |
| P1 | Mutation selected before sufficient factual evidence could open the mutation lane. | Fixed | Factual harness state and legal-action list now derive from validated observations. Mutation requires observed target path. |
| P1 | Kill during mutation application could leave mutation visible. | Fixed | Post-apply terminal recheck triggers immediate safety rollback and records rollback receipt plus FinalGate refs. |
| P1 | Report proof flags used `any(receipt)` / `any(finalgate)`. | Fixed | Proof completeness now requires passed run plus proof refs for all material steps. Failed runs do not claim proof-complete success. |
| P2 | Exact output ceiling was not recorded as truncation. | Fixed | Provider response and call record now include safe `finish_reason` and `output_truncated`; truncated invalid output is classified as `TRUNCATED_JSON`. |
| P2 | Replay was built before terminal event. | Fixed | Replay is built after terminal status update and must include terminal explanation to be complete. |
| P2 | Failed run could leave unverified mutation visible. | Fixed | Failed coding runs rollback applied governed mutations before terminal failure record. |

## Predictive Findings

| Severity | Failure class | Audit result |
| --- | --- | --- |
| P1 | Prose treated as material command | Guarded by strict JSON-only provider parsing and local validator. |
| P1 | State-skipping to mutation | Guarded by factual `CodingHarnessState` and legal actions. |
| P1 | Provider succeeds after kill | Guarded by terminal post-response discard. |
| P1 | Partial visible mutation | Guarded by chunk validation, base hash checks, post-apply terminal rollback, failed-run rollback. |
| P1 | Raw provider material persistence | Guarded by hash-only invalid output records and tests. |
| P2 | Provider finish reason portability | Guarded when supplied; accepted limitation when provider omits finish reason. |
| P2 | Process restart during mutation assembly | Accepted limitation; in-memory channel invalidates safely but does not resume chunks durably. |
| P2 | Simultaneous missions targeting same workspace | Accepted limitation for this certification harness; production daemon/leases exist elsewhere but are not bound into this local harness. |
| P2 | Multi-file atomic mutation | Accepted limitation; V3 channel rejects multi-file mutation. |
| P3 | Observe/diagnose efficiency loops | Bounded by model/tool/token/duration budgets; not fully optimized. |

## Generic Fixes Made

Runtime and harness changes:

- Added strict JSON-only parsing option to `OpenAICompatibleChatProvider`.
- Added safe provider finish metadata: `finish_reason`, `output_truncated`.
- Added factual coding state machine:
  - `OBSERVING`
  - `DIAGNOSING`
  - `MUTATION_READY`
  - `MUTATION_GENERATING`
  - `MUTATION_VALIDATING`
  - `MUTATION_APPLYING`
  - `VERIFYING`
  - `COMPLETING`
  - `CHECKPOINTED`
  - `FAILED`
- Added state-derived legal actions to safe task summary.
- Added terminal guards before/after provider calls and before tool execution.
- Added mutation FinalGate refs and rollback receipt refs.
- Added rollback of unverified governed mutations on failed runs.
- Added terminal-complete replay check.
- Added observation freshness/index markers and latest observation hash refs.

These are generic harness fixes. No C-A1 solution, file hint, deterministic fallback, provider-native tool, or fallback/AUTO path was added.

## Authority Review

The model still cannot execute directly. Model output remains parsed advisory data only.

Material mutation path in V3.1:

```text
model selector JSON
-> local schema validator
-> factual state guard
-> governed mutation channel
-> validated artifact chunks
-> base hash and path checks
-> L3 reversible workspace executor
-> receipt
-> LowRiskFinalGate
-> oracle
-> replay
```

Known limitation: the certification harness still invokes local organ executors internally. This is not a model-direct organ path, and it is bounded by contracts, receipts, FinalGate, and MissionKernel terminal checks. It should be unified through the broader AgentRuntime/PowerRuntime bridge before claiming production-grade autonomous coding certification.

## Provider-Material Review

No raw key, raw prompt, raw provider response, raw reasoning, or authorization header is persisted by the added code.

The scan hits are expected field names, rejection tests, local environment credential reads, and safe hash-only reasoning metadata.

## Readiness Decision

V3.1 is safe and useful to execute as a controlled experiment with accepted limitations.

It is not a Wave 1 lock, not a score increase, and not browser certification.

Required V3.1 discipline:

- one pinned provider/backend/model contract
- no fallback/AUTO
- no provider-native tools
- no task-specific hints
- strict JSON-only response handling
- governed mutation channel enabled
- one C-A1 fresh run first
- independent oracle supremacy
- preserve failed runs
- stop after the first V3.1 result for review
