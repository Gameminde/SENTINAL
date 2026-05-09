# P6O Real World Gauntlet Fixes

Date: 2026-05-09

## Summary

P6O did not create a new organ. It pushed the existing organ set harder and
implemented targeted strengthening where P6N showed the organs were too thin.

## Fix 1: Credential Grant Enforcement

P6N named credentials as the weakest organ. P6M could resolve an env-backed
`CredentialRef`, but it did not yet have a real local grant layer with expiry
and revocation.

P6O adds:

```text
EnvCredentialGrant
RealityCredentialGrantStore
```

The store requires:

```text
credential_ref_id match
allowed_scope match
allowed_env_var match
non-expired grant
non-revoked grant
redacted resolution receipt
```

This keeps credential use powerful enough to unlock future API/channel/provider
flows while preserving reference-only secret handling.

## Fix 2: Workspace Root Containment

P6M used string-prefix path containment. P6O replaces that with
`Path.relative_to` root checks in:

```text
LocalChannelDraftStore
DesktopWorkspaceOperator
```

This prevents prefix-confusion paths such as:

```text
C:\tmp\root2
```

from being treated as inside:

```text
C:\tmp\root
```

## Fix 3: Batch/Max-Mode Execution Pressure

P6M proved single-path reality activation. P6O adds max-mode gauntlet methods
that run repeated operations:

```text
browser multi-page reads
API batch GET/HEAD
multi-draft channel campaign
desktop batch create/write/read/list
multi-symbol market data and paper trades
multi-vendor test-mode spend
```

## Fix 4: Cross-Organ Evidence Path

P6O proves that receipts from existing organs can flow into capital reasoning:

```text
Browser/API/Desktop/Channel receipts
-> Capital signal ledger
-> Opportunity assessment
-> Spend test-mode path
```

This is the first stronger proof that Sentinel can combine organs, not merely
operate them in isolation.

## Not Changed

P6O does not add:

```text
new organ family
real payment provider
real broker execution
live channel send
account creation
browser stealth/login/mutation
host desktop control
shell/process execution
vendor runtime bridge
silent authority expansion
```

Those surfaces remain promotion candidates, not deleted powers.
