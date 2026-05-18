# Sentinel Implemented vs Documented Matrix

Date: 2026-05-18
Mode: docs-only audit matrix.

Legend:

```text
IMPLEMENTED = production/test code exists
TESTED = dedicated tests exist
LOCKED = lock docs claim accepted phase
PARTIAL = some code/tests exist but not full intended power
DOCS_ONLY = mostly plans/specs/audits
STALE = document conflicts with newer code
```

| Subsystem | Implemented | Tested | Locked | Docs-only / partial / stale | Evidence |
| --- | --- | --- | --- | --- | --- |
| MissionAuthorityEnvelope | yes | yes | yes | no | `mission/models.py`, mission tests |
| Scope/risk/budget mission controls | yes | yes | partial | action/mission token budget open | `mission/budget.py`, `risk.py`, context closure logs |
| MissionRunner | yes | yes | yes | no | `mission/runner.py`, `test_mission_*`, kill switch tests |
| Revocation / kill switch | yes | yes | yes | no | `cancellation.py`, `exceptions.py`, `test_kill_switch_reactive_property.py` |
| Trace timeline | yes | yes | yes | no | `trace_timeline.py`, trace hash tests |
| AgentRuntime | yes | yes | yes | large and central | `agent/runtime.py`, `test_agent_runtime.py` |
| CoreFinalGate | yes | yes | yes | no | `final_gate.py`, final gate tests |
| FinalGate registry decomposition | yes | yes | yes | no | `final_gate_registry.py`, `test_final_gate_registry.py` |
| Performance receipts in FinalGate | yes | yes | yes | narrow invariants only | perf bench tests |
| Context cache key closure | yes | yes | yes | action/mission token budget still open | perf cache tests, closure log |
| LLMDecisionFrame | yes | yes | yes | no | `decision_frame.py`, LLM decision cycle tests |
| Prompt render cache | yes | yes | yes | no | `runtime.py`, cache tests |
| Frame budget governor | yes | yes | yes | no | runtime and perf cache tests |
| ModelCallOptimizer | yes | yes | yes | advisory only | `model_call_optimizer.py`, decision-cycle tests |
| RealModelRequest/Response/Result | yes | yes | yes | lock docs lag | `model_execution/models.py`, backend tests |
| ModelExecutionCoordinator | yes | yes | yes | no auto router | `coordinator.py`, backend/runtime tests |
| Runtime model execution wiring | yes | yes | not reflected in lock | stale docs | `runtime.py`, `test_runtime_model_execution_wiring.py` |
| Groq provider adapter | yes | skip-safe real test | yes as evidence | not architecture default | `groq.py`, Groq tests |
| OpenRouter provider adapter | yes | diagnostic tests | partial | no success overclaim | `openrouter.py`, problem report |
| NVIDIA provider adapter | yes | diagnostic tests | partial | timeout observed | `nvidia.py`, problem report |
| Provider catalog | yes | yes | not state-locked | new after lock | `catalog.py`, `provider_profiles.py`, catalog tests |
| OpenAI-compatible base | yes | yes | not state-locked | new after lock | `openai_compatible.py`, base tests |
| Native OpenAI Responses | no | no | no | planned/catalog only | provider docs/catalog |
| Native Anthropic/Gemini/Cohere | no | no | no | planned/catalog only | provider docs/catalog |
| Local model runtimes | no | no | no | catalog/design only | provider docs/catalog |
| Brain architecture | partial code | yes | yes | live external execution absent | Brain docs, P5 tests |
| Mission entropy / agent count / society | yes | yes | yes | no live model agents | P5C/P5D docs/tests |
| Workspace/belief/debate/epistemic action | yes | yes | yes | mostly internal planning/certification | P5E-P5H docs/tests |
| Resourcefulness/procedure graph/BrainBench | yes | yes | yes | proposal/certification only | P5I-P5K docs/tests |
| Brain L4 integrated review | yes | yes | yes | not full autonomous brain runtime | P5L docs/tests |
| Browser V3 and organ | substantial | yes | many staged locks | production task scope gated | browser/organs docs/tests |
| Desktop workspace L6 | partial | yes | staged lock | not full desktop sidecar product | P6S docs/tests |
| External API organ | partial | yes | staged lock | P6U not started | P6D docs/tests |
| Channel organ | partial | yes | staged lock | no live send by default | P6E docs/tests |
| Credential organ | partial | yes | staged lock | no broad vault product | P6F docs/tests |
| Spend/trading/capital | partial/sandbox | yes | staged locks | high-risk, special authority only | P6G-P6I docs/tests |
| AgentLab vendor harvest | docs/tools | audit tests/tools | yes as research | no vendor runtime import | `agent-lab/*` |
| Mission OS UI | no/early | no | no | product docs only | `docs/product/*`, `docs/mission-os/*` |
| README state | doc | no | no | stale | `README.md` |
| CURRENT_STATE_LOCK top section | doc | no | yes but stale | conflicts with latest code | `CURRENT_STATE_LOCK.md` |

## Stale Or Contradictory Artifacts

| Artifact | Problem | Required correction |
| --- | --- | --- |
| `README.md` | Says runtime model execution is `NOT_WIRED` | Update after audit/lock decision to reflect Wave 9 and provider catalog/base hardening |
| `CURRENT_STATE_LOCK.md` | Top section says Wave 9 open | Add new current phase or update provider/runtime lock truth |
| `POST_CLEANUP_HANDOFF.md` | Historical cleanup state only | Treat as archive, not current truth |
| Kiro real-model spec tasks | Checkboxes not synchronized with implementation | Update in a future docs consolidation pack |
| Some implementation logs | Preserve pre-squash/diagnostic evidence | Mark as historical evidence if stale hashes remain |

