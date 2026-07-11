# SENTINEL_ROOT_POWER_SIMPLIFICATION_CUT_PLAN_V1

Status: audit and cut plan only.

Provider calls: 0.
Browser/channel/external runs: 0.
Runtime source changes: 0.
Push: not performed.

## 1. Executive Verdict

Attempt 5C proves that Pack 6C moved Sentinel in the right direction, but not far
enough for product power.

Pack 6C added the correct kernel concepts:

```text
ActionFailureClass
RecoverableActionObservation
ActionAliasNormalizer
ActionabilityFrame
BrowserActionabilityRegistry
recovery/correction lanes
```

Attempt 5C then proved:

```text
real Alibaba opened
provider reached
model extraction succeeded
world model existed
stable refs existed
search-like refs existed
product/result candidate cards existed
real model chose real_browser.type_text
replay stayed pure
```

But it also proved the deeper product problem:

```text
The browser power layer is still too low-level and fragile.
```

The model should not be piloting brittle Playwright locators. The model should
pilot a browser skill. Sentinel should translate model intent into robust
Playwright actuation, recovery, receipts, and replay.

Recommended next implementation:

```text
POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
```

Do not implement only:

```text
FIX_REAL_BROWSER_RUNTIME_REF_ACTUATION_RECOVERY_V1
```

That narrow fix is a subtask of Pack 6D, not the strategic move.

## 2. Product Doctrine

```text
Power first, receipts always.
Do not control intelligence.
Control only real-world damage.
Sentinel must be complex inside, but simple and powerful for the model.
```

Browser version:

```text
The model does not drive Playwright.
The model drives a browser skill.
Sentinel handles selectors, waits, focus, scrolling, retries, recovery,
evidence, receipts, replay, and hard boundary stops.
```

## 3. Evidence From Current Code

### 3.1 ActionKernel still terminalizes generic runtime exceptions

File:

```text
sentinel-control/services/sentinel-core/sentinel/operator/action_kernel.py
```

Evidence:

```text
ActionKernel.execute catches any non-ActionKernelError exception and raises
ActionKernelError(str(exc)).
```

Impact:

```text
If a runtime throws a normal in-scope execution error, the generic loop sees a
terminal kernel error instead of a recoverable observation.
```

This is acceptable for source invariants and hard boundary failures, but not
for normal browser actuation failures.

### 3.2 Real browser type_text is a thin Playwright fill

File:

```text
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
```

Evidence:

```text
_type_text resolves a ref, then calls engine.type_text(ref, text).
PlaywrightRealBrowserEngine.type_text calls page.locator(selector).fill(text).
```

Impact:

```text
There is no robust skill behavior:
- no scroll into view
- no focus fallback
- no clear/type fallback
- no Enter/submit fallback
- no alternate search candidate fallback
- no post-failure world model refresh before terminalization
```

Attempt 5C failed exactly here.

### 3.3 Current selector map is index-fragile

File:

```text
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
```

Evidence:

```text
observe() builds refs from button/input/textarea/select/a/[role] nodes.
If no data-sentinel-ref exists, selectors are role-to-tag nth selectors such
as input,textarea >> nth=N.
```

Impact:

```text
The model may see a stable-looking ref, but the backend may still resolve it
through a brittle nth selector. On dynamic commerce pages this is fragile.
```

This is a direct actionability contract violation:

```text
model-visible candidate != reliably runtime-executable skill target
```

### 3.4 Browser world model exists but is not the skill

Files:

```text
sentinel-control/services/sentinel-core/sentinel/operator/browser_world_model.py
sentinel-control/services/sentinel-core/sentinel/operator/browser_decision_frame.py
sentinel-control/services/sentinel-core/sentinel/operator/action_power_contract.py
```

Evidence:

```text
BrowserWorldModelBuilder builds stable refs, search-like refs, product/result
candidate cards, blockers, recommended actions.
BrowserDecisionFrameCompiler exposes candidates and schema.
BrowserActionabilityRegistry maps aliases such as search_box.
```

Impact:

```text
The perception layer is now useful, but action execution still exposes
primitive low-level operations. The world model does not yet own robust
actuation.
```

### 3.5 Loop still has browser-specific proof friction

File:

```text
sentinel-control/services/sentinel-core/sentinel/operator/model_led_task_loop.py
```

Evidence:

```text
real_browser_assertion_due_to_material_budget routes the loop into an
assertion-only mode.
_is_premature_real_browser_finish can block finish while progress_state starts
with real_browser_.
```

