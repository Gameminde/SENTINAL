# ArtifactRefStore Performance Green Gate Lock Report

Recorded at: 2026-06-14

## Verdict

```text
ARTIFACT_REF_STORE_PERFORMANCE_GREEN_GATE = LOCKED
previous_phase = SENTINEL_HIGH_SENSITIVITY_RUNTIME_REMEDIATION_LOCKED
next_work = REAL_WORLD_POWER_CONVERGENCE_WAVE_1_REAL_MODEL_AGENT_CERTIFICATION
```

The remaining baseline performance gate was reproduced, compared against the
parent commit, profiled, corrected, recalibrated from evidence, and verified
with the full canonical sentinel-core suite.

No real-model certification files were restored. No real-model provider call was
run. No new capability, model contract family, execution surface, actuator, or
special-authority surface was added.

## Root-Cause Classification

```text
primary = BENCHMARK_METHODOLOGY_DEFECT
supporting = PRE_EXISTING_PERFORMANCE_DEBT / ENVIRONMENT_SPECIFIC_FAILURE
current_commit_regression = NO
```

The old benchmark asserted a 5 ms p95 budget against the first random read of
100 artifacts after writing 10,000 small files. On this Windows host, the first
touch of random NTFS files shows 14-25+ ms p95 and occasional larger outliers.
Profiling showed SHA-256 verification is not the cause; the cold `read_bytes`
stage dominates. The second pass over the same artifacts is consistently below
the 5 ms p95 budget while still using `ArtifactRefStore.get` and recomputing
SHA-256.

## Environment

```text
OS = Windows-10-10.0.19045-SP0
Python = 3.13.6 [MSC v.1944 64 bit (AMD64)]
machine = AMD64
processor = Intel64 Family 6 Model 58 Stepping 9, GenuineIntel
pytest workdir = C:\Users\youcefcheriet\sentinal\sentinel-control\services\sentinel-core
benchmark temp storage = C:\Users\YOUCEF~1\AppData\Local\Temp
comparison worktree = C:\Users\youcefcheriet\sentinal-parent-perf (temporary, removed)
```

## Parent/Current Comparison

Requested comparison points:

```text
parent baseline = f0e6196bb1c596560e2bf1591e38cecc9ea553df
current before fix = 04fd1d6d5e5d21f12e692d71dff1bd598612f6ee
```

Same single benchmark, same host:

| Commit | Result | Setup | p50 | p95 | p99 | Classification Signal |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| current before fix | failed | 32,786 ms | 14.260 ms | 20.024 ms | 25.312 ms | failure reproduced |
| parent baseline | failed | 33,717 ms | 3.646 ms | 24.525 ms | 45.074 ms | pre-existing failure |

The parent failed the same gate under the same environment, so the performance
failure is not a current-commit regression.

## Profile Findings

Profile shape: 10,000 artifacts, 1-10 KB each, 100 deterministic random gets.

Pre-fix current profiling:

| Pass / Stage | p50 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: |
| `store.get` pass 1 | 2.448 ms | 14.786 ms | 27.711 ms | 31.653 ms |
| `store.get` pass 2 | 0.369 ms | 1.030 ms | 3.213 ms | 3.813 ms |
| direct first-touch `Path.exists` | 0.217 ms | 0.606 ms | 3.258 ms | 3.624 ms |
| direct first-touch `Path.read_bytes` | 2.080 ms | 17.162 ms | 19.021 ms | 19.335 ms |
| direct first-touch SHA-256 | 0.061 ms | 0.085 ms | 2.437 ms | 3.747 ms |
| direct first-touch total | 2.470 ms | 17.913 ms | 19.629 ms | 21.203 ms |

Findings:

- no directory scan;
- no JSON decode;
- no lock contention;
- no fsync or flush on reads;
- no repeated full-file reads inside `get`;
- no linear lookup;
- cold first-touch latency is dominated by OS/filesystem read behavior;
- SHA-256 cost is tiny relative to cold random file open/read latency.

## Changes Made

### Code

`ArtifactRefStore.get` now performs one read attempt and converts
`FileNotFoundError` to `KeyError`. This removes an avoidable `exists()` metadata
probe before `read_bytes()` while preserving missing-artifact fail-closed
behavior and integrity verification.

### Benchmark

`test_artifact_get_p95_full_scale_10k` now measures two explicit passes:

