# Sentinel Power Cleanup Pack 2 - Recoverable Observation Dominates Loop Guard And FinalGate V1

Status: locally implemented
Implementation commit: `34867bf`
Provider calls: 0
Real browser runs: 0
Push: not performed

## Why This Pack Exists

Pack 1 made model-facing action truth executable or recoverable before dispatch. The next audit blocker was loop-level friction:

```text
recoverable in-scope miss with useful next actions
-> counted as no progress
-> loop_guard_no_progress / FinalGate blocked truth
```

That behavior is too weak for power. A recoverable miss that refreshes candidates or recommends a living skill is not mission failure; it is Sentinel doing its job below the model.

## Audit Rows Addressed

Primary rows:

- BF-CORE-001: recoverable runtime miss becomes mission death
- BF-CORE-006: repeated/guard logic can preempt recovery
- BF-CORE-008: budget/guard blocks before recovery path
- BF-PROOF-001: FinalGate certifies avoidable blocked truth before recovery exhaustion
- BF-BROWSER-008: search/open failure with cards/candidates should route to extraction/recovery

## What Changed

`LoopGuard.record_result()` now treats a recoverable action result as productive recovery when it carries at least one of:

```text
recommended_next_actions
recovery_observation.recommended_next_actions
recovery_observation.refreshed_candidate_refs
recovery_observation.recovery_actions
```

Empty recoveries still count as no progress and can still block. Hard stops are unchanged.

## Before / After

Before:

```text
recoverable search miss
recommended_next_actions = extract_product_cards
-> no receipt/evidence
-> no_progress += 1
-> loop_guard_no_progress can block
```

After:

```text
recoverable search miss
recommended_next_actions = extract_product_cards
-> productive recovery
-> no_progress resets
-> next model turn can use the live skill
```

## Files Changed

- `sentinel-control/services/sentinel-core/sentinel/operator/loop_guard.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_recoverable_observation_loop_guard.py`

## Hard Boundaries Preserved

This pack does not weaken any hard stop. It only changes no-progress accounting for typed recoverable observations with live recovery lanes.

Still hard-stopped:

```text
payment / checkout / spend
credential or secret access
login / account mutation
external send outside grant
cookies / session persistence
upload/download outside authority
arbitrary JS outside grant
workspace escape
destructive writes outside authority
provider-native tools
fallback/AUTO
replay side effects
```

## Validation

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_cleanup_recoverable_observation_loop_guard.py -q
```

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_cleanup_recoverable_observation_loop_guard.py tests/operator/test_power_reconnection_recoverable_execution_contract.py tests/operator/test_power_cleanup_model_facing_executable_skill_truth.py tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_pack6d_browser_skill_spine.py tests/operator/test_power_pack6_real_browser_bounded_web_control.py tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack1_model_led_task_loop.py -q
```

Passed:

```text
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
```

Passed:

```text
git diff --check
```

Targeted scan on touched Pack 2 files:

```text
rg -n "sk-[A-Za-z0-9]|Authorization:|Bearer [A-Za-z0-9]|raw_provider|raw_reasoning|reasoning_content|provider_native_tools|provider-native tools|fallback:AUTO|fallback:auto" sentinel-control/services/sentinel-core/sentinel/operator/loop_guard.py sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_recoverable_observation_loop_guard.py
```

No matches.

## Remaining Blockers

This pack fixes loop no-progress accounting for useful recoveries. It does not yet fully simplify:

1. FinalGate ownership across product surfaces.
2. Skill/backend/organ registry drift.
3. Read-only dominance in the product dispatcher.
4. Provider/schema/prose friction outside browser-native mapping.
5. Physical deletion/merge of duplicate browser proof owners.

## Recommended Next Pack

```text
POWER_CLEANUP_PACK_3_SKILL_BACKEND_ORGAN_REGISTRY_CONSOLIDATION_V1
```

Goal:

```text
ActionabilityRegistry + PowerSkillRegistry + OrganSpecRegistry
-> one source of skill/backend/proof/recovery truth
-> no decorative backend frame
-> no organ power stranded outside model-facing skills
```
