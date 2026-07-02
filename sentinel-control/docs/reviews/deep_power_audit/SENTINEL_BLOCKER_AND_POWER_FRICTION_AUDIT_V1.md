# SENTINEL_BLOCKER_AND_POWER_FRICTION_AUDIT_V1

## Verdict

```text
SENTINEL_BLOCKER_AND_POWER_FRICTION_AUDIT_V1 = COMPLETE
```

This audit agrees with the product correction:

```text
Do not delete safety blindly.
Delete, demote, or recover blockers that do not protect real-world damage.
```

Sentinel still has too many small walls between the model brain and the runtime body. The problem is not that Sentinel has receipts, replay, authority, or FinalGate. Those are the moat. The problem is that ordinary in-scope misses still become mission death in several places, and model-facing paths can still expose or prefer brittle internal mechanics instead of simple executable skills.

The target doctrine remains:

```text
Model thinks.
Sentinel executes.
Receipts/replay stay in the background.
Hard stop only on real damage.
Everything else becomes recovery, warning, hidden routing, or skill translation.
```

## Scope And Inputs

This audit inspected:

- `SENTINEL_DEEP_POWER_AUDIT_V1_MASTER_REPORT.md`
- `SENTINEL_GLOBAL_POWER_RECONNECTION_CORRECTION_PLAN_V1.md`
- `SENTINEL_POWER_RECONNECTION_PACK_SEQUENCE_V1.md`
- `SENTINEL_DEEP_POWER_SURGICAL_CUT_LIST_V1.md`
- `SENTINEL_ORGANS_AND_BROWSER_INVENTORY_V1.md`
- Prior power-friction blocker audits V1/V2
- Core runtime files under `sentinel/operator`
- Browser skill/runtime/world-model files
- Provider/schema/extraction files
- Workspace/code/channel runtime files
- Authority/proof/replay/organ registry files
- Sub-agent subsystem audits for core loop, browser, and provider/schema paths

No runtime code was changed. No provider call was made. No browser run was made. No push was performed.

## Matrix Summary

The companion CSV contains the detailed blocker matrix:

```text
SENTINEL_BLOCKER_AND_POWER_FRICTION_MATRIX_V1.csv
```

Audit count:

```text
total_blockers_classified = 59
KEEP_HARD_STOP = 8
KEEP_BUT_REQUIRE_CLEAR_AUTHORITY = 18
CONVERT_TO_RECOVERY = 17
REPLACE_WITH_SKILL_ROUTING = 8
MOVE_BELOW_MODEL = 8
DELETE = 0
DEMOTE_TO_WARNING = 0
```

Important: `DELETE = 0` does not mean no friction should be removed. It means the next product-safe move is to delete or hide model-facing friction paths first, not physically delete source modules before replacement paths are proven.

## Core Finding

The main blocker class is still:

```text
in-scope miss
-> runtime/schema/locator/ref/budget failure
-> ActionKernelError or loop guard error
-> ModelLedTaskLoop blocked
-> FinalGate/certificate records blocked truth
```

That is honest, but product-weak.

The desired behavior is:

```text
in-scope miss
-> typed recoverable observation
-> refreshed context/actionability frame
-> model or skill router chooses next best skill
-> receipts remain truthful
-> only final-block after real recovery exhaustion
```

## What Must Stay Hard

These hard stops protect real-world damage and should not be removed:

| Boundary | Why it remains hard |
|---|---|
| payment / checkout / spend | Financial irreversible action |
| credentials / secrets / API keys / tokens | Credential compromise |
| login / account mutation | Identity/account side effects |
| contact supplier / external send outside explicit grant | External message side effect |
| cookies / session persistence | Session theft / privacy leakage |
| upload/download outside authority | Data exfiltration or filesystem mutation |
| arbitrary browser JavaScript | Page/session/code execution escalation |
| workspace escape | Local filesystem boundary breach |
| destructive writes outside authority | Data loss |
| provider-native tools | Provider-side action bypassing Sentinel receipts |
| fallback/AUTO routing | Unapproved model/backend authority expansion |
| raw provider output/reasoning/DOM/screenshots/cookies persistence | Sensitive material persistence |
| replay causing side effects | Duplicate send, click, patch, code exec, browser action |

## What Is Friction Masquerading As Safety

These classes do not usually protect real damage and should be removed, moved below the model, or converted to recovery:

