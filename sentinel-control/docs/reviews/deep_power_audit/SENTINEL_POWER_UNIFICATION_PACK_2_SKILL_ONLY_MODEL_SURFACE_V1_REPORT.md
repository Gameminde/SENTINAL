# Sentinel Power Unification Pack 2: Skill-Only Model Surface V1

Status:

```text
POWER_UNIFICATION_PACK_2_SKILL_ONLY_MODEL_SURFACE_V1 = IMPLEMENTED_CANDIDATE
product_proven = focused local context/product-loop proof only
provider_call = no
real_browser_run = no
real_external_channel_call = no
push = not performed
```

## Purpose

Pack 2 cuts the next model-facing friction layer from the monster-runtime
plan:

```text
model sees simple mission skills
ActionEnvelope stays internal
organs/backends/runtime fields stay below the model-facing surface
legacy canonical action fields remain compatibility only
```

The model-facing vocabulary is now:

```text
read
patch
run_check
browse_search
extract
send_message
spawn_worker
remember
finish
```

Only currently executable/available skills appear. Future skills such as
`spawn_worker` and `remember` remain absent until their product route exists.

## Files Changed

```text
sentinel/operator/model_skill_surface.py
sentinel/operator/skill_decision_frame.py
sentinel/operator/decision_context.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/runtime_host.py
tests/operator/test_power_unification_pack2_skill_only_model_surface.py
```

## Behavior Before / After

Before:

```text
DecisionContext.primary_model_recommended_next_action = workspace_patch.apply_patch | real_browser_control.real_browser.search | ...
RuntimeHost.product_task_loop_entrypoint_frame().model_visible_available_actions = canonical ActionEnvelope action names
Product task-loop context model_visible_available_actions = canonical ActionEnvelope action names
```

After:

```text
primary_model_surface = model_visible_skills
primary_model_language = simple_mission_skills
action_envelope_language = internal_runtime_only
model_visible_skills = read / patch / run_check / browse_search / extract / send_message / finish
runtime_internal_action_map = simple skill -> canonical internal action
```

Compatibility fields such as `model_visible_available_actions`,
`primary_model_recommended_next_action`, and `recommended_next_action` remain
present so existing tests and runtime extractors do not break. They are no
longer the declared primary model surface.

## Runtime Mapping

Examples:

| Simple skill | Internal canonical action examples |
|---|---|
| `read` | `read_only_research.search_text`, `read_only_research.read_file_segment` |
| `patch` | `workspace_patch.apply_patch` |
| `run_check` | `workspace_patch.run_bounded_check`, `code_execution_sandbox.code_exec.run_profile` |
| `browse_search` | `real_browser_control.real_browser.search`, `real_browser_control.real_browser.inspect_result` |
| `extract` | `real_browser_control.real_browser.extract_product_cards`, `real_browser_control.real_browser.verify_extraction` |
| `send_message` | `bounded_channel.send_message` |
| `finish` | `sentinel_loop.summarize_evidence`, `sentinel_loop.finish` |

Raw browser primitives like `type_text`, `click`, `select_option`, and
Playwright/Cloak locator details remain hidden/internal when present.

## Hard Boundaries Preserved

Pack 2 does not enable:

```text
payment / checkout / spend
credential or secret access
login / account mutation
contact supplier or external send outside grant
destructive write outside authority
workspace escape
cookies/session/raw DOM/raw screenshot persistence
provider-native tools
fallback/AUTO
replay causing real side effects
proof tampering / fake receipt
```

High-risk or unregistered actions are not emitted as simple model skills. They
are tracked as hidden/locked with hard-stop boundary metadata.

## Tests Run

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack2_skill_only_model_surface.py -q
5 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
9 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q
12 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
3 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py -q
14 passed

py -3.13 -m compileall sentinel-control/services/sentinel-core/sentinel/operator/model_skill_surface.py sentinel-control/services/sentinel-core/sentinel/operator/skill_decision_frame.py sentinel-control/services/sentinel-core/sentinel/operator/decision_context.py sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
passed

git diff --check
passed

targeted scan for raw provider / reasoning / credential / session / cookie / DOM / provider-native / fallback markers
benign hits only: hard-boundary marker strings and test assertions
```

## Monster Runtime Scorecard Update

| Metric | Pack 2 update |
|---|---|
| `product_spine_coverage` | Unchanged; no new execution path |
| `direct_bypass_count` | Unchanged from Pack 0/1 |
| `dual_path_count` | Unchanged |
| `model_facing_primitive_leakage_count` | Reduced: DecisionContext, RuntimeHost product entrypoint, and product task-loop context now declare simple skills as primary model surface |
| `recoverable_failure_continuation_coverage` | Unchanged |
| `real_provider_product_loop_proof` | Unchanged; no provider call |
| `replay_parity_coverage` | Preserved through Pack 9/10 regressions |
| `browser_product_backend_coverage` | Unchanged; browser product backend remains future Pack 4 in unification sequence |
| `agent_workspace_readiness` | Unchanged |
| `multi_worker_orchestration_readiness` | Unchanged |
| `signed_mission_artifact_readiness` | Unchanged |

## Remaining Blockers

```text
ActionEnvelope decisions are still used by fake/local fixture clients.
Natural model intent mapping exists for browser-specific paths but is not yet generalized across all product skills.
BYPASS-MUTATION-001 remains open.
Browser L5/L6 product backend remains open.
Agent workspace runtime remains open.
Multi-worker orchestration remains open.
Signed mission artifact export/replay verifier remains open.
```

## Recommended Next Action

Proceed to:

```text
POWER_UNIFICATION_PACK_3_AGENT_WORKSPACE_RUNTIME_V1
```

Carry forward:

```text
simple model skills are now the declared primary surface, but future real-provider product loops must prove that provider prompts/decision clients consume this surface rather than compatibility canonical-action fields.
```