Impact:

```text
For commerce/research browser tasks, meaningful extraction cards and grounded
summary can be a better proof than assert_text. The loop should not force a
toy assertion shape onto real web research.
```

### 3.6 Attempt 5C precise outcome

Report:

```text
sentinel-control/docs/reviews/SENTINEL_REAL_POWER_ATTEMPT_5C_MODEL_LED_ALIBABA_ACTIONABILITY_RECOVERY_V1_REPORT.md
```

Safe facts:

```text
provider_decision_calls = 2
model_extraction_failures = 0
real_browser.open = 1
real_browser.observe = 2
real_browser.type_text = 0
world_model_cards = 2
max_visible_refs = 60
search_like_refs_seen = true
link_refs_seen = true
product_or_result_candidate_card_count = 8
```

Interpretation:

```text
The model was not blind.
The model did not fail schema extraction.
The browser did not lack search-like candidates.
The action runtime failed to turn a model-chosen browser action into robust
in-scope browser work.
```

## 4. Evidence From Agent-Lab / OpenClaw

Agent-Lab/OpenClaw browser reference is not product code, but it contains the
right power patterns.

Files inspected:

```text
agent-lab/module-harvest/browser/openclaw/OPENCLAW_BROWSER_POWER_FILES_MAP.md
agent-lab/module-harvest/browser/openclaw/BROWSER_SUPREMACY_ROADMAP.md
agent-lab/module-harvest/browser/openclaw/power-files/src/browser/pw-tools-core.interactions.ts
agent-lab/module-harvest/browser/openclaw/power-files/src/browser/pw-role-snapshot.ts
agent-lab/module-harvest/browser/openclaw/power-files/src/agents/tools/browser-tool.schema.ts
```

Patterns to import Sentinel-native:

```text
role/a11y refs, not only nth CSS selectors
refs restored before action
bounded timeout normalization
AI-friendly error conversion
click/type/press/wait/scroll action taxonomy
scrollIntoView before action
type with submit option
flat action schema to avoid model/tool schema brittleness
compact interactive snapshots
duplicate role/name handling
```

Do not copy:

```text
vendor runtime code
arbitrary evaluate power
downloads/uploads/dialog/file chooser
full browser profile/session reuse
raw screenshot/DOM persistence by default
unbounded internet browsing
```

## 5. What To Cut Or Deflate

These should be removed, deprecated, or moved below the model-facing skill
surface.

| Cut target | Current problem | Replacement |
| --- | --- | --- |
| Model-facing fragile locator refs as primary control | The model sees refs that may resolve to brittle nth selectors. | Model-facing browser intents and skill refs backed by resolver health. |
| Direct `locator(selector).fill(text)` as product action | It dies on dynamic pages. | Robust type/search skill: scroll, focus, clear, fill, type fallback, submit, wait, recapture. |
| Generic runtime exception -> terminal mission block | In-scope browser failures become mission death. | Runtime returns recoverable action observation with refreshed frame. |
| Browser assertion-only proof bias | Real product research needs extraction/evidence, not toy text assert. | Accept extraction cards + summary + finish as proof for research tasks. |
| Parallel browser stacks not wired together | Existing organs hold power but Pack 6 uses a thin runtime. | Browser skill spine importing world model, semantic extraction, recovery, and navigation candidates. |
| Prompt compensation for runtime weakness | The prompt says “use search_box” but runtime does not do enough. | Runtime skill owns action success. Prompt becomes smaller. |
| Candidate refs invented by prose | Model can see candidates not guaranteed live. | ActionabilityFrame must be generated from executable registry. |
| Pack-specific finish hacks | Each pack adds special finish logic. | Shared proof/finish policy by task type and receipts. |
| Reporting “power gained” before action passes | Docs can make a blocked action sound near-success. | Truth standard: real state change or meaningful extraction receipt. |

## 6. What Must Stay Hard

Do not weaken:

```text
payment
checkout
contact supplier
send inquiry
login with credentials
credential access/exfiltration
ungranted browser origin
ungranted channel destination
workspace path escape
destructive write/delete outside grant
duplicate external send on replay
provider-native tools
fallback/AUTO
raw provider/reasoning persistence
cookies/session/full DOM/screenshot persistence by default
fake success
proof/replay/finalgate tampering
```

## 7. New Root Shape

Replace this product path:

```text
model picks primitive ref
-> ActionKernel dispatches primitive action
-> Playwright locator timeout
-> ActionKernelError
-> ModelLedTaskLoop blocks
-> FinalGate certifies blocked
```

