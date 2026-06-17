# Sentinel Runtime-Owned Mutation Intent V1 Architecture

Date: 2026-06-16

## Verdict

`SENTINEL_GENERAL_PROTOCOL_ARCHITECTURE_FIX_RUNTIME_OWNED_MUTATION_INTENT_V1` replaces the failed mandatory generative selector protocol with a runtime-owned mutation intent protocol.

This is an experimental real-model harness architecture correction. It is not Wave 1 lock, not production certification, not a score increase, and not a commit/push closeout.

Readiness verdict for local architecture: `MUTATION_INTENT_V1_READY_WITH_LIMITATIONS`.

Provider probe status: `EXECUTED_ONCE_FAILED`.

The first real-model C-A1 probe used the active protocol and proved the selector was not used (`selector_calls = 0`) and the runtime-owned mutation lane was entered (`mutation_generation_calls = 6`). It failed before artifact acceptance because the provider/model did not produce a valid intent-bound artifact response within budget (`mutation_invalid_structured_outputs = 5`, `mutation_chunk_count = 0`).

## Historical Selector Architecture

The previous active protocol required the model to emit a generative selector decision:

```text
model observes/diagnoses
-> model emits propose_mutation selector JSON
-> runtime opens mutation lane
-> model emits artifact
```

This path is now marked:

```text
EXPERIMENTAL_REJECTED_FOR_ACTIVE_PROTOCOL
```

The selector code remains only to preserve historical V3.1/V3.2 tests, replay comparisons, and failure evidence. It is not used by the active `RUNTIME_OWNED_MUTATION_INTENT_V1` protocol and is not an automatic fallback.

## New Call Graph

The active protocol is:

```text
model observes/diagnoses
-> runtime evaluates factual mutation readiness
-> runtime constructs GovernedMutationIntent
-> model generates exactly one intent-bound artifact response
-> runtime validates chunk/order/hash/target/base hash
-> runtime assembles and secret-scans full payload
-> ArtifactRefStore performs second llm_exposable safety guard
-> existing reversible workspace executor applies only complete artifact
-> runtime verifies tests/oracle
-> receipts / FinalGate / replay remain evidence, never permission
```

The runtime owns protocol state and legal transitions. The model still owns mutation substance. The runtime does not generate the patch or hardcode a C-A1 solution.

## Governed Mutation Intent

`GovernedMutationIntent` contains metadata only:

```text
schema_version
intent_id
mission_id
run_id
workspace_ref
authority_ref
telemetry_certification_ref
observed_failure_ref
observed_target_paths
target_path
base_hashes
allowed_target_paths
required_postconditions
forbidden_paths
maximum_artifact_size
maximum_chunk_count
evidence_refs
policy_ref
created_at
expires_at
```

It excludes:

```text
solution
patch
raw prompt
raw provider response
raw reasoning
credentials
authorization headers
task-specific hidden hints
```

The intent is hash-bound through `intent_hash()` and through evidence refs attached to the mutation proposal.

## Readiness Policy

The runtime may construct an intent only after validated evidence proves readiness:

```text
mission not terminal
certified telemetry when available
mutation budget remains
deterministic test/failure observed
last test status is failing
failure category exists
source target was actually inspected
target path is inside workspace
target base hash is available
evidence continuation budget not exhausted
```

A simple file read, model claim, prompt text, or workspace content cannot create mutation readiness.

## Artifact Protocol

The active V1 mutation lane asks for:

```text
schema_version = sentinel_mutation_artifact_response_v1
response_type = artifact_chunk | needs_more_evidence | cannot_propose_safely | checkpoint
intent_id = matching runtime intent id
```

For `artifact_chunk`, the nested chunk remains the existing `sentinel_mutation_chunk_v1` shape and is normalized internally. Wrong intent id, wrong target, wrong mission/run, stale base hash, out-of-order chunk, duplicate chunk, missing chunk, oversized artifact, and secret-like assembled payload fail closed.

For `needs_more_evidence`, `cannot_propose_safely`, and `checkpoint`, the active mutation state is abandoned cleanly so duplicate mutation state cannot survive into the next loop.

## Authority And Terminal Checks

The mutation artifact channel uses an injected runtime guard with a fallback MissionKernel terminal check. The runner checks terminal/telemetry state before model artifact requests and after model responses; the channel checks again before chunk acceptance, assembly, and apply.

The post-apply safety check now uses the full `active_block_reason()` guard instead of only MissionKernel terminal status.

## Rollback And Oracle

Mutation application still uses the existing reversible workspace executor. The independent oracle remains authoritative. Model self-report cannot pass the run.

Rollback is required when postcondition/oracle/FinalGate/terminal safety requires it. A failed rollback prevents proof-complete success.

## Existing Runtime Reuse

Reused:

```text
MissionKernel
operator mission store
TelemetryKernel certified-mode checks when present
reversible workspace executor
ArtifactRefStore
safety scanner / redaction helpers
receipts
FinalGate refs
MissionReplayBuilder
real model execution provider wrapper
```

No second workspace executor, provider router, authority system, telemetry system, or model runtime was added.

## Remaining Limits

This V1 harness still has accepted limitations:

```text
single-target full-text replacement only
no crash-resume for provider probes
no concurrent workspace lease model inside this experimental harness
not fully unified with production AgentRuntime/PowerRuntime mission execution
provider probe not run without process-scoped credential
historical selector tests remain for comparison, not active protocol
```

## Next Decision

Recommended next move after review:

```text
FREEZE_PROTOCOL_AND_BEGIN_REPETITIONS
```

The next move should not be repetitions yet. The correct recommendation after the first real probe is:

```text
GENERAL_PROTOCOL_FIX_REQUIRED
```

The issue is now localized to mutation artifact protocol compliance/output shaping, not to the retired selector path.
