# Sentinel Deep Power Audit V1 - Surgical Cut List

Status: audit-only decision table
Doctrine: power first, receipts always
Provider calls: 0
Source runtime changes: 0

## Verdict

The previous deep audit is accepted as a map, but not as a deletion plan.

This document supplies the missing operational table:

```text
DELETE / MERGE / HIDE / KEEP / WIRE
```

The point is not to delete aggressively for theater. The point is to remove or hide everything that makes the model pilot internal APIs instead of useful skills.

## Decision Legend

| Decision | Meaning |
|---|---|
| `DELETE` | Remove when proven dead or harmful; no current required target in this pass |
| `MERGE` | Keep behavior, collapse duplicate ownership into one spine |
| `HIDE` | Keep internally, stop exposing as the preferred model-facing route |
| `KEEP` | Keep as-is for now |
| `KEEP_LOCKED` | Keep hard-blocked or special-authority only |
| `WIRE` | Existing power organ should be wired into the product skill path |

## Top-Level Surgical Cut Table

| Rank | Decision | Target | Current problem | Required action |
|---:|---|---|---|---|
| 1 | `MERGE` | `real_browser_control_runtime.py` + `browser_world_model.py` + `browser_decision_frame.py` + `browser_action_candidates.py` | Pack 6 browser path has perception and frames, but actuation is still low-level and Playwright-ref brittle | Merge under one `BrowserSkillSpine` where model sees search/inspect/extract, not locator operations |
| 2 | `WIRE` | `browser_session_manager_l5_live.py` + `organs/browser/cloak_backend.py` | CloakBrowser primary backend exists but recent real Alibaba path used `PlaywrightRealBrowserEngine` | Route real browser skill backend through session manager/Cloak backend where configured |
| 3 | `HIDE` | `real_browser.type_text`, `real_browser.click`, `real_browser.select_option` as primary DecisionContext recommendations | These are internal actuation primitives, not user/model-level browser skills | Keep internally; expose as fallback/debug only, not preferred research actions |
| 4 | `MERGE` | Browser proof/finalgate owners | Browser proof exists in both `agent/final_gate.py` and `organs/browser/final_gate.py` | Pick one browser proof owner; keep adapter layer only if needed |
| 5 | `MERGE` | `browser_control_runtime.py` fake/local browser and `real_browser_control_runtime.py` | Two model-facing browser capabilities split fake vs real | Keep fake backend as test backend under same skill spine |
| 6 | `HIDE` | Playwright renderer/interaction backend | Useful compatibility/test engine, but not product-leading browser power | Hide behind backend interface; do not expose as model-facing path |
| 7 | `WIRE` | `browser_failure_recovery_engine_v1.py`, `browser_trajectory_planner_l5.py`, `browser_semantic_extraction_organ_v1.py` | Strong browser organs exist but are not the main Pack 6 real-browser loop | Wire their ideas/cards into BrowserSkillSpine recovery and extraction |
| 8 | `MERGE` | `read_only_operator_spine.py` into generic evidence/read-only skill | Read-only route proved the spine but still dominates product architecture | Convert read-only into one skill in generic action loop, not the center of all power |
| 9 | `MERGE` | `organ_dispatch.py` and `runtime_execution.py` branch matrices | New organs require branch-heavy updates | Replace with organ/capability spec registry |
| 10 | `KEEP` | Receipts, replay, FinalGate, authority envelope | This is Sentinel's moat | Keep invisible and automatic |
| 11 | `KEEP_LOCKED` | Browser login, account creation, payment, JS sandbox, WebMCP L7 | Real damage surfaces | Keep special-authority only |
| 12 | `KEEP_LOCKED` | Credential vault material, cookies, session data, Authorization | Secret surfaces | Keep locked; hash/redact only |

## Browser 6D Cut Rules

Pack 6D must follow these rules:

```text
No new model-facing browser primitive unless an old fragile primitive is hidden or demoted.
No new browser report/proof layer unless one duplicate proof path is merged or deprecated.
No direct Playwright locator action may be the preferred model-facing action for web research.
No in-scope locator timeout may terminalize the mission before recovery is attempted.
```

