# Sentinel Organs And Browser Inventory V1

Status: audit-only
Generated data:

```text
sentinel_organs_inventory.csv
sentinel_organs_inventory_summary.json
```

## Executive Summary

The organ inventory confirms the user's memory: Sentinel has a large browser organ surface, and CloakBrowser was introduced as a primary backend for the L5 browser session manager.

But the recent Pack 6 real Alibaba route is not using that Cloak-first session manager. It is using `RealBrowserControlRuntime` with `PlaywrightRealBrowserEngine`.

Therefore the current browser power failure is not:

```text
we never built browser organs
```

It is:

```text
we built strong browser organs, including CloakBrowser session backend,
but the newest real browser model-led loop is connected to a thinner Playwright runtime.
```

## Organ Counts

| Metric | Count |
|---|---:|
| Organ/runtime files inventoried | 167 |
| Browser-related files | 89 |
| `sentinel/organs/browser` files | 44 |
| `sentinel/agent/organs` files | 36 |
| Operator power runtime files included | 22 |
| Desktop organ files | 15 |
| Channel organ files | 9 |
| Credential organ files | 8 |
| External API organ files | 8 |

## Browser Surface Layers

| Layer | Files | Role |
|---|---:|---|
| `sentinel/organs/browser` | 44 | Canonical lower-level browser organs, contracts, receipts, L6 navigation, Cloak backend, Playwright compatibility |
| `sentinel/agent/organs/browser_*` | 25+ | Higher-level browser packs: preparation, readonly, extraction, session manager, trajectory, recovery, devtools, special authority |
| `sentinel/operator/browser_*` | 6 | Power Pack 4/6 browser runtimes, world model, decision frame, fake browser |
| `sentinel/operator/real_browser_*` | 3 | Recent real browser model-led loop runtime, replay, models |

## CloakBrowser Truth

Evidence:

| Fact | Evidence |
|---|---|
| Optional dependency exists | `sentinel-control/services/sentinel-core/pyproject.toml` includes `cloakbrowser>=0.3.31` |
| Cloak backend exists | `sentinel/organs/browser/cloak_backend.py` defines `CloakBrowserSessionBackend` |
| Playwright compatibility backend exists | same file defines `PlaywrightSessionBackend` |
| Session manager default is Cloak | `browser_session_manager_l5_live.py` has `engine: str = "cloak"` |
| CLI default is Cloak | `sentinel cli` browser session demo uses `--engine`, default `cloak`, choices `cloak/playwright` |
| Report says no silent fallback | `BROWSER_SESSION_MANAGER_L5_LIVE_REPORT.md` says Playwright is explicit compatibility only |

Conclusion:

```text
CloakBrowser is real in the repo and is the intended primary backend for BrowserSessionManagerL5Live.
```

## Playwright Still Present

Evidence:

| File | Usage |
|---|---|
| `sentinel/operator/real_browser_control_runtime.py` | Defines `PlaywrightRealBrowserEngine` and builds it from env |
| `sentinel/operator/real_browser_control_runtime.py` | Uses `sync_playwright`, `page.locator(...).fill`, `click`, `select_option`, `press` |
| `sentinel/organs/browser/playwright_renderer.py` | Compatibility renderer |
| `sentinel/organs/browser/playwright_interaction_backend.py` | Compatibility interaction backend |
| `sentinel/organs/browser/cloak_backend.py` | Contains Playwright compatibility backend |

Conclusion:

```text
Playwright was not fully replaced.
It remains as compatibility/test backend, and also remains the active backend in the newer real_browser_control_runtime path.
```

This is the browser connection bug:

```text
CloakBrowser primary session organ exists,
but Alibaba/Pack 6 real_browser route uses PlaywrightRealBrowserEngine directly.
```

## Browser Organ Inventory By Purpose

### Core Browser Backend And Session

| File | Decision | Purpose |
|---|---|---|
| `sentinel/organs/browser/cloak_backend.py` | `WIRE` | CloakBrowser primary backend plus Playwright compatibility backend |
| `sentinel/agent/organs/browser_session_manager_l5_live.py` | `WIRE` | Persistent live browser session workflow, default Cloak engine |
| `sentinel/agent/organs/browser_operator_agent_l4_l5_live.py` | `WIRE` | Governed live observe/act wrapper |
| `sentinel/organs/browser/playwright_renderer.py` | `HIDE` | Compatibility/test renderer |
| `sentinel/organs/browser/playwright_interaction_backend.py` | `HIDE` | Compatibility/test interaction backend |

