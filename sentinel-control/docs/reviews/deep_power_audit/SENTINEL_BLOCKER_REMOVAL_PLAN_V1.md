# SENTINEL_BLOCKER_REMOVAL_PLAN_V1

## Purpose

This plan converts the blocker audit into an execution order. It is not a security removal plan. It is a product-power friction cut plan:

```text
remove blockers that do not prevent real damage
keep hard stops that protect real boundaries
```

## Top 20 Blockers To Remove Or Move Below The Model First

These are the blockers most likely to keep Sentinel feeling weak even when the underlying power exists.

| Rank | Blocker | Decision | Why first |
|---:|---|---|---|
| 1 | `BF-BROWSER-001` visible product cards but ambiguous intent routes away from extraction | `REPLACE_WITH_SKILL_ROUTING` | Direct 5F failure root |
| 2 | `BF-BROWSER-002` open intent outranks current-world extraction/finish | `REPLACE_WITH_SKILL_ROUTING` | Causes repeated open/search loops |
| 3 | `BF-CORE-013` legacy recommendations remain visible beside skill frame | `MOVE_BELOW_MODEL` | Old fields can override Pack D |
| 4 | `BF-BROWSER-007` raw browser primitives leak through model-facing paths | `MOVE_BELOW_MODEL` | Model should pilot skills, not Playwright-like refs |
| 5 | `BF-BROWSER-011` candidate refs/actions not guaranteed executable | `REPLACE_WITH_SKILL_ROUTING` | Violates core actionability contract |
| 6 | `BF-READONLY-001` read-only spine remains product gravity | `MOVE_BELOW_MODEL` | Keeps richer powers secondary |
| 7 | `BF-ORGAN-001` organ dispatch branch matrix keeps organs dormant | `REPLACE_WITH_SKILL_ROUTING` | Existing power remains disconnected |
| 8 | `BF-ORGAN-002` runtime request branch matrix duplicates spec logic | `REPLACE_WITH_SKILL_ROUTING` | Creates connection bugs |
| 9 | `BF-PROVIDER-006` read-only action set rejects safe higher-level skill intent | `REPLACE_WITH_SKILL_ROUTING` | Keeps model trapped in old protocol |
| 10 | `BF-PROVIDER-003` harmless metadata object rejection | `MOVE_BELOW_MODEL` | Provider dialect friction |
| 11 | `BF-APPROVAL-001` manifest/identity layers can become approval theater | `MOVE_BELOW_MODEL` | Control-plane should feed power, not block it |
| 12 | `BF-ORGAN-003` backend frame consumed descriptively only | `MOVE_BELOW_MODEL` | Must guide runtime selector without becoming authority |
| 13 | `BF-CORE-003` model-visible action with missing executor | `REPLACE_WITH_SKILL_ROUTING` | Dead actions must not be shown to model |
| 14 | `BF-BROWSER-014` browser organs not wired into skill spine | `REPLACE_WITH_SKILL_ROUTING` | Large existing browser investment unused |
| 15 | `BF-BROWSER-015` duplicate browser proof ownership | `MOVE_BELOW_MODEL` | Conflicting proof gates cause finish friction |
| 16 | `BF-PROVIDER-007` broad authority word scan for harmless metadata | `KEEP_BUT_REQUIRE_CLEAR_AUTHORITY` | Needs semantic classifier, not raw keyword block |
| 17 | `BF-AUTH-001` alias mismatch hides granted power | `KEEP_BUT_REQUIRE_CLEAR_AUTHORITY` | Existing grants must expose canonical skills |
| 18 | `BF-BROWSER-004` hard-boundary keyword overreach | `KEEP_BUT_REQUIRE_CLEAR_AUTHORITY` | Avoid blocks on benign research text |
| 19 | `BF-BROWSER-005` URL param blocks even authority-bounded URLs | `KEEP_BUT_REQUIRE_CLEAR_AUTHORITY` | Future bounded web tasks need granted navigation |
| 20 | `BF-PROOF-001` FinalGate closes avoidable blocked truth | `MOVE_BELOW_MODEL` | Recovery must happen before terminal proof |

## Top 20 Blockers To Convert To Recovery First

