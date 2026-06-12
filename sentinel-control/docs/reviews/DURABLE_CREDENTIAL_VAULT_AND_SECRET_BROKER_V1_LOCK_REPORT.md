# Durable Credential Vault And Secret Broker V1 Lock Report

Date: 2026-06-12

## Verdict

```text
DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1 = LOCKED
previous_phase = REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1_LOCKED
next_phase = ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1
roadmap_doctrine = product power under provable authority
```

Sentinel now has a Sentinel-native durable credential metadata vault and scoped
secret broker foundation. V1 is intentionally conservative:

```text
vault_maturity = fake_sealed_store
durable_metadata = true
durable_raw_secret_persistence = BLOCKED
os_keychain_live_backend = NOT_STARTED
cloud_vault_live_backend = NOT_STARTED
password_manager_import = NOT_STARTED
account_creation_login_authority = NOT_STARTED / next
```

The vault persists safe records, refs, hashes, policies, unlock sessions,
leases, receipts, FinalGate certificates, telemetry, and replay metadata. It
does not persist raw API keys, passwords, cookies, OAuth refresh tokens,
provider keys, prompts, provider responses, or reasoning.

## Research And Design

Created first:

```text
sentinel-control/docs/reviews/DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1_RESEARCH_AND_DESIGN.md
```

Official source mechanisms reviewed:

- Microsoft DPAPI `CryptProtectData`: user/machine-bound local protection
  concept for a future OS-keychain adapter.
- Apple Keychain Services: item metadata and encrypted keychain posture for a
  future macOS adapter.
- freedesktop Secret Service API: session and item-attribute posture for a
  future Linux adapter.
- AWS Secrets Manager, Google Secret Manager, and Azure Key Vault: versioning,
  rotation, access policy, and audit logging concepts.
- 1Password Connect and Bitwarden machine accounts: vault/project scoped access
  concepts and secret-delivery risks.

No OS keychain, cloud vault, password-manager, vendor runtime, provider API, or
network secret service was called or integrated.

## AgentLab Mechanisms Harvested

```text
JARVIS / OpenJarvis = local assistant/session/vault-shape inspiration
Agent Zero / gptme = operator-visible secret-use status and compact summaries
OpenClaw = skill secret declaration and scanner inspiration
Hermes / DeerFlow = workflow credential propagation risks
Letta-style memory agents = memory-context-only secret summary posture
```

Harvest result:

```text
mechanisms harvested = yes
vendor code copied = no
vendor runtime bridged = no
dependency installed = no
external account connected = no
parallel authority system created = no
```

## Sentinel Components Reused

```text
MissionAuthorityEnvelope
MissionKernel / MissionRunStore
MissionRunStore.atomic_write_json
TelemetryKernel / TelemetryStore event and metric vocabulary
operator redaction helpers
shared safety scanner
existing memory-not-authority doctrine
voice/desktop/channel/worker/skill/daemon advisory boundary posture
receipt / FinalGate / replay patterns
```

## Runtime Added

Created:

```text
sentinel-control/services/sentinel-core/sentinel/operator/credential_vault_models.py
sentinel-control/services/sentinel-core/sentinel/operator/credential_vault.py
sentinel-control/services/sentinel-core/sentinel/operator/credential_vault_replay.py
sentinel-control/services/sentinel-core/tests/test_durable_credential_vault_secret_broker_v1.py
```

Extended:

```text
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
```

## Vault And Broker Behavior

Implemented concepts:

```text
CredentialVaultConfig
CredentialVaultRuntime
CredentialVaultStore
SecretMetadata
SecretMaterialEnvelope
SecretRef
SecretHandle
VaultUnlockPolicy
VaultUnlockSession
VaultOperatorApproval
SecretAccessRequest
SecretAccessGrant
SecretAccessLease
SecretCheckoutToken
SecretCheckoutResult
SecretUseContext
SecretUseReceipt
SecretFinalGateCertificate
SecretLeakScanResult
SecretReplayView
```

Behavior:

```text
register_secret hashes supplied test material and stores fake sealed refs only
request_unlock creates a locked metadata session
approve_unlock_session requires operator approval metadata
request_secret_access requires secret policy, consumer allowlist, MissionAuthorityEnvelope, and unlock session
create_secret_lease creates scoped time-bound leases
checkout_secret returns handle/token metadata only
record_secret_use creates receipt and FinalGate records
revocation, expiry, rotation-required, and kill-triggered lease invalidation are persisted
replay reconstructs vault lifecycle without secret materialization
```

## Authority Review

```text
vault-created authority = BLOCKED
broker-created authority = BLOCKED
unlock-session-as-authority = BLOCKED
secret-handle-as-authority = BLOCKED
secret-lease-as-authority = BLOCKED
receipt-as-authority = BLOCKED
FinalGate-as-future-permission = BLOCKED
memory-as-secret-store = BLOCKED
voice/desktop/channel/skill/worker/daemon/scheduler/LLM ambient secret use = BLOCKED
provider fallback/AUTO = NOT_APPROVED
```

Secret use still requires the parent `MissionAuthorityEnvelope` plus policy,
purpose, scope, consumer, unlock-session, expiry, revocation, and kill checks.

## Telemetry And Replay

Added telemetry events and metrics for vault initialization, unlock requests,
unlock approval/expiry/revocation, secret registration, access grant/rejection,
lease creation/expiry/revocation, checkout, use, revocation, rotation-required,
leak scan, and failure surfaces.

