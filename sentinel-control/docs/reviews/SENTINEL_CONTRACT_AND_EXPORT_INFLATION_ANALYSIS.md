# Sentinel Contract And Export Inflation Analysis

Recorded at: 2026-06-13

## Verdict

Contract/export inflation is real architecture debt. It is not a current
authority bypass, but it can slow future backend work and make audits harder.

```text
operator_py_files = 60
operator_total_lines = 23236
operator_init_lines = 822
operator_init_export_entries = 375
sentinel_py_files = 479
sentinel_total_lines = 119365
test_files = 226
test_functions = 2278
```

## Largest Operator Surfaces

| File | Approx size |
|:--|:--|
| model_router.py | 49.5 KB |
| worker_fleet.py | 44.2 KB |
| live_desktop_backend.py | 43.9 KB |
| desktop_sidecar.py | 42.4 KB |
| skill_models.py | 41.4 KB |
| financial_authority.py | 37.6 KB |
| financial_authority_models.py | 36.3 KB |
| desktop_sidecar_models.py | 36.2 KB |
| harness_models.py | 35.6 KB |
| credential_vault_models.py | 35.1 KB |

## Highest Model-Class Density

| File | Classes | Lines |
|:--|--:|--:|
| financial_authority_models.py | 65 | 1038 |
| voice_models.py | 59 | 927 |
| account_authority_models.py | 59 | 930 |
| desktop_sidecar_models.py | 50 | 912 |
| credential_vault_models.py | 44 | 952 |
| skill_models.py | 32 | 1053 |
| live_desktop_backend_models.py | 32 | 573 |
| model_router_models.py | 29 | 756 |
| channel_adapter_models.py | 27 | 532 |
| daemon_models.py | 22 | 672 |

## Findings

| ID | Severity | Finding | Decision |
|:--|:--|:--|:--|
| CEI-1 | P3 architecture debt | `sentinel.operator.__init__` exports 375 symbols over 822 lines. | Accepted. Do not add broad exports without need. |
| CEI-2 | P3 architecture debt | Many phases add large model suites before live backends. | Accepted. Future work should reuse contracts and ship real backends. |
| CEI-3 | P3 audit cost | Large single files make invariant review slower. | Accepted. Future refactors should be scoped and test-backed. |
| CEI-4 | P2 if unmanaged | Export inflation can make unsafe imports easier to miss. | Mitigated by current tests/scanners; needs future hygiene pass. |

## Rules Going Forward

```text
new broad exports = avoid unless required for stable public API
new model families = only when real runtime needs them
contract-only additions = require explicit maturity label
real backend work = prefer before new speculative contracts
audit docs = must keep distinguishing LIVE_LOCAL_RUNTIME vs WIRED_FAKE_OR_SANDBOX
```

## Recommended Future Cleanup

```text
1. Split sentinel.operator.__init__ exports into curated public groups.
2. Add module-level import hygiene tests for dangerous shortcut imports.
3. Freeze model-only expansion during live backend phases unless required.
4. Add "public API / internal API" markers for operator modules.
5. Keep phase reports honest about fake, sandbox, injected, descriptor, and live maturity.
```

No cleanup is performed in this lock because this pack is an invariant audit and
minimal remediation pass, not an architecture refactor.
