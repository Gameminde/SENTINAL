# SENTINEL_POWER_FRICTION_AND_AUTHORITY_BLOCKER_AUDIT_V1

## Executive Verdict

Sentinel's power loop is no longer primarily blocked by provider access, model
schema extraction, or broad safety policy. The recurring product blocker is now
the runtime/control boundary between model-visible actionability and actual
execution.

The strongest pattern across recent real runs is:

```text
mission-level authority is granted
model chooses an in-scope useful action
Sentinel blocks terminally because an internal alias, context, budget, or ref
mapping contract is incomplete
```

This is product-power debt, not real-world damage prevention.

The doctrine remains:

```text
Do not control intelligence.
Control real-world power.

Model leads.
Sentinel executes.
Receipts in background.
Hard stop only on real damage.
```

The immediate browser ref fix should not be implemented as a narrow parser-only
patch. It should be absorbed into a broader actionability and recovery contract
pack:

```text
POWER_PACK_6C_ACTIONABILITY_AND_RECOVERY_RUNTIME_CONTRACT_V1
```

That pack should make the browser ref issue the first acceptance case, but the
contract must cover all model-led power surfaces.

## Evidence Inspected

Reports inspected:

```text
SENTINEL_REAL_POWER_ATTEMPT_2B_MODEL_LED_CODE_EXECUTION_LOOP_FINISH_V1_REPORT.md
SENTINEL_FIX_POWER_LOOP_READ_ONLY_VERIFICATION_GATE_AUTHORITY_V1_REPORT.md
SENTINEL_FIX_POWER_LOOP_POST_PATCH_VERIFICATION_ORDERING_V1_REPORT.md
SENTINEL_REAL_POWER_ATTEMPT_2E_MODEL_LED_CODE_EXECUTION_LOOP_FINISH_V1_REPORT.md
SENTINEL_REAL_POWER_ATTEMPT_4B_MODEL_LED_REAL_CHANNEL_SEND_FINISH_V1_REPORT.md
SENTINEL_REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1_REPORT.md
SENTINEL_POWER_PACK6B_BROWSER_WORLD_MODEL_AND_DECISION_FRAME_WIRING_V1_REPORT.md
SENTINEL_BROWSER_POWER_AUDIT_AND_AGENT_LAB_IMPORT_PLAN_V1.md
5B safe run report under .sentinel-runs/real-power-attempts
```

Source layers inspected:

```text
sentinel/operator/action_kernel.py
sentinel/operator/decision_context.py
sentinel/operator/model_led_task_loop.py
sentinel/operator/loop_guard.py
sentinel/operator/read_only_operator_spine.py
sentinel/operator/workspace_patch_runtime.py
sentinel/operator/code_execution_sandbox_runtime.py
sentinel/operator/browser_control_runtime.py
sentinel/operator/real_browser_control_runtime.py
sentinel/operator/connection_live_channel_action_runtime.py
sentinel/operator/channel_adapter.py
sentinel/operator/browser_world_model.py
sentinel/operator/browser_decision_frame.py
sentinel/operator/browser_action_candidates.py
sentinel/operator/runtime_host.py
```

Key code anchors:

```text
ActionKernel terminalizes missing executors and runtime exceptions:
sentinel/operator/action_kernel.py:158-184

ModelLedTaskLoop terminalizes ActionKernelError / LoopGuardError:
sentinel/operator/model_led_task_loop.py:137-218

DecisionContext controls finish availability and browser progress:
sentinel/operator/decision_context.py:118-172
sentinel/operator/decision_context.py:515-589

Real browser runtime exposes world cards after open/observe:
sentinel/operator/real_browser_control_runtime.py:303-342
sentinel/operator/real_browser_control_runtime.py:636-667

Playwright browser engine uses exact ephemeral ref -> selector mapping:
sentinel/operator/real_browser_control_runtime.py:753-802
sentinel/operator/real_browser_control_runtime.py:873-879

BrowserDecisionFrame shows candidate refs/examples to the model:
sentinel/operator/browser_decision_frame.py:29-66
sentinel/operator/browser_decision_frame.py:82-100
sentinel/operator/browser_decision_frame.py:113-149

Browser action extractor accepts params as model supplied:
sentinel/operator/browser_action_candidates.py:57-98
```

