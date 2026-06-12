# Durable Credential Vault And Secret Broker V1 - Research And Design

Date: 2026-06-12

## Verdict

`DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1` should be implemented as a
Sentinel-native durable metadata vault plus secret broker. V1 must not pretend
to be a production cryptographic vault. The selected implementation maturity is:

```text
vault_maturity = fake_sealed_store
durable_raw_secret_persistence = BLOCKED
os_keychain_live_calls = NOT_STARTED
cloud_vault_calls = NOT_STARTED
password_manager_import = NOT_STARTED
```

The vault may persist secret metadata, sealed material hashes, fake sealed refs,
scope policies, unlock sessions, leases, receipts, FinalGate certificates,
telemetry refs, revocation records, expiry, and rotation metadata. It must not
persist raw API keys, passwords, cookies, OAuth refresh tokens, provider keys,
prompts, provider responses, or reasoning.

## Design Law

```text
Credential existence != permission.
Secret handle != authority.
Secret lease != authority.
Unlock session != authority.
Receipt != future permission.
Memory != secret store.
LLM never sees raw secrets.
Replay never replays secrets.
Telemetry never stores raw secrets.
```

Secret use must still require `MissionAuthorityEnvelope`, secret use policy,
scope policy, a valid unlock session where required, expiry/revocation checks,
consumer allowlist, telemetry, safe receipts, and FinalGate certification.

## Official Source Research

| System | Architecture pattern | Useful mechanism | Sentinel-native adaptation | Risks | What not to copy | Implementation implication |
| --- | --- | --- | --- | --- | --- | --- |
| Windows DPAPI | User/machine-bound data protection | `CryptProtectData` protects data so typically only the same user on the same computer can decrypt it | Future `os_keychain_live_opt_in` descriptor may bind secret material to the local user/machine | Windows-only, live OS unlock semantics, migration complexity | Do not call DPAPI in V1 and claim production encryption without full tests | V1 records OS keychain descriptor concepts only and uses fake sealed refs |
| macOS Keychain | Encrypted database for small sensitive items | Item metadata, add/find/update/delete APIs, encrypted keychain storage | Future platform adapter can map `SecretMetadata` to keychain item attributes | User prompts, app entitlements, access groups, sync behavior | Do not import password manager/keychain items in V1 | V1 keeps metadata/material separation and item provenance |
| Linux Secret Service/libsecret | D-Bus service with collections, items, sessions, transfer of secrets | Explicit sessions and item attributes | Future Linux adapter can bind unlock sessions to Secret Service sessions | Desktop session availability and D-Bus policy differ by environment | Do not create hidden Secret Service calls in V1 | V1 models unlock sessions and scoped leases without OS calls |
| AWS Secrets Manager | Cloud secret lifecycle with versioning, rotation and CloudTrail audit | Versioning, rotation metadata, audit events | `SecretVersion`, `SecretRotationPolicy`, audit telemetry and replay | Cloud permissions, billing, network calls, external mutation | Do not add cloud vault or provider calls in V1 | V1 models version/rotation metadata and access audit records |
| Google Secret Manager | Secret version lifecycle and Cloud Audit Logs | Version pinning and access/admin audit logs | Route secret metadata and access decisions into Sentinel telemetry | IAM and data-access logs are separate concerns; cloud calls are external | Do not use GCP API or persist provider credentials | V1 uses local telemetry and route-safe refs only |
| Azure Key Vault | Cloud vault for keys, certificates and secrets with logging | Access logging, secret versioning, vault access policy concepts | `CredentialScopePolicy`, `VaultOperatorApproval`, version/revocation records | Cloud access can become ambient authority if not mission-bound | Do not add Azure integration in V1 | V1 requires explicit MissionAuthorityEnvelope for all use |
| 1Password | Vault/item model and developer secret delivery | Item metadata vs secret value, CLI/env injection patterns | Useful as a future final-consumer adapter pattern | CLI/env injection can leak secrets to process trees/logs | No 1Password import, CLI run, or env injection in V1 | V1 broker returns handles and leases, not raw values |
| Bitwarden Secrets Manager | Machine accounts, projects, scoped machine access | Scope a machine account to a discrete set of secrets | Model consumer refs, scopes, and grants narrowly | Access tokens and machine identities become high-risk credentials | No Bitwarden live connection or token persistence | V1 blocks provider keys and models scoped consumer policy |

Official sources consulted:

- Microsoft DPAPI `CryptProtectData`: https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- Apple Keychain Services: https://developer.apple.com/documentation/security/keychain-services
- freedesktop Secret Service API: https://specifications.freedesktop.org/secret-service/
- AWS Secrets Manager CloudTrail logging: https://docs.aws.amazon.com/secretsmanager/latest/userguide/monitoring-cloudtrail.html
- Google Cloud Secret Manager audit logging: https://docs.cloud.google.com/secret-manager/regional-secrets/audit-logging-rs
- Azure Key Vault logging/security: https://learn.microsoft.com/en-us/azure/key-vault/general/logging
- 1Password Connect API / developer secret delivery: https://www.1password.dev/connect/api-reference
- Bitwarden machine accounts: https://bitwarden.com/help/machine-accounts/

