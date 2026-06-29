# SENTINEL_BROWSER_POWER_AUDIT_AND_AGENT_LAB_IMPORT_PLAN_V1

Status: audit-only browser power review.

Provider calls: 0.
Browser/channel/external runs: 0.
Runtime behavior changes: 0.
Push: not performed.

## 1. Executive Verdict

Sentinel should not continue with a tiny post-Alibaba parser patch as the next
move. Attempt 5 failed after opening the bounded Alibaba page because the real
browser loop did not yet provide the real model with a strong browser operating
layer after the first `real_browser.open` receipt.

The current Pack 6 real-browser runtime is a thin action seam:

```text
open -> observe -> click/type/select -> assert/extract -> finish
```

That seam is valuable, but it is not yet an elite browser brain. The repository
already contains stronger browser organs and Agent-Lab/OpenClaw-harvested
patterns for:

```text
role snapshots
stable refs
semantic extraction
link/action candidates
navigation decision frames
DevTools evidence bundles
failure recovery
visual grounding
long-horizon browser benchmarks
compact LLM decision frames
```

The right next implementation is therefore:

```text
POWER_PACK_6B_BROWSER_WORLD_MODEL_AND_DECISION_FRAME_WIRING_V1
```

This should wire existing browser perception and decision-frame power into the
real-browser generic model-led loop, then run a real Alibaba-style attempt
again. It should not add arbitrary browser takeover, login, payment, profile
reuse, provider-native tools, or fallback/AUTO.

Core thesis:

```text
browser = operating layer
Perception -> stable world model -> model-led intent -> action execution
-> observation -> recovery -> verification -> receipts/replay
```

## 2. Current Browser-Power Inventory

| Surface | Location | Current maturity | Product status |
| --- | --- | --- | --- |
| Fixture browser control | `sentinel/operator/browser_control_*` | Deterministic local fixture with observe/click/type/select/assert and replay. | Product-proven for fixture path. |
| Real browser Pack 6 seam | `sentinel/operator/real_browser_control_*` | Playwright-backed bounded open/observe/click/type/select/assert/extract. | Implemented candidate, not product-proven on complex page. |
| Real browser Playwright engine | `sentinel/operator/real_browser_control_runtime.py` | Opens configured URL, derives simple DOM refs from buttons/inputs/textareas/selects/links/roles. | Open receipt proven in Attempt 5. |
| Browser read-only organ | `sentinel/agent/organs/browser_readonly_organ_v1.py` | Governed public read-only fetch/extract contract with MIME/redirect/scheme boundaries and receipts. | Strong organ, not wired into Pack 6 loop. |
| Browser semantic extraction organ | `sentinel/agent/organs/browser_semantic_extraction_organ_v1.py` | Evidence cards, claim hashes, confidence flags, prompt-injection/risk flags. | Strong organ, not wired into Pack 6 loop. |
| Browser preparation organ | `sentinel/agent/organs/browser_preparation_organ_v1.py` | Candidate targets and proposed steps from source observations; blocks forbidden action classes. | Strong planning layer, not wired into Pack 6 loop. |
| Browser DevTools intelligence | `sentinel/agent/organs/browser_devtools_machine_intelligence_v1.py` | Page targets, a11y refs, network ledger, console ledger, screenshot evidence bundle. | Strong perception layer, not wired into Pack 6 loop. |
| Browser trajectory planner | `sentinel/agent/organs/browser_trajectory_planner_l5.py` | Ranks stable targets, plans click/type/fill/select/hover/wait actions, can execute via session manager. | Strong planner, not wired into Pack 6 loop. |
| Browser failure recovery | `sentinel/agent/organs/browser_failure_recovery_engine_v1.py` | Classifies stale refs, overlays, redirects, network failures, captcha/KYC boundaries. | Strong recovery layer, not wired into Pack 6 loop. |
| Browser multi-step orchestrator | `sentinel/agent/organs/browser_multi_step_task_orchestrator_v1.py` | Observe/diagnose/plan/act/verify/recover phases against evidence bundles. | Strong orchestration concept, not wired into Pack 6 loop. |
| Browser Navigation L6 | `sentinel/organs/browser/navigation_l6.py` | Navigation authority, link/action refs, decision-frame slice, risk router, preview, receipt adapter. | Implemented organ promotion, not wired into Pack 6 loop. |
| Browser neural/cortex layer | `sentinel/agent/browser/cortex.py`, `sentinel/agent/browser/neural/*` | Evidence interpreter, blackboard, observation/planning/recovery neurons, operator squad. | Cognitive browser layer, not wired into Pack 6 loop. |
| Agent-Lab/OpenClaw browser harvest | `agent-lab/module-harvest/browser/openclaw/*` | Source-backed reference patterns for snapshots, role refs, interactions, trace, response ledgers, benchmarks. | Reference only; must be rewritten Sentinel-native. |