## Blocker And Control Architecture Map

### Authority Layer

`MissionAuthoritySummary` and `MissionAuthorityEnvelope` define the mission
grant. They are supposed to unlock smooth action inside scope. The current
contract is strong for boundaries, but alias and tool-name mismatches have
caused valid in-scope actions to reach Gate under the wrong capability identity.

Correct role:

```text
decide mission scope once
preserve allowed tools/actions/paths/domains
block escalation and scope escape
```

Incorrect role:

```text
be re-litigated for every in-scope step
make runtime aliases behave as separate authority scopes
```

### Action Kernel

`ActionKernel` dispatches `ActionEnvelope` by `capability_id`. It has no typed
distinction between:

```text
real danger boundary
recoverable in-scope failure
model protocol failure
runtime registry mismatch
```

Any missing executor or runtime exception becomes `ActionKernelError`, and
`ModelLedTaskLoop` converts that to a terminal blocked mission.

### Decision Context

`DecisionContextCompiler` is the model's operating frame. It decides:

```text
available_actions
progress_state
objective_satisfied
finish_available
recommended_next_action
browser_world_model_summary
browser_decision_frame
top_stable_refs
```

This is where power is either unlocked or starved. Previous failures show that
thin context and wrong progress state close finish too early, open finish too
late, or fail to show actionable recovery.

### Loop Guard

`LoopGuard` protects against runaway model calls, repeated actions, repeated
targets, no-progress loops, and material budget exhaustion. These are useful,
but today budgets also act as friction because correction/recovery turns are not
separated from useful material actions.

### Gate And FinalGate

Gate is right for real boundaries:

```text
path outside workspace
forbidden tool/action
credential/secret targets
unauthorized channel destination
payment/login/contact/cart
```

FinalGate is right for false-success prevention:

```text
no fake receipt
no completed mission without proof
no replay mutation
```

But Gate/FinalGate sometimes hides a product failure behind a safety-looking
terminal block. Example: read-only verification was valid but reached Gate under
the wrong alias, causing `READ_ACCESS_BLOCKED`.

### Runtime Layers

Each runtime has its own local authority and execution checks. That is good.
However, there is no shared "recoverable in-scope failure" return path:

```text
unknown browser ref
stale selector
missing model JSON action
read-only alias mismatch
bounded check missing
finish missing
```

These frequently become terminal blocks even though they did not attempt real
damage.

## Prior Real-Run Blockers

| Blocker | Origin | Why It Happened | Stopped Real Damage | Blocked Authorized Power | Recommended Behavior | Priority |
|---|---|---|---:|---:|---|---:|
| `READ_ACCESS_BLOCKED` in Attempt 2B | Read-only Gate through Power Loop | Read-only verification used a Power Loop capability alias not recognized as granted read-only research | No | Yes | Normalize authority/tool aliases before Gate; keep path boundary checks | P0 |
| `MODEL_ACTION_EMPTY_ENVELOPE` replacing `action_executor_missing` | Model-led loop action validation | Empty model action was previously routed like an executor problem | No | Yes | Typed model correction turn with exact schema and examples | P0 |
| Post-patch false finish risk | DecisionContext finish logic | Finish opened without ordered post-patch verification | Yes, prevented false success | No | Keep as hard false-success prevention, but guide verification action | P0 |
| Channel delivery succeeded but finish killed by budget | LoopGuard/material budget | Material budget consumed by real send before finish turn | No | Yes | Finish-only turn after delivery receipt; block only if model refuses finish | P0 |
| Attempt 5 Alibaba no stable refs | Browser context | `real_browser.open` proved launch but did not provide a useful world model to model | No | Yes | World model and decision frame after open | P0, fixed by Pack 6B |
| Attempt 5B `real_browser_element_ref_unknown` | Real browser runtime | World model exposed refs, model attempted `type_text`, runtime rejected selected ref as unknown | No | Yes | Actionability contract: shown candidate refs must be executable or become recovery observation | P0 |
| Provider malformed/missing model action | Extractor/protocol | Model returns non-action/prose/metadata envelope | No | Yes | Typed correction turn inside mission, not terminal unless exhausted | P1 |
| Browser captcha/login/consent/modal | Real browser state | Site blocks interaction or inserts overlay | Sometimes | Sometimes | Recovery observation if dismiss/read-only safe; hard stop on login/credential/payment/contact | P1 |
| Duplicate external channel send on replay | Replay/channel runtime | Re-sending would create real external side effect | Yes | No | Hard stop forever; replay must never resend | P0 |
| Payment/login/contact supplier/cart | Browser/channel authority boundary | Would expand real-world power beyond granted browser research | Yes | No | Hard stop unless future mission grants explicit special authority | P0 |