### Perception, World Model, Decision Frame

| File | Decision | Purpose |
|---|---|---|
| `sentinel/operator/browser_world_model.py` | `MERGE` | Builds browser world model/cards for model context |
| `sentinel/operator/browser_decision_frame.py` | `MERGE` | Compiles compact model decision frame |
| `sentinel/operator/browser_action_candidates.py` | `MERGE` | Parses/action candidate helpers |
| `sentinel/agent/organs/browser_preparation_organ_v1.py` | `WIRE` | Browser preparation pipeline |
| `sentinel/agent/organs/browser_semantic_extraction_organ_v1.py` | `WIRE` | Semantic extraction organ |
| `sentinel/agent/organs/browser_visual_grounding_ocr_v1.py` | `KEEP` | Visual/OCR grounding |
| `sentinel/organs/browser/accessibility_snapshot.py` | `WIRE` | Role/a11y snapshot support |
| `sentinel/organs/browser/cdp_ax.py` | `WIRE` | CDP accessibility snapshot support |

### Actuation And Navigation

| File | Decision | Purpose |
|---|---|---|
| `sentinel/operator/real_browser_control_runtime.py` | `MERGE` | Current real-browser action runtime; needs to become skill spine or delegate to it |
| `sentinel/operator/browser_control_runtime.py` | `HIDE` | Fake/local browser runtime for tests |
| `sentinel/organs/browser/navigation_l6.py` | `WIRE` | Rich L6 navigation/action candidate/ref/policy models |
| `sentinel/organs/browser/interaction_execution.py` | `WIRE` | Lower-level interaction executor |
| `sentinel/organs/browser/interaction_dry_run.py` | `KEEP` | Preview/dry-run support |
| `sentinel/organs/browser/controlled_runner.py` | `MERGE` | Large controlled runner, should inform skill runtime |
| `sentinel/agent/organs/browser_trajectory_planner_l5.py` | `WIRE` | Candidate trajectory planner |
| `sentinel/agent/organs/browser_failure_recovery_engine_v1.py` | `WIRE` | Recovery engine |
| `sentinel/agent/organs/browser_multi_step_task_orchestrator_v1.py` | `WIRE` | Multi-step browser orchestration |

### Evidence, Receipts, Replay, FinalGate

| File | Decision | Purpose |
|---|---|---|
| `sentinel/organs/browser/receipts.py` | `KEEP` | Browser receipt primitives |
| `sentinel/organs/browser/receipt_wrapper.py` | `KEEP` | Receipt wrapping/adaptation |
| `sentinel/organs/browser/evidence_adapter.py` | `MERGE` | Evidence collection, currently large |
| `sentinel/organs/browser/final_gate.py` | `MERGE` | Browser proof logic; duplicate owner candidate |
| `sentinel/operator/real_browser_control_replay.py` | `KEEP` | Real browser replay view |
| `sentinel/operator/browser_world_model_replay.py` | `KEEP` | World model replay |
| `sentinel/operator/browser_control_replay.py` | `KEEP` | Fake/local browser replay |
| `sentinel/agent/organs/browser_observability_replay_studio_v1.py` | `KEEP` | Replay/observability studio |

### Browser Risk, Policy, Guard

| File | Decision | Purpose |
|---|---|---|
| `sentinel/organs/browser/url_guard.py` | `KEEP` | URL/origin guard |
| `sentinel/organs/browser/power_governor.py` | `KEEP` | Browser power classification |
| `sentinel/organs/browser/misuse_classifier.py` | `KEEP` | Misuse classification |
| `sentinel/organs/browser/compliance_gate.py` | `KEEP` | Compliance/policy gate |
| `sentinel/organs/browser/fingerprint_risk.py` | `KEEP` | Fingerprint risk profile |
| `sentinel/organs/browser/session_policy.py` | `KEEP` | Session continuity policy |
| `sentinel/organs/browser/reliability_profile.py` | `KEEP` | Reliability profile |
| `sentinel/agent/organs/browser_boundary_manager_l6_l7.py` | `KEEP_LOCKED` | High-risk boundary manager |