## 3. Exact Files Inspected

Current product and attempt reports:

```text
sentinel-control/docs/reviews/SENTINEL_POWER_PACK4_BROWSER_COMPUTER_CONTROL_V1_REPORT.md
sentinel-control/docs/reviews/SENTINEL_POWER_PACK6_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1_REPORT.md
sentinel-control/docs/reviews/SENTINEL_REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1_REPORT.md
sentinel-control/docs/reviews/SENTINEL_AGENT_LAB_POWER_IMPORT_AUDIT_V1_REPORT.md
```

Current Pack 6 runtime:

```text
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_models.py
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_replay.py
sentinel-control/services/sentinel-core/sentinel/operator/decision_context.py
sentinel-control/services/sentinel-core/sentinel/operator/model_led_task_loop.py
sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py
```

Existing Sentinel browser organs and power docs:

```text
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_readonly_organ_v1.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_preparation_organ_v1.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_semantic_extraction_organ_v1.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_devtools_machine_intelligence_v1.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_multi_step_task_orchestrator_v1.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_trajectory_planner_l5.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_failure_recovery_engine_v1.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/navigation_l6.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/cortex.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/perception_adapter.py
sentinel-control/services/sentinel-core/sentinel/agent/browser/neural/*
sentinel-control/docs/organs/P6T_BROWSER_AGENTLAB_POWER_BINDING.md
sentinel-control/docs/organs/P6T_B_BROWSER_CONTROLLED_NAVIGATION_L6_SCORECARD.md
sentinel-control/docs/research/P6R_DECISION_FRAME_SPEC.md
sentinel-control/docs/research/P6R_SUBQUADRATIC_AGENT_CONTEXT_ENGINE_SCORECARD.md
```

Agent-Lab / OpenClaw reference:

```text
agent-lab/README.md
agent-lab/AGENT_LAB_PLAN.md
agent-lab/audits/SENTINEL_BROWSER_SPEC.md
agent-lab/audits/openclaw_capability_map.md
agent-lab/audits/final/openclaw_final_forensic_report.md
agent-lab/sentinel_integration_notes/openclaw_to_sentinel.md
agent-lab/module-harvest/browser/openclaw/OPENCLAW_BROWSER_POWER_FILES_MAP.md
agent-lab/module-harvest/browser/openclaw/BROWSER_SUPREMACY_ROADMAP.md
agent-lab/module-harvest/browser/openclaw/P3N_BROWSER_FINAL_SUPREMACY_REVIEW.md
agent-lab/benchmarks/browser_tasks/README.md
agent-lab/benchmarks/browser_tasks/reports/browser_operator_live_long_horizon_scorecard.md
agent-lab/benchmarks/browser_tasks/reports/browser_operator_open_web_like_scorecard.md
agent-lab/benchmarks/browser_tasks/reports/browser_visual_engine_scorecard.md
agent-lab/benchmarks/browser_tasks/reports/browser_v3_action_routing_scorecard.md
```

## 4. Pack 4 Browser Fixture Proof Summary

Pack 4 proves a controlled fixture loop:

```text
browser.observe
-> browser.click / browser.type_text / browser.select_option
-> browser.assert_text
-> sentinel_loop.finish
```

Strengths:

```text
stable fixture refs
receipts for observation/action/assertion
replay no re-click/no re-type/no re-assert
finish blocked before assertion
secret/password-like fields blocked
no cookies/session/raw DOM/screenshots
```

Limit:

```text
It is a synthetic browser fixture, not a complex live website.
```

## 5. Pack 6 Real-Browser Candidate Summary

Pack 6 adds:

```text
capability_id = real_browser_control
actions = real_browser.open / observe / click / type_text / select_option / assert_text / extract_text
engine = PlaywrightRealBrowserEngine
bounded URL env = SENTINEL_BROWSER_TEST_URL
headless env = SENTINEL_BROWSER_HEADLESS
```

Implementation facts:

```text
open() launches Chromium and navigates to the configured bounded URL.
open() returns observe() internally for a state hash.
observe() scrapes up to 60 button/input/textarea/select/a/[role] nodes.
refs are derived from role/name/index or data-sentinel-ref.
click/type/select use the ref selector map.
extract_text() hashes/truncates body innerText and records only count/hash.
receipts are structure-only and replay is count/hash based.
```

Limit:

```text
The model-facing context after open does not include the rich observed refs
unless the model explicitly emits real_browser.observe and that action succeeds.
```

