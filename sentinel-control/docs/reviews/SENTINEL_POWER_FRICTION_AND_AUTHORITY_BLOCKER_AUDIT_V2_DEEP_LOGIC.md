# SENTINEL_POWER_FRICTION_AND_AUTHORITY_BLOCKER_AUDIT_V2_DEEP_LOGIC

## Executive Verdict

V1 was directionally right but still too shallow.

The immediate Alibaba/browser failure is not just a stable-ref bug and not just
a model-output bug. The deeper product issue is that Sentinel has no single
runtime contract that guarantees:

```text
what the model sees as actionable
is actually executable by the runtime
and failures inside granted authority are recoverable observations
instead of terminal mission deaths
```

That is the power leak.

The current model-led loop has strong proof mechanics, but its actionability
mechanics are weaker than its safety/proof mechanics. Receipts, FinalGate, and
replay are real strengths. The missing layer is the "operating contract" between
model-visible candidates, authority-normalized actions, runtime-executable
targets, and recovery turns.

Doctrine remains:

```text
power first, receipts always
do not control intelligence
control real-world damage
hard stop only on real boundary violations
recover inside granted authority
```

Recommended next implementation is therefore:

```text
POWER_PACK_6C_ACTIONABILITY_RECOVERY_AND_POWER_STATE_MACHINE_V1
```

This should supersede a narrow:

```text
FIX_REAL_BROWSER_STABLE_REF_ACTION_RESOLUTION_V1
```

The browser ref issue should be the first acceptance case for Pack 6C, not the
whole pack.

## What V2 Adds Beyond V1

V1 identified the repeated pattern:

```text
mission authority granted
model chooses useful in-scope action
runtime blocks because an internal contract is incomplete
```

V2 identifies the actual missing architecture:

```text
Actionability contract
recoverable runtime failure lane
authority alias normalizer
separate material/proof/recovery budgets
power-state machine
browser ref registry with epoch/state binding
runtime-generated decision frame, not prose-generated candidates
```

In plainer terms:

```text
Sentinel currently proves what happened very well.
It does not yet guarantee that the model's next offered move is a live move.
```

## Evidence Map

Current repo state inspected:

```text
branch = experimental/real-model-lab-freeze-v1
latest V1 audit commit = 342f873 docs: audit power friction and authority blockers
pre-existing modified file = SENTINEL_REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1_REPORT.md
```

Source evidence:

```text
sentinel/operator/action_kernel.py:36-184
  ActionKernelError is a single terminal exception type for missing executors,
  authority issues, and runtime exceptions.

sentinel/operator/model_led_task_loop.py:137-218
  The generic loop catches ActionKernelError and LoopGuardError and terminalizes
  the mission with _block.

sentinel/operator/model_led_task_loop.py:139-216
  Material budget special cases are added per surface: finish-only, browser
  assertion, real-browser assertion.

sentinel/operator/decision_context.py:118-172
  DecisionContext controls objective_satisfied, finish_available,
  recommended_next_action, progress_state, and completion requirements.

sentinel/operator/decision_context.py:249-258
  DecisionContext exposes browser world-model summaries, decision frames, refs,
  candidates, search controls, blockers, and allowed action schema.

sentinel/operator/browser_decision_frame.py:82-100
  BrowserDecisionFrame builds candidate actions from world-model refs.

sentinel/operator/browser_decision_frame.py:113-149
  BrowserDecisionFrame emits exact JSON ActionEnvelope examples.

sentinel/operator/browser_action_candidates.py:57-98
  Browser action extraction validates shape/allowed action names but does not
  validate params.ref against a live runtime registry.

sentinel/operator/real_browser_control_runtime.py:760-802
  Playwright engine generates DOM-derived refs and resets _ref_selectors on each
  observe.

sentinel/operator/real_browser_control_runtime.py:873-879
  Runtime looks up exact ref in _ref_selectors and raises
  real_browser_element_ref_unknown when absent.

sentinel/operator/real_browser_control_runtime.py:303-342
  real_browser.open writes a receipt and context cards from a world model.

sentinel/operator/real_browser_control_runtime.py:636-667
  Runtime writes browser_world_model and browser_decision_frame artifacts.

sentinel/agent/organs/browser_failure_recovery_engine_v1.py:27-46
  Existing recovery organ already models stale_ref, modal/dialog, redirect,
  console/network failure, captcha/KYC/payment, and recovery actions.

sentinel/agent/organs/browser_failure_recovery_engine_v1.py:318-373
  Existing recovery organ maps recoverable failures to refresh_snapshot,
  retarget_by_role, wait_and_reobserve, check_network_console, or checkpoint.

sentinel/agent/organs/browser_trajectory_planner_l5.py:104-176
  Existing trajectory planner has ranked target steps, attempted step ids, and
  attempt receipt ids.

sentinel/agent/organs/browser_trajectory_planner_l5.py:218-306
  Existing trajectory planner can execute with recovery across ranked target
  candidates before failing.

sentinel/agent/organs/browser_multi_step_task_orchestrator_v1.py:32-39
  Existing browser orchestrator has phases: observe, diagnose, plan, act,
  verify, recover, continue.

sentinel/agent/organs/browser_multi_step_task_orchestrator_v1.py:346-418
  Existing browser orchestrator retries/recoveries before certifying success or
  failure.

sentinel/agent/browser/perception_adapter.py:188-225
  Existing perception adapter already computes actionable targets, confidence,
  runtime_ref_id, text, grounding, and action classes.

sentinel/agent/browser/cortex.py:325-384
  Existing cortex produces repair decisions such as recapture or alternative
  source when browser evidence is weak or rejected.
```

