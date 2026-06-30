# Sentinel Deep Power Audit V1 - Next Action Plan

Status: proposed plan
Doctrine: power first, receipts always

## Strategic Decision

Do not start another narrow browser timeout patch.

Do not start another security/manifest/control-plane pack.

Next implementation should be:

```text
POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
```

This pack should turn the browser from:

```text
model pilots Playwright-ish refs
```

into:

```text
model pilots a browser skill
Sentinel handles low-level actuation/recovery/proof
```

## Acceptance Target

The next real Alibaba-style attempt should not die at `type_text` locator timeout.

If a search input candidate fails:

```text
try alternate candidate
scroll into view
focus
fill or type
press Enter
click search submit if needed
wait for result
recapture world model
extract candidate product cards
continue
```

Only hard-stop on:

```text
captcha/login wall
payment/contact supplier
credential or personal-data request
out-of-scope origin
recovery budget exhausted after real attempts
```

## Pack 6D Workstreams

### 1. Browser Skill API

Add model-facing browser skill intents:

```text
real_browser.search
real_browser.inspect_result
real_browser.open_result
real_browser.extract_product_cards
real_browser.verify_extraction
sentinel_loop.finish
```

Keep low-level actions available internally:

```text
observe
click
type_text
press_key
wait_for_load
wait_for_text
scroll
extract_text
assert_text
```

But do not make the model depend on raw Playwright-like selectors.

### 2. Actionability Registry

Create a live actionability layer:

```text
BrowserActionabilityRegistry
BrowserActionCandidate
BrowserActuationPlan
BrowserRecoveryObservation
```

Rule:

```text
If a candidate is exposed to the model, Sentinel must have an executable plan for it.
```

### 3. Robust Browser Actuation

For search/type/click:

```text
resolve stable ref
validate origin/scope
scroll into view
wait visible/enabled
focus
clear/fill
fallback to type
fallback to keyboard shortcut if safe
press Enter or click search submit
wait for network/load/text/result change
recapture world model
```

Persist:

```text
action kind
target ref hash
before/after state hash
bounded summary hash
receipt id
```

Do not persist:

```text
cookies
session tokens
full DOM
screenshots by default
raw provider output
reasoning
credentials
```

### 4. Recovery Lane

Change behavior for in-scope ordinary failures:

```text
hidden element
disabled element
stale ref
timeout
candidate not found
dynamic loading
modal/consent ambiguity
```

from:

```text
ActionKernelError -> mission blocked
```

to:

```text
recoverable observation -> refreshed world model -> next model decision or automatic skill retry
```

Hard stops remain:

```text
scope escape
credential/payment/contact/login
ungranted origin
destructive action
raw secret risk
```

### 5. Proof Policy Simplification

Replace pack-specific finish/proof branches with mission-aware proof policy:

| Mission type | Valid proof |
|---|---|
| Browser research/extraction | extraction cards, product cards, wait_for_text, assert_text |
| Browser control | material action plus state-change proof |
| Channel send | delivery receipt plus no-resend replay |
| Workspace patch | patch receipt plus readback/check receipt |
| Code execution | code receipt plus bounded check receipt |

### 6. Replay Upgrade

All power surfaces should validate:

```text
no model call delta
no runtime action delta
no transport send delta
no patch/code/browser replay side effect
receipt count stable
receipt schema valid
receipt hash stable
FinalGate hash stable
artifact hashes stable
workspace/browser/channel state not mutated by replay
```

## Implementation Order

1. Add browser skill models and actionability registry.
2. Wire `DecisionContext` to expose skill-level actions, not raw fragile refs.
3. Implement robust actuation for search/type/click with recovery observations.
4. Modify `ActionKernel`/loop to classify recoverable in-scope misses separately from hard stops.
5. Replace real-browser proof-only branch with mission-aware proof policy.
6. Add fake hard-page tests for search, alternate ref recovery, extraction cards, finish.
7. Add replay no-reclick/no-retype/no-reextract tests.
8. Run the same Alibaba bounded real attempt once.

## Expected Tests

Focused fake/local tests:

```text
browser search uses alternate search candidate if first ref fails
type_text timeout becomes recoverable observation, not terminal mission block
search skill produces state change and receipt
extract_product_cards produces title/price/MOQ/supplier/caveat card on hard fake page
finish only allowed after extraction/control proof depending on mission
ungranted origin blocks
captcha/login/contact/payment blocks
replay does not reopen/reclick/retype/reextract
Power Pack 1-5 focused regressions still pass
```

No provider call during implementation.

## Future Real Attempt

After Pack 6D is locally committed:

```text
REAL_POWER_ATTEMPT_5D_MODEL_LED_ALIBABA_BROWSER_SKILL_SPINE_V1
```

Success threshold:

```text
real provider decision calls >= 3
real browser opens Alibaba
model uses browser skill, not brittle Playwright selectors
search/navigation or real state change occurs
product/search extraction card exists
evaluative summary exists
sentinel_loop.finish emitted
mission completes by model finish
replay no reopen/no reclick/no retype/no resubmit/no reextract
```

If failed, classify one:

```text
BROWSER_SKILL_ACTIONABILITY_EMPTY
ALIBABA_CAPTCHA_OR_LOGIN_WALL
BROWSER_ACTUATION_RECOVERY_EXHAUSTED
EXTRACTION_TOO_SHALLOW
MODEL_ACTION_PROTOCOL_FAILURE
FINISH_NOT_EMITTED
```

## Professional Cut Rule

For every future pack:

```text
If the pack does not increase model-visible real power,
it is not the next pack.
```

Receipts and replay stay.

Approval theater goes.

