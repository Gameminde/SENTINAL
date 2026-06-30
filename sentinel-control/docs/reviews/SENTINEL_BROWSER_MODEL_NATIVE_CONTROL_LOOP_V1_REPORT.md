# SENTINEL_BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1_REPORT

## Verdict

```text
BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1 = IMPLEMENTED_CANDIDATE
provider_calls = 0
real_browser_runs = 0
push = not_performed
product_proven = false
```

This pack fixes the protocol cage exposed by 5E. It does not claim Alibaba product success yet.

## Audit Comparison

Compared against:

```text
SENTINEL_DEEP_POWER_AUDIT_V1_MASTER_REPORT.md
SENTINEL_GLOBAL_POWER_RECONNECTION_CORRECTION_PLAN_V1.md
SENTINEL_POWER_RECONNECTION_PACK_SEQUENCE_V1.md
SENTINEL_DEEP_POWER_SURGICAL_CUT_LIST_V1.md
SENTINEL_POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1_REPORT.md
SENTINEL_REAL_POWER_ATTEMPT_5E_MODEL_LED_ALIBABA_BROWSER_BACKEND_BRIDGE_AND_SEARCH_RECOVERY_V1_REPORT.md
```

Mapped root finding:

```text
model-visible action protocol is too strict/cage-like
metadata/reply or natural useful intent can collapse into empty_action_envelope
correction budget can exhaust even when browser product cards are visible
```

## Implementation

Added:

```text
sentinel/operator/browser_model_native_control_loop.py
```

Updated:

```text
sentinel/operator/model_led_task_loop.py
tests/operator/test_power_pack6d_browser_skill_spine.py
```

Control docs updated:

```text
docs/reviews/deep_power_audit/SENTINEL_DEEP_POWER_AUDIT_V1_MASTER_REPORT.md
docs/reviews/deep_power_audit/SENTINEL_GLOBAL_POWER_RECONNECTION_CORRECTION_PLAN_V1.md
docs/reviews/deep_power_audit/SENTINEL_POWER_RECONNECTION_PACK_SEQUENCE_V1.md
docs/reviews/deep_power_audit/SENTINEL_DEEP_POWER_SURGICAL_CUT_LIST_V1.md
```

## New Control Contract

The model may now think in task intentions:

```text
I will extract the visible product cards now.
Search for glasses under 5 euro.
Inspect this result.
Open the best result.
Verify the extracted cards.
I have enough evidence, summarize and finish.
```

Sentinel maps those intents into internal runtime actions:

```text
real_browser_control.real_browser.search
real_browser_control.real_browser.inspect_result
real_browser_control.real_browser.open_result
real_browser_control.real_browser.extract_product_cards
real_browser_control.real_browser.verify_extraction
sentinel_loop.finish
```

`ActionEnvelope` remains the internal runtime language. It is no longer the only model-facing language for browser control.

## Runtime Behavior

`ModelLedTaskLoop` now accepts decision-client outputs that are:

```text
ActionEnvelope
natural language string
semi-structured dict with reply/message/content/text/intent/action_intent
metadata/reply envelope
```

If the decision is not already an `ActionEnvelope`, the loop calls the browser native intent mapper and executes the mapped internal envelope.

Safe examples:

| Model intent | Internal action |
|---|---|
| `Search for glasses under 5 euro` | `real_browser.search` with bounded query |
| `I will extract the visible product cards now` | `real_browser.extract_product_cards` |
| `Verify the extracted cards` | `real_browser.verify_extraction` |
| `I have enough evidence, summarize and finish` after verified evidence | `sentinel_loop.finish` |

Ambiguous safe intent uses the primary recommendation from `skill_decision_frame`.

## Proof Preservation

Finish is not auto-granted by words alone.

```text
finish requires finish_available + verified browser extraction evidence
extraction without verification maps finish intent to verify_extraction
visible product cards plus extraction intent maps to extract_product_cards
```

This keeps:

```text
no fake extraction
no fake finish
no fake receipt
no bypass of receipts/replay
```

## Hard Stops Preserved

These natural intents block before an internal action is created:

```text
login
account creation
contact supplier
form submit / inquiry
checkout / payment / spend
credential or secret access
cookies / session use
upload / download
arbitrary browser JavaScript
external API mutation
desktop-wide control
provider-native tools
fallback/AUTO
```

## Raw Persistence Boundary

The mapper keeps only safe diagnostics:

```text
visible_content_hash
visible_content_char_count
content_source
top_level_key_names
primary recommended action
product card count
finish availability
mapped action name
```

It does not persist:

```text
raw provider output
raw reasoning
raw prompt
raw response
raw DOM
screenshots
cookies
session material
credentials
```

## Tests Added

```text
test_natural_intent_extract_visible_cards_maps_to_extract_product_cards
test_natural_intent_search_under_price_maps_to_search_with_query
test_natural_intent_verify_cards_maps_to_verify_extraction
test_natural_intent_finish_requires_verified_evidence
test_ambiguous_safe_intent_uses_primary_skill_recommendation
test_hard_boundary_intent_blocks_contact_supplier_payment_login_credentials
test_metadata_reply_with_natural_intent_is_parsed_without_raw_persistence
test_action_envelope_remains_internal_runtime_format
test_no_raw_provider_output_or_reasoning_persisted
test_replay_no_react_still_holds
```

The replay test uses raw natural/semi-structured decisions through `ModelLedTaskLoop`, not a pre-mapped fake client.

## Validation

Commands run:

```powershell
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
git diff --check
targeted scan for secrets/raw-provider/provider-native/fallback/AUTO
```

Observed results:

```text
6D browser skill tests = 34 passed
decision context skill frame tests = 8 passed
Pack 6 real browser bounded tests = 14 passed
compileall = passed
git diff --check = passed with CRLF warnings only
targeted scan = no unsafe hits; benign hard-stop documentation mentions of Authorization only
```

## Recommendation

Prepare, but do not run without user approval:

```text
REAL_POWER_ATTEMPT_5F_MODEL_NATIVE_BROWSER_CONTROL_LOOP_V1
```

5F should prove whether model-native browser intent fixes the 5E failure on the bounded Alibaba path.
