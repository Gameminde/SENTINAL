# Mission Authority And Credential Vault Foundation Report

Recorded at: 2026-05-25

Pack: `MISSION_AUTHORITY_AND_CREDENTIAL_VAULT_FOUNDATION`

## Current State

Sentinel entered this pack with:

- Brain native candidate source = CLOSED
- Memory feedback = CLOSED through `RoleLoopMemoryBridge.build(...)`
- Replan-ready packet = CLOSED
- L2/L3 local execution runtime opt-in = CLOSED
- Browser ReadOnly / Preparation / Semantic Extraction runtime opt-in = CLOSED
- Durable memory persistence = NOT_STARTED
- Automatic replan execution = NOT_STARTED

This pack adds the authority and credential metadata foundation required before
CloakBrowser L5, API mutation, channel send, desktop, shell, spend, trading, or
credential-bearing browser sessions.

## Models Added Or Extended

New canonical foundation models live in:

```text
sentinel/organs/credentials/foundation.py
```

Implemented:

- `MissionAuthorityGrant`
- `MissionAuthorityGrantScope`
- `MissionAuthorityGrantStatus`
- `CredentialGrant`
- `CredentialGrantScope`
- `CredentialGrantStatus`
- `CredentialAccessRequest`
- `CredentialAccessDecision`
- `CredentialAccessProof`
- `CredentialRevocation`
- `CredentialAuditReceipt`
- `AuthorityPreset`
- `AuthorityPresetFactory`
- `AuthorityCredentialSafetyValidationResult`

Extended:

- `CredentialRef` now carries metadata-only mission, organ, domain, action,
  expiry, and revocation fields while still rejecting raw secret material.
- `MissionAuthorityEnvelope` now accepts `credential_grants` metadata.
- `OrganRuntimeExecutionConfig` now carries `credential_policy_refs` and
  `credential_proof_refs` metadata references only.
- `DelegatedActionGate` can require and validate credential proof metadata
  when an organ contract declares `credential_proof_required`.

## Existing Credential Concepts Unified

The pack does not create a parallel `sentinel/vault/` island.

It extends the existing credential plane:

```text
sentinel/organs/credentials/
```

Existing concepts preserved:

- `CredentialRef`
- `ScopedCredentialGrant`
- `CredentialVaultPolicy`
- `CredentialPolicyReceipt`
- `CredentialAccessSource`
- model-execution credential handles remain separate provider credential
  handles and are not converted into organ runtime authority.

## Authority Grant Semantics

`MissionAuthorityGrant` is scoped by:

- `mission_id`
- `allowed_organs`
- `allowed_action_levels`
- `domain_scope`
- `action_scope`
- optional `credential_ref_id`
- expiry / revocation metadata
- `user_approval_required`
- `finalgate_required`

It is metadata only:

```text
authority_effect = none
execution_effect = none
can_grant_authority = false
can_approve_execution = false
can_execute = false
data_not_instruction = true
```

## Credential Ref Semantics

`CredentialRef` is an opaque reference, not a secret container.

It rejects:

- `raw_secret`
- `secret_value`
- authority granting flags
- execution flags
- provider/backend/model override flags

No credential value is stored in the foundation.

## Revocation Semantics

Revocation wins over all grants.

`CredentialRevocation` and `CredentialAuditReceipt.from_revocation(...)`
record:

- mission id
- credential ref id
- grant id
- reason
- revocation timestamp
- audit receipt hash

They do not contain secret values and cannot approve future execution.

## Audit Receipt Model

`CredentialAuditReceipt` records:

- access decision
- proof id when access metadata is allowed
- evidence refs
- receipt refs
- trace refs
- deterministic receipt hash

It rejects secret access and secret values by construction.

## Preset Summary

`AuthorityPresetFactory` provides:

- `development_local`: L2/L3 local only, no credentials.
- `browser_perception`: L4 browser readonly/preparation/semantic only, no
  credentials.
- `operator_browser_l5_template`: non-executing L5 navigation/click/type
  template, no submit/login/payment and credential use disabled by default.
- `full_power_template`: non-executing template requiring explicit future
  grants.

All presets are metadata-only and default to credential use disabled.

## Status Truth Table

| Segment | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Mission authority grants foundation | CLOSED | `test_mission_authority_grant_is_metadata_only` | Grants are metadata only. |
| Credential refs/grants/proofs foundation | CLOSED | `test_credential_ref_contains_no_raw_secret`, `test_credential_grant_requires_*`, `test_credential_access_proof_*` | No real secret storage. |
| Revocation/audit model | CLOSED | `test_credential_revocation_and_audit_receipt_are_metadata_only` | No durable audit store. |
| Authority presets | CLOSED | `test_default_presets_do_not_enable_credentials` | Presets do not execute anything. |
| DelegatedActionGate credential proof metadata | CLOSED | `test_delegated_gate_rejects_missing_credential_proof_when_required`, `test_delegated_gate_accepts_valid_credential_proof_as_metadata_only` | Proofs remain metadata only. |
| FinalGate credential proof metadata validation | CLOSED | `test_finalgate_can_validate_credential_proof_metadata_only` | Helper validates metadata; it does not certify credentialed execution. |
| Real secret storage | NOT_STARTED | No vault persistence or secret value field added. | Required later. |
| Real credential use by organs | NOT_STARTED | No organ consumes a credential value. | Required before credentialed browser/API/channel. |
| Browser login/session credentials | NOT_STARTED | Forbidden surfaces remain blocked. | Requires later CloakBrowser/session contract. |
| CloakBrowser backend | NOT_STARTED | No browser backend code added. | Next spec candidate. |

## What Remains NOT_STARTED

```text
real_secret_storage = NOT_STARTED
real_credential_use_by_organs = NOT_STARTED
browser_login_session_credentials = NOT_STARTED
credentialed_api_mutation = NOT_STARTED
channel_send_credentials = NOT_STARTED
desktop_credential_use = NOT_STARTED
CloakBrowser controlled backend = NOT_STARTED
durable credential audit persistence = NOT_STARTED
```

## Why No Real Credential Runtime Is Enabled

This pack deliberately adds contracts and proofs only.

It does not:

- store a raw secret;
- resolve a credential value;
- inject credentials into browser/API/channel/desktop/shell;
- enable a global credential switch;
- change AgentRuntime default behavior;
- approve future execution from a proof or receipt.

Credential access remains per request, per grant, per mission scope, and
metadata-only.

## CloakBrowser Prerequisites Unlocked

Future CloakBrowser work can now depend on:

- credential references without raw secrets;
- grant scope validation;
- expiry and revocation semantics;
- proof metadata;
- audit receipts;
- non-executing authority presets.

The next safe pack is:

```text
CLOAKBROWSER_CONTROLLED_BACKEND_SPEC
```