Report evidence:

```text
SENTINEL_REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1_REPORT.md
  Attempt 5 opened the bounded Alibaba target, provider did not fail, but turn 2
  did not yield a canonical action envelope. No observe receipt, no stable refs,
  no extraction, no finish.

SENTINEL_BROWSER_POWER_AUDIT_AND_AGENT_LAB_IMPORT_PLAN_V1.md
  Existing browser organs are strong but not wired into the Pack 6 real-browser
  loop.

SENTINEL_POWER_PACK6B_BROWSER_WORLD_MODEL_AND_DECISION_FRAME_WIRING_V1_REPORT.md
  Pack 6B wired world model and decision frame, but the current acceptance tests
  still use fake exact refs and scripted decisions.
```

## Deep Root Cause

The root cause is a missing transactional contract between four planes:

```text
1. Intelligence plane
   The model decides the next action.

2. Actionability plane
   Sentinel must expose only live executable action candidates, or recover when
   a candidate goes stale.

3. Authority plane
   Sentinel must block only when the action crosses mission authority.

4. Proof plane
   Sentinel must receipt, certify, and replay without repeating side effects.
```

Sentinel has strong authority and proof planes. It has a growing intelligence
plane. The weak plane is actionability.

Current failure chain:

```text
DecisionContext shows action candidates
-> model chooses an action
-> extractor validates only schema and allowed action name
-> ActionKernel dispatches to runtime
-> runtime cannot resolve target/ref/state
-> runtime raises
-> ActionKernel wraps/propagates ActionKernelError
-> ModelLedTaskLoop blocks mission terminally
```

For real damage this is correct. For in-scope runtime drift it is product
friction.

## The Hard Logic

### 1. Model-visible candidate is not the same as runtime-executable action

`BrowserDecisionFrame` can list:

```text
candidate_actions
top_refs
exact_action_envelope_examples
```

But those are not backed by a versioned runtime registry contract. The runtime
later accepts only exact refs in its local `_ref_selectors` map. That map is
rebuilt on observe and has no exported epoch/registry hash contract with the
model frame.

Therefore the model can choose something Sentinel itself made look actionable
and still hit:

```text
real_browser_element_ref_unknown
```

That is not a safety win. That is an actionability contract violation.

### 2. The extractor validates shape, not actionability

`browser_action_candidates.extract_browser_action_envelope` answers:

```text
is this JSON object shaped like an allowed browser action?
```

It does not answer:

```text
does this ref exist in the current executable browser registry?
is this ref enabled?
is this ref secret?
is this ref stale?
is this alias resolvable?
does this candidate belong to the world-model epoch shown to the model?
```

