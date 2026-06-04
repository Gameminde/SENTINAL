# BROWSER_NEURAL_AUDIT_REMEDIATION_LOCK Report

Date: 2026-06-04

## Current State

This pack remediates the confirmed browser neural audit blockers before the next live backend or neural cortex pack. It does not add real credential usage, generic login, payment, API mutation, shell, desktop, channel send, or provider fallback.

## Files Changed

- `sentinel/shared/safety_scanner.py`
- `sentinel/agent/organs/safety_scanner.py`
- `sentinel/organs/browser/controlled_runner.py`
- `sentinel/agent/organs/organ_dispatch.py`
- `sentinel/agent/organs/local_artifact_executor.py`
- `sentinel/agent/organs/reversible_workspace_executor.py`
- `sentinel/organs/credentials/foundation.py`
- `sentinel/agent/organs/browser_download_upload_quarantine_l6.py`
- `sentinel/agent/organs/browser_session_manager_l5_live.py`
- `sentinel/agent/llm/context_pack.py`
- `sentinel/agent/browser/neural/motor_proposal.py`
- `sentinel/agent/browser/neural/__init__.py`
- `sentinel/agent/runtime.py`
- `sentinel/cli.py`
- `sentinel/perf/hot_cold/receipt_index.py`
- `sentinel/perf/measure/latency_profiler.py`
- `sentinel/shared/events.py`
- `tests/test_browser_neural_audit_remediation_lock.py`
- Updated regression tests for strict authority bools and browser bool parsing.

## Remediation Matrix

| Finding | Status | Evidence |
| --- | --- | --- |
| AUTHORITY_BOOL_PERMISSIVE | CLOSED | `parse_authority_bool` accepts only `type(value) is bool`; authority flags reject strings, ints, None, lists, and dicts. |
| AUTHORITY_EVIDENCE_BOOL_SEPARATION | CLOSED | `parse_evidence_bool` is separate and used only for evidence shaping such as screenshot capture. |
| L2_L3_POST_WRITE_PROOF | CLOSED | L2/L3 success now requires post-write readback hash matching expected content hash. |
| L3_ROLLBACK_PROOF | CLOSED | L3 separates `rollback_attempted` and `rollback_success`; success requires old-content readback hash match. |
| L2_ROLLBACK_OVERCLAIM | CLOSED | L2 does not claim guaranteed rollback restoration; write proof failure is blocked/failed with safe receipt posture. |
| CREDENTIAL_GRANT_ATOMIC_USE | CLOSED | Credential grant decision and `used_count` increment are under a shared lock; concurrent `max_use_count=1` accepts one worker. |
| DOWNLOAD_POLICY_NON_WEAKENING | CLOSED | `forbid_executables` cannot be disabled; effective max bytes is the minimum policy/contract/candidate limit. |
| SESSION_SANITIZER | CLOSED | Session sanitizer runs on normal close, failure block path, and `close_all`; only safe metadata enters result/receipt/log. |
| PRE_CONTEXT_SECRET_SWEEP | CLOSED | Context pack pre-sweep rejects Bearer, provider key, cookie, session token, and `.env`-like secret payloads before context/memory use. |
| MOTOR_PROPOSAL_DROP_DIAGNOSTICS | CLOSED | Known gated browser actions produce a diagnostic drop reason instead of disappearing silently. |

## Additional Verification Fixes

During the exact full suite, two existing performance guards failed independently of this browser pack. They were fixed because the requested full-suite gate cannot be honestly reported green while these fail.

- `ReceiptIndex.query` received a covering mission/timestamp/receipt index, explicit index hint for mission queries, and bounded mission query warm cache invalidated on canonical writes.
- `LatencyProfiler` now uses validated fast trace construction, direct trace payload rendering, and an owned-payload EventBus append path. EventBus hash-chain verification remains intact.
- CLI browser fixture mode now uses a deterministic fixture-only public DNS resolver, avoiding real DNS flakes when `--fixture-html` is supplied.

## What Remains Not Started

- Real credential storage and resolution.
- Generic browser login or credentialed private session.
- Payment/spend/trading browser authority.
- API mutation, shell, desktop, channel send.
- Provider fallback or AUTO routing.
- Next browser live backend/neural pack.

## Verification

Commands run:

```text
py -3.13 -m pytest tests/test_browser_neural_audit_remediation_lock.py -q
py -3.13 -m pytest tests/perf/hot_cold/test_receipt_index_property.py -q
py -3.13 -m pytest tests/perf/hot_cold/test_phase_b_benchmarks.py::test_receipt_index_query_p95_full_scale_100k -q -s
py -3.13 -m pytest tests/test_agent_event_bus.py -q
py -3.13 -m pytest tests/perf/measure/test_profiler_eventbus_wireup.py tests/perf/measure/test_performance_trace_property.py tests/perf/measure/test_performance_receipt_property.py tests/perf/measure/test_latency_profiler_benchmark.py -q -s
py -3.13 -m pytest -q -p no:cacheprovider -x
py -3.13 -m pytest -q -p no:cacheprovider
py -3.13 -m pytest --collect-only -p no:cacheprovider
```

Results:

- Pack test: 16 passed.
- Exact full suite: reached 100 percent with exit code 0.
- Collection count: 2161 tests collected.
- Visible skips in full suite output: 3 existing skips.

## Safety Statement

This pack tightens parsing, proof, rollback, credential grant accounting, quarantine policy, session cleanup, context secret screening, and diagnostics. It does not add new execution authority. It does not enable generic login, payment, API mutation, shell, desktop, channel send, arbitrary unsandboxed JS, real credential use, provider fallback, or AUTO routing.
