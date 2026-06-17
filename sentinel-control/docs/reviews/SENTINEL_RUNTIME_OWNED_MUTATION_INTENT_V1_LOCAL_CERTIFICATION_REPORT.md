# Sentinel Runtime-Owned Mutation Intent V1 Local Certification Report

Date: 2026-06-16

## Verdict

Local certification verdict:

```text
MUTATION_INTENT_V1_READY_WITH_LIMITATIONS
```

Provider probe status before the real endpoint was supplied:

```text
MUTATION_INTENT_V1_READY_NOT_RUN
```

After the endpoint/key were supplied locally, exactly one provider-backed C-A1 probe was executed.

Provider probe result:

```text
EXECUTED_ONCE_FAILED
```

No credential value was written into reports, telemetry, exceptions, or command output.

## Architecture Implemented

Implemented local harness changes:

```text
active experiment = RUNTIME_OWNED_MUTATION_INTENT_V1
selector status = EXPERIMENTAL_REJECTED_FOR_ACTIVE_PROTOCOL
runtime-owned GovernedMutationIntent
factual mutation readiness policy
intent-bound mutation artifact response parser
intent id carried through proposal/chunk/channel
clean abandon on needs_more_evidence / cannot_propose_safely / checkpoint
full active_block_reason guard after apply
frozen-policy hash includes provider/backend/model and endpoint hash
```

## Frozen Policy

Frozen no-provider policy command succeeded.

```text
experiment_version = RUNTIME_OWNED_MUTATION_INTENT_V1
task = C-A1
repetitions = 1
max_steps = 18
max_model_calls = 18
max_tool_steps = 16
control_output_tokens = 900
selector_output_tokens = 256
mutation_output_tokens = 2400
max_mutation_calls_per_proposal = 4
max_mutation_chunk_bytes = 8192
max_mutation_artifact_bytes = 32768
max_mutation_chunks = 8
max_evidence_continuations = 1
provider_retry_budget = 1
max_total_tokens = 24000
max_run_duration_seconds = 240
```

Initial no-provider placeholder policy hash:

```text
72ad6474ee4c06b061359872217871c863e3bfbf3e4e6d430e37a94073065be7
```

The provider-backed run required a corrected frozen policy hash because the real endpoint is now pinned by `base_url_hash`.

Provider-backed policy hash:

```text
e165bf7507e1428654a8228bb101d63529a04e73eee131f3c8264d6e6e96a67e
```

Provider identifiers, without credential:

```text
provider_id = alibaba_model_studio_certification
backend_id = alibaba_model_studio_openai_compatible_chat
model_id = deepseek-v4-pro
base_url_hash = 2d2c55d3b413880d0d943f7b4db15beb98a446dab2a8c82730b9dd4effc3fe72
credential_env = SENTINEL_CERT_MODEL_API_KEY
```

## Local Tests Run

Passed:

```text
py -3.13 -m pytest -q tests/test_real_model_behavioral_predictive_harness_audit.py tests/test_real_model_agent_certification_v0.py tests/test_governed_mutation_artifact_channel_v3.py
py -3.13 -O -m pytest -q tests/test_real_model_behavioral_predictive_harness_audit.py tests/test_real_model_agent_certification_v0.py tests/test_governed_mutation_artifact_channel_v3.py
py -3.13 -m pytest -q tests/test_openai_compatible_provider_base.py tests/test_real_model_execution_backend.py
py -3.13 -m pytest -q tests/test_real_world_power_convergence_wave1.py tests/test_mission_kernel.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_llm_live_operator_replay_v0.py tests/test_llm_memory_replay_and_checkpoints_v0.py
py -3.13 -m pytest -q tests/test_agent_runtime.py tests/test_agent_runtime_certification.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_sentinel_power_runtime_v0.py tests/test_llm_live_operator_power_runtime_bridge_v0.py
py -3.13 -m pytest -q tests/test_observability_telemetry_and_product_power_metrics_v1.py tests/test_durable_receipt_ledger_foundation.py tests/test_low_risk_execution_finalgate_receipts.py
py -3.13 -m compileall -q sentinel
git diff --check
```

