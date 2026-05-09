# P6F Credential Vault Policy Scorecard

Date: 2026-05-09

## Scope

P6F defines credential access as scoped references and policy decisions. It does
not integrate a real vault, read secrets, store raw secrets, or grant credential
authority from prompt, memory, workspace, vendor harvest, or expected profit.

## Implemented Files

```text
sentinel-control/services/sentinel-core/sentinel/organs/credentials/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/credential_ref.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/vault_policy.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/scoped_grant.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/redaction.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/revocation.py
sentinel-control/services/sentinel-core/sentinel/organs/credentials/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_credential_vault_policy.py
```

## Locked Behaviors

```text
CredentialRef stores only references, never raw secret values.
ScopedCredentialGrant includes mission, scope, expiry, allowed organ, and action
class.
CredentialTraceRedactor removes secret-like values from trace payloads.
Grants can be revoked deterministically.
Prompt, memory, workspace, vendor harvest, and expected profit cannot authorize
credential use.
Matching organ-runtime grants may allow reference use only.
Secret access remains false in P6F.
Credential policy decisions are Red Lane by default.
Credential policy receipts are deterministic and redacted.
```

## Trace Compatibility

P6F adds credential policy trace event definitions:

```text
CREDENTIAL_REF_REGISTERED
CREDENTIAL_GRANT_EVALUATED
CREDENTIAL_GRANT_REVOKED
```

## Verification

```bash
python -m pytest tests/test_p6_credential_vault_policy.py -v --tb=short
```

Result:

```text
13 passed
```

## Boundaries Preserved

```text
raw secret storage = 0
real credential vault integration = 0
secret value access = 0
payment/spend runtime = 0
trading runtime = 0
account creation runtime = 0
external API execution = 0
browser power expansion = 0
vendor runtime bridge = 0
vendor code copy = 0
silent authority expansion = 0
```
