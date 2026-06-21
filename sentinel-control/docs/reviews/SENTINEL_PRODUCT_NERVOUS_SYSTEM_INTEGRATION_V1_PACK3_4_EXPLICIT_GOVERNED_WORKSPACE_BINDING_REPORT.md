# Sentinel Product Nervous System Integration V1

## Pack 3.4 Explicit Governed Workspace Binding

Status: locally implemented candidate
Base commit: `8d6ce0b7ca4021ad313b7e0449a0d6fc75750f64`
Scope: product route binding only
Provider calls: none

## Attempt 3 Blocker

`ATTEMPT_3_WITH_COCKPIT_MISSION_UNDERSTANDING_V2` stopped during static preflight before any provider call.

Root cause:

```text
EXPLICIT_PRODUCT_WORKSPACE_BINDING_MISSING
```

The cockpit V2 schema intentionally does not allow the model to supply workspace or model-contract refs. The product route also did not yet provide a code-owned binding, so a started mission would have fallen back to:

```text
workspace_ref = snapshot:operator_session
model_contract_ref = model_contract:operator_session
```

The Pack 3 read-only dispatcher requires:

```text
workspace:<absolute-canonical-path>
```

Therefore the product route was not dispatchable to a real disposable repository.

## New Binding Contract

Pack 3.4 adds a Sentinel-owned `ProductExecutionBinding`:

```text
workspace_ref
model_contract_ref
capability_id
operation
binding_hash
data_not_authority = true
can_execute = false
```

The binding is created only from:

```text
CLI --workspace
explicit MissionAuthorityApprovalScope
explicit UserModelContract
code-owned read_only_research capability contract
```

The model cannot create, mutate, or expand this binding.

## Workspace Validation

The CLI product route now accepts:

```text
--workspace <path>
```

Validation requires:

```text
path exists
path is a directory
resolved path is canonical and absolute
path is not under the Sentinel run root
path is not an obvious credential/secret root
path is inside the approved authority scope
```

The persisted request ref is:

```text
workspace:<absolute-resolved-path>
```

Failure reasons include:

```text
workspace_binding_required
workspace_not_found
workspace_not_directory
workspace_path_traversal_ambiguous
workspace_sensitive_path_blocked
workspace_inside_run_root
workspace_outside_approved_scope
```

## Approval-Scope Intersection

The existing cockpit action narrowing remains in force:

```text
provider V2 requested capability
AND read_only_research capability actions
AND MissionAuthorityApprovalScope.allowed_actions
```

Forbidden actions are preserved and unioned from the V2 capability contract and approval scope.

The workspace itself must be permitted by `MissionAuthorityApprovalScope.allowed_paths`. `.` means the operator-approved selected workspace root. Absolute allowed paths may also authorize a containing directory. Sentinel does not broaden the approval scope automatically.

## Model Contract Ref Binding

For explicit product LLM mode, the request now receives a stable model contract ref:

```text
model_contract:<provider_id>:<backend_id>:<model_id>:<contract_hash>
```

The ref excludes credentials, authorization headers, endpoint URLs, raw provider config, raw prompts, raw responses, and hidden reasoning.

The same explicit `UserModelContract` drives:

```text
cockpit understanding
read-only exploration decision client
read-only report client
MissionExecutionRequest.model_contract_ref
```

## Provider Cannot Alter Binding

The cockpit mission-understanding V2 schema remains narrow. It rejects model-supplied control fields such as:

```text
workspace
workspace_ref
path
allowed_paths
model_contract_ref
authority_scope
approval_scope
budget
credentials
can_execute
```

Legacy deterministic paths may retain old smoke-test fallbacks, but governed LLM product mission start requires the Sentinel-owned binding.

## Request Creation Proof

For a valid product route, approval creates a persisted `MissionExecutionRequest` with:

```text
capability_id = read_only_research
operation = inspect_repository
workspace_ref = workspace:<absolute-canonical-path>
model_contract_ref = model_contract:<provider>:<backend>:<model>:<hash>
authority_envelope_ref = issued envelope id
```

The old executable product fallbacks are not used for Pack 3 LLM product missions:

```text
snapshot:operator_session
model_contract:operator_session
```

## Dispatchability Proof

Focused tests prove:

```text
CLI --workspace is accepted by the product route
inside-scope workspace creates workspace:<absolute-path>
daemon pump reaches dispatcher
adapter receives a dispatchable workspace ref
dispatcher no longer fails workspace_ref_not_dispatchable for valid product binding
```

Invalid or missing binding stops before `MissionExecutionRequest` creation.

## Conversation Outcome Truth

CLI JSON classification now distinguishes:

```text
mission_not_created_workspace_missing
mission_not_created_workspace_outside_scope
mission_queued
mission_dispatched
mission_terminal
```

Exit code alone is not mission proof.

## Remaining Limits

Pack 3.4 does not prove a real-provider product mission.

It only removes the static workspace-binding blocker discovered by Attempt 3. The next real-provider attempt still requires:

```text
fresh temporary credential
explicit endpoint configuration
same no-fallback/no-provider-native-tools contract
one mission only
no retry
```

Pack 4, additional capability surfaces, browser, desktop, channels, credentials, finance, voice, and memory are not connected by this pack.
