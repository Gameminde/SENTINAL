# P6D External API Organ Scorecard

Date: 2026-05-09

## Scope

P6D creates the Sentinel external API organ in dry-run mode. It can plan API
requests, classify allowlist status, estimate cost and latency, classify privacy
risk, and emit deterministic request receipts. It does not execute external API
requests.

## Implemented Files

```text
sentinel-control/services/sentinel-core/sentinel/organs/external_api/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/request_plan.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/allowlist.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/cost_estimator.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/privacy_risk.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/dry_run.py
sentinel-control/services/sentinel-core/sentinel/organs/external_api/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_external_api_organ.py
```

## Locked Behaviors

```text
External API organ contract registers through ExternalOrganRegistry.
Request plans are dry-run shaped and cannot start execution.
Future live use requires vendor/domain allowlist.
Dry-run planning is allowed even when future live use would be rejected.
Cost estimates include expected cost, latency, rate limit, and paid-API flag.
Privacy risk classifies personal and sensitive data.
Read-only API planning maps to Blue Lane when authorized and traced.
Paid/mutation/account-affecting API planning remains Orange/Red dry-run only.
Raw credential material is rejected; CredentialRef placeholders are allowed.
Request receipts require evidence refs and trace refs.
Request receipts are deterministic and cannot expand authority.
```

## Trace Compatibility

P6D adds external API organ trace event definitions:

```text
EXTERNAL_API_REQUEST_PLANNED
EXTERNAL_API_DRY_RUN_RECORDED
```

The external API organ contract advertises these events in addition to generic
P6A organ trace events.

## Verification

```bash
python -m pytest tests/test_p6_external_api_organ.py -v --tb=short
```

Result:

```text
11 passed
```

## Boundaries Preserved

```text
real external API execution = 0
payment/spend runtime = 0
trading runtime = 0
account creation runtime = 0
credential access = 0
browser power expansion = 0
vendor runtime bridge = 0
vendor code copy = 0
silent authority expansion = 0
```
