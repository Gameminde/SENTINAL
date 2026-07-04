# Sentinel Power Cleanup Pack 1 - Model-Facing Executable Skill Truth V1

Status: locally implemented
Implementation commit: `0bbe148`
Provider calls: 0
Real browser runs: 0
Push: not performed

## Why This Pack Exists

The deep power audit and agent reviews converged on the same root problem:

```text
what the model sees as possible
must be executable by the runtime
or recoverable before material effect
```

Sentinel had already created `skill_decision_frame`, actionability frames, backend frames, and recoverable observations, but direct/legacy `ActionEnvelope` decisions could still bypass that truth. A model or old prompt could emit an internal primitive such as `real_browser.type_text`, an unknown action, or a locked high-risk action, and the loop would often discover the mismatch only at executor dispatch.

That is power friction. The model should not pilot internal runtime primitives. It should pilot skills.

## Audit Rows Addressed

Primary rows:

- BF-CORE-003: model-visible action missing executor
- BF-CORE-013: legacy recommendations remain visible beside skill frame
- BF-BROWSER-007: raw browser primitives leak through model-facing paths
- BF-ORGAN-003: backend/action frames can be decorative unless consumed
- BF-AUTH-001: legacy authority aliases hide granted power

Related rows partially reduced:

- BF-CORE-001: recoverable in-scope miss becomes terminal mission death
- BF-BROWSER-011: candidate/action not backed by actionability
- BF-PROOF-001: avoidable blocked truth before recovery

## What Changed

`DecisionContextCompiler` now exposes:

```text
model_visible_available_actions
runtime_available_actions
```

`available_actions` remains for compatibility, but the model-facing truth is explicit and derived from the actionability registry.

`ModelLedTaskLoop` now validates a normalized model decision against the actionability registry before executor dispatch:

- `EXECUTABLE` actions can run.
- `HIDDEN_INTERNAL` actions become recoverable model-protocol observations.
- `NOT_REGISTERED` actions become recoverable model-protocol observations.
- `MISSING_AUTHORITY` blocks clearly.
- `LOCKED` high-risk actions hard-stop clearly.

The loop default action set now includes the already-proven workspace patch skill:

```text
workspace_patch.apply_patch
workspace_patch.run_bounded_check
```

Legacy mission grants such as `channel_send`, `list_directory`, and `real_browser.*` now map to the proper capability IDs for actionability checks, instead of causing false `MISSING_AUTHORITY`.

Browser model-loop tests were migrated away from raw `type_text/press_key/wait` decisions and now use the skill-level `real_browser.search`. The runtime can still use type/press internally as the hand, but the model-facing path is the skill.

## Before / After

Before:

```text
model emits real_browser.type_text
-> ActionKernel dispatches primitive
-> runtime may act or fail
```

After:

```text
model emits real_browser.type_text
-> loop sees hidden_internal
-> recoverable observation
-> recommended model-visible skills
-> no executor call, no material effect
```

Before:

```text
model emits ghost action
-> executor missing
-> terminal block
```

After:

```text
model emits ghost action
-> not_registered recoverable observation
-> strongest visible skill recommendations
```

Before:

```text
model emits payment_authority.submit
-> executor missing / unclear failure
```

After:

```text
model emits payment_authority.submit
-> locked high-risk skill
-> MODEL_ACTION_LOCKED_HARD_STOP
```

## Files Changed

- `sentinel-control/services/sentinel-core/sentinel/operator/decision_context.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/model_led_task_loop.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_model_facing_executable_skill_truth.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py`

## Hard Boundaries Preserved

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

This pack does not add provider calls, live browser action, new connector power, new external transport, or high-risk dispatch.

## Validation

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_cleanup_model_facing_executable_skill_truth.py -q
```

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_cleanup_model_facing_executable_skill_truth.py tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
```

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack1_model_led_task_loop.py tests/operator/test_power_pack2_workspace_write_patch.py -q
```

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
```

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_cleanup_model_facing_executable_skill_truth.py tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_reconnection_recoverable_execution_contract.py tests/operator/test_power_pack6d_browser_skill_spine.py tests/operator/test_power_pack6_real_browser_bounded_web_control.py tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack1_model_led_task_loop.py -q
```

Passed:

```text
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
```

Passed:

```text
git diff --check
```

Targeted scan:

```text
rg -n "sk-[A-Za-z0-9]|Authorization:|Bearer [A-Za-z0-9]|raw_provider|raw_reasoning|reasoning_content|provider_native_tools|provider-native tools|fallback:AUTO|fallback:auto" ...
```

The scan produced existing guard strings, redaction tests, safety scanners, and known canary assertions. No new credential, provider output, reasoning, raw DOM, cookie, session, provider-native tool, or fallback/AUTO persistence was introduced by this pack.

## Remaining Blockers

This pack cuts the first global truth bypass. It does not complete the whole audit.

Remaining high-value cuts:

1. Convert more in-scope runtime misses into typed recovery observations instead of terminal blocked truth.
2. Make recoverable observations with fresh candidates count as productive recovery in `LoopGuard`.
3. Consolidate skill/backend/organ metadata so `ActionabilityRegistry`, `PowerSkillRegistry`, and `OrganSpecRegistry` stop drifting.
4. Demote read-only spine from product center into one evidence skill.
5. Continue browser/organs consolidation, but only after the global skill/executable-truth spine is honored everywhere.

## Recommended Next Pack

```text
POWER_CLEANUP_PACK_2_RECOVERABLE_OBSERVATION_DOMINATES_LOOP_GUARD_AND_FINALGATE_V1
```

Goal:

```text
recoverable in-scope miss with fresh candidates
-> productive recovery lane
-> no FinalGate blocked truth until recovery exhausted or hard boundary hit
```
