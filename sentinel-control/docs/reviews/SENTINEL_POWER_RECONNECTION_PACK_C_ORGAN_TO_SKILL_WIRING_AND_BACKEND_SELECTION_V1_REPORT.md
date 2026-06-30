# SENTINEL_POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1_REPORT

## Verdict

`POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1 = IMPLEMENTED_CANDIDATE`

Implementation commit:

```text
7bc8f6e
```

## Big Audit Mapping

Pack C maps to the deep-audit finding:

```text
Existing powerful organs are split from product skills and model-facing actionability.
```

The target failure pattern was:

```text
Sentinel has organ/runtime power
-> DecisionContext exposes action names without backend truth
-> model sees brittle primitive or disconnected action
-> runtime/organ mismatch appears only after execution
```

The corrected control-plane path is now:

```text
model-visible skill
-> PowerSkillRegistry binding
-> owner module / organ refs / backend candidates
-> product reachability and task-loop reachability truth
-> DecisionContext power_skill_backend_frame
```

This is a data-only wiring layer. It does not enable new dispatch power.

## Opening Audit

Before coding, Pack C checked:

| Question | Finding |
|---|---|
| Does `RuntimeHost` product-dispatch every skill? | No. Default adapter registry only contains `read_only_research_adapter`. |
| Does `ActionabilityRegistry` know more skills than the dispatcher? | Yes. It already names read-only, workspace patch, code execution, bounded channel, browser fixture, and real browser skills. |
| Does Sentinel contain stronger browser organs than the thin Pack 6 path? | Yes. `sentinel/organs/browser/cloak_backend.py` and many browser organ modules exist. |
| Is CloakBrowser currently the model-facing skill backend? | Not before Pack C. Browser backend ownership was not surfaced as a product skill binding. |
| Should Pack C register new RuntimeHost adapters? | No. That would be new execution power. Pack C only maps organs/backends to skills. |

## Runtime / Control-Plane Changes

Added:

```text
sentinel/operator/browser_backend_selector.py
sentinel/operator/power_skill_registry.py
tests/operator/test_power_reconnection_organ_skill_wiring.py
```

Updated:

```text
sentinel/operator/decision_context.py
sentinel/operator/unified_execution_dispatcher.py
```

## Skill-To-Organ Wiring

| Skill | Model-visible backend | Owner / organ path | Product reachable | Task-loop reachable |
|---|---|---|---:|---:|
| `read_only_research` | `read_only_research_skill` | `ReadOnlyProductionSpineSession` / `read_only_research_adapter` | yes | yes |
| `workspace_patch` | `workspace_patch_skill` | `sentinel.operator.workspace_patch_runtime` | no | yes |
| `code_execution_sandbox` | `code_execution_skill` | `sentinel.operator.code_execution_sandbox_runtime` | no | yes |
| `bounded_channel` | `bounded_channel_skill` | `sentinel.operator.connection_live_channel_action_runtime` | no | yes |
| `browser_control` | `browser_fixture_skill` | `sentinel.operator.browser_control_runtime` | no | yes |
| `real_browser_control` | `browser_skill` | `sentinel.operator.real_browser_control_runtime` + browser organs | no | yes |

High-risk surfaces stay locked:

```text
external_api
desktop_control
voice_runtime
account_authority
financial_authority
payment_authority
```

## Browser Backend Selection

Pack C makes the browser backend decision explicit and data-only:

```text
preferred backend = cloak_browser when sentinel.organs.browser.cloak_backend is available
model-visible backend = browser_skill
Playwright backend = compatibility/test backend requiring explicit compatibility selection
silent fallback to Playwright = no
```

This directly addresses the audit note that the model should not pilot Playwright primitives. It should pilot the browser skill; Sentinel owns backend selection beneath it.

## DecisionContext Change

`DecisionContextCompiler` now includes:

```text
power_skill_backend_frame
```

The frame is safe model context:

```text
skills_map_to_organs_and_backends_without_granting_authority
```

It contains skill/backend reachability truth and does not grant execution or authority.

## RuntimeHost Preservation

Pack C adds:

```text
UnifiedExecutionAdapterRegistry.adapter_ids()
```

This is inspection-only. It proved the default RuntimeHost adapter registry remains:

```text
read_only_research_adapter
```

No patch/code/browser/channel adapters were registered into RuntimeHost by Pack C.

## Re-Audit Of Correction

What this fixes:

```text
existing organs now have a central skill/backend map
DecisionContext can expose backend truth without leaking primitive engine details
CloakBrowser is the preferred live browser backend when available
Playwright is no longer silently treated as the default product browser backend
RuntimeHost remains unchanged in execution behavior
```

What this does not yet fix:

```text
model decision prompts still need Pack D to make skill/backend frames primary truth
browser skill spine actuation remains future Pack 6D after core reconnection
workspace patch/code/channel are still task-loop reachable rather than default product-dispatch adapters
no new live browser or external action was run
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_reconnection_organ_skill_wiring.py -q
py -3.13 -m pytest tests/operator/test_power_reconnection_organ_skill_wiring.py tests/operator/test_power_core_actionability_registry.py tests/operator/test_power_reconnection_recoverable_execution_contract.py tests/operator/test_power_pack1_model_led_task_loop.py tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
```

Results:

```text
5 passed
68 passed
```

Additional validation:

```text
py -3.13 -m compileall sentinel/operator/browser_backend_selector.py sentinel/operator/power_skill_registry.py sentinel/operator/actionability_registry.py sentinel/operator/decision_context.py sentinel/operator/unified_execution_dispatcher.py sentinel/operator/runtime_host.py
git diff --check
targeted secret/raw-provider/fallback/provider-native scan over touched Pack C files
```

Results:

```text
compileall passed
git diff --check passed
targeted scan passed; matches were benign negative/doctrine strings and redaction assertions only
```

## No-New-Power Confirmation

```text
provider call = no
external network call = no
credential loading = no
provider-native tools introduced = no
fallback/AUTO introduced = no
RuntimeHost adapter registration changed = no
browser/payment/desktop/shell/network expansion = no
push = no
```

## Recommended Next Pack

```text
POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1
```

Pack D must make `model_visible_*` and `power_skill_backend_frame` primary model decision truth instead of compatibility context.