With:

```text
model picks browser intent
-> BrowserSkillSpine resolves executable plan
-> robust actuation attempts
-> recapture world model
-> if in-scope failure: recovery observation
-> model continues with better refs/intent
-> evidence cards + receipts
-> sentinel_loop.finish
-> replay no re-actuation
```

## 8. Browser Skill Spine

Add a model-facing browser skill layer above Playwright primitives.

Candidate model-facing operations:

```text
real_browser.search
real_browser.inspect_result
real_browser.extract_product_cards
real_browser.open
real_browser.observe
sentinel_loop.finish
```

Keep low-level operations available internally:

```text
real_browser.type_text
real_browser.click
real_browser.press_key
real_browser.wait_for_text
real_browser.wait_for_load
real_browser.scroll
real_browser.extract_text
real_browser.assert_text
```

But for complex web tasks, prefer model-facing:

```text
search(query="glasses under 5 euro")
extract_product_cards()
inspect_result(candidate_ref=...)
finish(summary=...)
```

The skill owns:

```text
best search input selection
alternate input candidate ranking
scroll/focus/clear/fill/type fallback
Enter vs search button submission
wait for state/result change
dynamic loading handling
modal/captcha/login detection
post-action recapture
safe product card extraction
receipt and finalgate writing
recoverable observation on in-scope failure
```

## 9. Robust Search Actuation Algorithm

For `real_browser.search`:

```text
1. Ensure page is open.
2. Capture fresh world model.
3. Rank search candidates:
   - role searchbox/textbox/combobox
   - name/placeholder/value/ref contains search/query/product/keyword
   - Agent-Lab style role/a11y refs if available
   - fallback DOM inputs with visible/enabled/non-secret state
4. For each candidate:
   a. scroll into view
   b. click/focus
   c. try fill with bounded timeout
   d. if fill timeout, clear + type slowly
   e. if target rejects input, try keyboard typing after focus
   f. submit with Enter
   g. if no state change, click search button candidate
   h. wait for load/text/state change
   i. recapture world model
   j. if product/result cards appear, success
5. If all candidates fail without boundary danger:
   return RECOVERABLE_BROWSER_STATE_FAILURE with attempt summary hashes and refreshed candidates.
6. If captcha/login/payment/contact/credential/out-of-origin appears:
   hard stop or valid failure according to boundary class.
```

The model receives only:

```text
search succeeded / failed recoverably
candidate card summaries
blocker signals
recommended next intents
receipt refs
hashes
```

Not:

```text
raw DOM
cookies
session data
screenshots by default
raw provider output
reasoning
endpoint or credentials
```

## 10. Module Plan For Pack 6D

### New or expanded modules

```text
sentinel/operator/browser_skill_models.py
sentinel/operator/browser_skill_spine.py
sentinel/operator/browser_ref_resolver.py
sentinel/operator/browser_actuation_recovery.py
```

Responsibilities:

```text
browser_skill_models.py
  BrowserSkillIntent
  BrowserSkillActionPlan
  BrowserActuationAttempt
  BrowserSkillResult
  BrowserSkillRecoveryObservation

browser_ref_resolver.py
  rank search/input/button/link refs
  map aliases to canonical refs
  track resolver health and stale refs
  avoid secret/hidden/disabled/payment/contact refs

browser_actuation_recovery.py
  convert Playwright timeouts and locator errors into typed recoverable results
  classify hard stops separately
  preserve attempt hashes only

browser_skill_spine.py
  implement real_browser.search / inspect_result / extract_product_cards
  call Playwright engine primitives internally
  write receipts and safe evidence
  return ActionResult objects for the generic loop
```

### Modify

```text
sentinel/operator/real_browser_control_runtime.py
  delegate high-level browser skill operations to BrowserSkillSpine
  catch in-scope Playwright actuation failures and return recoverable results
  keep low-level primitives for fixture/regression use

sentinel/operator/action_kernel.py
  stop converting every non-kernel exception into generic terminal mission death
  require executors to classify recoverable vs hard-stop where possible
  keep source invariant and missing executor as terminal

sentinel/operator/decision_context.py
  expose skill intents and evidence-card progress, not only primitive action names
  treat extraction cards as proof for browser research tasks

sentinel/operator/model_led_task_loop.py
  remove real-browser assertion-only bias for browser research missions
  allow extraction-card proof lane -> finish lane
  keep finish blocked before proof

sentinel/operator/browser_world_model.py
  improve candidate cards and action candidates for commerce/search tasks
  add resolver health fields and candidate confidence

sentinel/operator/browser_decision_frame.py
  make high-level browser skill actions first-class
  include exact ActionEnvelope examples for real_browser.search and extract_product_cards
```

