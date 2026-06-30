# SENTINEL_POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1_REPORT

## Verdict

`POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1 = IMPLEMENTED_CANDIDATE`

Implementation commit:

```text
pending_followup_ledger
```

## Big Audit Mapping

Pack D maps to the deep-audit finding:

```text
DecisionContext exposes primitive/static actions, not always live executable skills.
```

Pack A created actionability truth. Pack C created skill/backend truth. Pack D makes those frames the primary model-facing decision truth.

Corrected path:

```text
mission progress
-> skill_exposure_frame
-> power_skill_backend_frame
-> skill_decision_frame
-> primary_model_recommended_next_action
```

Legacy primitive recommendations remain present for compatibility, but they are now named as legacy:

```text
legacy_recommended_next_action
legacy_next_recommended_actions
```

## Opening Audit

Pack D compared against:

```text
SENTINEL_DEEP_POWER_AUDIT_V1_MASTER_REPORT.md
SENTINEL_GLOBAL_POWER_RECONNECTION_CORRECTION_PLAN_V1.md
SENTINEL_POWER_RECONNECTION_PACK_SEQUENCE_V1.md
SENTINEL_DEEP_POWER_SURGICAL_CUT_LIST_V1.md
SENTINEL_ORGANS_AND_BROWSER_INVENTORY_V1.md
```

Findings:

| Audit question | Finding |
|---|---|
| Does Pack A expose `model_visible_*`? | Yes. |
| Does Pack C expose backend truth? | Yes. |
| Did legacy primitive recommendations still exist? | Yes, `recommended_next_action` / `next_recommended_actions` still existed for compatibility. |
| Did browser guidance still prefer low-level primitives in some states? | Yes, legacy real-browser guidance could recommend `type_text`, `click`, and `select_option`. |
| Should Pack D remove compatibility fields? | No. Hide/demote them as legacy first, to avoid breaking existing tests and loops. |

## Runtime Changes

Added:

```text
sentinel/operator/skill_decision_frame.py
tests/operator/test_power_reconnection_decision_context_skill_frames.py
```

Updated:

```text
sentinel/operator/decision_context.py
```

## New Primary Model Contract

`DecisionContextCompiler` now emits:

```text
decision_context_primary_truth = skill_decision_frame
skill_decision_frame
primary_model_next_recommended_actions
primary_model_recommended_next_action
legacy_recommended_next_action
legacy_next_recommended_actions
```

The `skill_decision_frame` includes:

```text
mission_objective
current_progress_state
available_skills
executable_skills
skill_frames
recommended_next_actions
recent_receipts
recoverable_observations
proof_requirements
finish_available
hard_stop_boundaries
budget_remaining
completion_requirements
```

## Skill Frames

| Skill | Primary proof / behavior |
|---|---|
| `read_only_research` | Evidence/read-only observation receipt; one evidence skill, not architecture center |
| `workspace_patch` | Patch receipt plus post-patch verification receipt |
| `code_execution_sandbox` | Sandbox execution receipt plus bounded check or verification receipt |
| `bounded_channel` | Delivery receipt, no-resend replay proof, then finish |
| `browser_control` | Browser fixture observation/action proof |
| `real_browser_control` | Browser action or extraction receipt; search/inspect/extract preferred over raw actuation primitives |
| `sentinel_loop` | Finish only after objective proof |

## Browser Primitive Demotion

Legacy browser guidance may still list:

```text
real_browser_control.real_browser.type_text
real_browser_control.real_browser.click
real_browser_control.real_browser.select_option
```

But Pack D prevents those from dominating the primary model route. The `skill_decision_frame` prefers:

```text
real_browser_control.real_browser.search
real_browser_control.real_browser.inspect_result
real_browser_control.real_browser.extract_product_cards
real_browser_control.real_browser.extract_text
real_browser_control.real_browser.assert_text
```

This follows the surgical cut list: low-level primitives remain internal/fallback, not preferred model-facing browser research actions.

## Recoverable Observation Visibility

Recoverable observations now flow into `skill_decision_frame.recoverable_observations`, including:

```text
failure_class
failure_code
blocked_reason
recommended_next_actions
recovery_observation
```

The primary recommendations prefer recoverable next actions when they are model-visible and in scope.

## Re-Audit Of Correction

What this fixes:

```text
model-visible actionability and backend truth are no longer decorative context only
primary model recommendation path now comes from skill_decision_frame
legacy primitive recommendations are explicitly labeled legacy
browser research primary path prefers search/inspect/extract over type/click/select
workspace/code/channel frames expose proof requirements directly
recoverable observations are visible to the next model turn
```

What this does not yet fix:

```text
DecisionContext still contains older compatibility fields and pack-specific helper branches
ModelLedTaskLoop/provider prompt templates may still require further cleanup if they ignore primary_model_* fields
Pack E remains required to cut/merge branch-heavy organ matrices and reduce context compiler size
6D browser skill spine remains future work after root reconnection packs
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_pack1_model_led_task_loop.py tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m pytest tests/operator/test_power_core_actionability_registry.py tests/operator/test_power_reconnection_recoverable_execution_contract.py tests/operator/test_power_reconnection_organ_skill_wiring.py tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
```

Results:

```text
8 passed
65 passed
19 passed
```

Additional validation:

```text
py -3.13 -m pytest tests/operator/test_power_core_actionability_registry.py tests/operator/test_power_reconnection_recoverable_execution_contract.py tests/operator/test_power_reconnection_organ_skill_wiring.py tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
py -3.13 -m compileall sentinel/operator/skill_decision_frame.py sentinel/operator/decision_context.py sentinel/operator/actionability_registry.py sentinel/operator/power_skill_registry.py sentinel/operator/model_led_task_loop.py
git diff --check
targeted secret/raw-provider/fallback/provider-native scan over touched Pack D files
```

Results:

```text
19 passed
compileall passed
git diff --check passed
targeted scan passed; matches were benign negative/doctrine strings only
```

## No-New-Power Confirmation

```text
provider call = no
real browser run = no
external network call = no
credential loading = no
provider-native tools introduced = no
fallback/AUTO introduced = no
RuntimeHost adapter registration changed = no
new live power = no
push = no
```

## Recommended Next Pack

```text
POWER_RECONNECTION_PACK_E_FIRST_SIMPLIFICATION_CUT_ORGAN_BRANCH_MATRIX_V1
```

Pack E should start removing/merging branch-heavy internals now that the model-facing path has actionability, recoverable execution, backend ownership, and primary skill frames.
