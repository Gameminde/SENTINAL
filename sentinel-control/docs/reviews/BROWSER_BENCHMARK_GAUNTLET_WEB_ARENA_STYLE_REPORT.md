# Browser Benchmark Gauntlet Web Arena Style Report

Date: 2026-05-31

Pack: `BROWSER_BENCHMARK_GAUNTLET_WEB_ARENA_STYLE`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a browser benchmark gauntlet organ. It scores browser organ
workflows using WebArena-style scenario families instead of relying on
subjective claims of capability.

This pack creates the scoring contract, scenario matrix, deterministic hashes,
receipt, and FinalGate layer. It does not run external benchmark sites.

## Models Implemented

```text
BrowserBenchmarkScenarioKind
BrowserBenchmarkGauntletStatus
BrowserBenchmarkGauntletFinalGateDecision
BrowserBenchmarkGauntletContract
BrowserBenchmarkGauntletRequest
BrowserBenchmarkScenarioScore
BrowserBenchmarkGauntletReport
BrowserBenchmarkGauntletReceipt
BrowserBenchmarkGauntletFinalGateCertificate
BrowserBenchmarkGauntletResult
BrowserBenchmarkGauntletFinalGate
BrowserBenchmarkGauntletOrgan
render_browser_benchmark_gauntlet_receipt_as_untrusted_context
```

## Scenario Coverage

Implemented scoring families:

- multi-page workflow;
- broken selector recovery;
- authorized login with proof refs;
- upload/download quarantine;
- JS sandbox;
- failure recovery.

## Scoring Model

The gauntlet scores:

- success;
- trace quality;
- proof completeness;
- recovery usage where relevant;
- quarantine usage where relevant;
- sandbox escape blocking where relevant;
- missing required scenarios.

The output is a deterministic benchmark hash and an honest status:

- `passed`;
- `needs_hardening`;
- `blocked`.

## Boundaries Held

No added:

- live external benchmark execution;
- AgentRuntime default wiring;
- raw credential payload durability;
- hidden tool payload durability;
- browser submit/login/payment expansion;
- extension/WebMCP execution.

## Tests

Added:

```text
tests/test_browser_benchmark_gauntlet_web_arena_style.py
```

Focused tests:

```text
test_benchmark_gauntlet_scores_web_arena_style_scenarios
test_benchmark_gauntlet_detects_missing_required_scenarios_and_weak_scores
test_benchmark_gauntlet_blocks_raw_credentials_and_hidden_tool_payloads
test_benchmark_gauntlet_hash_is_deterministic_and_no_raw_scenario_payload
test_benchmark_gauntlet_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Scenario scoring | CLOSED | focused test | Inputs supplied by benchmark harness |
| Required scenario coverage | CLOSED | focused test | No live site runner in this pack |
| Weak-score detection | CLOSED | focused test | Heuristic score model |
| Unsafe payload blocking | CLOSED | focused test | Raw credential/tool payloads blocked |
| Deterministic benchmark hash | CLOSED | focused test | Metadata-only |
| Receipt + FinalGate | CLOSED | focused test | Certification data only |
| Live external benchmark run | NOT_STARTED | no backend in this pack | Future gauntlet runner pack |
| AgentRuntime benchmark wiring | NOT_STARTED | no runtime change | Future orchestration pack |

## Next Pack

```text
BROWSER_BOUNDARY_MANAGER_L6_L7
```

This should centralize auth-wall, CAPTCHA, KYC, payment, and suspicious-flow
checkpoints before payment/account-creation powers are expanded.

## Anti-Overclaim Statement

This pack does not claim Sentinel has passed external WebArena or live browser
benchmarks. It locks the Sentinel-native benchmark scoring and certification
layer.
