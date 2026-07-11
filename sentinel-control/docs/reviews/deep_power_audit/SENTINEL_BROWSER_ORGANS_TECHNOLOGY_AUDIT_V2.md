# SENTINEL_BROWSER_ORGANS_TECHNOLOGY_AUDIT_V2

Status: audit/design gate only.

Runtime changes: 0.
Provider calls: 0.
Real browser runs: 0.
External channel sends: 0.
Push: not performed.

## Executive Verdict

Sentinel's browser problem is not lack of browser work.

It is the opposite:

```text
browser power exists in many organs,
but it is dispatched across too many stacks,
and the product model loop still does not consume the full browser organism.
```

The user memory is correct: browser was heavily developed, CloakBrowser was
introduced, and Playwright was meant to stop being the product-leading live
backend.

Current truth:

```text
Cloak/session = intended product-leading live backend
BrowserSessionManager L5 = live session body
browser organs = strong but fragmented
Playwright = still present as compatibility/test and old direct path
product proof = improving, but browser is not yet a single monster organ
```

Decision:

```text
Do not build another small browser patch.
Do not blindly delete files yet.
Do product-kill Playwright first:
  no model-facing path
  no product proof
  no silent fallback
  compatibility-only quarantine
Then replace the product browser with a Browser Cortex on Cloak/session + CDP/BiDi/a11y/world-state.
```

## Repo Evidence

Browser-related inventory from the current checkout:

```text
total_browser_related_files = 209
operator_browser = 13
agent_organs_browser = 24
agent_browser_stack = 51
organs_browser_stack = 44
browser_tests = 77
playwright_refs = 149
cloak_refs = 157
devtools_cdp_bidi_refs = 336
```

Dependency evidence:

```text
sentinel-control/services/sentinel-core/pyproject.toml
  cloakbrowser>=0.3.31
```

Important source facts:

```text
sentinel/operator/real_browser_control_runtime.py
  CLOAK_BROWSER_BACKEND_ID = "cloak_browser"
  PLAYWRIGHT_REAL_BROWSER_BACKEND_ID = "playwright_real_browser_engine"
  BrowserSessionManagerRealBrowserEngine exists
  PlaywrightRealBrowserEngine still exists
  check_cloak_session_readiness exists
  backend mismatch validation exists

sentinel/agent/organs/browser_session_manager_l5_live.py
  BrowserSessionManagerL5Live exists
  BrowserSessionActionKind exists
  BrowserSessionContract exists
  special authority methods exist for submit, credential, upload, download, JS
  capture_screenshot defaults remain visible in this layer

sentinel/organs/browser/cloak_backend.py
  CloakBrowserSessionBackend exists
  PlaywrightSessionBackend exists
  Cloak launches a persistent browser context
  network and console metadata listeners exist

sentinel/operator/browser_world_model.py
  BrowserWorldModel exists
  ProductCandidateCard exists
  search_like_refs, link refs, blockers, cards exist
  product fields include price, MOQ, supplier/store, caveats

sentinel/operator/browser_model_native_control_loop.py
  natural browser intent mapper exists
  ActionEnvelope is internal runtime language
  extract_product_cards, verify_extraction, summarize_evidence, finish lanes exist
```

## What The Browser Contains Today

### 1. Product-facing operator browser spine

Files:

```text
sentinel/operator/real_browser_control_runtime.py
sentinel/operator/real_browser_control_models.py
sentinel/operator/real_browser_control_replay.py
sentinel/operator/browser_world_model.py
sentinel/operator/browser_decision_frame.py
sentinel/operator/browser_model_native_control_loop.py
sentinel/operator/browser_backend_selector.py
sentinel/operator/browser_action_candidates.py
```

Role:

```text
model/native intent
-> internal ActionEnvelope
-> real_browser.search / inspect_result / open_result / extract_product_cards / verify_extraction
-> receipt/replay
```

Current status:

```text
Good direction.
Still too thin as the full browser brain.
It should become the product skill facade, not the only browser intelligence.
```

