# C5_BROWSER_ORGAN_SOVEREIGN_BACKEND_CORRECTION

## Verdict

```text
C5_BROWSER_ORGAN_SOVEREIGN_BACKEND_CORRECTION = SOVEREIGN_BACKEND_SELECTED_AND_PHYSICAL_GATE_PASSED
canonical_backend = sentinel_chromium
cloak_reclassification = optional_external_backend
sovereign_tranche_provider_calls = 0
historical_C5B_provider_calls = 1
standalone_NVIDIA_smoke_calls = 1
browser_live_missions = 0
C5B_sentinel_chromium = NOT_RUN
FIXED_PROVEN = 0/65
```

This tranche does not declare C5B success. It replaces the mandatory browser
engine dependency with a Sentinel-owned backend contract and a sovereign
Chromium backend while preserving the existing Browser Organ governance,
affordances, receipts and historical Cloak evidence. The current proof is a
live physical browser gate, not a real-model Browser mission.

## Coupling Audit

Current source census for this tranche:

```text
source files mentioning Cloak/CLOAK/cloak = 20
source files mentioning Playwright/PLAYWRIGHT/playwright = 25
```

These are coupling locations, not deletion candidates. C5 sovereign only
changes the canonical product backend requirement; historical Cloak readiness
probes and explicit compatibility paths remain visible until parity gates allow
future retirement.

| File / symbol | Prior coupling | New disposition |
| --- | --- | --- |
| `sentinel.operator.browser_backend_selector.select_browser_backend` | Preferred `cloak_browser` when Cloak module existed. | Prefers `sentinel_chromium`; Cloak remains listed as `optional_external_backend`. |
| `sentinel.operator.real_browser_control_runtime.build_cloak_first_real_browser_engine_from_env` | Product-facing factory name and behavior implied Cloak-first live backend. | Preserved as explicit historical/optional Cloak builder only. |
| `sentinel.operator.real_browser_control_runtime.BrowserSessionManagerRealBrowserEngine` | Instance default backend id was `cloak_browser`; L5 manager default engine was `cloak`. | Instance default backend id is `sentinel_chromium`; L5 manager engine is configurable and defaults to `sentinel_chromium`. |
| `sentinel.operator.runtime_host._product_browser_engine` | RuntimeHost live product path called the Cloak-first factory. | RuntimeHost calls `build_canonical_real_browser_engine_from_env`. |
| `sentinel.operator.canonical_browser_readonly_adapter.PhysicalBrowserReadOnlyBackend` | Browser receipts selected Cloak by default. | Browser receipts select `sentinel_chromium` by default. |
| `sentinel.agent.organs.browser_session_manager_l5_live._backend_for_engine` | Supported `cloak` and `playwright_compat` only. | Adds `sentinel_chromium` as canonical engine. |
| `sentinel.organs.browser.cloak_backend.CloakBrowserSessionBackend` | Required live backend in product selection. | Preserved as optional external adapter and historical proof surface. |
| `sentinel.organs.browser.cloak_backend.PlaywrightSessionBackend` | Compatibility backend. | Remains internal mechanism reused by `sentinel_chromium`; Playwright objects do not cross the Sentinel backend contract. |
| `sentinel.operator.power_skill_registry._real_browser_binding` | Organ refs implied Cloak as the browser organ. | Exposes `SentinelChromium` and `CloakBrowserOptionalExternalAdapter`. |

## Minimal BrowserBackend Contract

The new Sentinel-owned contract is intentionally small. It covers only the
capabilities already consumed by the canonical read-only Browser route:

```text
browser_backend_id
session_manager_backend_kind
safe_url_origin_hash
bind_authority
bind_root_session_id
open
observe
close
```

This contract is not a model-facing primitive. The model still sees governed
Sentinel affordances such as observe, navigate, search, follow,
extract_evidence, verify, recover_session and finish. It never receives
Playwright objects, selectors, contexts, pages or Cloak objects.

## Sovereign Backend Shape