That validation happens too late, inside the runtime, and errors terminalize.

### 3. Runtime failure classes are collapsed too early

`ActionKernelError` currently covers all of these:

```text
missing executor
mission authority inactive
unknown browser ref
secret field
unbounded URL
action not authorized
internal runtime exception
```

But these are not the same class.

The product needs at least:

```text
HARD_STOP_REAL_DAMAGE
HARD_STOP_OUT_OF_SCOPE_AUTHORITY
RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE
RECOVERABLE_MODEL_PROTOCOL_FAILURE
RECOVERABLE_BROWSER_STATE_FAILURE
SOURCE_BUG_OR_RUNTIME_INVARIANT
```

Terminalizing them all makes the product feel weak.

### 4. Budgets are compensating for missing state machine semantics

Recent successful power packs needed special cases:

```text
finish_only_due_to_material_budget
browser_assertion_due_to_material_budget
real_browser_assertion_due_to_material_budget
channel finish after delivery
post-patch verification before finish
```

These are symptoms of missing lanes:

```text
material action lane
proof/verification lane
recovery/correction lane
finish lane
```

The loop should not need a new ad hoc boolean for every surface. It needs a
generic mission-progress state machine.

### 5. Existing Sentinel browser organs already know the missing concepts

The stronger organs already include:

```text
failure classification
stale ref recovery
retarget by role
wait and reobserve
multi-step observe/diagnose/plan/act/verify/recover phases
ranked target candidates
attempt receipt ids
repair recommendations
perception target confidence and actionability
```

Pack 6B imported some world-model/frame ideas, but did not wire the existing
recovery and trajectory mechanisms into the generic model-led loop.

### 6. FinalGate is not the recovery engine

FinalGate should certify the truth of terminal outcomes:

```text
accepted success
certified failure
blocked by real boundary
replay purity
artifact hash stability
```

It should not be the first place where an in-scope stale ref, missing schema
field, or dynamic-load mismatch dies. Recovery should happen before terminal
FinalGate whenever the failure did not attempt real damage.

## Power-State Machine Needed

Pack 6C should introduce a shared power-state machine for the generic model-led
loop.

Required states:

```text
DECISION_REQUESTED
MODEL_ACTION_PARSED
ACTIONABILITY_VALIDATED
AUTHORITY_BOUNDARY_CHECKED
MATERIAL_ACTION_EXECUTED
PROOF_ACTION_EXECUTED
RECOVERY_OBSERVATION_CREATED
CORRECTION_TURN_REQUESTED
FINISH_REQUESTED
TERMINAL_COMPLETED
TERMINAL_BLOCKED
```

Required transition law:

```text
If action crosses real boundary:
  TERMINAL_BLOCKED

If action is in scope but not currently executable:
  RECOVERY_OBSERVATION_CREATED
  then continue while recovery budget remains

If model output is visible but malformed:
  CORRECTION_TURN_REQUESTED
  then continue while correction budget remains

If proof exists and objective is satisfied:
  FINISH_REQUESTED
  then require sentinel_loop.finish

If replay would repeat external side effect:
  TERMINAL_BLOCKED
```

## Browser-Specific Runtime Contract

For real browser power, Pack 6C needs a browser actionability registry:

```text
BrowserActionabilityRegistry
  registry_id
  browser_state_hash
  world_model_id
  decision_frame_id
  generated_at_turn
  executable_refs
  aliases
  candidate_actions
  blocked_refs
  recovery_actions
```

Each executable ref should carry:

```text
canonical_ref
accepted_aliases
role
name_hash_or_safe_name
selector_hash
visible
enabled
secret
state_hash
expires_on_navigation
confidence
source = role_snapshot | dom_snapshot | a11y_snapshot | devtools | visual_fallback
```

Before executing browser click/type/press/select:

```text
resolve model ref against registry
reject secret/disabled/hidden as hard block or safe block
if unknown/stale in scope, create recovery observation
if resolved, execute canonical ref
receipt records canonical ref hash and registry id
```

The model can then use simple names like:

```text
search_box
first_product_card
search_submit_button
```

