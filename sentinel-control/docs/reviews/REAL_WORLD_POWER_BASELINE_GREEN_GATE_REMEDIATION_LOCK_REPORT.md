# Real-World Power Baseline Green Gate Remediation Lock Report

Recorded at: 2026-06-14

## Verdict

`REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION` is locked.

```text
current_phase = REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION_LOCKED
previous_phase = REAL_WORLD_POWER_BASELINE_AND_AGENTLAB_TASK_AUDIT_LOCKED
next_phase = REAL_WORLD_POWER_CONVERGENCE_WAVE_1_CODING_WORKSPACE_AND_BROWSER_LIVE_POWER
full canonical core suite = 2686 passed, 0 failed, 3 skipped
```

This was a narrow zero-growth remediation. It added no capability, actuator,
special authority, provider, connector, contract family, UX surface, or vendor
runtime. Convergence Wave 1 and Security Testing Special Authority were not
started.

## Failure Classification And Closure

| Failure | Classification | Root cause | Closure |
|:--|:--|:--|:--|
| `test_browser_final_capability_lock_docs_mark_roadmap_complete` | `STALE_TEST_EXPECTATION` | A historical browser lock test pinned the repository's top-level current phase to `PERSISTENT_SEMANTIC_MEMORY_V1_LOCKED`. | Replaced the stale literal with a stronger invariant: README, Current State Lock, and Master Roadmap must agree on the canonical current phase. Historical browser lock assertions remain. |
| `test_unsafe_browser_neural_signal_refs_are_hashed_before_memory_or_replan` | `CURRENT_RUNTIME_DEFECT` | Brain safety evaluated raw mixed browser-neural source refs before AgentRuntime's later normalization, rejecting the whole valid motor proposal and losing safe continuity ref `nsig_planner`. | Valid browser-neural motor artifacts now have unsafe refs hashed before Brain safety while safe refs are preserved; the normalized artifact hash is recomputed. |

## Browser-Neural Authority And Integrity Review

The pre-Brain normalization is deliberately narrow:

```text
only existing_proposal_artifacts are considered
only dict-shaped valid MotorProposalArtifact records are normalized
the original artifact hash and non-execution invariants must validate first
only browser-neural source ref fields are normalized
mission id and all authority/runtime fields remain unchanged
invalid or tampered artifacts remain rejected
unrelated unsafe cognition payloads remain rejected
```

The correction does not grant authority or introduce a direct execution path.
Brain, MissionAuthorityEnvelope, Gate/runtime dispatch, receipts, FinalGate,
memory, and replay boundaries remain in place.

## Continuity Impact

```text
mission continuity = preserved
safe browser-neural recovery refs = preserved
unsafe browser-neural refs = hash-only before persistence/replan
invalid motor artifact = fail closed
unrelated unsafe cognition payload = fail closed
checkpoint/resume = unchanged
receipt/FinalGate correlation = unchanged existing path
replay = unchanged / no re-execution
```

## TDD And Regression Evidence

```text
original baseline failures reproduced together = 2 failed
invalid-motor-artifact anti-laundering regression = RED before final guard
focused stale-truth + neural regression = 7 passed in 20.43s
browser runtime/session/neural slice = 115 passed in 126.26s
workflow/replan/checkpoint/replay slice = 116 passed in 27.77s
Gate/FinalGate/evidence slice = 226 passed in 62.01s
provider/skip-reason inspection slice = 116 passed, 3 skipped in 42.48s
compileall = OK
```

## Complete Suite Green Gate

Canonical command, run from
`sentinel-control/services/sentinel-core`:

```text
py -3.13 -m pytest -o addopts="" -q tests
collected = 2689
passed = 2686
failed = 0
skipped = 3
duration = 687.39 seconds
```

Known skips:

| Test surface | Reason |
|:--|:--|
| OpenRouter real provider | `OPENROUTER_API_KEY` absent; real provider call skipped. |
| NVIDIA real provider | `NVIDIA_API_KEY` absent; real provider call skipped. |
| Groq real provider | `GROQ_API_KEY` absent; real provider call skipped. |

## Self-Audit Findings

| Severity | Finding | Decision |
|:--|:--|:--|
| P2 | Historical test asserted a superseded top-level phase. | Fixed with cross-document current-phase invariant. |
| P2 | Valid mixed-ref browser motor proposal lost safe continuity ref. | Fixed before Brain safety with integrity-gated normalization. |
| P1 prevented | Pre-Brain normalization could launder a tampered artifact if integrity were not checked first. | RED regression added; normalization restricted to valid original `MotorProposalArtifact`. |
| P1 prevented | Browser-neural normalization could accidentally permit unrelated unsafe cognition data. | Regression proves unrelated unsafe payload still fails closed with no execution. |

Open P0/P1 or serious P2 findings in this remediation scope: none.

## Boundaries Preserved

```text
new capability = NOT_ADDED
new execution surface = NOT_ADDED
new actuator family = NOT_ADDED
new special authority = NOT_ADDED
direct organ bypass = NOT_ADDED
provider fallback/AUTO = NOT_ADDED
vendor runtime = NOT_INTEGRATED
raw credential/provider-key persistence = NOT_ADDED
Wave 1 = NOT_STARTED
Security Testing Special Authority V1 = NOT_STARTED
```

## Files Changed

Runtime and tests:

```text
sentinel-control/services/sentinel-core/sentinel/agent/runtime.py
sentinel-control/services/sentinel-core/tests/test_browser_final_capability_lock.py
sentinel-control/services/sentinel-core/tests/test_browser_neural_memory_feedback_lock.py
```

Truth and report files:

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/docs/roadmaps/SENTINEL_REAL_WORLD_POWER_CONVERGENCE_ROADMAP.md
sentinel-control/docs/reviews/SENTINEL_REAL_WORLD_POWER_BASELINE.md
sentinel-control/docs/reviews/SENTINEL_PRODUCT_POWER_SCORECARD.md
sentinel-control/docs/reviews/REAL_WORLD_POWER_BASELINE_AND_AGENTLAB_TASK_AUDIT_LOCK_REPORT.md
sentinel-control/docs/reviews/REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION_LOCK_REPORT.md
```

## Next Phase

```text
REAL_WORLD_POWER_CONVERGENCE_WAVE_1_CODING_WORKSPACE_AND_BROWSER_LIVE_POWER
```

It remains next and was not started.
