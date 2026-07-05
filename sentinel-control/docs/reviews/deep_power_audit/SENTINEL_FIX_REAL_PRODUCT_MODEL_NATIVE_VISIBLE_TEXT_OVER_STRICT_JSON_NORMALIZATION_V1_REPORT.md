# SENTINEL_FIX_REAL_PRODUCT_MODEL_NATIVE_VISIBLE_TEXT_OVER_STRICT_JSON_NORMALIZATION_V1_REPORT

## Verdict

`FIX_REAL_PRODUCT_MODEL_NATIVE_VISIBLE_TEXT_OVER_STRICT_JSON_NORMALIZATION_V1 = LOCALLY_COMMITTED`

Implementation commits:

```text
20a9c15f64e21ba37cc63b6e722b0d6a09180d29
779dc8a7c3a4f55c327dd942f38c7e934c9a9576
ca595956c27e0e7c049401da71e79b52fa95ab27
```

## 4B Failure Interpreted

`REAL_PRODUCT_ATTEMPT_4B_ARBITRARY_LOCAL_APP_CREATION_EXECUTION_V1` proved that the real provider could create multiple local app files and that duplicate create-file target recovery worked.

The remaining blocker was:

```text
PRODUCT_NATIVE_VISIBLE_TEXT_STRICT_JSON_NORMALIZATION_GAP
```

The model/provider wrapper could include useful safe visible text while also reporting a strict JSON normalization failure such as:

```text
normalization_strategy = no_json_object_detected
```

Before this fix, Sentinel discarded the visible model-native intent and raised:

```text
MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED
```

That made the model feel more caged than it needed to be. ActionEnvelope remains the internal runtime language, but useful safe model-native text should be allowed to map to simple product skills.

## Runtime Change

Changed:

```text
sentinel/operator/product_model_native_decision_client.py
sentinel/agent/model_execution/openai_compatible.py
sentinel/operator/model_client.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
```

Before:

```text
any visible-content normalization failure blocked immediately
```

After:

```text
normalization failure blocks only when no usable visible text exists
product_model_native_intent_v1 keeps provider visible text in memory for immediate product-native skill mapping
raw_provider_response remains hash-only/sanitized in persisted provider payloads
after create-file plans are done, dead patch recommendations are hidden and run_check becomes the living next skill
```

This preserves the empty-content blocker while allowing safe natural/semi-structured text such as:

```text
Run the bounded local check.
```

to map to:

```text
code_execution_sandbox.code_exec.run_profile
```

## Tests Added

Changed:

```text
tests/operator/test_real_monster_product_model_native_decision_client.py
tests/test_llm_operator_model_client_v0.py
```

Added:

```text
test_visible_text_survives_strict_json_normalization_failure
test_catalog_model_client_preserves_product_native_visible_text_memory_only
test_created_app_workspace_recommends_run_check_not_dead_patch
```

The test first failed with:

```text
MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED
```

Then passed after the runtime change.

## Validation

Commands run:

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_visible_text_survives_strict_json_normalization_failure -q
```

Result:

```text
failed before fix as expected
```

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_visible_text_survives_strict_json_normalization_failure tests/operator/test_real_monster_product_model_native_decision_client.py::test_empty_visible_provider_content_blocks_instead_of_falling_back_to_patch -q
```

Result:

```text
2 passed
```

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q
```

Result:

```text
50 passed
```

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py tests/test_llm_operator_model_client_v0.py -q
```

Result:

```text
67 passed
```

Because the four-file validation slice exceeded the 300 second combined command timeout, the same files were also run individually with durations:

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=10 --maxfail=1
py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q --durations=10 --maxfail=1
py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q --durations=10 --maxfail=1
py -3.13 -m pytest tests/test_llm_operator_model_client_v0.py -q --durations=10 --maxfail=1
```

Result:

```text
29 passed
12 passed
10 passed
17 passed
```

```text
py -3.13 -m compileall -q sentinel
```

Result:

```text
passed
```

```text
git diff --check
```

Result:

```text
passed with Windows LF/CRLF warnings only
```

Targeted scan:

```text
secrets/raw-provider/provider-native/fallback/AUTO/cookie/session-token scan over touched diff
```

Result:

```text
no unsafe persistence introduced
```

## Boundaries Preserved

Unchanged:

```text
no fallback/AUTO
no provider-native tools
no raw provider/reasoning persistence
no credential/session/cookie persistence
empty visible provider output still blocks
visible non-JSON provider text is in-memory only for ProductModelNativeDecisionClient
hard boundary credential requests still block
non-executable patch is not shown as the primary next skill when no patch plan exists
ActionEnvelope remains internal runtime format
```

## Next Prepared Attempt

Prepared but not run by this report:

```text
REAL_PRODUCT_ATTEMPT_4C_ARBITRARY_LOCAL_APP_CREATION_EXECUTION_V1
```

Expected proof target:

```text
real provider
-> create arbitrary local app files
-> run bounded check
-> fake/local channel send
-> worker or verifier step if selected
-> finish
-> replay no-react
```