## Blocker Taxonomy

### HARD_STOP_REAL_DAMAGE

Use for actions that can create external irreversible or high-risk effects:

```text
payment
checkout
contact supplier
send inquiry outside granted channel
account creation
login with credentials
credential exfiltration
duplicate real external send during replay
destructive write/delete outside granted workspace
```

These should stay terminal unless a future explicit mission-level grant covers
that exact power.

### HARD_STOP_OUT_OF_SCOPE_AUTHORITY

Use when the requested action exceeds the granted mission envelope:

```text
workspace escape
absolute outside path
ungranted browser origin
ungranted channel destination
ungranted shell/network/browser/payment tool
model-supplied authority escalation
```

These should stay terminal, with clear typed reason.

### RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE

Use when the action is in granted scope but runtime mapping/state failed:

```text
real_browser_element_ref_unknown
stale selector
click intercepted by overlay
search control disappeared after page load
bounded check command missing from decision context
workspace file target alias not canonicalized
```

These should become model-visible observations and keep the mission alive while
budgets allow.

### RECOVERABLE_MODEL_PROTOCOL_FAILURE

Use when provider returned visible content but not a canonical action:

```text
metadata-only JSON
missing capability_id/operation/params
wrong envelope key names
prose instead of JSON
action not allowed by current frame
```

These should become typed correction turns with the exact current schema and
top executable candidates. They should not immediately kill the mission.

### RECOVERABLE_BROWSER_STATE_FAILURE

Use when the page is dynamic, blocked, or not ready:

```text
modal/consent overlay
captcha signal
login wall
dynamic loading not settled
result cards not loaded
price hidden behind login
```

Some are recoverable by observe/wait/scroll/extract. Login/captcha can become a
valid failure, but it should be reported as browser state, not generic runtime
death.

### AUTHORITY_ALIAS_OR_MAPPING_BUG

Use when capability names differ across model frame, ActionEnvelope, runtime,
Gate, or authority:

```text
read_only_research vs Power Loop read-only executor
real_browser.open vs real_browser_control.real_browser.open
finish vs sentinel_loop.finish
bounded_channel.send_message vs channel_transport.send_message
```

These are source bugs, not safety wins.

### ACTIONABILITY_CONTRACT_VIOLATION

Use when Sentinel shows an action/ref/candidate to the model that the runtime
cannot execute.

Attempt 5B is the current best example: the world model exposed useful refs,
but the next model action was rejected as unknown. Either the model selected an
alias not accepted by the runtime or the ref registry changed before execution.
In both cases the invariant failed:

```text
model-visible candidate -> executable runtime target
```

### CONTEXT_TOO_THIN

Use when the model cannot reasonably choose a useful action because the frame
lacks world state, stable refs, exact schema, progress state, or completion
requirements.

Attempt 5 before Pack 6B is the canonical example.