```text
SENTINEL Browser Organ
└── BrowserBackend contract
    ├── sentinel_chromium — canonical backend
    │   └── Chromium + Playwright as internal implementation details
    └── cloak_adapter — proprietary optional external backend
```

`sentinel_chromium` currently wraps the existing Playwright session machinery
behind `SentinelChromiumSessionBackend`. This is a skeleton for the sovereign
backend, not a claim that the C5B physical mission has passed.

## Local Proof

Validated in this tranche:

```text
selector_prefers_sentinel_chromium_when_cloak_available = true
selector_does_not_require_cloak_module = true
canonical_engine_factory_requires_no_cloak_env = true
canonical_readonly_receipts_use_sentinel_chromium = true
RuntimeHost_live_product_factory_uses_canonical_builder = true
historical_cloak_readiness_probe_path_preserved = true
post_commit_live_smoke_sentinel_chromium = PASSED
provider_calls = 0
browser_live_missions = 0
```

Historical live smoke, not a C5B gate:

```text
backend = sentinel_chromium
target_kind = public_read_only_origin
origin = example.com
open = PASSED
observe = PASSED
close = CALLED
Cloak dependency = false
provider_calls = 0
product_browser_mission = NOT_RUN
sovereign_5_of_5_gate = HISTORICAL_NOT_RUN
```

## Sovereign Physical Gate

Current C5 sovereign physical gate, provider-free:

```text
C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE = SOVEREIGN_PHYSICAL_GATE_PASSED
source_head_before_gate = 885be68d70cfd29da8348f5f179ba78b7128fcf2
actual_backend_id = sentinel_chromium
cloak_dependency = false
provider_calls = 0
product_browser_missions = 0
live_sentinel_chromium_cycles = 5
usable_context_page_observation = 5/5
close_completed = 5/5
owned_pid_tree_dead_before_next_cycle = 5/5
process_baseline_restored = 5/5
profile_material_persisted = false
terminal_receipt_unique = true
```

Boundary probes:

```text
same_origin_allowed = true
redirect_cross_origin_blocked = true
cross_origin_cleanup_completed = true
timeout_launch = true
timeout_context = true
timeout_navigation = true
physical_cancellation = true
process_tree_kill = true
late_publication_blocked = true
terminal_receipt_unique = true
```

Public route correction:

```text
canonical-product-run supports --enable-browser-readonly-physical
browser_backend_id = sentinel_chromium
cloak_dependency = false
capability_graph = ExecutableCapabilityGraph
effect_dispatch = ProductActionKernel
legacy ActionEnvelope exposed to model = false
```

Safe evidence bundle:

```text
sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE/sovereign_physical_gate.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE/origin_boundary.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE/boundary_timeout_and_cancellation.safe.json
```

Validation commands:

```text
python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_reconnection_organ_skill_wiring.py sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c5_physical_browser_boundary.py -q
python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -k "backend or readiness or cloak or playwright" -q
python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
```

Known validation debt, not fixed in this backend tranche:

```text
sentinel-control/services/sentinel-core/tests/operator/test_browser_search_actuation_open_world_feedback.py::test_no_search_control_with_visible_links_recommends_follow_or_inspect_not_search
= FIXED_LOCAL_DYNAMIC_AFFORDANCE_AVAILABILITY
```

That failure concerned dynamic model-visible affordance filtering after a page
without a search control. The fix prevents a stale recommended browser search
or workspace search label from being presented as an executable Browser search
affordance when the observed Browser state does not support it.

## Before C5B

The sovereign backend has now passed the required provider-free live physical
proof:

```text
5/5 sequential launches
context + page + observation usable
origin/redirect enforcement
timeout + cancellation + process-tree kill
cleanup and return to baseline before every cycle
profile_material_persisted = false
late publication blocked
cloak_dependency = false
```

The next authorized step is exactly one C5B run with NVIDIA MiniMax M3 on
`sentinel_chromium`. No Cloak repair is required unless the generic
BrowserBackend contract regresses.
