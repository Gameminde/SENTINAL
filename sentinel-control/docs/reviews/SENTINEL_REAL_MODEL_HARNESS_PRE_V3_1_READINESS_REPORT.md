# Sentinel Real-Model Harness Pre-V3.1 Readiness Report

Date: 2026-06-15

Verdict: V3_1_READY_WITH_ACCEPTED_LIMITATIONS

## What Was Done

This was a behavior-informed local audit and hardening pass before another paid/provider-backed real-model experiment.

No V3.1 provider run was executed.

No commit or push was performed.

## Observed Failures Fixed

- strict JSON-only response handling for certification
- safe finish reason and output truncation metadata
- factual harness state and state-derived legal actions
- mutation lane blocked until target evidence is observed
- late provider response after terminal mission state discarded
- mutation apply rolled back if terminal state appears during execution
- failed runs rollback unverified governed mutations
- mutation applications now carry FinalGate refs
- proof completeness counters no longer overclaim failed or partially-proved runs
- replay completeness now requires terminal mission replay

## Predicted Failures Guarded

- truncated control response
- truncated mutation chunk
- provider error after accepted selector
- invalid selector followed by valid repair
- two invalid selectors
- mutation selector with insufficient evidence
- oversized mutation
- multi-file mutation
- stale file after artifact generation
- kill before apply
- oracle failure after successful apply
- prompt injection in source file
- context summary missing remaining requirement
- budget exhaustion during diagnosis or mutation generation

## Remaining Limits

| Limit | Severity | Rationale |
| --- | --- | --- |
| Durable mutation chunk resume after process restart is not implemented. | Accepted limitation | Safe failure is preferable to replaying stale chunks. V3.1 should be single-run only. |
| Harness-level workspace lease for concurrent certification missions is not implemented. | Accepted limitation | Do not run concurrent V3.1 missions against the same workspace. |
| Multi-file atomic mutation is not implemented. | Accepted limitation | V3.1 can still do sequential governed single-file mutations; multi-file atomicity must come later. |
| Internal harness still invokes local executors directly after constructing governed requests. | Accepted limitation | Model cannot directly call organs; receipts/FinalGate/MissionKernel guards exist. Full AgentRuntime/PowerRuntime unification remains future hardening. |
| Finish reason may be absent on some providers. | Accepted limitation | Safe hash-only invalid output still fails closed. |

## CodeRabbit Advisory Review

CodeRabbit used: no.

Reason: CodeRabbit CLI was unavailable in the environment, and this audit explicitly forbids additional real-model/provider calls. Manual exhaustive local review and deterministic tests were performed instead.

CodeRabbit did not become authority.

## Tests Run

Local deterministic tests:

```text
py -3.13 -m pytest -q tests/test_real_model_behavioral_predictive_harness_audit.py
10 passed

py -3.13 -m pytest -q tests/test_real_model_agent_certification_v0.py tests/test_governed_mutation_artifact_channel_v3.py
52 passed

py -3.13 -O -m pytest -q tests/test_real_model_behavioral_predictive_harness_audit.py tests/test_real_model_agent_certification_v0.py tests/test_governed_mutation_artifact_channel_v3.py
62 passed

py -3.13 -m pytest -q tests/test_openai_compatible_provider_base.py tests/test_real_model_execution_backend.py
43 passed

py -3.13 -m pytest -q tests/test_real_world_power_convergence_wave1.py tests/test_mission_kernel.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_llm_live_operator_replay_v0.py tests/test_llm_memory_replay_and_checkpoints_v0.py
100 passed

py -3.13 -m pytest -q tests/test_agent_runtime_certification.py tests/test_agent_runtime.py tests/test_organ_execution_agentruntime_opt_in.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_llm_live_operator_power_runtime_bridge_v0.py tests/test_sentinel_power_runtime_v0.py
109 passed

py -3.13 -m pytest -q tests/test_observability_telemetry_and_product_power_metrics_v1.py tests/test_low_risk_execution_finalgate_receipts.py tests/test_durable_receipt_ledger_foundation.py tests/test_agent_trace_replay.py tests/test_reversible_workspace_action_executor_l3.py
89 passed

py -3.13 -m compileall -q sentinel
OK

git diff --check
OK
```

Scan result:

- no raw provider key persisted
- no raw prompt persisted
- no raw provider response persisted
- no raw reasoning persisted
- no fallback/AUTO path added
- no provider-native tool path added
- expected scan hits are rejection tests, forbidden field names, local environment credential reads, and safe hash-only metadata

## Exact V3.1 Run Policy

Recommended next provider-backed experiment:

```text
experiment_version = V3_1_STATEFUL_STRICT_JSON_GOVERNED_MUTATION
task = C-A1
repetitions = 1 first
selected provider = pinned explicit provider
selected backend = pinned explicit backend
selected model = pinned explicit model
strict_json_only = true
provider_native_tools = false
fallback = false
AUTO = false
control output budget = 900 tokens
mutation output budget = 2400 tokens
provider retry budget = 1
structured repair budget = 1 per lane
max total model calls = 18
max tool steps = 16
governed mutation channel = enabled
oracle = independent oracle only
failed-run rollback = required
stop condition = stop after one fresh V3.1 C-A1 result
```

Do not run C-A2/C-A3/C-A4 or browser certification until the V3.1 C-A1 result is reviewed.

## Final Confirmation

- no real provider call executed
- no task-specific hints added
- no validation weakening
- no deterministic fallback added
- reasoning remains rejected
- previous Initial/V1/V2/V3 evidence preserved
- scores unchanged
- no commit or push
- Browser certification not started
- Wave 2 not started
- Security Testing not started