- strict JSON/prose-wrapper failures when useful safe intent is visible;
- `metadata.reply` dialect friction after model text is already available;
- `empty_action_envelope` loops when model-native intent can be mapped;
- stale/unknown/hidden browser refs as terminal blockers;
- search/open repetition when product cards are already visible;
- proof-not-yet-satisfied as mission death instead of proof lane;
- finish policy that ignores verified extraction evidence;
- backend-frame mismatch surfacing too late or as confusion;
- primitive browser actions leaking into model-facing decision context;
- old read-only spine gravity blocking richer skill paths;
- generic `ActionKernelError` for in-scope runtime misses;
- budget exhaustion before the strongest safe recovery path is tried;
- FinalGate certifying avoidable blocked truth before recovery options are exhausted.

## Current Evidence From Real Attempts

The recent Alibaba path is the strongest proof.

5D showed that Pack 6D had not fully solved backend truth and actuation:

```text
selected Cloak/session visibility did not equal actual runtime backend
search actuation failed
product extraction did not become the dominant route
```

5F moved further:

```text
model-native intent was consumed
metadata.reply did not collapse into empty_action_envelope
raw primitives were not primary
product/result cards were visible
```

But 5F still failed because:

```text
EXTRACTION_NOT_TRIGGERED_WITH_VISIBLE_CARDS
loop eventually blocked by loop guard / provider decision churn
```

That is not useful security. It is a routing/friction blocker.

## Cross-System Diagnosis

### Core Loop

The loop has a recoverable observation mechanism, but several terminal conditions still fire too early. The biggest issue is not a missing concept; it is incomplete dominance of the recovery/state machine over old terminal branches.

### Browser

Browser power is still the highest-leverage problem because it exposes the whole architecture:

```text
world model exists
refs/cards exist
model can express useful intent
runtime still may prefer open/search or fail on low-level actuation
```

The next browser work should not add more primitive APIs. It should remove primitive model-facing pressure and make product-card extraction the dominant path when cards are visible.

### Provider / Schema

Provider truth retention improved the system, but old strict-schema paths remain. The model should not be forced to think in Sentinel internals. Natural/semi-structured intent should map into internal `ActionEnvelope` skills, with unsafe control/credential/reasoning fields still hard-stopped.

### Workspace / Code

Patch and code execution hard stops are mostly valid. The key improvement is not loosening workspace escape or shell/network controls. It is converting stale patch/check failures into recovery observations that tell the model what to refresh.

### Channel

Channel hard stops are mostly correct: no resend on replay, no send outside grant, finish after delivery. The friction risk is natural finish mapping, not channel authority.

### Authority / Proof / Replay

Authority, receipts, and replay should remain hard. FinalGate should certify the final truth, but routine recoverable misses should not rush to FinalGate while recovery paths remain available.

## Highest-Risk False Positive Zones

1. Browser hard-boundary keyword scanning.
2. Provider wrapper metadata rejection.
3. Strict JSON/prose parsing.
4. Legacy recommended actions overriding skill frames.
5. Loop guard repeated-action/deadline on dynamic pages.
6. Read-only action set rejecting safe higher-level skill intent.
7. Authority alias mismatch before canonical skill routing.
8. Product extraction proof predicates too narrow or too shallow.

## Audit Decision

Do not target a fake percentage such as "delete exactly 80%".

Target this:

```text
Audit 100% of blockers.
Keep hard stops tied to exact real damage.
Convert or hide the rest.
```

The matrix proves a large majority of the product-friction blockers should not remain model-facing terminal blocks. They should be converted to recovery, moved below the model, or replaced by skill routing.

## Immediate Pack Recommendation

```text
POWER_FRICTION_CUT_PACK_1_REMOVE_STUPID_BLOCKERS_V1
```

Scope:

```text
1. Fix 5F blocker: visible product cards + safe ambiguous intent routes to extract_product_cards.
2. Reorder browser native intent priority around current world state: finish/verify/extract before open/search.
3. Convert no-safe-recommendation into recoverable observation with best skill fallback.
4. Move legacy primitive browser action schema below model-facing decision context.
5. Convert stale/hidden/disabled browser ref failures to recoverable observations unless secret/password.
6. Ensure FinalGate does not close avoidable blocked truth before recovery options are exhausted.
```

Not in scope:

```text
payment
login
contact supplier
credentials
cookies/session
upload/download
arbitrary JS
workspace escape
provider-native tools
fallback/AUTO
```

## Required Proof For The Next Pack

Before another real Alibaba run:

```text
fake hard page:
open
-> world model has product cards
-> ambiguous/natural intent maps to extract_product_cards
-> verify_extraction
-> natural finish
-> no primitive model-facing action
-> replay no-react
```

Then one real attempt can test:

```text
REAL_POWER_ATTEMPT_5G_OR_5F_RERUN_AFTER_FRICTION_CUT
```

Only after fake/local proof.

## Confirmation

```text
runtime_code_changed = false
provider_call = false
browser_run = false
push = false
delete_performed = false
```
