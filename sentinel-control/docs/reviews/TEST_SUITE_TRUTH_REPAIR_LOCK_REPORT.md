# Test Suite Truth Repair Lock Report

Date: 2026-05-26

Base commit: `a2137f0` (`runtime: remediate audit safety findings`)

## Purpose

This repair addresses tests that no longer expressed the already-implemented
runtime contracts. It changes tests only; it does not enable providers, organs,
credentials, network calls, or default execution.

## Opus Changes Verified And Preserved

- `tests/perf/test_context_cache_structural_guards.py` now baselines the
  `AgentEventType` closure guard at `634d709`, the commit that legitimately
  introduced `ORGAN_DISPATCH_COMPLETED` and `ORGAN_DISPATCH_SKIPPED`.
- `tests/perf/sched/test_scheduler_benchmark.py` preserves the strict Linux
  `1.0ms` submit target and uses `3.0ms` only on Windows to account for IOCP
  scheduler variance.

Evidence:

- `test_u11_no_new_agent_event_type_member_introduced_by_closure` passed.
- `test_scheduler_submit_p95_under_1ms` passed on Windows.

## Provider Test Truth Repair

The three provider test modules could not be imported standalone because they
used `tests.test_real_model_execution_backend` while `tests` is not a package
in the targeted pytest execution form.

After repairing collection, the tests exposed two stale expectations:

- Requests did not populate the selected `backend_id`, causing the provider
  contract to correctly reject them as `DISABLED_BACKEND`.
- The OpenRouter HTTP-error assertion expected a raw provider error message,
  while the hardened base provider now stores only its hash and a redaction
  marker.

Repairs:

- Added the same local test-helper import pattern already used by the
  OpenAI-compatible base test.
- Pinned each fixture request to its declared backend constant as both
  `backend_id` and compatibility `backend`.
- Replaced the raw OpenRouter diagnostic assertion with hash/redaction
  assertions.

## Status

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| U11 structural guard truth | CLOSED | Targeted guard test passed. | Baseline updates remain intentional-change only. |
| Windows scheduler benchmark flake | CLOSED | Targeted benchmark passed. | Linux keeps the stricter budget. |
| Groq/NVIDIA/OpenRouter standalone collection | CLOSED | Provider suite collects and runs. | Real calls remain skip-safe without keys. |
| Provider/backend/model invariant in fixtures | CLOSED | Requests now provide declared backend IDs. | No provider runtime activation is added. |
| Raw provider diagnostic persistence expectation | CLOSED | OpenRouter test asserts hash-only diagnostic. | Raw provider error data remains forbidden. |

## Verification Evidence

Executed:

```text
python -m pytest tests/test_real_model_execution_groq.py tests/test_real_model_execution_nvidia.py tests/test_real_model_execution_openrouter.py -q -rs
```

Result: `15 passed, 3 skipped`. Each skip is the expected no-real-key
skip-safe provider test.

## Safety Statement

- No provider was activated by default.
- No fallback or AUTO routing was added.
- No raw key, credential, prompt, response, reasoning, or raw provider error
  message is made durable.
- No browser/API/channel/shell/desktop/payment execution was added.