## Missing Or Weak Test Areas

- End-to-end product workflow with real model planning plus controlled organ
  execution remains limited.
- Native provider tests for Anthropic, OpenAI Responses, Gemini, Cohere,
  Mistral, xAI, DeepSeek, local runtimes are not implemented.
- Streaming model response handling is not proven.
- Production retry/rate-limit/fallback policy is not implemented.
- Action and mission token budget enforcement for model/tool spend remains open.
- Multi-role model loops are not proven.
- Browser/desktop high-power flows need careful per-organ lock review before
  any broad product-level claim.

## Truth Boundary

The implemented code can prove:

```text
user-selected model contract
-> model call plan
-> coordinator
-> provider response
-> validated LLMDecisionResult
-> safe receipt
-> FinalGate-certified AgentRunResult
```

It cannot yet prove:

```text
full autonomous Mission OS
multi-provider intelligent routing
model-controlled tools
model-controlled organs
unbounded browser/desktop/channel/API powers
Brain L4 as live multi-agent model society
```

## Expanded Implementation Matrix

| Subsystem | Implemented code | Tests/proof | Docs-only or partial claims | Audit judgment |
| --- | --- | --- | --- | --- |
| Mission authority envelope | Yes | Used across runtime/mission/organs | Final Mission OS authority doctrine extends further | Implemented authority source, but global product workflows still partial. |
| Scope checker/risk router | Yes | Scope/risk tests in mission suite | Some future lanes like API/spend/trading need more locks | Strong current blocker layer. |
| AgentRuntime LLM seam | Yes | `test_llm_backed_decision_cycle.py`, runtime wiring tests | Some docs still say model execution deferred | Implemented and tested; docs stale. |
| Real runtime model execution | Yes | `test_runtime_model_execution_wiring.py` including skip-safe real provider path | State lock still says NOT_WIRED in places | Real provider success exists through runtime, not just adapter. |
| Provider catalog | Yes | `test_model_provider_catalog.py` | Future providers not implemented | Catalog is metadata-only and correctly non-executing. |
| Generic OpenAI-compatible base | Yes | `test_openai_compatible_provider_base.py` | Native providers still future | Good foundation for future adapter packs. |
| Groq provider adapter | Yes | Real success validated | Groq is evidence provider, not architecture default | Proven first real path. |
| OpenRouter adapter | Yes, diagnostic | Tests report rate/timeouts/errors honestly | Not production-ready | Correctly not overclaimed. |
| NVIDIA MiniMax adapter | Yes, diagnostic | Tests report timeout honestly | Not production-ready | Correctly not overclaimed. |
| FinalGate | Yes | FinalGate tests and runtime certification tests | Future FinalGate may need richer model-exec semantics | Strong certification layer. |
| EventBus ledger | Yes | Event tests | Full trace replay product not complete | Hash-chain event foundation implemented. |
| Context cache key closure | Yes | Closure tests and logs | Action/mission token budget deferrals remain | Key closure locked; token budget open. |
| Brain architecture | Partial | Brain docs and some agent modules | Multi-role live Brain, debate, Science loops | Doctrine strong, live cognition incomplete. |
| Browser L6 | Partial | Browser organ tests/docs | Full browser assistant/autonomy | Strong route/rejection scaffolding, not broad mutation. |
| Desktop L6 | Partial | Desktop workspace code/tests/docs | Full desktop control | Workspace operations only; host control blocked. |
| External API organs | Mostly planned/scaffold | Request-plan checks | Authenticated API read/write workflows | P6U not started here. |
| Channel send | Gate/scaffold | SendGate denies live send | Real channel sending | Blocked by design; not active power. |
| Spend/trading | Sandbox/gates/docs | Tests and docs where present | Real payment/trading execution | Future high-risk powers, not current. |
| Product/GTM pack | Partial real artifact generation | Safe executor artifacts | General product-launch autonomy | Useful but narrow. |
| AgentLab reuse | Docs/audits only | Forensic reports | Vendor runtime integration | Reuse concepts only; direct bridge rejected. |

## Stale Evidence And Contradiction Register

| Stale item | Why it is stale | Required correction |
| --- | --- | --- |
| `CURRENT_STATE_LOCK.md` model provider section | Describes runtime model execution as `NOT_WIRED` while later commits prove Wave 9 runtime wiring and validation | Update at final lock consolidation, not during this audit unless explicitly authorized. |
| `README.md` current-state bullets | May still reflect pre-Wave-9 provider adapter lock | Align with current runtime success and remaining open gates. |
| Real model backend implementation log | Some Pack B/Pack C notes predate runtime success | Mark provider success and runtime wiring separately. |
| Provider profile success commit hash | Catalog may contain pre-squash `39888c1` for Groq evidence while final log has `187d251` plus later runtime commits | Normalize to final commit set or annotate as historical local evidence hash. |
| `.kiro` spec task checkboxes | Some specs may remain unchecked after equivalent tracked docs/code advanced | Treat `.kiro` as local planning aid, not sole state truth. |

## Missing Tests That Matter Most

- A no-regression test that fails if runtime source contains provider-specific
  names should remain and should be run after provider expansion.
- A state-lock drift check should compare `CURRENT_STATE_LOCK.md` against
  current commit markers for model execution, provider catalog, and runtime
  wiring.
- Provider catalog tests should remain strict that recommendation is metadata
  only and cannot execute.
- Future model-role-loop tests must prove planner/critic/verifier outputs are
  evidence only, not action authority.
- Future token-budget closure tests must cover action and mission budgets, not
  only prompt/frame budgets.