### BUDGET_TOO_STRICT

Use when material or model-call budgets prevent low-risk completion/recovery:

```text
send receipt happened but no finish turn
patch happened but verification turn unavailable
browser action happened but assertion/extraction turn unavailable
```

Budgets should limit power, not cut off proof.

### FALSE_SUCCESS_PREVENTION

Use when blocking prevents Sentinel from claiming success without evidence:

```text
finish before post-patch verification
finish before browser assertion/extraction
mission completed without receipt
replay mismatch
```

These are good blocks.

### SECURITY_THEATER_FRICTION

Use when a block looks like governance but does not reduce real-world damage:

```text
per-action friction for already-granted read-only actions
terminalizing schema mistakes without correction
terminalizing unknown in-scope refs without recovery candidates
requiring perfect final report before first useful action
```

These should be removed or downgraded.

## Hard-Stop Vs Recoverable Matrix

| Failure | Classification | Terminal? | Recovery Expected |
|---|---|---:|---|
| Workspace path escape | HARD_STOP_OUT_OF_SCOPE_AUTHORITY | Yes | No |
| Credential or Authorization access | HARD_STOP_REAL_DAMAGE | Yes | No |
| Payment/checkout/add-to-cart/contact supplier | HARD_STOP_REAL_DAMAGE | Yes | No |
| Unauthorized channel destination | HARD_STOP_OUT_OF_SCOPE_AUTHORITY | Yes | No |
| Duplicate external channel send during replay | HARD_STOP_REAL_DAMAGE | Yes | No |
| Read-only alias mismatch | AUTHORITY_ALIAS_OR_MAPPING_BUG | No | Normalize alias then retry/continue |
| Empty ActionEnvelope | RECOVERABLE_MODEL_PROTOCOL_FAILURE | No initially | Typed correction turn |
| Model action not allowed by frame | RECOVERABLE_MODEL_PROTOCOL_FAILURE | No initially | Correction turn with current allowed actions |
| Unknown browser stable ref | ACTIONABILITY_CONTRACT_VIOLATION | No initially | Recovery observation with executable refs |
| Stale browser selector | RECOVERABLE_BROWSER_STATE_FAILURE | No initially | Re-observe and refresh refs |
| Consent/modal overlay | RECOVERABLE_BROWSER_STATE_FAILURE | Maybe | Observe/click safe close if visible and in scope |
| Captcha/login wall | RECOVERABLE_BROWSER_STATE_FAILURE | Usually valid failure | Report blocker, no fake success |
| Finish before post-patch verification | FALSE_SUCCESS_PREVENTION | Yes for that turn | Guide verification first |
| Finish missing after delivery receipt | BUDGET_TOO_STRICT | No initially | Finish-only correction turn |
| Provider timeout | RECOVERABLE_MODEL_PROTOCOL_FAILURE or provider failure | Maybe | One bounded timeout policy, no hidden retry |

## Where Sentinel Over-Blocks Authorized Power

1. `ActionKernelError` is a single terminal path for multiple classes of
   failures. Missing executor, runtime unknown ref, and real boundary violation
   are all collapsed into a blocked mission.

2. `ModelLedTaskLoop` catches `ActionKernelError` and `LoopGuardError` and
   immediately calls `_block`. It does not ask whether the error is recoverable
   and in scope.

3. Decision frames expose candidates but there is no executable-candidate
   registry. The browser frame can show refs and exact examples, but runtime
   execution still relies on exact ephemeral `_ref_selectors`.

4. Browser action extraction validates only action shape and allowed action
   names. It does not validate or canonicalize `params.ref` against the latest
   world model before handing it to runtime.

5. Material budgets are still partly mixed with proof/completion turns. Recent
   fixes created finish-only and assertion-only turns, but the core budget model
   remains material-action-first rather than mission-progress-first.

6. Gate and FinalGate reasons sometimes mask product-power bugs. A Gate denial
   caused by capability alias mismatch reads like safety but was actually an
   authority propagation bug.

