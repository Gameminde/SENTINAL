# SENTINEL_FIX_PRODUCT_LOOP_REPLAY_LARGE_BROWSER_ARTIFACT_HASHING_V1

## Purpose

Fix the V16B post-loop runner hang where `ProductActionKernelTaskLoopReplay.from_store` stalled while hashing large browser/world-model JSON artifacts.

## Root Cause

The replay helper previously did this for every mission JSON artifact:

```text
read_text -> json.loads -> stable_hash(payload)
```

Large browser request/context artifacts can contain bulky world-model structures. Re-parsing and stable-hashing those payloads is unnecessary for replay no-react proof.

## Fix

Updated:

```text
sentinel/operator/model_led_product_action_kernel_task_loop.py
```

Behavior:

```text
before:
  replay artifact stability hashed parsed JSON objects

after:
  replay artifact stability hashes raw file bytes
```

This still proves artifact immutability and avoids expensive JSON object normalization.

## Test Added

Updated:

```text
tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py
```

Added:

```text
test_browser_replay_hashes_large_artifacts_without_reparsing_json
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_visible_irrelevant_cards_finish_with_negative_relevance_not_fake_match tests/operator/test_power_pack6d_browser_skill_spine.py::test_relevance_gap_after_search_does_not_repeat_search_as_primary tests/operator/test_power_pack6d_browser_skill_spine.py::test_finish_intent_after_irrelevant_summary_finishes_with_grounded_caveat tests/operator/test_power_pack6d_browser_skill_spine.py::test_finish_requires_relevance_assessment tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_browser_replay_hashes_large_artifacts_without_reparsing_json -q
result = 5 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 92 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 18 passed
```

## Safety

```text
no provider call during fix
no real browser run during fix
no fallback/AUTO
no provider-native tools
no raw DOM/cookies/session/profile material introduced
no replay side effects introduced
```

## Next Prepared Attempt

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V17_AFTER_NEGATIVE_RELEVANCE_COMPLETION_AND_REPLAY_HASHING
```
