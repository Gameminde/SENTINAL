# SENTINEL CONNECTIONS PACK 2 - CONNECTION MANIFEST REGISTRY V1

Report date: 2026-06-28
Repo: `C:\Users\youcefcheriet\sentinal`
Branch: `experimental/real-model-lab-freeze-v1`

## Accepted Starting State

`CONNECTION_PACK_2_CONNECTION_MANIFEST_REGISTRY_V1 = IMPLEMENTED`

Accepted inputs:

- Pack 1 audit report committed as `77f119c docs: audit connection surface inventory`.
- Opus Deep Audit V2 accepted as strategic input.
- Codex Connection Pack 1 accepted.
- Real-provider read-only route already proven by 5Q / 6A / 6C.
- Current product-dispatchable surface remains `read_only_research` only.
- No critical uncontrolled connector is active.

Core Pack 2 invariants:

```text
Manifest = map, not authority.
Registry = visibility, not execution.
Credential name = metadata, not permission.
```

## Files Added

- `sentinel-control/services/sentinel-core/sentinel/operator/connection_manifest_models.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/connection_manifest_registry.py`
- `sentinel-control/services/sentinel-core/tests/operator/test_connection_manifest_registry_pack2.py`
- `sentinel-control/docs/reviews/SENTINEL_CONNECTIONS_PACK2_CONNECTION_MANIFEST_REGISTRY_V1_REPORT.md`

No RuntimeHost, dispatcher, adapter, provider, browser, channel, desktop, credential, or external connector behavior was changed.

## Manifest Schema

Each `ConnectionManifest` is a data-only record with these required fields:

```text
connection_id
surface_id
surface_kind
owner_module
runtime_class_name
adapter_id
current_status
production_reachable
product_dispatchable
direction
risk_class
data_types
credential_env_names
credential_required
authority_required
capability_id
operation
can_read
can_write
can_send
can_execute
external_side_effects_possible
requires_gate
requires_finalgate
requires_receipts
requires_replay
requires_kill_or_revocation
prompt_injection_exposure
secret_exfiltration_exposure
receipt_schema_ref
replay_schema_ref
approval_policy_ref
allowed_destinations_policy_ref
status_reason
missing_to_dispatchable
```

Hard model invariants:

```text
data_not_authority = true
authority_effect = none
authority_granting = false
can_grant_authority = false
registry_can_execute = false
can_execute = false
fallback_auto_allowed = false
provider_native_tools_allowed = false
```

The model rejects:

- credential-looking values in credential fields;
- raw endpoint URLs in fields that may only carry source names, hashes, or policy refs;
- raw provider payload markers such as raw prompt, raw response, raw reasoning, reasoning content, or wrapper payload;
- C4/C5 surfaces marked as product-dispatchable, production-reachable, or adapter-bound by default.

## Initial Manifest Entries

The default registry seeds 30 governed surfaces:

```text
account_authority_runtime
agent_runtime_bridge
browser_click_type_submit
browser_live_operator
browser_login_session
browser_payment_account_special_authority
browser_read_only_observation
channel_connector_runtime
credential_vault_runtime
cueidea_bridge_client
desktop_sidecar_runtime
external_api_dry_run
external_api_read_write
external_organ_registry
file_system_workspace_bridge_read_only
file_system_workspace_bridge_write_shell_future
financial_authority_runtime
interactive_exploration
live_desktop_backend_runtime
mission_kernel
model_provider_catalog
model_router_runtime
operator_memory_candidate
power_runtime_bridge
read_only_research
skill_fabric_runtime
supabase_trace_repository
tool_registry
voice_runtime
worker_fleet_runtime
```

Product-dispatchable:

```text
read_only_research
```

All other surfaces are non-dispatchable in Pack 2.

## Risk Classification

| Risk | Count | Pack 2 status |
|---|---:|---|
| C0 internal metadata | 3 | metadata-only |
| C1 local/read-only/internal bounded | 7 | non-dispatchable except `read_only_research` |
| C2 external read-only | 1 | non-dispatchable |
| C3 provider/dry-run/outbound bounded | 2 | non-dispatchable |
| C4 controlled external action | 9 | locked |
| C5 high-risk/privileged/destructive | 8 | locked |

C4/C5 locked surfaces:

```text
account_authority_runtime
browser_click_type_submit
browser_live_operator
browser_login_session
browser_payment_account_special_authority
channel_connector_runtime
credential_vault_runtime
cueidea_bridge_client
desktop_sidecar_runtime
external_api_read_write
file_system_workspace_bridge_write_shell_future
financial_authority_runtime
live_desktop_backend_runtime
power_runtime_bridge
skill_fabric_runtime
supabase_trace_repository
voice_runtime
```

Lockout proof:

```text
production_reachable = false
product_dispatchable = false
adapter_id = null
```

for every C4/C5 default manifest.

## Runtime Connection Registry Comparison

Existing `runtime_connections.py` runtime profiles covered by manifests:

```text
mission_kernel
agent_runtime_bridge
power_runtime_bridge
read_only_research
browser_live_operator
interactive_exploration
tool_registry
external_organ_registry
```

Runtime profiles missing from manifests:

```text
none
```

Manifest rows without a current `RuntimeConnectionProfile`:

```text
account_authority_runtime
browser_click_type_submit
browser_login_session
browser_payment_account_special_authority
browser_read_only_observation
channel_connector_runtime
credential_vault_runtime
cueidea_bridge_client
desktop_sidecar_runtime
external_api_dry_run
external_api_read_write
file_system_workspace_bridge_read_only
file_system_workspace_bridge_write_shell_future
financial_authority_runtime
live_desktop_backend_runtime
model_provider_catalog
model_router_runtime
operator_memory_candidate
skill_fabric_runtime
supabase_trace_repository
voice_runtime
worker_fleet_runtime
```

This is expected for Pack 2. The manifest sees more surfaces than the legacy runtime connection registry, but it does not make them dispatchable.

## Adapter Readiness

Readiness result:

```text
read_only_research:
  manifest_exists = true
  RuntimeConnectionProfile exists = true
  UnifiedExecutionAdapter exists = true
  RuntimeHost registered = true
  product_dispatchable = true
  missing_to_dispatchable = []
```

Every other surface reports `product_dispatchable = false`.

Common missing readiness reasons:

```text
runtime_connection_profile_missing
unified_execution_adapter_missing
runtimehost_registration_missing
high_risk_locked
not_execution_surface
experimental_only
covered_by_read_only_research
```

Pack 2 does not create any new adapter and does not register anything in RuntimeHost.

## Credential Boundary

Credential fields accept names only, for example:

```text
SENTINEL_CERT_MODEL_API_KEY
SENTINEL_ALIYUN_DASHSCOPE_BASE_URL
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Credential fields reject credential-looking values such as API-key prefixes, bearer strings, assignment strings, raw URLs, or authorization material.

The safe export includes:

```text
credential_env_names
credential_env_name_hashes
safe_export_hash
```

It does not include credential values, authorization headers, raw endpoint URLs, raw provider responses, raw prompts, or raw reasoning.

## Safe Export Proof

The registry exposes `export_safe_summaries()`.

Safe export guarantees:

```text
names are allowed
hashes are allowed
credential values are rejected before export
raw endpoint URLs are rejected before export
raw provider payload markers are rejected before export
```

The focused tests assert exported summaries do not contain:

```text
sk-
https://
Authorization
raw_provider_payload
```

## No-New-Power Confirmation

Pack 2 added visibility only.

```text
new execution power = no
new adapter dispatch = no
RuntimeHost behavior change = no
provider call = no
external network call = no
browser/email/slack/telegram/discord action = no
write/shell/browser/network expansion = no
credential loading = no
new UnifiedExecutionAdapter = no
RuntimeHost adapter registration change = no
push = no
```

## Validation

Focused Pack 2 TDD:

```text
py -3.13 -m pytest tests/operator/test_connection_manifest_registry_pack2.py -q
9 passed
```

Python optimized focused slice:

```text
py -3.13 -O -m pytest tests/operator/test_connection_manifest_registry_pack2.py -q
9 passed
```

Focused runtime/protocol/product wiring regressions:

```text
py -3.13 -m pytest \
  tests/operator/test_runtime_connection_registry.py \
  tests/operator/test_product_nervous_system_pack3.py \
  tests/operator/test_read_only_research_decision_protocol_pack3_7.py \
  tests/operator/test_model_decision_extractor_pack3_13.py \
  tests/operator/test_runtime_host_pack1.py \
  tests/operator/test_mission_lifecycle_service.py \
  tests/test_cli_runtime_host_product_wiring_pack1b.py \
  tests/test_llm_operator_model_client_v0.py \
  -q
164 passed
```

Focused Pack 4A/4B/4B.1 read-only production spine regression slice:

```text
py -3.13 -m pytest \
  tests/operator/test_connection_manifest_registry_pack2.py \
  tests/operator/test_runtime_connection_registry.py \
  tests/operator/test_product_nervous_system_pack3.py \
  tests/operator/test_read_only_research_decision_protocol_pack3_7.py \
  tests/operator/test_model_decision_extractor_pack3_13.py \
  tests/operator/test_runtime_host_pack1.py \
  tests/operator/test_mission_lifecycle_service.py \
  tests/test_cli_runtime_host_product_wiring_pack1b.py \
  tests/test_llm_operator_model_client_v0.py \
  tests/test_real_model_read_only_operator_production_spine_v1.py \
  -q
```

Result:

```text
222 passed
1 failed
```

The failing assertion is outside Pack 2 files:

```text
tests/test_real_model_read_only_operator_production_spine_v1.py::test_model_decision_timeout_is_classified_without_tool_action
expected blocked_reason = model_decision_timeout
actual blocked_reason = TIMEOUT
```

The failure also reproduces in isolation and Pack 2 did not modify `read_only_operator_spine.py`. It is recorded as an existing focused regression and was not repaired in this manifest-only pack.

Compile and diff checks:

```text
py -3.13 -m compileall sentinel/operator/connection_manifest_models.py sentinel/operator/connection_manifest_registry.py
passed

git diff --check
passed
```

Targeted secret/raw-provider/fallback/provider-native scan:

```text
rg -n "sk-|Authorization|raw_prompt|raw_response|raw_reasoning|reasoning_content|raw_provider_payload|fallback|AUTO|provider-native|provider_native_tools|https://"
```

Result:

```text
benign policy/test/report literals only
no credential values
no Authorization value
no raw prompt
no raw provider response
no raw reasoning
no provider wrapper payload
no fallback/AUTO enablement
no provider-native tool enablement
```

## Commit

Pack 2 local commit hash is reported in the final closeout response. The commit hash cannot be embedded in this file without changing the file and therefore changing the commit hash.

## Recommended Next Action

```text
START_CONNECTION_PACK_3_IDENTITY_TENANT_CREDENTIAL_BOUNDARY_V1
```