### 2. Cloak/session live backend

Files:

```text
sentinel/agent/organs/browser_session_manager_l5_live.py
sentinel/organs/browser/cloak_backend.py
```

Role:

```text
persistent controlled browser session
profile directory management
CloakBrowser backend
Playwright compatibility backend
open / observe / click / type / fill / select / hover / wait
session receipts
```

Current status:

```text
This is the product-leading live browser backend.
It must be the default live backend when available.
```

Open gaps:

```text
first-class press_key is missing in BrowserSessionManager action enum
product browser still needs stronger session state graph
screenshot/profile defaults must be controlled by product policy
special authorities are present but not yet fluid mission-level powers
```

### 3. Canonical lower-level browser organs

Folder:

```text
sentinel/organs/browser/
```

Contains:

```text
accessibility_snapshot.py
cdp_ax.py
dom_snapshot.py
visual_observation.py
rendered_snapshot.py
navigation_l6.py
interaction_execution.py
interaction_dry_run.py
live_fetch.py
extraction.py
evidence_adapter.py
receipts.py
receipt_wrapper.py
final_gate.py
url_guard.py
power_governor.py
session_policy.py
reliability_profile.py
fingerprint_risk.py
misuse_classifier.py
download_quarantine.py
upload_authorized.py
form_submit.py
multitab_operator.py
cloak_backend.py
playwright_renderer.py
playwright_interaction_backend.py
```

Role:

```text
browser perception
browser actuation
browser policy
browser receipts
browser proof/finalgate
browser special authority primitives
```

Current status:

```text
Powerful but split.
The product browser should consume these organs as backend capabilities,
not expose them as separate product paths.
```

### 4. Agent-level browser organs

Folder:

```text
sentinel/agent/organs/browser_*.py
```

Key organs:

```text
browser_operator_agent_l4_l5_live.py
browser_session_manager_l5_live.py
browser_trajectory_planner_l5.py
browser_failure_recovery_engine_v1.py
browser_semantic_extraction_organ_v1.py
browser_devtools_machine_intelligence_v1.py
browser_devtools_input_parity_l5_l6.py
browser_devtools_backend_adapter_v1.py
browser_multi_step_task_orchestrator_v1.py
browser_visual_grounding_ocr_v1.py
browser_preparation_organ_v1.py
browser_readonly_organ_v1.py
browser_boundary_manager_l6_l7.py
browser_login_credential_session_broker_l6.py
browser_form_submit_special_authority_l6.py
browser_js_sandbox_special_authority_l6.py
browser_download_upload_quarantine_l6.py
browser_account_creation_special_authority_l7.py
browser_payment_spend_special_authority_l7.py
```

Role:

```text
live operation
trajectory planning
semantic extraction
DevTools/browser intelligence
failure recovery
visual grounding
special authorities
```

Current status:

```text
This is where a lot of the dormant monster power lives.
It must be wired into the product browser skill spine.
```

### 5. Agent browser cognitive stack

Folder:

```text
sentinel/agent/browser/
sentinel/agent/browser/neural/
```

Contains:

```text
cortex.py
perception_adapter.py
accessibility_snapshot.py
cdp_ax.py
dom_snapshot.py
operator_runtime.py
interaction_execution.py
extraction.py
observability.py
neural/blackboard.py
neural/perception.py
neural/planning.py
neural/recovery.py
neural/motor_proposal.py
neural/ledger.py
neural/squad.py
```

Role:

```text
browser cognition
perception fusion
planning
blackboard memory
recovery
multi-agent/browser squad concepts
```

Current status:

```text
Not product-spine dominant.
This stack should be mined into Browser Cortex, then old direct paths hidden.
```

## Playwright Decision

The user says: delete Playwright.

Engineering decision:

```text
Delete from product path now.
Do not physically delete code in the first cut.
Quarantine it as compatibility/test only.
Delete physically only after equivalent Cloak/session/CDP/BiDi tests replace it.
```