7. Recovery observations are missing as first-class loop results. In-scope
   failures should add context like:

   ```text
   attempted action failed because ref stale/unknown
   current executable refs are ...
   recommended next action = observe
   ```

   Today they often become terminal blocked reasons.

8. Runtime registries are fragmented. Browser, channel, read-only, patch, and
   code execution each solve action names and authority in their own local way.

9. DecisionContext is increasingly rich for browser, but not yet guaranteed to
   be source-of-truth for what ActionKernel can execute.

10. Correction turns are not a general primitive. They exist indirectly through
    finish-only or assertion-only special cases, but not as a reusable recovery
    lane.

## Where Sentinel Correctly Blocks Real Danger

The following blocks are real product safety, not theater:

```text
workspace path escape
absolute outside file paths
symlink escapes
sensitive workspace targets
credential-like text
browser secret/password fields
unbounded browser URLs
login/contact supplier/cart/payment/account creation
unauthorized channel recipients/domains
duplicate channel sends on replay
workspace patch base hash mismatch
workspace patch not applicable
bounded check shell injection
missing/tampered receipt or FinalGate hash
finish before proof when objective evidence is absent
```

These controls should remain hard.

## Actionability Contract

Core invariant:

```text
Anything shown to the model as an actionable candidate must be executable by
the runtime that will receive the ActionEnvelope.
```

Violations found:

| Surface | Current Risk | Required Contract |
|---|---|---|
| Browser stable refs | Refs are generated from DOM snapshot and runtime accepts exact ephemeral refs only | Frame must carry executable ref IDs backed by a ref registry with epoch/state hash |
| Browser candidate actions | Candidate action lists are advisory and not tied to executor validation | Candidate action must include canonical capability, operation, required params, and ref validity |
| Channel destination refs | Destination is bounded, but action aliases differ across channel layers | Destination refs must be canonicalized once and reused across adapter/runtime |
| Workspace target refs | Patch/read-only paths use different local policies | Workspace target refs should normalize to approved root-relative refs before Gate |
| Code execution profile refs | Profiles are bounded but model context must show exact allowed profile IDs | Decision frame must list executable profile IDs, not prose |
| Read-only path refs | Gate can classify valid path as blocked if tool alias is wrong | Alias normalization must happen before Gate |

Actionability should be enforced before provider-visible frames are emitted:

```text
compile candidates from runtime registry
validate candidate refs against current runtime snapshot
emit only canonical actions the ActionKernel can execute
on stale/unknown ref, refresh and return recovery candidates
```

## Mission Authority Contract

Core invariant:

```text
Mission-level grant should unlock smooth execution inside scope.
It should not create per-action friction unless the next action expands
real-world power.
```

Violations found:

```text
read-only verification was blocked because the same granted workspace read
authority reached Gate under the wrong alias.

channel send receipt needed a finish-only correction because material budget
closed the loop too early.

browser type_text on an in-scope bounded target caused terminal block instead
of ref recovery.
```

Authority should be normalized into a runtime-ready shape once:

```text
canonical tools
canonical actions
canonical domains
canonical workspace roots
canonical browser target refs
canonical channel destination refs
```

Then per-action checks enforce the boundary without forcing human or terminal
friction on normal in-scope steps.

## Recovery Contract

Core invariant:

```text
In-scope recoverable failures should become observations, not terminal mission
deaths.
```

Required behavior:

| Failure | Recovery Observation |
|---|---|
| Unknown browser ref | Re-observe, expose latest executable refs, say attempted ref was invalid |
| Stale selector | Re-observe and retry with refreshed ref candidates |
| Model JSON malformed | Typed correction turn with exact schema and current candidates |
| Action not allowed | Correction turn with allowed action list |
| Search control not found | Recovery frame listing visible controls and extraction alternative |
| Dynamic loading | wait/observe/scroll candidate |
| Captcha/login wall | Valid failure with blocker signal unless a safe read-only alternative exists |
| Finish missing after objective proof | Finish-only turn |
| Bounded check missing | Show exact bounded check action/profile |