while runtime maps them to canonical refs. The model should not be forced to
memorize brittle DOM-derived ids on dynamic ecommerce pages.

## Recovery Contract

Pack 6C should introduce a reusable result form, not only browser-specific
exceptions:

```text
ActionFailureClass
  HARD_STOP_REAL_DAMAGE
  HARD_STOP_OUT_OF_SCOPE_AUTHORITY
  RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE
  RECOVERABLE_MODEL_PROTOCOL_FAILURE
  RECOVERABLE_BROWSER_STATE_FAILURE
  SOURCE_BUG_OR_RUNTIME_INVARIANT

RecoverableActionObservation
  attempted_action_hash
  failure_class
  failure_code
  safe_summary
  recommended_next_actions
  refreshed_candidates
  recovery_budget_remaining
  material_effect = false
  authority_effect = none
```

For example:

```text
real_browser_element_ref_unknown
-> failure_class = RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE
-> recovery action = real_browser.observe
-> context includes latest refs and aliases
```

But:

```text
payment / contact supplier / login / credential / unbounded URL
-> failure_class = HARD_STOP_REAL_DAMAGE or HARD_STOP_OUT_OF_SCOPE_AUTHORITY
-> terminal block
```

## Authority Normalization Contract

A mission grant should be normalized once into runtime-ready capability names.

Current aliases across packs:

```text
read_only.list_directory
read_only_research.list_directory
browser_control.browser.click
real_browser_control.real_browser.click
bounded_channel.send_message
channel_transport.send_message
finish
sentinel_loop.finish
```

Pack 6C should add:

```text
ActionAliasNormalizer
  model_action_name -> canonical capability_id + operation
  authority action alias -> canonical allowed action
  runtime operation alias -> canonical executor operation
```

This is not safety weakening. It is removing accidental product friction inside
the already granted mission envelope.

## Budget Contract

Current `LoopGuard` has:

```text
max_model_calls
max_material_actions
max_same_action_hash
max_repeated_target
max_no_progress_turns
deadline_seconds
```

Pack 6C should split budgets:

```text
max_material_actions
max_recovery_turns
max_correction_turns
max_proof_turns
max_finish_turns
max_repeated_effective_action
max_repeated_recovery_for_same_failure
```

This prevents two bad outcomes:

```text
material budget kills proof/finish
infinite recovery loops hide no progress
```

## Existing Browser Organs To Wire

Do not reimplement everything from scratch. Wire selectively:

| Existing organ | Power it already contains | Pack 6C use |
|---|---|---|
| `BrowserFailureRecoveryEngineV1` | stale_ref/modal/redirect/network/captcha classification and recovery plan | classify browser runtime failures and produce recovery observation |
| `BrowserTrajectoryPlannerL5` | ranked target candidates and execute-with-recovery attempts | generate fallback executable candidates for click/type/select |
| `BrowserMultiStepTaskOrchestratorV1` | observe/diagnose/plan/act/verify/recover phase grammar | inform generic loop phase/state machine |
| `BrowserPerceptionAdapter` | actionable targets with confidence and runtime_ref_id | enrich registry and candidate quality |
| `BrowserEvidenceInterpreter` / cortex | repair decisions and confidence pressure | decide recapture/alternative-source guidance |
| `navigation_l6` | link/action candidate refs, navigation receipts, decision-frame slice | preserve bounded navigation proof model |
| `reliability_profile` | launch/session/viewport/locale/profile stability dimensions | report browser readiness before real run |

If a component is too heavy to wire fully, Pack 6C should create explicit bridge
interfaces and tests proving the bridge receives/returns safe cards.

## Tests Missing Today

Current Pack 6B tests prove:

```text
fake hard page can expose refs
scripted model can use exact ref
extract card can be created from fake page text
replay does not re-execute actions
```

They do not prove:

```text
model-visible candidate must be executable
ref alias resolves to canonical ref
unknown in-scope ref recovers
stale ref after dynamic load recovers
modal/consent blocker becomes recovery, not generic block
captcha/login becomes typed valid failure
candidate action registry epoch is stable
extractor validates params.ref against registry
correction turn after metadata/prose response works
hard danger still terminalizes
```

Pack 6C tests should add exactly those.

