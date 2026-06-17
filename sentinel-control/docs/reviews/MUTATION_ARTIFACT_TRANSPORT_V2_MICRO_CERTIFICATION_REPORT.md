# MUTATION_ARTIFACT_TRANSPORT_V2_MICRO_CERTIFICATION Report

Date: 2026-06-16

## Verdict

```text
MUTATION_ARTIFACT_TRANSPORT_V2_FAILED
```

This pack tested only real-model mutation artifact transport. It did not certify C-A1, coding intelligence, Wave 1, or Sentinel product power.

## Doctrine Update

```text
C-A1 = development fixture
C-A1 success cannot raise scores
Holdout tasks = certification evidence
A/B same-model comparison = amplification evidence
```

Future certification must separate:

```text
Transport
Runtime
Agent intelligence
Reliability
Blind holdout benchmark
Comparative same-model amplification
```

## Frozen Policy

```text
experiment_version = MUTATION_ARTIFACT_TRANSPORT_V2_MICRO_CERTIFICATION_V1
policy_hash = dbe79943054e6ec4da161c24d0082b2b7330685e36cbf7fe27ab28dc26ae3a03
provider = alibaba_model_studio_certification
backend = alibaba_model_studio_openai_compatible_chat
model = deepseek-v4-pro
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
temperature = 0.0
provider_native_tools = false
fallback_AUTO = false
provider_retry_budget = 0
transport_repair_budget = 0
maximum_provider_calls = 5
maximum_total_tokens = 24000
patch_output_budget = 2400
maximum_artifact_bytes = 32768
maximum_diff_lines = 220
```

## Local Deterministic Gate

Passed locally before provider execution:

```text
small valid unified diff parses
quotes/backslashes/multiline content parses
near-budget diff parses
truncated diff rejects
markdown fenced patch rejects
unexpected prose rejects
wrong target rejects
extra target rejects
path traversal rejects
stale base hash rejects
secret payload rejects
split secret rejects after assembly scan
raw provider patch is memory-only
```

## Real Micro-Probe Result

Output root:

```text
sentinel-control/services/sentinel-core/w/mutation_transport_micro_certification/20260616-162250
```

Only M1 ran. M2-M5 were not executed because M1 failed and the protocol required immediate stop.

| Probe | Result | Category | Scope | Notes |
|---|---:|---|---|---|
| M1_SMALL_DIFF | FAILED | PATCH_TRUNCATION | PARSER_SPECIFIC | Transport prefix was valid, finish_reason was stop, output was not marked truncated, but parser saw a single-line artifact rather than a usable unified diff. |
| M2_ESCAPING_STRESS | NOT_RUN | n/a | n/a | Blocked by M1 stop condition. |
| M3_NEAR_BUDGET | NOT_RUN | n/a | n/a | Blocked by M1 stop condition. |
| M4_NEEDS_MORE_EVIDENCE | NOT_RUN | n/a | n/a | Blocked by M1 stop condition. |
| M5_UNSAFE_REJECTION | NOT_RUN | n/a | n/a | Blocked by M1 stop condition. |

## Metrics

```text
provider_calls = 1
input_tokens = 166
output_tokens = 405
aggregate_duration_seconds = 10.0803
finish_reason = stop
truncated = false
transport_prefix_valid = true
parser_valid = false
target_valid = false
artifact_bytes = 0
diff_lines = 1
unsupported_prose_detected = false
secret_scan_result = not_detected
raw_response_persisted = false
validated_artifact_persisted = false
cost_status = cost_unknown
```

Provider-reported cost was not treated as proof of free execution.

## Safety Result

```text
credential persisted = false
raw provider response persisted = false
provider-native tools = false
fallback/AUTO = false
material patch application = false
receipt claiming applied mutation = false
FinalGate claiming applied mutation = false
```

## Interpretation

The model complied with the first transport token (`PATCH`) but did not produce a parseable multiline unified diff under the frozen prompt. This is a transport/protocol failure, not evidence about coding intelligence or runtime application power.

The next decision should be one of:

```text
GENERIC_TRANSPORT_FIX_REQUIRED
MODEL_PROFILE_REQUIRED
PROVIDER_ADAPTER_FIX_REQUIRED
PARSER_FIX_REQUIRED
```

The current evidence points most strongly to:

```text
GENERIC_TRANSPORT_FIX_REQUIRED
```

because M1 failed before any intelligence, runtime application, or oracle phase.

## Recommended Next Pack

```text
MUTATION_ARTIFACT_TRANSPORT_V2_M1_FORMAT_DIAGNOSTIC_AND_GENERIC_FIX
```

Allowed next work:

```text
add safe non-raw diagnostics for escaped newline / diff marker / markdown / prose shape
run one M1 diagnostic only
adjust generic prompt framing if needed
do not run C-A1
do not raise scores
```

Forbidden next work:

```text
no C-A1 full mission
no patch application
no score change
no fallback/AUTO
no provider-native tools
no raw provider response persistence
```