Reason:

```text
149 source references still exist.
Many tests and compatibility modules still import it.
A blind delete would break useful historical coverage and distract from product power.
```

Product rule:

```text
Playwright must not certify browser product power.
Playwright must not be selected silently.
Playwright must not be model-facing.
Playwright must not be fallback.
Playwright may exist only as explicit compatibility/test backend until migration is complete.
```

Target deletion path:

```text
1. PRODUCT BAN:
   block Playwright from all product browser attempts unless explicit compatibility flag.

2. TEST MIGRATION:
   migrate browser product tests to Cloak/session or fake Cloak session adapter.

3. PHYSICAL DELETION:
   remove PlaywrightRealBrowserEngine and old playwright_* modules only after tests prove parity.
```

## Browser Technology Direction

The future browser should not be a Playwright wrapper.

It should be:

```text
Browser Cortex
-> Cloak/session controlled browser
-> CDP / WebDriver BiDi protocol state
-> accessibility tree
-> DOM/role/action graph
-> network/storage/session metadata graph
-> visual fallback
-> skill-level actuation
-> receipts/replay/finalgate
```

### Why CDP/BiDi and accessibility tree matter

Current external references converge on the same architecture:

```text
accessibility tree for semantic UI roles/names/states
browser protocol events for network/console/page state
state compression instead of raw DOM dumps
agent-native browser environment with replayable observations/actions
```

Relevant references:

```text
Building Browser Agents: Architecture, Security, and Practical Evaluation
https://arxiv.org/html/2511.19477v1

web.dev - Build agent-friendly websites
https://web.dev/articles/ai-agent-site-ux

OpenClaw managed browser docs
https://docs.openclaw.ai/tools/browser

BrowserGym / AgentLab ecosystem
https://github.com/servicenow/browsergym
https://arxiv.org/abs/2412.05467

WebDriver BiDi W3C draft
https://www.w3.org/TR/webdriver-bidi/

Browser-use CDP migration note
https://browser-use.com/posts/playwright-to-cdp
```

## Browser State Philosophy

Sentinel should understand the browser deeply.

That includes:

```text
cookies exist / names / domains / expiry / httpOnly / secure / sameSite
storage keys exist / origin / size / volatility
network requests / status / host / resource type
console errors / hashed messages
auth/session state category
forms / fields / submit capability
iframes / tabs / history
accessibility tree roles / names / focus
visual layout and OCR fallback
product/search result cards
```

But:

```text
raw cookie values are bearer credentials.
raw session tokens are credentials.
raw passwords are credentials.
```

Product-power compromise:

```text
The runtime may use existing session state as the browser body.
The model should receive a powerful state graph, not raw bearer values.
The model can reason: logged in, cart exists, cookie domain, expiry, session volatility.
The model does not need the raw token string to operate the browser.
```

This is not security theater. It is the line between:

```text
model controls browser body
```

and:

```text
model receives transferable account credentials
```

The future monster should minimize friction, not leak credentials.

## What Must Be Cut Or Hidden

Immediate cuts:

```text
raw Playwright backend from product proof
raw locator primitives as primary model language
organ request fields from model-facing frame
direct browser organ product paths
separate browser finalgate/proof owners where product FinalGate can own them
schema-perfect model prison where natural task intent is enough
open/search loops after product cards or verified extraction already exist
terminal mission death on in-scope stale ref / hidden ref / locator miss / dynamic load
```

Must stay hard by default:

```text
payment / spend / checkout
credential value exposure
raw cookie/session token exposure
account mutation
external contact/send outside grant
upload/download outside authority
arbitrary JS outside explicit special authority
workspace escape
provider-native tools
fallback/AUTO
replay causing side effects
fake receipts or proof tampering
```

Important future stance:

```text
login/contact/payment are not banned forever.
They are special-authority mission powers.
They should become fluid only when a future mission grant explicitly gives them.
```

## Where We Are

Already good:

```text
Cloak backend exists.
BrowserSessionManager L5 defaults to Cloak.
ProductActionKernel browser product route exists.
Browser skill frame exists.
Model-native intent mapper exists.
Product-card extraction exists.
Verified extraction -> summary -> finish lane exists.
Backend mismatch blocking exists.
Replay no-react exists.
Receipts/finalgate culture is strong.
```

Still not monster:

```text
browser intelligence is split across 5+ stacks
Playwright still exists in direct runtime/export/test surfaces
world model does not yet fuse full CDP/BiDi/a11y/storage/session/network/visual state
BrowserSessionManager lacks first-class keyboard and some robust actuation primitives
profile/screenshot/session material policy needs product-level defaults
special authority organs exist but are not mission-level fluid powers
real browser proof remains too tied to individual attempts instead of one durable Browser Cortex
```

## Next Pack Recommendation

Do not start with Alibaba again.
Do not start with physical Playwright deletion.

Start with:

```text
BROWSER_CORTEX_PACK_0_PRODUCT_BROWSER_CUTOVER_LOCK_V1
```

Purpose:

```text
Declare one product browser architecture and classify every browser path:
PRODUCT_SPINE
HIDDEN_BACKEND
COMPATIBILITY_ONLY
DEPRECATED
SPECIAL_AUTHORITY_LOCKED
DELETE_AFTER_PARITY
```

Then:

```text
BROWSER_CORTEX_PACK_1_ENVIRONMENT_STATE_GRAPH_V1
```

Goal:

```text
Build BrowserEnvironmentState from Cloak/session + CDP/BiDi/a11y/world model:
page
tabs
frames
forms
actions
network
storage/cookie metadata
session state class
visual fallback refs
product/result cards
blockers
recommended skills
```

Then:

```text
BROWSER_CORTEX_PACK_2_CLOAK_ACTUATION_UPGRADE_V1
```

Goal:

```text
first-class search/type/fill/press/submit-search/wait/scroll/open-card
robust recovery
no Playwright product path
```

Then:

```text
BROWSER_CORTEX_PACK_3_REAL_BROWSER_PRODUCT_PROOF_V1
```

Goal:

```text
real model
-> Cloak/session
-> environment graph
-> search/extract/summary/finish
-> replay no-react
```

## Concrete Next Acceptance Tests

Pack 0:

```text
test_every_browser_path_classified
test_playwright_not_product_proof
test_cloak_session_manager_product_backend
test_special_authority_organs_locked_not_deleted
test_browser_cortex_consumes_existing_organs
```

Pack 1:

```text
test_browser_environment_state_includes_a11y_roles
test_browser_environment_state_includes_network_console_metadata
test_browser_environment_state_includes_cookie_storage_metadata_without_values
test_browser_environment_state_includes_product_cards
test_model_context_sees_state_graph_not_raw_dom_cookie_screenshot
```

Pack 2:

```text
test_cloak_search_uses_focus_fill_press_or_submit
test_cloak_press_key_first_class
test_cloak_scroll_and_wait_are_first_class
test_stale_hidden_timeout_recover_to_alternate_ref
test_playwright_absent_from_product_runtime
```

Pack 3:

```text
real provider/browser attempt:
provider decision calls >= 3
selected_backend = actual_backend = cloak_browser
environment state graph present
search actuated or cards extracted
relevant evidence summary
finish
replay no-react
```

## Final Recommendation

Canonical decision:

```text
SENTINEL_BROWSER_ORGANS_TECHNOLOGY_AUDIT_V2 = CREATED
NEXT = BROWSER_CORTEX_PACK_0_PRODUCT_BROWSER_CUTOVER_LOCK_V1
```

Do not make Sentinel generic.

Make browser the first full monster organ:

```text
model thinks in browser mission skills
Sentinel body sees the whole browser environment
Cloak/session actuates
CDP/BiDi/a11y/world-state explains the environment
DevTools/recovery/extraction organs become hidden power
receipts/replay/finalgate stay in background
hard stop only on real damage
```

