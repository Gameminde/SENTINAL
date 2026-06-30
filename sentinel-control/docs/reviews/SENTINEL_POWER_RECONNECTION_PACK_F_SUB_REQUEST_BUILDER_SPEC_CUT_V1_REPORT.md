# Sentinel Power Reconnection Pack F - Sub-Request Builder Spec Cut V1

Status: implemented candidate
Implementation commit: `e404e98f46f784fd76966eef45cf5da66f59e0bf`
Provider calls: 0
Real browser runs: 0
Push: not performed

## Accepted Input State

Pack E added the data-only organ runtime spec registry and wired organ lookup/runtime proof metadata into dispatch and execution. Pack E deliberately left a follow-up cut:

```text
typed sub-request construction remained branch-heavy
runtime request field selection remained manual
new organ wiring still required editing dispatcher request-field matrices
```

Pack F is the requested continuation of that simplification, not a new live power pack.

## Opening Audit Against Deep Power V1

Mapped audit finding:

```text
organ_dispatch.py and runtime_execution.py branch matrices tax power.
Adding or wiring an organ should flow from specs/factories, not repeated manual string comparisons.
```

Pack F preserves the core doctrine:

```text
power first
receipts always
model-facing simplicity
runtime hard stops only for real boundaries
```

It does not open new provider/browser/channel power and does not make high-risk organs dispatchable.

## Runtime Changes

Added:

```text
sentinel/agent/organs/organ_request_factory.py
```

The factory is data/control-plane only:

```text
OrganRequestBuildContext
OrganRequestBuildResult
OrganRequestFactory
```

It cannot grant authority, cannot execute, and cannot register runtime adapters. It maps:

```text
organ id or alias
-> OrganRuntimeSpec
-> request_field
-> typed sub-request builder
-> OrganRuntimeExecutionRequest kwargs
```

Updated:

```text
sentinel/agent/organs/organ_dispatch.py
sentinel/agent/organs/organ_spec_registry.py
sentinel/agent/organs/runtime_execution.py
```

## Simplification Cut

Before Pack F, `OrganDispatcher._execute_candidate()` manually selected exactly one runtime request field with per-organ comparisons:

```text
if runtime_organ_kind == browser_readonly -> browser_readonly_request
if runtime_organ_kind == browser_session_manager -> browser_session_request
...
```

After Pack F:

```text
OrganRequestFactory.build(runtime_organ_kind, context)
-> spec lookup
-> request_field from OrganRuntimeSpec
-> typed builder result
-> runtime_request_kwargs()
```

The old `_build_typed_sub_request()` remains as a compatibility wrapper, but the active dispatch path consumes `OrganRequestBuildResult`.

## Proof Preservation

Runtime summaries now include:

```text
organ_spec_id
request_field
runtime_handler
skill_binding
receipt_kind
proof_requirements
replay_expectations
recoverable_failure_classes
hard_stop_categories
```

This keeps proof/receipt/replay metadata visible for blocked and executed paths.

## High-Risk Lockout Proof

Pack F does not change the Pack E lockout state. These remain non-dispatchable by default:

```text
browser_form_submit_special_authority
browser_login_credential_session_broker
browser_download_upload_quarantine
browser_js_sandbox_special_authority
browser_payment_spend_special_authority
```

Unknown organs still block honestly:

```text
unknown_organ_not_registered
```

## Re-Audit

What improved:

```text
typed sub-request request-field selection is spec-owned
browser_session_manager aliases build through the factory
browser_readonly builds through the factory
browser_semantic_extraction builds through the factory using readonly receipt context
runtime proof summaries preserve request_field
unknown organ request builds return typed blocked reason
```

What remains:

```text
concrete builder functions still live in organ_dispatch.py
runtime_execution.py still contains concrete executor functions and mode preflights
Pack F is not real-provider product proof
The next power move should be browser skill spine 6D, not another generic registry pack
```

## Tests Run

```text
py -3.13 -m pytest tests/test_organ_request_factory_spec_dispatch.py -q
7 passed

py -3.13 -m pytest tests/test_organ_spec_registry_runtime_dispatch.py -q
8 passed

py -3.13 -m pytest tests/test_agent_browser_operator_runtime_integration.py -q
8 passed

py -3.13 -m pytest tests/test_browser_session_manager_l5_live.py -q
12 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
8 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_organ_skill_wiring.py -q
5 passed

py -3.13 -m compileall -q sentinel
passed

git diff --check
passed; CRLF warnings only from the Windows checkout

targeted secret/raw-provider/provider-native/fallback/AUTO scan
passed; only benign fallback comments were found
```

## No-New-Power Confirmation

```text
provider call = no
real browser run = no
external network call = no
new live connector power = no
high-risk organ enabled by default = no
fallback/AUTO introduced = no
provider-native tools introduced = no
receipt/replay/FinalGate weakened = no
push = no
```

## Recommended Next Action

```text
POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
```

Pack F should be the last generic internal registry/factory cut before returning to visible product power. The next work should make browser research model-facing as a skill:

```text
model pilots browser skill
Sentinel handles robust actuation/recovery/proof below the model
Alibaba-like product research should not die on a brittle locator timeout
```