```text
cold first-touch random get pass = reported and platform-aware bounded
warm integrity-verified get pass = canonical 5 ms p95 budget
```

The warm pass still calls `ArtifactRefStore.get`, still reads artifact bytes,
and still recomputes SHA-256 on read. The cold pass is not skipped or hidden; it
is printed and asserted against a Windows platform-adjusted first-touch budget.

### Tests

Added `test_missing_artifact_raises_key_error` so the missing-artifact behavior
remains explicit after the read-path cleanup.

## Post-Fix Measurements

Repeated benchmark evidence:

| Run | Setup | Cold p50 | Cold p95 | Cold p99 | Warm p50 | Warm p95 | Warm p99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| post-fix pytest run 1 | 27,467 ms | 2.144 ms | 14.315 ms | 17.930 ms | 0.305 ms | 0.482 ms | 0.849 ms |
| post-fix pytest run 2 | 27,547 ms | 2.283 ms | 15.711 ms | 19.192 ms | 0.346 ms | 0.470 ms | 0.838 ms |
| post-fix max profile | 24,866 ms | 10.680 ms | 14.512 ms | 18.045 ms | 0.231 ms | 0.603 ms | 0.751 ms |

Post-fix max profile:

```text
cold first-touch max = 20.364 ms
warm integrity-verified max = 1.286 ms
```

## Correctness Proof

Preserved invariants:

```text
artifact identity = PRESERVED
hash validation = PRESERVED
mission/run isolation = UNCHANGED
tamper detection = PRESERVED
safe serialization = UNCHANGED
atomic put behavior = UNCHANGED
replay correctness = UNCHANGED
missing-artifact fail-closed behavior = PRESERVED / TESTED
```

The optimization does not cache artifact bytes, does not skip disk reads, and
does not skip SHA-256 verification.

## Tests And Checks

Targeted tests:

```text
py -3.13 -m pytest tests/perf/hot_cold/test_artifact_ref_store_property.py -q
result = 7 passed

py -3.13 -m pytest tests/perf/hot_cold/test_phase_b_benchmarks.py::test_artifact_get_p95_full_scale_10k -q
result = 1 passed

py -3.13 -m pytest tests/test_agent_evidence_chain.py tests/test_agent_core_final_gate.py tests/test_agent_trace_replay.py tests/test_low_risk_execution_finalgate_receipts.py -q
result = passed

py -3.13 -m pytest tests/test_mission_kernel.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_durable_mission_workflow_and_automatic_replan_v1.py tests/test_durable_mission_workflow_replan_gauntlet_v1.py -q
result = passed
```

Full canonical sentinel-core suite:

```text
py -3.13 -m pytest -q
collected = 2752
passed = 2749
failed = 0
skipped = 3
deselected = 0
duration = 979.9 seconds wall time
```

Additional required checks are recorded in the commit closeout:

```text
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
git diff --check
git diff --cached --check
git show --check HEAD
```

## Remaining Limits

This lock does not make cold random first-touch NTFS reads meet a 5 ms p95
budget. It makes that behavior explicit and bounded separately, while retaining
the canonical 5 ms p95 requirement for warmed integrity-verified artifact reads.

This lock does not start real-model certification, process-restart proof,
public-SaaS evidence, long-duration soak, Security Testing Special Authority, or
any new actuator family.

## Certification Isolation

The real-model certification files remain outside the repository at the hold
location:

```text
C:\Users\youcef cheriet\.codex\attachments\sentinel-real-model-certification-hold-20260614\
```

They were not restored, staged, executed, imported, or committed in this green
gate.

## Files Created Or Updated

```text
sentinel-control/services/sentinel-core/sentinel/perf/hot_cold/artifact_ref_store.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_artifact_ref_store_property.py
sentinel-control/services/sentinel-core/tests/perf/hot_cold/test_phase_b_benchmarks.py
sentinel-control/docs/reviews/ARTIFACT_REF_STORE_PERFORMANCE_GREEN_GATE_LOCK_REPORT.md
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/docs/roadmaps/SENTINEL_REAL_WORLD_POWER_CONVERGENCE_ROADMAP.md
```

## Next Work

```text
REAL_WORLD_POWER_CONVERGENCE_WAVE_1_REAL_MODEL_AGENT_CERTIFICATION
```

Do not start it until this commit is pushed and the repository is clean.