## Pack 6C Acceptance Tests

Required fake/browser tests:

```text
1. world model emits an actionability registry with registry_id and state hash.
2. decision frame candidate_actions are generated from executable registry refs.
3. extractor rejects/resolves refs against registry before runtime execution.
4. alias "search_box" resolves to canonical search textbox ref.
5. unknown in-scope ref returns recoverable observation, not terminal block.
6. stale ref after navigation triggers observe/recovery and then succeeds.
7. disabled/hidden/secret refs stay blocked.
8. unbounded URL/login/payment/contact supplier remains terminal hard stop.
9. metadata-only/prose model output receives correction turn with exact schema.
10. repeated correction/recovery exhausts budget and blocks honestly.
11. material budget does not prevent proof or finish lane.
12. replay does not reopen/reclick/retype/repress/rescroll/reextract.
13. existing Power Pack 1-6 tests still pass.
```

Required fake hard mission:

```text
open
-> world model + registry
-> model chooses alias search_box
-> resolver maps to canonical ref
-> type search
-> press Enter or click search
-> wait/scroll/extract
-> product/search card created
-> finish
```

Required recovery mission:

```text
open
-> model chooses stale/unknown in-scope ref
-> recoverable observation returned
-> observe refreshes executable refs
-> model chooses refreshed ref
-> action succeeds
-> finish
```

Required hard-stop mission:

```text
open
-> model chooses contact supplier/payment/login/credential/unbounded URL
-> terminal hard stop
-> no material action receipt
```

## Real Attempt After Pack 6C

After Pack 6C is locally committed and focused tests pass, run exactly once:

```text
REAL_POWER_ATTEMPT_5C_MODEL_LED_ALIBABA_ACTIONABILITY_RECOVERY_V1
```

Success threshold:

```text
provider decision calls >= 3
real_browser.open receipt
world model / observe receipt
actionability registry created
model uses stable ref or alias that resolves to executable ref
real search/navigation/state change happens
meaningful product/search extraction card exists
evaluative summary produced
sentinel_loop.finish emitted
mission completes by model finish
replay no reopen/no reclick/no retype/no resubmit/no reextract
```

Valid failures must be typed:

```text
ACTIONABILITY_REGISTRY_EMPTY
ALIAS_RESOLUTION_FAILED
RECOVERY_BUDGET_EXHAUSTED
ALIBABA_CAPTCHA_OR_LOGIN_WALL
DYNAMIC_LOADING_NOT_CAPTURED
PRODUCT_EXTRACTION_TOO_SHALLOW
MODEL_CORRECTION_BUDGET_EXHAUSTED
HARD_STOP_REAL_DAMAGE_BLOCKED
```

## Recommended Next Implementation Pack

```text
POWER_PACK_6C_ACTIONABILITY_RECOVERY_AND_POWER_STATE_MACHINE_V1
```

Minimum scope:

```text
ActionFailureClass
RecoverableActionObservation
ActionAliasNormalizer
ActionabilityFrame / BrowserActionabilityRegistry
browser ref alias resolver
extractor ref/actionability validation hook
ModelLedTaskLoop recovery/correction lanes
LoopGuard split recovery/proof/finish budgets
bridge BrowserFailureRecoveryEngineV1 into real browser runtime failures
tests for recovery vs hard stop
```

Do not start with:

```text
browser parser-only fix
prompt-only fix
Alibaba-specific DOM selector hack
raw screenshot persistence
per-click approval
another dry-run/browser audit pack
```

## Product Logic Summary

The product should feel like:

```text
grant once
model acts
Sentinel checks boundaries invisibly
runtime recovers ordinary operating misses
receipts are created
replay proves no repeated side effect
hard stop only on real damage or scope escape
```

It should not feel like:

```text
model suggests a thing
Sentinel says no because an internal name did not line up
model tries again
Sentinel blocks because a ref changed
FinalGate certifies that nothing useful happened
```

The next pack must make the model's visible operating world real.

## Validation Notes

This V2 audit is documentation-only.

No provider call was made.
No browser run was made.
No Telegram/channel send was made.
No runtime/source behavior was changed.
No push was performed.
