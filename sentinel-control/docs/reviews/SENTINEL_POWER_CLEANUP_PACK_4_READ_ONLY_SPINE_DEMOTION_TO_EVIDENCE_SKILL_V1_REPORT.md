# SENTINEL POWER CLEANUP PACK 4 READ ONLY SPINE DEMOTION TO EVIDENCE SKILL V1 REPORT

## Verdict

```text
POWER_CLEANUP_PACK_4_READ_ONLY_SPINE_DEMOTION_TO_EVIDENCE_SKILL_V1 = LOCALLY_IMPLEMENTED
implementation_commit = 7f7ac92
product_proven = no
provider_call = no
real_browser_run = no
push = no
```

## Purpose

The deep power audit identified a structural product drag:

```text
read_only_research proved the first product route,
but it remained too central in model-facing architecture.
```

Pack 4 keeps read-only power, receipts, and verification utility. It demotes the model-facing role from central product path to supporting evidence skill.

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/decision_context.py
sentinel-control/services/sentinel-core/sentinel/operator/skill_decision_frame.py
sentinel-control/services/sentinel-core/tests/operator/test_power_reconnection_decision_context_skill_frames.py
```

## Behavior Before

```text
skill_decision_frame exposed read_only_research like any other power skill
recommended_next_action could still follow legacy progress guidance
legacy read-only recommendations could appear as the generic current recommendation
```

That kept the old read-only route alive as architectural gravity even when workspace/code/browser/channel skills were the stronger product path.

## Behavior After

`skill_decision_frame.skill_frames.read_only_research` now includes:

```text
model_facing_role = supporting_evidence_skill
architecture_role = evidence_skill_not_product_center
```

`DecisionContextCompiler.recommended_next_action` now follows the skill-first primary model recommendation:

```text
recommended_next_action = primary_model_recommended_next_action
```

Legacy guidance remains available only under:

```text
legacy_recommended_next_action
legacy_next_recommended_actions
next_recommended_actions
```

## Power Preserved

Read-only is not deleted.

```text
read_only_research.list_directory
read_only_research.search_text
read_only_research.read_file_segment
read_only receipts
read-only verification summaries
```

remain available inside granted authority.

## No New Power

```text
no provider call
no real browser run
no RuntimeHost adapter change
no fallback/AUTO
no provider-native tools
no high-risk surface opened
```

## Test Proof

New regression:

```text
test_read_only_frame_is_supporting_evidence_skill_in_mixed_power_loop
```

It proves:

```text
read_only_research is tagged as supporting evidence
read_only_research is not the primary model recommendation in a mixed workspace/code/read-only loop
recommended_next_action matches primary_model_recommended_next_action
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py::test_read_only_frame_is_supporting_evidence_skill_in_mixed_power_loop -q
result = passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
result = 9 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_recoverable_observation_loop_guard.py tests/operator/test_power_cleanup_model_facing_executable_skill_truth.py tests/operator/test_power_reconnection_organ_skill_wiring.py tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_pack6d_browser_skill_spine.py tests/operator/test_power_pack6_real_browser_bounded_web_control.py tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack1_model_led_task_loop.py -q
result = passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
result = passed

git diff --check
result = passed
```

Targeted scan:

```text
secret/raw-provider/provider-native/fallback/AUTO scan = clean for changed runtime behavior
hits = hard-stop labels and existing internal fallback wording only
```

## Remaining Blockers

```text
product dispatcher still centers read_only_research as the only RuntimeHost adapter
generic task loop still has default read_only aliases for backward compatibility
browser product proof still needs a real bounded run after cleanup sequence
workspace/code/channel skill routes need product-native dispatcher parity
```

## Recommended Next Pack

```text
POWER_CLEANUP_PACK_5_PRODUCT_DISPATCHER_SKILL_NATIVE_ROUTING_V1
```

Purpose:

```text
move product dispatch from read-only-only adapter gravity toward skill-native routing
without enabling new external surfaces or fake success
```
