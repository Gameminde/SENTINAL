# P6C Browser Organ Contract Review Scorecard

Date: 2026-05-09

## Scope

P6C normalizes Sentinel browser capability under the P6A external organ foundry
contract system. It does not recreate the browser runtime and does not add new
browser execution powers.

## Implemented Files

```text
sentinel-control/services/sentinel-core/sentinel/organs/lanes.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/contract.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/power_governor.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/misuse_classifier.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/reliability_profile.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/session_policy.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/fingerprint_risk.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/compliance_gate.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/detection_bench.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/receipts.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_browser_organ_contract.py
```

## Power Classification

```text
P0 normal browser reliability
P1 human-like operation
P2 fingerprint consistency
P3 detection-resilience research
P4 special-authority stealth operation
P5 forbidden misuse objective
```

P5 is misuse-objective rejection, not capability deletion. Cloak-like browser
powers are classified and governed by Sentinel authority, risk, compliance,
evidence, trace, and FinalGate expectations.

## Autonomy/Risk Lane Mapping

```text
P0 public read/observe -> Blue Lane when authorized and traced
P1/P2 interaction/fingerprint planning -> Orange Lane
P3 diagnostics/research -> Red Lane research/dry-run posture
P4 stealth -> Red Lane special authority
P5 misuse objective -> Black Lane blocked
```

The `BrowserPowerGovernor` downgrades to the lowest needed power when stronger
power is not justified. Sensitive submit/form/login/upload-like actions remain
dry-run/proposal in P6C unless future promotion explicitly authorizes them.

## Locked Behaviors

```text
browser organ contract registers through ExternalOrganRegistry
contract remains execution_enabled = false
browser capabilities require authority mapping and source refs
misuse classifier blocks fake identity, KYC bypass, credential theft, spam,
unauthorized scraping, and unlawful evasion
browser session policy blocks credential storage in P6C
fingerprint and stealth powers are risk-classified instead of discarded
detection bench is deterministic and non-executing
browser receipts require evidence refs and trace refs
browser receipts cannot start execution or expand authority
```

## Trace Compatibility

P6C adds browser-organ-specific trace event definitions:

```text
BROWSER_ORGAN_POWER_GOVERNED
BROWSER_ORGAN_MISUSE_CLASSIFIED
BROWSER_ORGAN_RECEIPT_RECORDED
BROWSER_ORGAN_DETECTION_BENCH_RUN
```

The browser organ contract advertises these events in addition to the generic
P6A organ trace events.

## Verification

```bash
python -m pytest tests/test_p6_browser_organ_contract.py -v --tb=short
```

Result:

```text
11 passed
```

## Boundaries Preserved

```text
real browser power expansion = 0
payment/spend runtime = 0
trading runtime = 0
account creation runtime = 0
credential access = 0
vendor runtime bridge = 0
vendor code copy = 0
silent authority expansion = 0
```