### Locked Special Authorities

| File | Decision | Reason |
|---|---|---|
| `browser_login_credential_session_broker_l6.py` | `KEEP_LOCKED` | Credentialed login/session |
| `browser_form_submit_special_authority_l6.py` | `KEEP_LOCKED` | Submit/contact/data-send boundary |
| `browser_js_sandbox_special_authority_l6.py` | `KEEP_LOCKED` | Arbitrary JS |
| `browser_download_upload_quarantine_l6.py` | `KEEP_LOCKED` | Upload/download |
| `browser_account_creation_special_authority_l7.py` | `KEEP_LOCKED` | Account creation |
| `browser_payment_spend_special_authority_l7.py` | `KEEP_LOCKED` | Payment/spend |
| `browser_controlled_extension_webmcp_bridge_l7.py` | `KEEP_LOCKED` | Extension/WebMCP bridge |

## Browser Root Problem

There are two browser worlds:

### Cloak-first organ world

```text
browser-session-demo
-> BrowserSessionManagerL5Live
-> CloakBrowserSessionBackend by default
-> PlaywrightSessionBackend only if explicitly selected
-> persistent session/profile
-> open/type/observe/close receipts
```

### Pack 6 real-browser world

```text
model-led task loop
-> real_browser_control_runtime
-> PlaywrightRealBrowserEngine
-> page.locator(selector).fill/click/press
-> brittle nth selectors
-> timeout can block mission
```

The fix is not to delete Cloak or Playwright. The fix is:

```text
Make BrowserSkillSpine choose backend below the skill boundary.
Cloak/session manager should be a first-class backend for live real web.
Playwright should remain compatibility/test/fallback only when explicitly selected.
```

## Practical Next Cut

For Pack 6D:

```text
WIRE:
  browser_session_manager_l5_live.py
  organs/browser/cloak_backend.py
  browser_failure_recovery_engine_v1.py
  browser_trajectory_planner_l5.py
  browser_semantic_extraction_organ_v1.py

MERGE:
  real_browser_control_runtime.py
  browser_world_model.py
  browser_decision_frame.py
  browser_action_candidates.py

HIDE:
  PlaywrightRealBrowserEngine from model-facing path
  real_browser.type_text/click/select as preferred model actions
```

## Pack 6D Implementation Status

Pack 6D moved the model-facing browser route toward the inventory target, but it does not close the entire browser organ split.

Implemented:

```text
DecisionContext and BrowserDecisionFrame now prefer skill-level browser actions.
ActionabilityRegistry exposes search / inspect_result / open_result / extract_product_cards / verify_extraction.
RealBrowserControlRuntime owns robust search actuation behind real_browser.search.
In-scope search actuation failures become recoverable observations with refreshed world/actionability context.
Product extraction cards and verify_extraction receipts can satisfy browser research proof in fake/local tests.
```

Still tracked:

```text
Playwright remains a compatibility/test backend, not the product-leading browser backend.
5K proved the live bounded Alibaba path can select and execute through Cloak/session without silent Playwright fallback.
The next product gap is not backend selection; it is relevance-quality, search-result grounding, and automatic profile-material cleanup on the Cloak path.
Browser proof/finalgate ownership remains a merge candidate after the vertical proof.
```

Latest update:

```text
FIX_CLOAK_BROWSER_RELEVANT_SEARCH_RESULT_QUALITY_AND_PROFILE_CLEANUP_V1
implemented candidate, not real-provider/browser product-proven

BrowserWorldModel now strips search-result intro/query text before extracting
cards, scores multilingual eyewear terms as relevant to glasses missions, and
keeps generic Alibaba scaffolding from becoming the primary product title.
DecisionContext and skill frames now demote repeated search after a search
receipt exists without relevant evidence.
BrowserSessionManagerRealBrowserEngine exposes close/cleanup so local Cloak
profile material is removed by the runtime path.
```

## Final Diagnosis

The browser work was not wasted.

The opposite: Sentinel has enough browser organs that the current failure is a wiring failure.

The next pack should stop building another browser layer and instead create one browser skill spine that consumes the existing organs.