| Rank | Blocker | Recovery behavior required |
|---:|---|---|
| 1 | `BF-CORE-001` loop terminalizes normal ActionKernelError | Emit typed recoverable observation when not real boundary |
| 2 | `BF-CORE-002` unclassified executor failure | Classify in-scope timeout/ref/runtime miss as recoverable |
| 3 | `BF-CORE-004` empty action envelope | Map natural intent first, then recovery with exact skill frame |
| 4 | `BF-CORE-005` recovery/correction budget exhaustion | Exhaust only after real recovery attempts and preserve next best route |
| 5 | `BF-CORE-006` repeated action/target | Treat refreshed refs/candidates as progress |
| 6 | `BF-CORE-008` deadline | Offer final proof/recovery compaction before block when safe |
| 7 | `BF-CORE-012` recent-observation-only proof | Use durable receipt index for proof context |
| 8 | `BF-BROWSER-003` no safe recommendation | Use strongest safe skill fallback as recovery |
| 9 | `BF-BROWSER-008` search actuation failed | If product cards exist, route to extract/verify |
| 10 | `BF-BROWSER-009` hidden/disabled ref | Recover with refreshed candidates; keep secret field hard stop |
| 11 | `BF-BROWSER-010` modal/loading blocker | Route to safe wait/observe/dismiss when allowed; captcha/login valid-fail |
| 12 | `BF-BROWSER-012` shallow product extraction | Recover by extraction-card strengthening or unknown-field caveat |
| 13 | `BF-PROVIDER-001` strict JSON-only rejection | Extract single safe object or natural intent below model |
| 14 | `BF-PROVIDER-002` wrapper key rejection | Sanitize provider metadata and use safe visible content |
| 15 | `BF-PROVIDER-004` prose reply parse failure | Map safe intent before correction budget |
| 16 | `BF-PROVIDER-010` tool-call parse failure | Recovery repair frame, registry policy still enforced |
| 17 | `BF-WORKSPACE-002` patch old text not found | Recover by re-read/current hash route |
| 18 | `BF-CODE-002` bounded check failure | Feed check result summary/hash into next patch turn |
| 19 | `BF-PROVIDER-008` provider config disabled/missing | Preflight config names only; no consumed attempt |
| 20 | `BF-PROVIDER-010` tool-call parse failure | Repair frame for safe parse miss; registry policy still enforced |

## Hard Stops To Keep

These remain hard until explicit special-authority packs exist:

```text
payment / checkout / spend
credential or secret access
login / account mutation
contact supplier or external send outside explicit grant
cookies or session persistence
upload/download outside authority
arbitrary browser JavaScript
workspace escape
destructive writes outside authority
provider-native tools
fallback/AUTO
raw provider output / raw reasoning / raw DOM / screenshots / cookies persistence
replay causing real side effects
mission authority revoked / killed
data/control-plane object trying to grant authority
```

## First Implementation Pack

```text
POWER_FRICTION_CUT_PACK_1_REMOVE_STUPID_BLOCKERS_V1
```

### Objective

Cut the blockers that caused 5F and the surrounding model-facing friction:

```text
visible product cards + safe intent
-> extract product cards
-> verify extraction
-> summary/finish
```

The model should not need perfect JSON. It should not need to know internal primitive browser APIs. Sentinel should translate intent to the strongest safe skill.

### Required Changes

1. In the browser native intent mapper, when product/result cards exist, safe ambiguous intent must prefer `real_browser.extract_product_cards`.
2. Intent priority must be current-state aware:
   - finish with verified extraction -> `sentinel_loop.finish`
   - finish with extraction but no verification -> `real_browser.verify_extraction`
   - finish/extract/compare with cards -> `real_browser.extract_product_cards`
   - search only when no useful cards/extraction exist or the model explicitly asks a new query
   - open only at mission start or when no page/world model exists.
3. `BROWSER_INTENT_NO_SAFE_RECOMMENDATION` becomes a recoverable observation with the strongest safe skill fallback, not a terminal block.
4. DecisionContext must stop exposing raw browser primitive operation schema as the preferred model-facing schema.
5. Hidden/disabled browser refs become recovery observations with refreshed candidates; secret/password refs remain hard stops.
6. Loop guard deadline/repetition should not block if current context has visible product cards and extraction has not been attempted.
7. FinalGate should not close avoidable blocked truth until recovery paths are exhausted or a real hard boundary is hit.

### Required Tests

```text
test_visible_product_cards_and_ambiguous_intent_maps_to_extract
test_finish_with_cards_maps_to_extract_then_verify_then_finish
test_safe_ambiguous_intent_without_recommendation_recovers_not_blocks
test_raw_browser_primitives_not_primary_model_schema
test_hidden_or_disabled_ref_recovers_but_secret_ref_hard_stops
test_loop_guard_does_not_preempt_first_extraction_when_cards_visible
test_finalgate_not_written_for_recoverable_pre_extraction_miss
test_replay_no_reextract_no_reclick_no_retype
test_hard_boundaries_payment_login_contact_credentials_still_block
```

### Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
py -3.13 -m pytest tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
git diff --check
targeted scan for secrets/raw-provider/provider-native/fallback/AUTO
```

No provider or real browser run until fake/local proof passes.

## Second Implementation Pack

```text
POWER_FRICTION_CUT_PACK_2_PROVIDER_AND_SCHEMA_FRICTION_DEMOTION_V1
```

Goal:

```text
provider dialects and prose/schema misses map below the model into safe intents or recovery,
while unsafe control/material fields remain hard stops.
```

## Third Implementation Pack

```text
POWER_FRICTION_CUT_PACK_3_RECOVERY_BUDGET_AND_FINALGATE_ROLE_V1
```

Goal:

```text
FinalGate certifies truth after hard stop or recovery exhaustion,
not routine avoidable recoverable misses.
```

## Fourth Implementation Pack

```text
POWER_FRICTION_CUT_PACK_4_DORMANT_ORGANS_TO_SKILL_SPINE_V1
```

Goal:

```text
wire existing browser/planner/recovery/extraction organs into skill spine
without exposing organ internals to the model.
```

## Acceptance Rule

Each pack must:

```text
1. compare against the big audit;
2. implement one friction cut;
3. re-audit the touched path;
4. update the audit/control docs;
5. prove fake/local behavior;
6. run exactly one real attempt only when approved;
7. never mark product-proven from pytest alone.
```