This matters because Attempt 5 consumed the first open action, then the second
provider turn failed before an observe receipt exposed Alibaba search controls
or product cards.

## 6. Attempt 5 Alibaba Failure Analysis

Accepted state:

```text
REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1 = VALID_FAILED
POWER_PACK_6_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1 = IMPLEMENTED_CANDIDATE_NOT_PRODUCT_PROVEN
```

What worked:

```text
real model reached
provider transport ok
bounded Alibaba origin opened
real_browser.open receipt persisted
replay purity held
no fallback/AUTO
no provider-native tools
no raw provider/reasoning/credential persistence
```

What failed:

```text
provider_decision_calls = 2
model_extraction_failures = 1
no explicit real_browser.observe action receipt
stable_refs_quality = zero
no search/input/filter refs reached the model
no search/navigation happened
no product extraction
no summary
no finish
```

Safe diagnostic interpretation:

```text
The blocker was not browser launch, credential, endpoint, authority, replay,
fallback, or provider-native tools.

The blocker was:
REAL_BROWSER_MODEL_ACTION_EXTRACTION_CONTEXT_GAP
```

Important nuance:

```text
Open internally captured a state hash, but not a model-usable Alibaba world
model. The product loop expected the model to choose explicit observe next,
yet the retained second-turn diagnostics did not contain a canonical action
object. The run never reached the richer stable-ref stage.
```

Therefore the immediate fix should not be only:

```text
parse one more envelope shape
```

The better fix is:

```text
after opening a real bounded browser page, feed the model a compact browser
decision frame that includes actual page perception, stable refs, candidate
actions, extraction hints, blockers, and the exact allowed action schema.
```

## 7. Agent-Lab/OpenClaw Power Patterns Found

Agent-Lab is present at:

```text
C:\Users\youcefcheriet\sentinal\agent-lab
```

Key power patterns:

| Pattern | Source evidence | Sentinel adaptation |
| --- | --- | --- |
| Browser as part of an action kernel | `openclaw_capability_map.md`, OpenClaw gateway/plugin/browser maps | Keep browser behind `ActionEnvelope`, but expose a stronger browser world model to the loop. |
| Role/a11y snapshots and stable refs | `OPENCLAW_BROWSER_POWER_FILES_MAP.md`, `pw-role-snapshot.ts` mapping | Replace weak DOM-only ref discovery with a layered role/a11y/ref builder. |
| Snapshot/trace/response ledgers | OpenClaw power file map, P3F/P3N docs | Feed DevTools evidence bundle into receipt-backed context. |
| Readability/extraction quality | `web-fetch-utils.ts` mapping, Sentinel read-only/semantic organs | Use semantic evidence cards for product title/price/MOQ/supplier extraction. |
| Interaction taxonomy | `browser-tool.schema.ts`, interaction port maps | Keep actions narrow, but add browser-native primitives needed for real pages: wait, press key, scroll, click link/card. |
| Long-horizon browser fluency | `benchmarks/browser_tasks/README.md` | Move from one-step fixture tests to multi-step open-web-like tasks. |
| Failure recovery | open-web-like and live long-horizon scorecards | Add stale-ref, overlay/modal, dynamic-load, network-failure recovery into loop. |
| Visual grounding | visual engine scorecard | Add screenshot/visual/OCR fallback as compact refs, not raw screenshots. |
| Context economy | P6R Decision Frame docs | Send compact page/target cards, not raw DOM/full body/all links. |
| Replay-first proof | Sentinel advantage in reports and P3N review | Preserve Sentinel receipts/replay as the moat while increasing action power. |

## 8. Capability Matrix With 0-5 Scores

| Capability | Pack 6 current | Dormant Sentinel organs | Agent-Lab/OpenClaw reference | Gap |
| --- | ---: | ---: | ---: | --- |
| Real browser open | 4 | 4 | 4 | Product route opened Alibaba once. |
| Real browser observe on complex page | 1 | 4 | 4 | Existing refs/perception not exposed after open in Attempt 5. |
| Stable role refs | 2 | 4 | 4 | Pack 6 DOM heuristic is thin; organs/harvest have better role/a11y patterns. |
| Search/input operation | 1 | 3 | 4 | Current actions lack press-enter/wait/submit-safe navigation path. |
| Link/card/product extraction | 1 | 4 | 4 | Semantic extraction exists but not wired to Pack 6. |
| Dynamic page recovery | 1 | 4 | 4 | Failure recovery exists but not wired. |
| Visual fallback | 1 | 3 | 4 | Visual grounding and benchmarks exist; Pack 6 does not use them. |
| Long-horizon browser loop | 2 | 4 | 4 | Generic loop exists; browser loop lacks world-model continuity. |
| Receipts/replay | 5 | 5 | 2 | Sentinel is strongest here. |
| Boundary control | 4 | 5 | 2 | Sentinel is strong, but must not strangle useful in-scope action. |
| Model decision frame | 2 | 5 | 3 | P6R exists; Pack 6 context is not using it. |
| Product summary synthesis | 0 | 3 | 3 | Attempt 5 produced no product summary. |

