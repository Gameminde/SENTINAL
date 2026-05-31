# Browser Multi Step Task Orchestrator V1 Report

Date: 2026-05-31

Pack: `BROWSER_MULTI_STEP_TASK_ORCHESTRATOR_V1`

Status: `LOCKED`

## Executive Verdict

Sentinel now has the first browser task orchestrator loop:

```text
observe -> diagnose -> plan -> act -> verify -> recover -> continue
```

This is the pack that starts turning browser powers into a mission-capable
browser operator. It consumes DevTools machine-intelligence evidence bundles,
builds a hash-only plan, calls a backend action protocol, verifies the outcome,
and records a receipt plus FinalGate certificate.

## Models Implemented

```text
BrowserOrchestratorActionKind
BrowserOrchestratorPhase
BrowserOrchestratorStatus
BrowserOrchestratorFinalGateDecision
BrowserOrchestratorContract
BrowserOrchestratorPlanStep
BrowserOrchestratorPlan
BrowserOrchestratorRequest
BrowserOrchestratorBackendActionResult
BrowserOrchestratorActionBackend
BrowserOrchestratorFakeActionBackend
BrowserOrchestratorReceipt
BrowserOrchestratorFinalGateCertificate
BrowserOrchestratorResult
BrowserOrchestratorFinalGate
BrowserMultiStepTaskOrchestratorV1
render_browser_orchestrator_receipt_as_untrusted_context
```

## Capability Added

The orchestrator can:

- consume a DevTools evidence bundle;
- diagnose target availability from AX refs;
- create a hash-only action plan;
- call a backend action protocol;
- verify through evidence hashes;
- recover from failed actions;
- stop when recovery budget is exhausted;
- block payment/spend, extension execution, and WebMCP execution.

## Boundaries Held

No raw durable:

- desired text;
- raw browser DOM;
- raw console output;
- raw network body;
- credential values;
- MCP payloads.

No added:

- AgentRuntime default wiring;
- live CDP/MCP invocation;
- payment/spend;
- account creation;
- extension execution;
- WebMCP execution.

## Tests

Added:

```text
tests/test_browser_multi_step_task_orchestrator_v1.py
```

Focused tests:

```text
test_orchestrator_runs_observe_diagnose_plan_act_verify_loop
test_orchestrator_recovers_after_first_action_failure
test_orchestrator_blocks_forbidden_payment_extension_webmcp_actions
test_orchestrator_stops_when_recovery_budget_exhausted
test_orchestrator_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Observe/diagnose/plan/act/verify loop | CLOSED | focused test | Backend protocol uses fake backend in this pack |
| Recovery path | CLOSED | focused test | Recovery strategy is first deterministic layer |
| Recovery budget stop | CLOSED | focused test | Deeper recovery next pack |
| Plan hash/no raw text | CLOSED | focused test | No raw desired text durable |
| FinalGate receipt | CLOSED | focused test | Metadata-only |
| L7 dangerous actions blocked | CLOSED | focused test | Payment/extension/WebMCP later |
| AgentRuntime wiring | NOT_STARTED | no runtime change | Future opt-in |
| Live CDP/MCP backend | NOT_STARTED | no backend invocation | Future backend implementation |

## Next Pack

```text
BROWSER_FAILURE_RECOVERY_ENGINE_V1
```

This should replace first-layer recovery with a stronger engine using:

- DOM/AX deltas;
- screenshot and bounding boxes;
- network failures;
- console exceptions;
- modals/dialogs;
- redirects;
- SPA route errors;
- disabled buttons;
- stale refs.

## Anti-Overclaim Statement

This pack does not claim full autonomous browser mastery. It locks the
orchestration skeleton that future live browser backends and recovery engines
will make powerful.