Telemetry remains data only. It cannot execute, grant authority, unlock
credentials, or become future permission.

Replay reconstructs:

```text
vault configs
secret metadata
unlock sessions
access grants
leases
checkouts
receipts
FinalGate certificates
revocations
leak scans
timeline refs
```

Replay does not materialize secrets, call external services, unlock vaults,
repeat secret use, or execute organs.

## CodeRabbit Advisory Review

```text
CodeRabbit used = no
reason = coderabbit command not found in this environment
decision = no unknown dependency installed and no token/auth flow started
manual exhaustive audit = performed
CodeRabbit authority = none
```

## Exhaustive Audit Findings

| Severity | Finding | File/surface | Decision | Fix or rationale | Remaining limits |
| --- | --- | --- | --- | --- | --- |
| P0 | Raw secret persistence could not be allowed in any durable record | credential vault models/store | fixed | `safe_model_dump` redacts raw-material key names and validators reject true raw-material flags | V1 fake sealed store only |
| P0 | Broker could not expose raw material to memory, worker, prompt, telemetry, receipt, FinalGate, or replay | runtime/replay/tests | fixed | checkout returns handle/token metadata only; tests assert raw material absence | no live final-consumer secret injection in V1 |
| P0 | Voice/desktop/channel/skill/worker/daemon/scheduler/LLM must not ambiently use secrets | advisory surfaces | fixed | `request_advisory_surface_secret_use` blocks advisory surfaces | future phases must add explicit final-consumer contracts |
| P1 | Windows temp paths could exceed path length when long IDs were used as filenames | vault store | fixed | vault store maps IDs to short hash-bound JSON filenames while preserving record IDs inside payloads | local filesystem store only |
| P1 | Redacted persisted records had to reload without reintroducing raw fields | models | fixed | safe alias fields are accepted and rejected if true | aliases remain metadata only |
| P1 | Secret policy errors should remain precise before authority-scope rejection | access request | fixed | request validates secret policy/scope/consumer before authority scope for clearer blocked results | no execution before authority validation |
| P1 | Telemetry could not become a parallel authority or store raw secrets | telemetry kernel/models | fixed | credential events/metrics are safety-domain data only; no raw material in metadata | no telemetry cloud |
| P2 | V1 must not overclaim OS keychain/cloud/password-manager maturity | docs/report | fixed | docs state fake sealed store and mark production secret backends NOT_STARTED | cryptographic vault remains future |
| P2 | CodeRabbit was unavailable | advisory review | accepted | no install/auth performed due phase safety rule | manual audit performed |

No open P0/P1 or serious P2 issues remain in this lock.

## Honest V1 Limits

```text
no production encrypted vault
no Windows DPAPI call
no macOS Keychain call
no Linux Secret Service call
no AWS/GCP/Azure secret manager call
no 1Password or Bitwarden import
no browser auto-login
no account creation/login special authority
no payment/spend/trading/security/device power
no provider key execution path
no voice biometric unlock
no provider fallback/AUTO
```

## Tests And Checks

Targeted tests completed:

```text
py -3.13 -m pytest tests/test_durable_credential_vault_secret_broker_v1.py -q
result = PASS / 23 tests

py -3.13 -m pytest tests/test_durable_credential_vault_secret_broker_v1.py tests/test_realtime_voice_ambient_operator_v1.py tests/test_live_desktop_operator_backend_system_monitoring_v1.py tests/test_permissioned_desktop_sidecar_visual_grounding_v1.py tests/test_real_channel_adapters_v1.py tests/test_local_model_hardware_and_cost_router_v1.py -q
result = PASS / 104 tests

py -3.13 -m pytest tests/test_governed_skill_and_procedure_fabric_v1.py tests/test_model_amplification_execution_harness_v1.py tests/test_production_mission_daemon_and_scheduler_v1.py tests/test_mission_worker_fleet_authority_inheritance_v1.py tests/test_observability_telemetry_and_product_power_metrics_v1.py tests/test_durable_mission_workflow_and_automatic_replan_v1.py tests/test_durable_mission_workflow_replan_gauntlet_v1.py tests/test_persistent_semantic_memory_v1.py tests/test_persistent_semantic_memory_integrations_v1.py tests/test_llm_live_operator_cockpit_flow_v0.py tests/test_llm_live_operator_power_runtime_bridge_v0.py tests/test_sentinel_power_runtime_v0.py tests/test_agent_runtime.py tests/test_brain_to_organ_runtime_closed_loop.py tests/test_delegated_action_gate_model_v0.py tests/test_agent_core_final_gate.py tests/test_agent_event_bus.py tests/test_agent_evidence_chain.py -q
result = PASS / 296 tests
```

Final closeout checks are recorded in the final commit response.

## Files Created Or Updated

Created:

```text
sentinel-control/docs/reviews/DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1_RESEARCH_AND_DESIGN.md
sentinel-control/docs/reviews/DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1_LOCK_REPORT.md
sentinel-control/services/sentinel-core/sentinel/operator/credential_vault_models.py
sentinel-control/services/sentinel-core/sentinel/operator/credential_vault.py
sentinel-control/services/sentinel-core/sentinel/operator/credential_vault_replay.py
sentinel-control/services/sentinel-core/tests/test_durable_credential_vault_secret_broker_v1.py
```

Updated:

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
```

## Next Phase

```text
ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1
```

Do not start it until the credential vault lock is committed, pushed, and
verified against `origin/main`.