Pack 6D implementation status:

```text
POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1 =
implemented candidate, not real-browser product-proven

Model-facing browser research now prefers search / inspect_result / open_result /
extract_product_cards / verify_extraction.

Raw browser primitives remain available as internal/fallback/debug operations, but
they are no longer the preferred model-facing path when the skill frame is present.

Search actuation now ranks search-like refs, tries alternates, and returns a
recoverable observation on in-scope locator/runtime misses instead of treating a
normal web actuation failure as immediate mission death.

Fake hard-page proof is green. Real Alibaba proof remains the next gated run.
```

Browser model-native control loop implementation status:

```text
BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1 =
implemented candidate, not real-provider/browser product-proven

The model no longer has to emit perfect internal ActionEnvelope JSON for every
browser step. Natural or semi-structured intent such as "extract the visible
product cards" or `metadata/reply` content is mapped into the canonical internal
browser skill envelope.

ActionEnvelope remains the runtime language, but it is no longer the cognitive
interface the model must always speak. Hard boundaries still block before
mapping; finish still requires verified evidence.
```

## What Must Stop Being Preferred Model-Facing API

These can stay internally, but should not be the main action vocabulary for Alibaba-style research:

```text
real_browser.type_text
real_browser.click
real_browser.select_option
real_browser.press_key
real_browser.wait_for_load
real_browser.wait_for_text
```

Preferred model-facing browser skills:

```text
natural/semi-structured browser intent
real_browser.search
real_browser.inspect_result
real_browser.open_result
real_browser.extract_product_cards
real_browser.verify_extraction
sentinel_loop.finish
```

## Cut/Merge Targets By File

| File | Decision | Reason |
|---|---|---|
| `sentinel/operator/real_browser_control_runtime.py` | `MERGE` | Current real Alibaba path; direct Playwright engine and locator fill/click leak too much implementation detail |
| `sentinel/operator/browser_world_model.py` | `MERGE` | Keep as perception builder, but output must feed executable skill actions |
| `sentinel/operator/browser_decision_frame.py` | `MERGE` | Keep compact frame, but it must be generated from actionability registry |
| `sentinel/operator/browser_action_candidates.py` | `MERGE` | Good alias/candidate logic, but should support skill-level intents |
| `sentinel/operator/browser_control_runtime.py` | `HIDE` | Useful fake/local backend; should sit under unified browser skill |
| `sentinel/organs/browser/cloak_backend.py` | `WIRE` | CloakBrowser primary adapter exists and should be backend option for real browser skill |
| `sentinel/agent/organs/browser_session_manager_l5_live.py` | `WIRE` | Persistent session and Cloak primary path should be part of real browser power spine |
| `sentinel/organs/browser/playwright_renderer.py` | `HIDE` | Compatibility/test renderer; not product-facing skill |
| `sentinel/organs/browser/playwright_interaction_backend.py` | `HIDE` | Compatibility/test interaction backend; not product-facing skill |
| `sentinel/agent/organs/browser_operator_agent_l4_l5_live.py` | `WIRE` | Existing live observe/act contract can inform skill runtime receipts |
| `sentinel/agent/organs/browser_failure_recovery_engine_v1.py` | `WIRE` | Recovery taxonomy should drive in-scope browser misses |
| `sentinel/agent/organs/browser_trajectory_planner_l5.py` | `WIRE` | Use for ranking action/search paths |
| `sentinel/agent/organs/browser_semantic_extraction_organ_v1.py` | `WIRE` | Use for product/search extraction cards |
| `sentinel/organs/browser/final_gate.py` | `MERGE` | Duplicate browser proof ownership with core FinalGate |
| `sentinel/agent/final_gate.py` | `MERGE` | Keep one browser proof source of truth |
| `sentinel/agent/organs/browser_login_credential_session_broker_l6.py` | `KEEP_LOCKED` | Credentialed login/session is real damage boundary |
| `sentinel/agent/organs/browser_payment_spend_special_authority_l7.py` | `KEEP_LOCKED` | Payment/spend hard stop |
| `sentinel/agent/organs/browser_account_creation_special_authority_l7.py` | `KEEP_LOCKED` | Account creation hard stop |
| `sentinel/agent/organs/browser_js_sandbox_special_authority_l6.py` | `KEEP_LOCKED` | JS execution requires special authority |
| `sentinel/agent/organs/browser_form_submit_special_authority_l6.py` | `KEEP_LOCKED` | Submit/contact/data-send boundary |