### Tests

```text
tests/operator/test_power_pack6d_browser_skill_spine.py
tests/operator/test_power_pack6_real_browser_bounded_web_control.py
tests/operator/test_power_pack6c_actionability_recovery_contract.py
```

## 11. TDD Acceptance Tests For Pack 6D

Add focused tests proving:

```text
1. real_browser.search ranks search-like refs from the world model.
2. real_browser.search scrolls/focuses/fills/submits through a fake hard page.
3. fill timeout falls back to click + type + Enter.
4. failed first search candidate tries the next equivalent candidate.
5. search success creates receipt and refreshed world model.
6. search failure inside scope returns RECOVERABLE_BROWSER_STATE_FAILURE, not terminal block.
7. ActionKernel does not turn classified recoverable browser failures into mission death.
8. captcha/login wall produces typed valid failure/hard stop, not fake success.
9. contact supplier/cart/checkout/payment refs remain hard blocked.
10. extraction cards count as browser research proof.
11. finish after extraction-card proof completes.
12. finish before proof still blocks.
13. replay does not reopen/reclick/retype/repress/rescroll/reextract.
14. existing Pack 6C recovery tests still pass.
15. Pack 5/4/3/2/1 regressions still pass.
```

## 12. Real Alibaba Acceptance Criteria

Run after Pack 6D only:

```text
REAL_POWER_ATTEMPT_5D_MODEL_LED_ALIBABA_BROWSER_SKILL_SPINE_V1
```

Success threshold:

```text
provider_decision_calls >= 3
real_browser.open receipt exists
browser world model exists
model chooses browser skill intent or accepted high-level action
real_browser.search creates state change or result/card extraction
product/search result extraction card exists
evaluative summary produced
sentinel_loop.finish emitted
mission completed by model finish
replay no reopen/no reclick/no retype/no resubmit/no reextract
```

Valid failure reasons:

```text
ALIBABA_CAPTCHA_OR_LOGIN_WALL
DYNAMIC_LOADING_NOT_CAPTURED_AFTER_RECOVERY
BROWSER_SKILL_SEARCH_RECOVERY_BUDGET_EXHAUSTED
BROWSER_SKILL_EXTRACTION_TOO_SHALLOW
MODEL_ACTION_EXTRACTION_FAILURE
HARD_STOP_REAL_DAMAGE_BLOCKED
SOURCE_BUG_OR_RUNTIME_INVARIANT
```

Do not mark product-proven for:

```text
open only
world model only
type action chosen but no material state change
extract count/hash without useful product card
summary without evidence cards
pytest-only fake success
```

## 13. Cut Order

Implement Pack 6D in this order:

```text
1. Add browser skill models and fake hard-page tests.
2. Add resolver ranking and resolver health.
3. Add robust search actuation over fake engine with failure injection.
4. Convert in-scope actuation exceptions into recoverable ActionResult.
5. Wire real_browser.search into RealBrowserControlRuntime.
6. Update DecisionContext to prefer browser skill intents over primitive locator actions.
7. Update loop proof policy: extraction cards can satisfy browser research proof.
8. Keep primitive actions for compatibility, but stop making them the preferred model-facing path.
9. Run focused regressions.
10. Run one real Alibaba 5D attempt.
```

## 14. No-Go Changes

Do not:

```text
remove receipts
remove replay
remove FinalGate truth
allow payment/contact/login/checkout
persist cookies/session/full DOM/raw screenshots
use provider-native tools
use fallback/AUTO
add arbitrary evaluate power as model-facing action
hardcode Alibaba selectors
hide failures behind success
run more than one real provider attempt after first provider call
```

## 15. Recommended Next Instruction

```text
START_POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
```

Implementation objective:

```text
Make browser work feel like a skill to the model, not a locator API.
```

Product acceptance:

```text
Alibaba must not die on a normal type/search locator timeout.
Sentinel must recover automatically inside the granted browser scope,
try equivalent candidates, and either produce useful extraction evidence
or fail with a typed blocker after real recovery attempts.
```

## 16. Confirmation

```text
report_type = cut_plan_only
provider_call = 0
browser_run = 0
source_runtime_change = 0
push = not_performed
```