## AgentLab Source-Only Harvest

| Vendor/system | Architecture pattern | Useful mechanism | Sentinel-native adaptation | Risks | What not to copy | Implementation implication |
| --- | --- | --- | --- | --- | --- | --- |
| JARVIS | Local assistant with sidecar and vault retrieval references | Sidecar/session lifecycle and auditable local assistant shape | Vault events attach to mission, receipts, FinalGate, replay | Sidecar tokens and config mutation can expand host power | Do not copy JARVIS sidecar/vault runtime or tool authority | Secret broker is mission-bound and cannot control desktop/login |
| OpenJarvis | Config/env/session patterns and local/cloud routing | Explicit runtime configuration surfaces | Provider keys become future `SecretKind.api_key` metadata only | Learned config mutation or remembered approvals can switch providers | Do not let memory/config auto-select credentials | Router and memory cannot materialize or switch secrets |
| Agent Zero | Broad local execution ergonomics | Operator-visible background task progress | Expose safe vault status and checkpoints | Ambient host reach and plugins can consume secrets unsafely | Do not permit plugin or host connector raw secret access | Skills/workers receive handles only, not values |
| gptme | Local config/env ergonomics | Compact session continuity | Safe summaries can improve operator UX | Env values leak easily into shell/logs | Do not inject secrets into shell/env in V1 | No unbounded shell or env secret materialization |
| OpenClaw | Plugin/skill admission and required secret declarations | Scanner flags required env/secrets and plugin secret access | Skill requirements become declarative only | Plugin secret manager actions can bypass policy | No remote plugin runtime or `read_secret` skill | Skill can declare requirements but cannot approve/unlock |
| Hermes / DeerFlow | Workflow credential propagation risks | Task graph can carry requirements without values | Worker/task context can include secret refs and evidence refs | Memory/skills/tool outputs may poison credential scope | Do not propagate raw secrets through workers/memory | Worker outputs and memory write-through are secret-free |
| Letta / memory agents | Durable memory as context | Persistent facts and utility | Store safe secret metadata summaries only | Memory can become latent instruction/authority | Do not store secret material or approvals in memory | Memory never unlocks, approves, or routes secret use |

## Sentinel Components Reused

```text
MissionAuthorityEnvelope
MissionKernel / MissionRunStore
TelemetryKernel / TelemetryStore
operator redaction and safety scanners
CredentialRef / CredentialGrant / CredentialAccessRequest foundation
browser login credential-session broker concepts
voice raw secret blocking posture
desktop raw secret blocking posture
channel credential_ref placeholder posture
memory context-only doctrine
receipts / FinalGate refs / replay patterns
```

## Runtime Architecture Decision

V1 adds:

```text
CredentialVaultConfig
CredentialVaultRuntime
CredentialVaultStore
CredentialVaultId
SecretMetadata
SecretMaterialEnvelope
SecretRef / SecretHandle
SecretAccessRequest / Grant / Lease
SecretCheckoutToken / SecretCheckoutResult
VaultUnlockPolicy / VaultUnlockSession
SecretUseReceipt
SecretFinalGateCertificate
SecretReplayView
```

The vault store is local and mission-run scoped. It persists JSON records under
the existing mission run directory through `MissionRunStore.atomic_write_json`.
The store never persists raw material. `register_secret(..., secret_material=)`
hashes the provided material and records a fake sealed ref. The raw value is
discarded.

## Storage Posture

```text
storage_maturity = fake_sealed_store
metadata_durable = true
sealed_payload_hash_durable = true
raw_secret_durable = false
encrypted_payload_durable = false
```

This is intentionally conservative. It is powerful enough to test authority,
leasing, auditing, replay, revocation, and consumer binding before real
OS-keychain or cryptographic storage is admitted.

## Broker Behavior

The broker returns:

```text
SecretHandle
SecretAccessLease
SecretCheckoutToken metadata
redacted display label
expiry
audit refs
receipt refs
FinalGate refs
```

It does not return raw secret material to LLMs, memory, telemetry, replay,
workers, voice, desktop, channel messages, model prompts, receipts, or
FinalGate certificates.

## Authority Boundary

The broker rejects access when any of these are missing or invalid:

```text
MissionAuthorityEnvelope
secret purpose/scope match
consumer allowlist
unlock session
expiry and revocation checks
telemetry certified mode
```

High-risk secret kinds are modeled but blocked by default:

```text
payment_method_ref
trading_api_key_ref
device_pairing_secret
```

## V1 Limits

```text
no OS keychain live call
no password manager import
no cloud vault
no raw secret persistence
no browser auto-login
no account creation/login expansion
no payment/spend/trading
no provider key execution path
no voice biometric unlock
no provider fallback/AUTO
```

These limits are intentional. Future account/login and special-authority
phases can bind real final-consumer adapters to the broker only after this
metadata, leasing, telemetry, and replay foundation is proven.
