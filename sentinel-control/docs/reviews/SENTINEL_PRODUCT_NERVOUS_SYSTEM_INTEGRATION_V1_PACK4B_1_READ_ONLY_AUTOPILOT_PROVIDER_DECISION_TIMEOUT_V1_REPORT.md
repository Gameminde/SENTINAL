# SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_PACK4B_1_READ_ONLY_AUTOPILOT_PROVIDER_DECISION_TIMEOUT_V1

## Verdict

PACK_4B_1_READ_ONLY_AUTOPILOT_PROVIDER_DECISION_TIMEOUT_V1 is locally implemented and focused on the Attempt 6B blocker.

This pack did not call a real provider, did not push, and did not add write, shell, browser, network, fallback, AUTO, or provider-native tool power.

## 6B Accepted State

Attempt 6B is accepted as:

```text
ATTEMPT_6B_REAL_PROVIDER_AUTOPILOT_WITH_SUMMARY_AND_MEMORY
= VALID_FAILED_AFTER_FIRST_RECEIPT_TIMEOUT
```

Attempt 6B proved:

```text
real product route reached provider
Pack 4B flags active
first material read-only action succeeded
receipt/evidence created
workspace unchanged
replay purity held
no fallback/AUTO
no provider-native tools
no raw credential/provider/reasoning persistence
```

Attempt 6B did not prove:

```text
mission summary artifact
operator memory candidate artifact
successful Pack 4B closeout
```

Root blocker:

```text
second read-only provider decision call timed out
```

## Runtime And CLI Changes

Added a bounded request execution option:

```text
execution_options.provider_decision_timeout_seconds
```

Added CLI flag:

```text
--provider-decision-timeout-seconds <seconds>
```

Rules:

```text
valid only with --model-led-read-only-autopilot
minimum = 5 seconds
maximum = 180 seconds
persisted in immutable MissionExecutionRequest.execution_options
applies to read-only exploration decision calls only
does not change report-lane timeout
does not change Gate/tool execution semantics
does not enable retry
does not enable fallback/AUTO
does not enable provider-native tools
```

Default behavior remains unchanged when the flag is absent:

```text
read_timeout_seconds = 20.0
total_timeout_seconds = 22.0
```

Configured behavior for the intended Pack 4B.1 run:

```text
--provider-decision-timeout-seconds 90
read_timeout_seconds = 90.0
total_timeout_seconds = 92.0
```

## Request Persistence

The CLI product route persists the configured timeout in the immutable execution request:

```json
{
  "execution_options": {
    "provider_decision_timeout_seconds": 90
  }
}
```

The read-only decision client also attaches the safe timeout policy to the generated `RealModelRequest.request_metadata.timeout_policy` so the catalog-backed provider client can apply it without raw provider material.

Malformed timeout metadata fails closed as:

```text
READ_ONLY_TIMEOUT_POLICY_INVALID
```

## Timeout Semantics

If the provider decision call times out before Pack 4B success threshold:

```text
dispatch status = blocked
blocked_reason = TIMEOUT
FinalGate accepted = false
FinalGate reason = TIMEOUT
no fake additional receipt
no fake mission summary artifact
no fake operator memory candidate artifact
MissionKernel = BLOCKED
```

The existing successful fake Pack 4B path remains unchanged:

```text
receipts created
summary artifact created
operator memory candidate artifact created
FinalGate accepted
MissionKernel completed
replay purity held
```

## No-Retry / No-Fallback / No-Provider-Native Proof

The model retry policy remains unchanged:

```text
max_attempts = 1
retryable_outcomes = []
```

The new option only changes the bounded timeout value used by read-only decision calls. It does not introduce alternate providers, AUTO routing, provider-native tools, or provider tool-calling fields.

## Replay Proof

The timeout test verifies replay remains material-pure after a blocked timeout path:

```text
reexecuted = false
decision client counters unchanged
report client counters unchanged
receipt writes unchanged
FinalGate writes unchanged
mission run store events unchanged
workspace mutations unchanged
```

Pack 4A/4B success-path replay regressions were also re-run.

## Validation

Focused tests:

```text
py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -k "model_led_autopilot or provider_decision_timeout or read_only_summary or operator_memory_candidate or low_friction" -q
result: 7 passed

py -3.13 -m pytest tests/operator/test_product_nervous_system_pack3.py -k "pack4b_1 or pack4b or pack4a" -q
result: 9 passed

py -3.13 -m pytest tests/operator/test_model_decision_extractor_pack3_13.py tests/operator/test_read_only_research_decision_protocol_pack3_7.py -k "pack3_13 or pack3_16 or pack3_17 or pack3_18" -q
result: 39 passed

py -3.13 -m pytest tests/test_llm_operator_model_client_v0.py -k "pack3_18 or read_only_decision_timeout_policy or invalid_read_only_decision_timeout_policy" -q
result: 3 passed

py -3.13 -m pytest tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py -q
result: 13 passed
```

Python optimized focused slice:

```text
py -3.13 -O -m pytest tests/operator/test_product_nervous_system_pack3.py -k "pack4b_1 or pack4b or pack4a" -q
result: 9 passed

py -3.13 -O -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -k "provider_decision_timeout or model_led_autopilot or read_only_summary or operator_memory_candidate" -q
result: 5 passed

py -3.13 -O -m pytest tests/operator/test_read_only_research_decision_protocol_pack3_7.py -k "pack3_13 or pack3_16 or pack3_17 or pack3_18" -q
result: 23 passed
```

Mechanical checks:

```text
py -3.13 -m compileall sentinel/cli.py sentinel/operator/mission_lifecycle_service.py sentinel/operator/model_client.py sentinel/operator/read_only_model_clients.py sentinel/operator/read_only_operator_spine.py
result: passed

git diff --check
result: passed, with Windows LF/CRLF warnings only
```

Targeted scan:

```text
scanned for API key patterns, Authorization, raw_prompt, raw_response, raw_reasoning, reasoning_content, provider wrapper payload, fallback/AUTO enablement, provider-native tool enablement
result: no real secret or unsafe enablement found
benign matches: test fake Authorization assertion, deny-list strings, and raw-material rejection test text
```

## Commit

The final local commit hash is recorded by the Pack 4B.1 completion response after this report is committed.

## Confirmation

```text
real provider call during Pack 4B.1 = 0
push = not performed
write/shell/browser/network power = not added
fallback/AUTO = not added
provider-native tools = not added
```
