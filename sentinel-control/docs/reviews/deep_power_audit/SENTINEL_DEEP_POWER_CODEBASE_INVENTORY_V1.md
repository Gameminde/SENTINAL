# Sentinel Deep Power Audit V1 - Codebase Inventory

Status: audit-only
Root: `C:\Users\youcefcheriet\sentinal`

## Generated Tables

The complete file table is in:

```text
sentinel-control/docs/reviews/deep_power_audit/sentinel_full_file_inventory.csv
sentinel-control/docs/reviews/deep_power_audit/sentinel_full_file_inventory.json
```

Recommended columns to use from the CSV/JSON:

```text
path
zone
extension
bytes
lines
is_binary
```

## Inventory Summary

| Metric | Count |
|---|---:|
| Files | 2213 |
| Text lines | 564430 |
| Total bytes | 43237504 |
| Python files parsed | 823 |
| Python lines | 266056 |
| Markdown files | 872 |
| Python files | 910 |
| TypeScript files | 179 |
| TSX files | 102 |

## Zone Table

| Zone | Files | Interpretation |
|---|---:|---|
| `sentinel_docs` | 660 | Truth docs, reports, reviews, roadmap/log artifacts |
| `sentinel_core_runtime` | 528 | Main Sentinel runtime and operator source |
| `reddit_pulse` | 382 | Separate app/product surface in same repo |
| `sentinel_core_tests` | 296 | Sentinel focused tests |
| `agent_lab` | 234 | Power reference/import material |
| `sentinel_control_other` | 85 | Control files outside runtime package |
| `planning_docs` | 19 | Strategy/planning documents |
| `agent_lab_vendors` | 7 | Imported/vendor-like reference files |
| `other` | 2 | Root-level or uncategorized files |

## Main Runtime Map

| Area | Responsibility | Power relevance |
|---|---|---|
| `sentinel/operator` | Product cockpit, mission kernel, authority, runtime host, action kernel, model-led task loop, power runtimes | Highest relevance |
| `sentinel/agent` | Agent runtime, FinalGate, model execution, browser agent layers, organ wrappers | High relevance |
| `sentinel/organs` | Lower-level organs, especially browser/desktop/channel/API/credential surfaces | High relevance |
| `sentinel/mission` | Mission scope, plans, risk, kill/revocation, success criteria | Control and mission framing |
| `sentinel/power` | Typed PowerRuntime V0 | Power sequencing reference |
| `sentinel/telemetry` | Events, receipts, lifecycle telemetry | Proof spine |
| `sentinel/memory` / `sentinel/learning` | Persistent memory and feedback/eval loops | Future autonomy |
| `sentinel/perf` | Performance and benchmark harnesses | Speed and scale support |

## Entrypoints

| Entrypoint | Evidence | Notes |
|---|---|---|
| CLI console script | `sentinel-control/services/sentinel-core/pyproject.toml` | `sentinel = "sentinel.cli:main"` |
| Module entry | `sentinel/__main__.py` | Delegates to CLI |
| Primary CLI | `sentinel/cli.py` | `cockpit`, browser demos, runtime host wiring |
| Real model certification | `sentinel/operator/real_model_certification.py` | Large certification harness |
| Power lab | `sentinel/power_lab.py` | Local mission/preset runner |
| Read-only exploration CLIs | `interactive_exploration_read_only.py`, `self_exploration_read_only.py` | Audit/research paths |

No FastAPI/uvicorn service entry point was found in `sentinel-core` during static search.

## Largest Python Runtime Files

| Lines | File | Audit interpretation |
|---:|---|---|
| 4773 | `sentinel/operator/real_model_certification.py` | Certification monolith |
| 3250 | `sentinel/agent/runtime.py` | Agent runtime god file |
| 3033 | `sentinel/agent/final_gate.py` | Large proof/gate owner |
| 2438 | `sentinel/agent/organs/runtime_execution.py` | Organ runtime branch matrix |
| 2266 | `sentinel/operator/read_only_operator_spine.py` | Read-only spine dominates product route |
| 1964 | `sentinel/organs/browser/final_gate.py` | Duplicate browser proof owner |
| 1883 | `sentinel/telemetry/kernel.py` | Telemetry boilerplate/registry |
| 1839 | `sentinel/agent/organs/organ_dispatch.py` | Organ dispatch branch matrix |
| 1717 | `sentinel/operator/interactive_exploration_read_only.py` | Read-only audit CLI |
| 1521 | `sentinel/operator/self_exploration_read_only.py` | Read-only audit CLI |
| 1465 | `sentinel/cli.py` | CLI product and demo wiring |
| 1308 | `sentinel/agent/organs/reversible_workspace_executor.py` | Strong local mutation executor |
| 1283 | `sentinel/agent/organs/browser_session_manager_l5_live.py` | Live browser organ |
| 1221 | `sentinel/agent/organs/browser_readonly_organ_v1.py` | Browser read-only organ |
| 1209 | `sentinel/operator/read_only_model_clients.py` | Read-only model path |

## Long Function Hotspots

| Length | Function | File |
|---:|---|---|
| 1131 | `sentinel.agent.runtime.run` | `sentinel/agent/runtime.py` |
| 650 | `real_model_certification.run_coding_task` | `sentinel/operator/real_model_certification.py` |
| 649 | `organs.browser.controlled_runner.run` | `sentinel/organs/browser/controlled_runner.py` |
| 597 | `static_catalog.load_static_fixture_manifests` | `sentinel/capabilities/fixtures/static_catalog.py` |
| 471 | `browser.rendered_snapshot.capture` | `sentinel/organs/browser/rendered_snapshot.py` |
| 373 | `connection_manifest_registry._default_manifests` | `sentinel/operator/connection_manifest_registry.py` |
| 362 | `worker_fleet.run` | `sentinel/operator/worker_fleet.py` |
| 354 | `agent.final_gate._browser_capability_receipts` | `sentinel/agent/final_gate.py` |
| 354 | `organs.browser.final_gate._check_browser_capability_receipts` | `sentinel/organs/browser/final_gate.py` |
| 336 | `browser.evidence_adapter.collect` | `sentinel/organs/browser/evidence_adapter.py` |

These are not automatic deletion targets. They are ownership and simplification targets. The strongest first cuts are browser stack unification and organ dispatch registry extraction, because they reduce future power-pack cost.

## Suspicious / Cleanup Targets

| Target | Issue |
|---|---|
| `sentinel/agent/browser` | Mostly compatibility shims to `sentinel/organs/browser`; needs canonical vs shim labels |
| Multiple browser layers | `browser_control`, `real_browser_control`, `browser_live_operator`, L4/L5/L6/V3 organs overlap |
| `WORKSPACE_MAP.md` | Stale relative to current repo size and package map |
| Local/generated dirs | `w`, `data/generated_projects`, `.pytest_cache`, `.hypothesis`, `.codex-perf-tmp`, temp dirs should be artifact-classified |
| `--legacy-internal-direct` in CLI | Should remain clearly non-product |

## Inventory Classification Recommendation

For each file in the master CSV, add or derive:

```text
category
responsibility
entrypoint
power_level
maturity
authority_boundary
receipt_or_finalgate_evidence
tests
docs_link
generated_or_ignored
cleanup_note
```

Recommended category values:

```text
real-local-action
live-browser
external-api
channel-send
fake-injected
sandbox-paper
authority-proof
mission-control
agent-brain
memory-telemetry
perf
docs-truth
generated-artifact
legacy-shim
scratch-local
```

