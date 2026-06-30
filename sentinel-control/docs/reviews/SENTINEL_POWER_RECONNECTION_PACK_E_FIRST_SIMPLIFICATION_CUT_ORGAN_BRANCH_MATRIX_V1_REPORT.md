# Sentinel Power Reconnection Pack E - First Simplification Cut Organ Branch Matrix V1

Status: implemented candidate
Implementation commit: `pending_followup_ledger`
Provider calls: 0
Real browser runs: 0
Push: not performed

## Accepted State

Pack D made `skill_decision_frame` the primary model decision truth, with legacy primitive recommendations left as compatibility fields. Pack D is a major foundation step but not product-proven by a real provider run.

Pack E applies the next global audit correction: reduce branch-heavy organ execution code so organs become declarative specs consumed by dispatch/runtime, without deleting useful organs or weakening receipts, replay, FinalGate, or hard-stop boundaries.

## Opening Audit Against Deep Power V1

Mapped audit finding:

```text
organ_dispatch.py and runtime_execution.py branch matrices tax power.
Adding or wiring an organ requires manual branch updates in multiple places.
Browser/session organ lookup is especially fragile because Cloak/session aliases are not declared as one executable spec.
```

Pack E intentionally does not open high-risk organs, does not add live power, and does not change RuntimeHost dispatch behavior.

## Runtime Changes

Added:

```text
sentinel/agent/organs/organ_spec_registry.py
```

The registry declares data-only `OrganRuntimeSpec` entries with:

```text
organ_id
request_model
runtime_handler
authority_level
backend_kind
skill_binding
proof_requirements
receipt_kind
replay_expectations
recoverable_failure_classes
hard_stop_categories
default_dispatchable
locked_reason
```

The registry also preserves firewall invariants:

```text
data_not_authority = true
authority_granting = false
can_grant_authority = false
registry_can_execute = false
```

Updated:

```text
sentinel/agent/organs/organ_dispatch.py
sentinel/agent/organs/runtime_execution.py
sentinel/organs/registry.py
```

## Simplification Cut

Before Pack E, browser runtime organ resolution used a manual branch/list inside `organ_dispatch.py`.

After Pack E:

```text
browser_session_manager_l5_live
cloakbrowser_session
browser_l5_live_session
```

resolve through the declarative spec registry to:

```text
browser_session_manager
```

`runtime_execution.py` now checks the spec registry before runtime preflight and records safe spec metadata in blocked/runtime results. Unknown organs block honestly with:

```text
unknown_organ_not_registered
```

## Preserved Proof And Power Boundaries

Receipts and FinalGate are not bypassed. The existing organ executor functions still produce the existing receipts/certificates.

Examples:

```text
browser_readonly -> browser_readonly_receipt + browser_readonly_finalgate
browser_session_manager -> browser_session_receipt + browser_session_finalgate
reversible_workspace -> workspace_patch_receipt + low_risk_finalgate
```

High-risk organs remain non-dispatchable by default:

```text
browser_form_submit_special_authority
browser_login_credential_session_broker
browser_download_upload_quarantine
browser_js_sandbox_special_authority
browser_payment_spend_special_authority
```

Their specs carry `locked_reason` and hard-stop categories such as:

```text
external_send
credential_access
login_session
file_upload
file_download
javascript_execution
payment
checkout
```

## Re-Audit

What improved:

```text
known organ dispatch can be resolved through spec registry
unknown organ blocks with a typed honest reason
browser/session organ alias lookup no longer depends on manual branch lists
receipt/finalgate requirements are visible as spec data
locked/high-risk organs stay locked by default
skill_binding metadata is available to decision/context layers
recoverable and hard-stop metadata is available from specs
```

What remains:

```text
runtime_execution.py still contains concrete executor functions and preflight mode checks
sub-request construction remains branch-heavy and should be cut in a later pack
Pack E is not real-provider product proof
Pack 6D browser skill spine still depends on this but remains future work
```

## Tests Run

```text
py -3.13 -m pytest tests/test_organ_spec_registry_runtime_dispatch.py -q
8 passed

py -3.13 -m pytest tests/test_organ_spec_registry_runtime_dispatch.py tests/test_agent_browser_operator_runtime_integration.py tests/test_browser_session_manager_l5_live.py tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_reconnection_organ_skill_wiring.py -q
41 passed

py -3.13 -m compileall -q sentinel
passed
```

```text
git diff --check
passed; CRLF warnings only for existing Windows checkout behavior

targeted secret/raw-provider/provider-native/fallback/AUTO scan
passed; matches are benign negative/doctrine/test strings and an existing fallback comment, not activation or persisted secrets
```

## No-New-Power Confirmation

```text
provider call = no
real browser run = no
new live connector power = no
high-risk organ enabled by default = no
fallback/AUTO introduced = no
provider-native tools introduced = no
receipt/replay/FinalGate weakened = no
push = no
```

## Recommended Next Action

```text
POWER_RECONNECTION_PACK_F_SUB_REQUEST_BUILDER_SPEC_CUT_V1
```

Pack F should continue the same simplification direction by moving typed sub-request field selection/building out of branch matrices and into specs/factories, without changing authority, receipts, replay, or FinalGate behavior.