## 9. Top Missing Browser Powers Ranked By Impact

1. Browser world model after open.
   The model needs a compact page state with stable refs, search controls,
   product/result candidates, link candidates, blockers, and next legal
   actions immediately after page open.

2. Browser-specific decision frame.
   Use P6R-style `LLMDecisionFrame`: mission, authority, progress, page card,
   top refs, selected browser action surface, required output schema.

3. Better stable refs.
   Combine current DOM heuristic with accessibility snapshot, role snapshot,
   link/action candidate refs, and fallback visual refs.

4. Search primitives.
   Real web search needs `press_key`, `wait_for_load`, `wait_for_text`,
   `scroll`, and safe click of search/result refs. Pack 6 currently has only
   click/type/select/assert/extract.

5. Semantic extraction cards.
   Product tasks need title, price/unit, MOQ, supplier, caveats, URL ref/hash,
   and confidence flags. Current `extract_text` only returns char count/hash.

6. Failure recovery.
   Alibaba-style pages may show modals, geo banners, overlays, lazy results,
   stale refs, login walls, or automation blocks. Recovery must be a first-class
   loop phase.

7. Visual grounding fallback.
   When DOM/a11y is weak, the model needs bounded visual/crop/OCR-derived
   candidates, not a raw screenshot dump.

8. Multi-step browser state memory.
   The loop should remember previous page states, action receipts, ref maps,
   extraction cards, and blockers across turns.

9. Browser result summarizer.
   Finishing a shopping/research task requires producing a bounded summary from
   evidence cards, not only asserting arbitrary text.

10. Cross-power browser pipelines.
   Future product power should allow browser -> channel, browser -> workspace
   note, or browser -> code/data extraction under grants, while receipts remain
   in the background.

## 10. Existing Sentinel Browser Work Not Wired Into Pack 6

Not currently wired into the Pack 6 real-browser loop:

```text
BrowserReadOnlyReceipt / BrowserReadOnlyResult
BrowserSemanticEvidenceCard
BrowserPreparationTargetRef
BrowserDevToolsEvidenceBundle
BrowserDevToolsA11yRefV2
BrowserTrajectoryPlanStep
BrowserFailureRecoveryPlan
BrowserNavigationDecisionFrameSlice
BrowserLinkCandidateRef
BrowserActionCandidateRef
BrowserPerceptionAdapter
BrowserEvidenceInterpreter
BrowserEvidenceBlackboard
BrowserObservationNeuron
ActionPlannerNeuron
VerifierNeuron
FailureRecoveryNeuron
BrowserNeuralOperatorSquad
P6R LLMDecisionFrame
```

Effect:

```text
Sentinel has browser power in the repo, but Pack 6 currently exposes only a
small operator runtime and a generic context summary. Attempt 5 did not benefit
from the older browser brain.
```

## 11. Recommended Elite Browser Architecture

Use the existing generic ActionEnvelope spine, but insert a browser operating
layer:

```text
real_browser.open
-> BrowserWorldModelBuilder
   -> Playwright observe
   -> accessibility/role refs
   -> DevTools evidence bundle
   -> semantic extraction candidates
   -> link/action candidates
   -> failure/blocker signals
-> BrowserDecisionFrameCompiler
   -> compact P6R-style decision frame
   -> allowed actions only
   -> required action-envelope schema
   -> top-k refs and evidence cards
-> model-led action decision
-> ActionKernel execution
-> post-action recapture
-> recovery or verification
-> evidence/receipt
-> summary/finish
-> replay no re-open/no re-click/no re-type/no re-extract
```

Module receivers:

```text
sentinel/operator/real_browser_control_runtime.py
  keep execution and receipts

sentinel/operator/decision_context.py
  replace thin real_browser summary with BrowserDecisionFrame slice

sentinel/operator/model_led_task_loop.py
  keep generic loop and budgets; add browser-specific recovery/verification mode only as context

sentinel/operator/browser_world_model.py
  new adapter layer over existing browser organs and Playwright engine

sentinel/operator/browser_decision_frame.py
  new compact frame compiler, borrowing P6R discipline

sentinel/agent/organs/browser_* and sentinel/organs/browser/navigation_l6.py
  harvest existing refs, evidence cards, recovery, and navigation candidates
```