Recovery must still obey budgets. But budgets should count:

```text
material actions
external side effects
recovery/correction turns
```

separately. A single ref mismatch should not consume the mission's entire power
proof.

## Recommended Core Architecture Changes

1. Add `ActionabilityFrame` or equivalent inside `DecisionContext`.

   This should be compiled from registered executors and current runtime
   snapshots, not hardcoded prose. It should include canonical actions, param
   schemas, executable refs, ref epoch/state hash, and recovery actions.

2. Add `RecoverableActionFailure`.

   Runtimes should be able to return a non-material `ActionResult` with:

   ```text
   status = recoverable_failed
   failure_class
   attempted_action_hash
   recovery_observation
   refreshed_candidates
   ```

   instead of raising terminal `ActionKernelError` for in-scope failures.

3. Split terminal danger from recoverable execution.

   `ActionKernelError` should be reserved for hard boundaries and internal
   invariant failures. Runtime misses such as unknown in-scope browser ref
   should not use the same terminal path.

4. Add authority alias normalization as a shared layer.

   The system needs one normalizer for:

   ```text
   read_only_research.search_text
   real_browser_control.real_browser.type_text
   bounded_channel.send_message
   channel_transport.send_message
   finish / sentinel_loop.finish
   ```

5. Add typed model correction turns.

   Model protocol failures should feed a compact correction frame:

   ```text
   your last output was visible but not actionable
   failure_code = MODEL_ACTION_SCHEMA_INVALID
   allowed actions = ...
   exact JSON examples = ...
   ```

6. Separate recovery budget from material budget.

   Recovery/correction/observe refresh turns should be bounded, but should not
   be treated like successful material actions.

7. Make FinalGate certify truth, not operate as the first recovery mechanism.

   FinalGate should block false success and tampered proof. It should not be the
   place where correctable in-scope runtime misses die.

8. Add a cross-surface failure classification adapter.

   Every runtime should classify failures into the taxonomy in this report.

9. Keep hard-stop denylist narrow and real.

   Payment, login, credential, external send outside scope, destructive write,
   and replay side effects stay hard.

10. Preserve receipts/replay as the moat.

   Power should increase without removing receipt, evidence, replay, and safe
   redaction guarantees.

## Recommended Browser-Specific Changes

1. Introduce a browser ref registry tied to browser state hash.

   ```text
   ref
   selector
   role
   name
   enabled/visible/secret
   snapshot_state_hash
   expires_on_next_navigation
   ```

2. Validate model-selected refs before execution.

   If the ref is unknown but close to a known ref, do not click/type silently.
   Return a recovery observation with executable refs.

3. Add `real_browser.observe` as auto-recovery for unknown/stale refs.

   Unknown ref on a bounded page is usually not danger. It is a browser state
   mismatch.

4. Couple `BrowserDecisionFrame.candidate_actions` to runtime registry.

   Candidate actions should not be merely advisory. They should be generated
   from currently executable refs.

5. Include ref aliases explicitly.

   Large websites produce model-hostile refs such as:

   ```text
   textbox:search_alibaba:4
   ```

   The frame can include:

   ```text
   canonical_ref = textbox:search_alibaba:4
   short_ref = search_box
   accepted_refs = [...]
   ```

   but the runtime must resolve these aliases, not reject them as unknown.

6. Add blocker-specific recovery for Alibaba-like pages.

   ```text
   consent/modal -> safe close if visible
   captcha/login -> valid failure
   dynamic loading -> wait/scroll/observe
   product cards absent -> search/extract alternative
   ```

7. Treat extraction cards as evidence candidates, not success by themselves.

   Current 5B cards were weak and mostly page chrome. Product-proven needs
   meaningful title/price/MOQ/supplier/caveat extraction.

