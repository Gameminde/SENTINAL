# C6 Public Product Canonical Cutover Report

## Verdict

```text
C6_PUBLIC_PRODUCT_CANONICAL_CUTOVER = IMPLEMENTED_LOCAL_CANDIDATE_WITH_LIVE_PROVIDER_BLOCKER
public_product_route = CANONICAL_RUNTIME_REACHED
real_provider_attempted = YES
real_browser_backend = sentinel_chromium
material_browser_dispatch = NOT_REACHED_IN_C6_LIVE_RUN
terminal_blocker = PROVIDER_TRANSPORT_CONNECT_ERROR
FIXED_PROVEN = 0/65
```

This tranche connects the user-facing web product to the canonical Sentinel runtime path. It does not close any of the 65 findings yet, because the live mission did not reach a useful browser action and final grounded answer.

## Baseline

```text
source_head_before_tranche = 4dcb639bc0c54e6b9f85d4be12314b55a2d4d6e5
provider_target = aliyun_dashscope / aliyun_openai_compatible_chat / qwen-plus
browser_backend = sentinel_chromium
authority = public_web_read_only
target_origin = sqlite.org
```

## Product Path Implemented

```text
public Web /api/runs
-> canonical product runtime helper
-> python sentinel.cli canonical-product-run
-> RuntimeHost
-> RootMissionRuntime
-> ProductModelNativeDecisionClient
-> Model Freedom Intent Bridge
-> ExecutableCapabilityGraph
-> ProductActionKernel
-> sentinel_chromium read-only backend
-> MissionProofRoot
-> web run store
-> dashboard product view
```

The public API defaults to the canonical route. The old sandbox/demo path remains available only through an explicit `mode = sandbox_hypothesis`.

## Implemented Changes

- Added a web runtime sidecar helper that invokes the canonical Python product command and stores only safe product-run output.
- Added canonical mission fields to the web run model: mission state, stage, provider/model, authority scope, graph affordances, completed actions, evidence refs, terminal answer/blocker, cleanup and proof flags.
- Updated `/api/runs` and the product dashboard to display canonical runtime state rather than only demo data.
- Preserved graph-derived affordances and removed direct frontend dispatch to provider or browser.
- Fixed the presence UI TypeScript compatibility issue caused by `findLastIndex`.
- Added provider transport diagnostics for safe local/transport failures without persisting raw provider output.
- Added recoverable model-expression feedback for narrative and invalid-argument non-decisions.
- Made initial browser affordances dynamic: before a page is open, the model sees `open`, `observe`, and recovery only, not search/extract/follow.
- Projected authorized browser origins into the model-visible `real_browser.open` schema as `default` and `enum`.
- Extended the intent bridge to accept JSON fields containing function-like model expressions such as `browser.open(target_origin="sqlite.org")`.
- Added safe bridge telemetry to non-decision observations: candidate count, source expression type, extraction method, selection basis, typed rejection, JSON shape and canonical field presence.

## Live Public Runs

Observed public product run IDs in this tranche include:

```text
GR-202608211234-d3ae49
GR-202608211242-c12a5b
GR-202608211257-b7a5e4
GR-202608211303-199d6b
GR-202608211317-3185ac
```

Truthful progression:

```text
public API route reached = YES
root MissionRecord created before provider = YES
authority snapshot before provider = YES
sentinel_chromium readiness before provider = YES
provider/model selected = aliyun_dashscope / qwen-plus
ProductActionKernel browser dispatch = NOT_REACHED
receipts = proof root only; no material browser receipt in C6 live run
cleanup = COMPLETED
replay side effects = false
```

The latest live run terminated before model decision completion:

```text
terminal_blocker = CANONICAL_DECISION_TRANSPORT_REJECTED:provider_failure_PROVIDER_TRANSPORT_ERROR_transport_ConnectError
material_action_count = 0
evidence_refs = 0
cleanup = completed
proof_root_verified = true
```

Earlier live attempts exposed model-expression blockers:

```text
narrative_only_response = recoverable observation added
invalid_arguments = recoverable observation added
invalid_arguments.no_compatible_route = now reported safely
```

## Validation

```text
pytest targeted C6/core/provider group = PASS
npm run test:canonical-product-cutover = PASS
npx tsc --noEmit = PASS
npm run build = PASS
py -3.13 -m compileall sentinel = PASS
git diff --check = PASS (line-ending warnings only)
targeted secret scan = no new live secret in changed source; existing hits are scanners/fixtures
```

Targeted pytest group:

```text
test_browser_initial_prompt_shows_only_executable_open_with_authorized_origin
test_model_non_decision_observation_includes_safe_bridge_telemetry
test_model_expression_bridge_accepts_arguments_only_when_one_schema_candidate_exists
test_model_expression_bridge_rejects_arguments_only_when_schema_candidate_is_ambiguous
test_model_expression_bridge_accepts_json_action_field_with_function_like_browser_intent
test_initial_browser_state_only_advertises_executable_browser_affordances
test_model_invalid_arguments_are_returned_as_replan_observation_without_dispatch
test_provider_request_error_preserves_safe_transport_diagnostics
```

## Remaining Blocker

```text
first_current_blocker = provider transport ConnectError before executable model decision
browser_content_failure = NO
sentinel_chromium_lifecycle_failure = NO
ProductActionKernel_failure = NOT_REACHED
SQLite_content_failure = NOT_REACHED
```

C6 therefore proves the public product cutover locally and reaches the real provider boundary live, but it does not prove a completed useful public browser mission.

## Finding Status

```text
P0-01 = IMPLEMENTING
C-P0-01 = IMPLEMENTING
C-P0-02 = IMPLEMENTING
C-P0-03 = IMPLEMENTING
C-P0-06 = IMPLEMENTING
FIXED_PROVEN = 0/65
```

No finding is closed from this tranche because the live route did not complete through material browser evidence and final grounded answer.

## Next Recommendation

Do not start long-horizon yet. The next narrow step should stabilize real-provider transport or introduce the already-planned ProviderMesh resume semantics, then rerun the same public product mission without changing the Browser backend.