Design rule:

```text
The model leads the browsing strategy.
Sentinel supplies the browser state and executes in-scope actions.
Receipts/replay stay automatic in the background.
Hard stop only on real boundary damage.
```

## 12. Recommended Next Fix After Audit

Recommended implementation pack:

```text
POWER_PACK_6B_BROWSER_WORLD_MODEL_AND_DECISION_FRAME_WIRING_V1
```

Do not implement:

```text
single-shape parser tweak only
toy Alibaba prompt hack
fixture-only browser success
raw DOM dump to model
per-click approval loop
```

Pack 6B should:

```text
1. Preserve Pack 6 ActionEnvelope actions and receipts.
2. Add BrowserWorldModelBuilder that turns current page state into compact refs/cards.
3. Use existing Browser DevTools / semantic / navigation / recovery organs where possible.
4. Compile a browser-specific LLM decision frame after open and after every browser action.
5. Make post-open context strongly recommend real_browser.observe or auto-promote an observation card.
6. Add extraction diagnostics that distinguish no visible content, prose, metadata-only, wrong JSON, and valid action.
7. Add real browser primitives required for web search: press_key, wait_for_load/text, scroll, click_link/ref.
8. Keep all URL/session/cookie/raw-DOM/raw-screenshot secrecy boundaries.
9. Prove fake/local hard pages before one real Alibaba rerun.
```

## 13. Recommended Pack 6B Real-Browser Plan

Implementation proof path:

```text
fake hard browser fixture:
open
-> observe world model with search input + result cards
-> type_text search query
-> press_key Enter or click search ref
-> wait_for_text/results
-> extract product cards
-> click/open one card
-> extract product detail card
-> finish with summary
-> replay no re-execute
```

Real-provider proof path after implementation:

```text
REAL_POWER_ATTEMPT_5B_MODEL_LED_ALIBABA_BROWSER_WORLD_MODEL_V1
```

Success threshold:

```text
provider decision calls >= 3
real_browser.open receipt
real_browser.observe/world-model receipt
real search/navigation or state change
product/result extraction card
summary produced
sentinel_loop.finish
mission completed by model finish
replay no reopen/reclick/retype/resubmit/reextract
```

Valid failure classifications:

```text
WORLD_MODEL_EMPTY
STABLE_REFS_TOO_WEAK
SEARCH_CONTROL_NOT_FOUND
ALIBABA_CAPTCHA_OR_LOGIN_WALL
DYNAMIC_LOADING_NOT_CAPTURED
MODEL_ACTION_EXTRACTION_FAILURE
BROWSER_ACTION_RUNTIME_FAILURE
EXTRACTION_TOO_SHALLOW
FINISH_NOT_EMITTED
```

## 14. Recommended Pack 7 Multi-Power Web-To-Channel Plan

After Pack 6B proves real browser search/extraction:

```text
POWER_PACK_7_BROWSER_TO_CHANNEL_RESEARCH_DELIVERY_V1
```

Goal:

```text
browser searches/extracts product information
-> model summarizes with evidence refs
-> bounded channel sends short summary to granted destination
-> receipts for browser evidence and channel delivery
-> replay does not browse again or resend
```

This is the product-power path:

```text
real web operation + real channel delivery + receipts in background
```

Do not promote payments, account creation, login, checkout, supplier contact,
or arbitrary form submission in Pack 7.

## 15. Anti-Toy-Agent Warnings

Do not call browser work product-proven if it only:

```text
opens a page
counts refs
types in a local fixture
asserts static fixture text
extracts only char count/hash
finishes without evidence
passes pytest with fake decisions only
```

Do not solve Attempt 5 by:

```text
forcing a prompt to say observe
accepting metadata-only provider output as a browser action
claiming Alibaba extraction without product evidence
dumping full DOM or screenshots into the prompt
adding approval spam before every click
removing receipts/replay to go faster
```

A real browser-power proof must show:

```text
real model chooses browser actions
real browser state changes
real page evidence is extracted
model adapts from observations
summary is grounded in evidence
replay is pure
```

## Recommended Decision

```text
recommended_next_implementation = POWER_PACK_6B_BROWSER_WORLD_MODEL_AND_DECISION_FRAME_WIRING_V1
```

This is power-first:

```text
more browser cognition
more model-led web operation
same receipts/replay
same hard blocks for login/payment/secrets/profile/cookies/out-of-scope actions
```

## Confirmation

```text
agent-lab found = true
provider call = 0
browser/channel run = 0
source runtime changes = 0
push = not performed
```