`git diff --check` produced only expected LF/CRLF working-copy warnings on pre-existing tracked files and no whitespace errors.

## Local Adversarial Scenarios Covered

Covered by targeted tests:

```text
simple file read cannot create mutation intent
runtime-owned V1 opens mutation lane without selector
active V1 coding prompt forbids model-generated propose_mutation
intent metadata excludes raw payload/solution
intent carries base hash, telemetry ref, policy ref, target list, size/chunk bounds
wrong intent id rejected
wrapped artifact response normalized into validated chunk
split secret across chunks rejected before artifact-store persistence
ArtifactRefStore still rejects llm_exposable secret text
kill/revocation blocks assembly/apply
terminal response after model call discarded separately
provider retry does not duplicate material action
needs_more_evidence returns cleanly to diagnosis without duplicate mutation state
```

## Safety Scan

Targeted scans were run on modified/restored files for:

```text
real credentials
authorization headers
raw prompts
raw provider responses
raw reasoning
fallback/AUTO
provider-native tools
direct organ bypass strings
task-specific C-A1 hints
```

Findings were expected guard/test references only:

```text
credential env var names
runtime Authorization header construction without persistence
synthetic test secrets
forbidden payload key lists
anti-fallback policy text
raw prompt/provider/reasoning rejection tests
```

No real credential, provider key, raw provider response, raw reasoning, deterministic fallback, provider-native tool execution, or direct organ bypass was found in modified/restored files.

## Provider Probe

Exactly one C-A1 provider probe was run.

```text
run_root = w/runtime_owned_mutation_intent_v1_probe/20260616-151812
experiment_version = RUNTIME_OWNED_MUTATION_INTENT_V1
policy_hash = e165bf7507e1428654a8228bb101d63529a04e73eee131f3c8264d6e6e96a67e
primary outcome = ARTIFACT_PROTOCOL_COMPLIANCE
evidence scope = GENERIC_SYSTEM_FINDING
status = failed
selector_calls = 0
control_calls = 3
mutation_generation_calls = 6
mutation_invalid_structured_outputs = 5
mutation_first_pass_structured_validity_rate = 0.3333
mutation_chunk_count = 0
mutation_validation_result = generation_failed
partial_mutation_applications = 0
duplicate_material_side_effects = 0
cross_mission_contamination = 0
oracle_passed = false
replay_complete = true
input_tokens = 12017
output_tokens = 13447
cost_usd = 0.0 reported by provider metadata
```

Failure categories:

```text
EXTRA_UNSUPPORTED_FIELD
TRUNCATED_JSON
NON_JSON_TEXT
EXTRA_UNSUPPORTED_FIELD
TRUNCATED_JSON
```

Interpretation:

```text
The runtime-owned intent path activated correctly.
The historical selector path was not used.
No artifact chunk was accepted.
No partial mutation became visible.
No duplicate side effect occurred.
The first real failure is mutation artifact response compliance/output shaping.
```

## Historical Evidence Preservation

Historical experimental evidence remains preserved:

```text
Initial C-A1 = PASS
V1 = FAIL
V2 = FAIL
V3 = FAIL
V3.1 initial = FAIL
Aggressive V3.1 R1/R2/R3 = FAIL
Adjacent V3.2 probe = FAIL
```

No historical run was deleted, overwritten, hidden, or reclassified.

## Limits

The protocol is ready for one controlled C-A1 probe when a process-scoped credential is present, but remains limited:

```text
not Wave 1 lock
not production certification
not browser certification
not score increase
single-target full-text replacement in this harness
no automatic retries until success
no commit/push
```

## Recommendation

Recommended next action:

```text
GENERAL_PROTOCOL_FIX_REQUIRED
```

Do not begin repetitions yet. Improve the generic mutation artifact response profile before another run. The next fix should stay generic and must not add C-A1-specific hints, target filenames, or deterministic fallback.

Most likely generic fix area:

```text
artifact response contract too verbose or too easy to violate
mutation output budget / chunk protocol pressure
safe response repair feedback should focus on the wrapper shape
possibly use a smaller canonical artifact response shape or provider JSON-mode profile
```
