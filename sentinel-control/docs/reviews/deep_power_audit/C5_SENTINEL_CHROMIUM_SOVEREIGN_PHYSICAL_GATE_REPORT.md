# C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE

## Verdict

```text
C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE = SOVEREIGN_PHYSICAL_GATE_PASSED
source_head_before_gate = 885be68d70cfd29da8348f5f179ba78b7128fcf2
actual_backend_id = sentinel_chromium
cloak_dependency = false
provider_calls = 0
product_browser_missions = 0
FIXED_PROVEN = 0/65
```

This is a live physical Browser backend proof only. It does not declare C5B,
multi-site Browser quality, or any finding closure.

## Sequential Physical Cycles

Five fully sequential cycles were executed through the canonical
`sentinel_chromium` backend:

```text
baseline
-> fresh owned launch
-> context
-> page
-> bounded read-only observation
-> explicit close
-> process-tree reap
-> profile cleanup
-> baseline restored
```

Observed gate results:

```text
launches = 5/5
usable context + page + observation = 5/5
close_completed = 5/5
owned PID tree dead before next cycle = 5/5
process baseline restored before next cycle = 5/5
profile_material_persisted = false
terminal_receipt_unique = true
```

The process census records only counts and safe hashes. It does not persist raw
paths, command lines, profile material, DOM, URLs, cookies, tokens or secrets.

## Boundary Probes

Additional provider-free probes proved the required sovereign physical
boundaries:

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

The timeout probes use an owned child process and owned child tree. The parent
rejects late publication after terminalization and records one terminal receipt.

## Public Route Correction

The public `canonical-product-run` surface now has an explicit sovereign
physical Browser option:

```text
--enable-browser-readonly-physical
--browser-allowed-origin <origin>
```

This route uses:

```text
RuntimeHost
-> RootMissionRuntime
-> ProductModelNativeDecisionClient or decision script
-> ExecutableCapabilityGraph
-> authority check
-> ProductActionKernel
-> PhysicalBrowserReadOnlyBackend
-> RealBrowserControlRuntime
-> sentinel_chromium
```

The model sees only governed Sentinel affordances. Playwright and Chromium
remain hidden internal implementation details behind `BrowserBackend`.

## Safe Artifacts

```text
sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE/sovereign_physical_gate.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE/origin_boundary.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE/boundary_timeout_and_cancellation.safe.json
```

## Validation

```text
python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_chromium_sovereign_physical_gate.py -q
= 7/7 passed

python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c5_physical_browser_boundary.py -q
= 6/6 passed

python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_browser_search_actuation_open_world_feedback.py -q
= 6/6 passed

python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
= 9/9 passed

python -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack2_skill_only_model_surface.py::test_runtimehost_entrypoint_exposes_simple_skills_as_primary_surface -q
= 1/1 passed
```

## Remaining Truth

```text
C5B real-model Browser mission = NOT_RUN
provider calls in this physical gate = 0
historical C5B provider calls = 1
standalone NVIDIA smoke calls = 1
Browser Organ completion = NOT_CLAIMED
FIXED_PROVEN = 0/65
```