## Non-Browser Cut Targets

| File / area | Decision | Reason |
|---|---|---|
| `sentinel/operator/read_only_operator_spine.py` | `MERGE` | Convert from center of product to evidence/read-only skill under generic loop |
| `sentinel/operator/real_model_certification.py` | `MERGE` | Split into harness phases; do not let certification monolith drive product architecture |
| `sentinel/agent/runtime.py` | `MERGE` | Extract explicit phases from 1131-line `run` method |
| `sentinel/agent/organs/organ_dispatch.py` | `MERGE` | Replace branch matrix with capability spec registry |
| `sentinel/agent/organs/runtime_execution.py` | `MERGE` | Replace organ runtime branch matrix with declarative runtime specs |
| `sentinel/operator/action_kernel.py` | `WIRE` | Must classify hard stop vs recoverable observation instead of broad terminal errors |
| `sentinel/operator/model_led_task_loop.py` | `WIRE` | Must continue after recoverable in-scope action misses |
| `sentinel/operator/decision_context.py` | `MERGE` | Current giant context compiler should become skill-frame compiler composition |

## DELETE Candidates

No immediate physical `DELETE` is recommended in this pass.

Reason:

```text
The repo has many overlapping paths, but several are still useful as test compatibility, proof evidence, or bridge points.
The first real cut should hide/merge model-facing paths, not delete source before replacement is proven.
```

Physical deletion should come only after:

```text
1. BrowserSkillSpine passes fake hard-page tests.
2. Alibaba 5D succeeds or fails past the previous locator timeout.
3. Replay and receipts are validated on the replacement path.
4. Legacy paths have no product route or required tests.
```

## 6D Definition Of Done

```text
DecisionContext recommends browser skills, not raw Playwright-like primitive actions.
Browser skill exposes executable actionability candidates only.
Cloak/session backend preference is visible through the backend/actionability frame; live Cloak/session actuation remains tracked for the real 5D proof if the injected runtime backend cannot satisfy it.
Search skill handles focus/fill/type/enter/click/wait/recover internally.
Locator timeout becomes recoverable action observation.
Product extraction cards can satisfy web research proof.
Replay validates receipt schemas and hashes.
Hard stops remain for login/contact/payment/credential/origin escape.
```

## Blocker Audit V1 Cut Overlay

The blocker audit adds the first surgical cut overlay:

| Blocker row | Cut decision | Effect |
|---|---|---|
| `BF-BROWSER-001` | `REPLACE_WITH_SKILL_ROUTING` | Visible cards + safe ambiguous intent must route to extraction |
| `BF-BROWSER-002` | `REPLACE_WITH_SKILL_ROUTING` | Current-world extraction/finish outranks repeated open/search |
| `BF-CORE-013` | `MOVE_BELOW_MODEL` | Legacy recommended actions must not dominate skill frame |
| `BF-BROWSER-007` | `MOVE_BELOW_MODEL` | Raw browser primitives become internal/fallback/debug, not primary model path |
| `BF-CORE-001` | `CONVERT_TO_RECOVERY` | Normal in-scope loop misses stay recoverable until budgeted recovery exhaustion |
| `BF-PROOF-001` | `MOVE_BELOW_MODEL` | FinalGate certifies after recovery/hard-stop truth, not routine avoidable miss |

No physical source deletion is approved by this overlay yet. First cut model-facing friction and prove replacement behavior.
