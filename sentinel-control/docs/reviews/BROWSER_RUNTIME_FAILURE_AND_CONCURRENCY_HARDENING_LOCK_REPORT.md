# Browser Runtime Failure And Concurrency Hardening Lock Report

Date: 2026-06-02

## Current State

The Opus browser runtime audit found that the promoted Browser L5/L6 runtime path is real and routed through the Sentinel chain, but that multi-agent / neural browser work should wait until failure paths and session concurrency are governed. This lock addresses the confirmed runtime blockers without adding new browser powers.

## Findings Treated

| Finding | Status | Evidence |
| --- | --- | --- |
| CR-1 session cache race on `_BROWSER_SESSION_MANAGERS` | CLOSED | `_BROWSER_SESSION_MANAGERS_LOCK` guards cache lookup, creation, reuse, and close-pop; test covers concurrent manager access. |
| CR-2 L5/L6 special-authority session continuity surprise | CLOSED | `BROWSER_L5_L6_SPECIAL_AUTHORITY_ONLY` now requires `browser_persist_sessions=True`; test verifies fail-closed result when disabled. |
| CR-3 browser executor exception without governed runtime result | CLOSED | Promoted browser runtime executors now catch unexpected exceptions and return blocked receipt/FinalGate-compatible results with sanitized reason hashes. |
| CR-4 close-on-open default-mode ambiguity | CLOSED FOR L5/L6 SPECIAL MODE | L5 standalone remains atomic when non-persistent; L5/L6 special runtime sequences fail closed unless persistence is enabled. |
| LR-1 Gate priority inversion | CLOSED | authority/action/organ rejection now outranks budget exhaustion. |
| LR-6 raw candidate correlation by list index | CLOSED | dispatcher now correlates raw candidate data by `source_proposal_id`, not candidate position. |

## Implementation Summary

- Added a thread lock around the browser session manager runtime cache.
- Added explicit L5/L6 special-authority continuity enforcement.
- Added sanitized browser exception conversion helpers in `runtime_execution.py`.
- Added `BrowserSessionManagerL5Live.produce_blocked_result(...)` for runtime failure conversion.
- Preserved organ-local validators and FinalGate behavior.
- Kept Browser L5/L6 surfaces unchanged: no new submit/login/upload/download/JS capability was introduced.
- Kept all default-off runtime behavior unchanged.

## Failure Path Semantics

Unexpected browser executor exceptions are converted to:

- `OrganRuntimeExecutionStatus.BLOCKED`
- a blocked organ receipt when a typed request exists
- a FinalGate-compatible certificate when the organ FinalGate certifies the blocked receipt
- a sanitized blocked reason in the form:

```text
<organ_kind>_executor_exception:<ExceptionType>:<message_hash_prefix>
```

The raw exception message is not persisted. This prevents raw browser data, credential values, bearer tokens, or backend details from being serialized into runtime results.

## Scope Boundaries

This lock does not add:

- CloakBrowser or DevTools backend implementation
- Browser Neural Cortex
- Browser Multi-Agent Squad
- generic browser login/upload/download/private session
- arbitrary JS outside the existing sandbox organ
- API/channel/shell/desktop/payment execution
- provider fallback or AUTO routing

## Test Evidence

New test file:

- `tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py`

Targeted proof:

- lock exists and concurrent cache access reuses one manager
- L5/L6 special mode rejects non-persistent session configs
- executor exception returns sanitized receipt + FinalGate-compatible result
- Gate authority rejection outranks budget exhaustion
- dispatcher raw candidate correlation survives bridge reordering

## Status Table

| Segment | Status | Limitation |
| --- | --- | --- |
| Browser session cache concurrency | CLOSED | Covers runtime cache; does not claim full multi-agent scheduler safety. |
| L5/L6 session continuity | CLOSED | Enforced for special-authority runtime mode; L5 standalone can remain atomic. |
| Browser runtime exception receipts | CLOSED | Covers promoted runtime executors with typed requests; pre-request construction errors can still block before receipt. |
| Browser FinalGate on failure path | CLOSED | Blocked receipts are FinalGate-compatible and certificate-hashed when certifiable. |
| Gate rejection priority | CLOSED | Decision wording now preserves authority as the primary blocker. |
| Dispatcher raw correlation | CLOSED | Uses stable `source_proposal_id`; duplicate proposal IDs still collapse by last writer and should be avoided by upstream proposal generation. |
| Browser Neural Cortex readiness | PREPARED | Ready after independent verification; not started in this lock. |

## Anti-Overclaim Statement

This lock closes browser runtime failure-path and session-cache hardening for currently promoted browser organs. It does not claim Browser Multi-Agent Squad, neural browser cognition, live DevTools/CDP/MCP backend, payment/account authority, or full durable browser replay. It makes the current browser runtime path cleaner before the next power pack.
