# Sentinel Deep Power Audit V1 - Connection Graph And Failures

Status: audit-only

## Static Graph Artifacts

| Artifact | Meaning |
|---|---|
| `sentinel_python_import_edges.csv` | Raw internal import edges |
| `sentinel_python_cluster_edges.csv` | Cluster-to-cluster import graph |
| `sentinel_top_import_targets.csv` | Most imported internal modules |
| `sentinel_connection_failure_matrix.csv` | Curated power connection failures |

## Graph Summary

| Metric | Count |
|---|---:|
| Parsed Python modules | 823 |
| Internal import edges | 4059 |
| Python classes | 2625 |
| Python functions | 10408 |
| Parse errors | 0 |

Top import targets:

| Module | Import count |
|---|---:|
| `sentinel.shared.models` | 310 |
| `sentinel.mission.models` | 180 |
| `sentinel.shared.enums` | 164 |
| `sentinel.agent.model_execution.redaction` | 148 |
| `sentinel.agent` | 86 |
| `sentinel.shared.events` | 85 |
| `sentinel.operator.models` | 82 |
| `sentinel.mission` | 69 |
| `sentinel.operator.kernel` | 64 |
| `sentinel.operator.redaction` | 46 |

## Known-Good Product Route

The strongest connected route today is:

```text
pyproject console script
-> sentinel.__main__
-> sentinel.cli
-> _run_cockpit_command
-> ProductExecutionBinding
-> OperatorCatalogModelClient
-> SentinelRuntimeHost
-> LLMLiveOperatorCockpit
-> MissionLifecycleService
-> MissionKernel / MissionAuthorityEnvelopeIssuer
-> MissionExecutionRequest
-> MissionExecutionCoordinator
-> RuntimeConnectionRegistry
-> UnifiedExecutionDispatcher
-> ReadOnlyResearchAdapter
-> ReadOnlyProductionSpineSession
-> OperatorAgentRuntimeBridge
-> receipt / FinalGate / replay
```

This route is product-proven by prior real runs.

## Power Surface Connection Table

| Surface | Product-connected? | Current state |
|---|---|---|
| Read-only research | Yes | Default product adapter |
| Workspace patch | Partially | Executable in model-led loop/harness, not default cockpit dispatcher |
| Code execution sandbox | Partially | Executable in power loop; alias/executor registration must align |
| Real channel send | Partially | Real Telegram worked through power loop; not general product dispatcher |
| Real browser control | Partially | Real page open/world model works; action actuation fragile |
| Browser live operator L4/L5 | No/opt-in | Declared not product reachable |
| External API read/write | Not product-active | Bounded organ exists |
| Desktop/voice/finance/account | Mostly fake/injected/high-risk | Not product-dispatchable |

## Connection Failures

| Connection | Status | Failure mode | Required correction |
|---|---|---|---|
| `product -> patch/code/browser/channel` | partial | Default runtime host registers only read-only adapter | Promote proven powers through one product skill registry |
| `model action -> executor` | fragile | Capability ids and visible names diverge | Single action alias normalizer before model context |
| `browser ref -> Playwright locator` | fragile | Stable refs degrade to brittle nth selectors | Browser skill actuation with multi-strategy resolution |
| `recoverable miss -> loop` | broken | Runtime timeout/ref miss becomes terminal block | Return recoverable observation and continue within budget |
| `world model -> executable action` | partial | World model can list refs that still fail at executor | Decision frame must come from actionability registry |
| `proof -> finish` | overconstrained | Browser proof after budget only allows assert | Mission-type proof policy: assert/extract/wait/product cards |
| `new power replay -> receipt truth` | uneven | Count/hash stability weaker than receipt validation | Mirror read-only replay validation for all power receipts |
| `channel send -> idempotency` | fragile | Marker written after transport success | Pre-reserve pending send before transport |

## Model-Visible But Not Always Executable

| Example | Why it can fail |
|---|---|
| `code_exec.run_profile` | Visible name differs from `code_execution_sandbox` capability unless normalized |
| `read_only.*` | Bare read-only schema and capability names differ |
| `real_browser.type_text` | Ref may be stale or mapped to brittle selector |
| `browser_live_operator` | Known connection but not product-reachable |
| `channel_transport.send_message` | Needs exact recipient policy, grant, transport config, telemetry |

## Core Design Defect

Sentinel currently has separate planes:

```text
intelligence plane
actionability plane
authority plane
proof plane
```

Authority and proof are strong.

Actionability is weak:

```text
The model can be shown moves that are not guaranteed live.
The runtime can know a miss is recoverable but the loop may terminalize anyway.
```

Fix principle:

```text
Do not show the model raw runtime affordances.
Show only executable skills and intents backed by live actionability checks.
```

## Browser-Specific Connection Diagnosis

Real Alibaba Attempt 5C showed:

```text
real browser opened
world model existed
60 refs visible
search-like refs detected
8 product/result candidate cards detected
model chose type_text
Playwright locator fill timed out
mission blocked
```

That means:

```text
browser perception improved
but browser actuation is still too low-level
```

The browser route must become:

```text
model chooses search/inspect/extract intent
-> browser skill resolves refs and acts robustly
-> recovery attempts happen below model
-> receipts are emitted
-> model sees result, not Playwright guts
```

## Agent-Lab/OpenClaw Import Implication

Agent-Lab/OpenClaw patterns to import are not just "more refs":

```text
role/a11y snapshot
stable ref registry
observe-act gateway
scroll/focus/wait/type/click recovery
AI-friendly error messages
compact decision frame
browser state compression
```

Sentinel-native translation:

```text
BrowserSkillRuntime
BrowserActionabilityRegistry
BrowserActuationPlan
BrowserRecoveryObservation
BrowserProductExtractionCard
BrowserSkillReceipt
```

