# SENTINEL_POWER_CORE_PACK1_ACTIONABILITY_AND_SKILL_REGISTRY_V1_REPORT

## Verdict

`POWER_CORE_PACK_1_ACTIONABILITY_AND_SKILL_REGISTRY_V1 = IMPLEMENTED_CANDIDATE`

This pack starts the global reconnection work from the deep power audit. It is not a browser-only patch.

## Why This Pack Exists

The deep power audit found that Sentinel already has many powerful organs, but the model-facing action plane is not reliably connected to runtime truth. A listed action can be an alias, a fragile internal primitive, a lab-only path, or a locked future surface. That makes the model steer through implementation details instead of durable skills.

Pack 1 introduces a central actionability/skill registry so Sentinel can separate:

- model-visible skills
- runtime-internal primitives
- missing-authority actions
- locked high-risk surfaces
- unregistered actions

## New Runtime Contract

The model-facing action list must converge toward this invariant:

```text
No action is shown to the model as a preferred skill unless Sentinel knows:
- the canonical skill/action name
- the runtime/executor action is available
- the capability is inside granted authority
- the proof requirement is known
- the recovery policy is known
```

The registry is data/control-plane only:

```text
data_not_authority = true
authority_effect = none
can_grant_authority = false
can_execute = false
```

It does not execute actions, grant authority, load credentials, call providers, or register RuntimeHost adapters.

## Implemented Files

- `sentinel/operator/actionability_registry.py`
- `sentinel/operator/decision_context.py`
- `tests/operator/test_power_core_actionability_registry.py`

## Initial Skill Coverage

Model-visible when available and granted:

- `sentinel_loop.finish`
- `read_only_research.list_directory`
- `read_only_research.search_text`
- `read_only_research.read_file_segment`
- `read_only_research.finish_exploration`
- `workspace_patch.apply_patch`
- `workspace_patch.run_bounded_check`
- `code_execution_sandbox.code_exec.run_profile`
- `code_execution_sandbox.code_exec.inspect_result`
- `bounded_channel.send_message`
- `browser_control.browser.observe`
- `browser_control.browser.assert_text`
- `real_browser_control.real_browser.open`
- `real_browser_control.real_browser.observe`
- `real_browser_control.real_browser.search`
- `real_browser_control.real_browser.inspect_result`
- `real_browser_control.real_browser.extract_product_cards`
- `real_browser_control.real_browser.extract_text`
- `real_browser_control.real_browser.assert_text`

Runtime-internal primitives remain mapped but hidden from the new model-visible skill plane:

- `browser_control.browser.click`
- `browser_control.browser.type_text`
- `browser_control.browser.select_option`
- `real_browser_control.real_browser.click`
- `real_browser_control.real_browser.type_text`
- `real_browser_control.real_browser.select_option`
- `real_browser_control.real_browser.press_key`
- `real_browser_control.real_browser.wait_for_text`
- `real_browser_control.real_browser.wait_for_load`
- `real_browser_control.real_browser.scroll`

Locked high-risk surfaces:

- `external_api`
- `desktop_control`
- `voice_runtime`
- `account_authority`
- `financial_authority`
- `payment_authority`

## DecisionContext Wiring

`DecisionContextCompiler` now includes:

- `skill_exposure_frame`
- `model_visible_next_recommended_actions`
- `model_visible_recommended_next_action`

The legacy fields remain for compatibility:

- `next_recommended_actions`
- `recommended_next_action`

This is intentional. Pack 1 introduces the new truth plane without breaking existing fake/model tests. Later packs should migrate model prompts and decision clients to prefer `model_visible_*` fields and then delete/deprecate brittle legacy recommendations.

## Power Gained

This pack does not add another organ. It starts removing confusion between organs.

It makes these failures detectable before they become real run blockers:

- alias is shown but canonical runtime action differs
- low-level browser primitive is available but should not be model-facing
- high-risk action appears in an available list but is locked
- action is unregistered and should not be suggested
- authority does not cover the capability

## What Remains

This pack does not yet replace the browser action path. It creates the global frame needed for:

```text
POWER_CORE_PACK_2_SKILL_FIRST_DECISION_CONTEXT_MIGRATION_V1
POWER_CORE_PACK_3_RECOVERABLE_FAILURE_LANE_UNIFICATION_V1
POWER_CORE_PACK_4_BROWSER_SKILL_SPINE_AND_ACTUATION_V1
```

## Validation

Targeted validation was run after implementation:

```text
py -3.13 -m pytest tests/operator/test_power_core_actionability_registry.py -q
py -3.13 -m pytest tests/operator/test_power_core_actionability_registry.py tests/operator/test_power_pack1_model_led_task_loop.py tests/operator/test_power_pack6c_actionability_recovery_contract.py -q
py -3.13 -m pytest tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m compileall sentinel/operator/actionability_registry.py sentinel/operator/decision_context.py
git diff --check
targeted secret/raw-provider/fallback/provider-native scan over touched diff
```

Result:

```text
4 passed
16 passed
50 passed
compileall passed
git diff --check passed
targeted scan passed
```

## No-New-Power Confirmation

```text
provider call = no
external network call = no
credential loading = no
RuntimeHost adapter registration changed = no
new browser/payment/desktop/shell/network execution power = no
fallback/AUTO introduced = no
provider-native tools introduced = no
push = no
```