8. Prevent raw DOM/screenshot/session persistence.

   Continue preserving only bounded summaries, hashes, refs, and cards.

## Recommended Channel Changes

1. Keep real outbound duplicate/replay hard-blocked.
2. Treat successful send as objective-satisfying for a finish-only turn.
3. Keep destination grant mission-level, no per-message approval spam.
4. Normalize channel action aliases before ActionKernel/Gate.
5. Preserve delivery refs as hashes only.

## Recommended Workspace And Code Changes

1. Keep destructive/outside workspace blocks hard.
2. Keep base-hash mismatch hard for patches.
3. Make post-patch verification guidance first-class.
4. Ensure read-only verification always uses the same granted workspace scope.
5. Do not allow finish after patch until bounded check or read-only verification
   receipt exists.

## Recommended Read-Only Changes

1. Keep outside path, secret path, and unapproved root reads hard.
2. Normalize read-only aliases before Gate.
3. Treat provider schema/model action issues as typed correction turns when the
   provider is alive.
4. Keep first material receipt and autopilot receipt modes, but separate timeout
   and model-protocol failure classifications.

## Top 10 Power-Friction Removals

1. Replace terminal `real_browser_element_ref_unknown` with a recovery
   observation and refreshed executable refs.
2. Add a cross-runtime actionability registry: model-visible candidates must be
   executable.
3. Add typed model correction turns for malformed/non-action model outputs.
4. Normalize authority aliases before Gate and runtime dispatch.
5. Split recovery/correction budgets from material action budgets.
6. Convert in-scope runtime mapping failures from `ActionKernelError` into
   recoverable `ActionResult` records.
7. Make DecisionContext compile allowed actions from the real executor registry.
8. Add browser ref aliases and state-hash-bound ref epochs.
9. Keep FinalGate focused on proof truth, not routine recoverable misses.
10. Add per-surface failure taxonomy reporting so product blockers are not
    mislabeled as safety wins.

## Next Implementation Pack Recommendation

Recommended next implementation:

```text
POWER_PACK_6C_ACTIONABILITY_AND_RECOVERY_RUNTIME_CONTRACT_V1
```

Not recommended as the immediate next move:

```text
FIX_REAL_BROWSER_STABLE_REF_ACTION_RESOLUTION_V1
```

Reason:

```text
The browser ref issue is real, but it is a symptom of a broader contract gap.
If we patch only one parser/ref path, the next power surface will hit the same
class of blocker under another name.
```

Pack 6C should include:

```text
ActionabilityFrame / executable candidate registry
RecoverableActionFailure / recovery ActionResult path
shared authority alias normalizer
browser ref registry and alias resolver as first concrete use case
typed model correction turn for non-action/malformed ActionEnvelope
DecisionContext recovery frame
LoopGuard recovery budget separate from material budget
tests proving unknown in-scope browser ref recovers instead of terminal block
tests proving out-of-scope/payment/login/contact/credential actions still hard stop
```

Acceptance target for 6C:

```text
fake hard browser mission:
open -> world model -> model chooses alias/short ref -> resolver maps to canonical ref
-> type/search -> extract card -> finish

negative path:
out-of-scope URL/login/payment/contact/credential remains terminal hard stop

recovery path:
unknown/stale in-scope ref -> recovery observation -> model receives refreshed refs
-> next action succeeds
```

After 6C, rerun:

```text
REAL_POWER_ATTEMPT_5C_MODEL_LED_ALIBABA_ACTIONABILITY_RECOVERY_V1
```

Product success should require:

```text
real Alibaba open receipt
world model/observe receipt
model uses executable stable ref or recovered alias
real search/navigation/state change
meaningful product/search extraction card
evaluative summary
sentinel_loop.finish
replay no reopen/no reclick/no retype/no resubmit/no reextract
```

## Validation Notes

This audit is documentation-only.

No provider call was made.
No browser run was made.
No Telegram/channel send was made.
No runtime/source behavior was changed.
No push was performed.

