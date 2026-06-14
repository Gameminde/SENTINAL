# Real-World Power Convergence Wave 1 - Benchmark Report

Date: 2026-06-14

## Verdict

```text
wave_status = PARTIALLY_CLOSED
coding_workspace_backend = BACKEND_CERTIFIED / AGENT_LEVEL_NOT_RUN
browser_backend = LIVE_BOUNDED / CONTROLLED_FIXTURE_CERTIFIED
reliability = REPEATED_VERTICAL_EVIDENCE / NO_LONG_SOAK
```

Wave 1 converts existing Sentinel workspace, shell, browser, MissionRunStore,
telemetry, receipt, FinalGate, and replay surfaces into repeated vertical task
proof. It does not certify a real-model coding agent, browser process-restart
continuity, or long-duration soak reliability.

## Benchmark Environment

```text
coding_fixture = deterministic local multi-file Python repository
browser_fixture = controlled example.com Playwright document fixtures
external mutation = none
real accounts = none
real credentials = none
provider calls = none
vendor runtime = none
```

## Coding / Workspace Tasks

| Task | Result | Evidence | Honest limit |
| --- | --- | --- | --- |
| C1 repository inspection | PASS | Project structure, relevant source/test, misleading nearby file, and test command identified from controlled repository | Textual/local inspection; no LSP claim |
| C2 multi-file edit | PASS | Two related files changed through `L3ReversibleWorkspaceExecutor`; before/after hashes differ; unrelated user note preserved | Backend-driven deterministic repair |
| C3 failure diagnosis and repair | PASS | Targeted pytest fails, two-file root cause repair executes, targeted pytest passes | Diagnosis is encoded in deterministic benchmark, not a real-model reasoning certification |
| C4 regression completion | PASS | Full controlled repository pytest passes with shell receipt and FinalGate | Small deterministic repository |
| C5 interrupted resume | PARTIAL PASS | Durable workflow regression proves checkpoint resume without repeated certified step; vertical coding task proves stale completed mutation is blocked by before-hash mismatch | Actual L3 multi-file edit was not resumed across a new process/workflow instance |
| C6 rollback | PASS | Both edits rollback through atomic replace and original hashes/content are restored | Text workspace rollback only |

Repeatability:

```text
runs = 5
passes = 5
failures = 0
median_duration = 6.743 seconds
p95_duration = 8.083 seconds
human_interventions = 0
silent_success = 0
duplicate_material_side_effects = 0
cross_mission_contamination = 0
```

## Browser Tasks

| Task | Result | Evidence | Honest limit |
| --- | --- | --- | --- |
| B1 multi-step navigation | PASS | Real Playwright engine, persistent session, controlled page/form sequence, evidence hashes | Repository-controlled fixture, not public SaaS |
| B2 multi-tab | PASS | Bounded live open/switch/close tabs, tab ids/counts, contract-bound limits, cross-mission block | No browser process-restart restoration |
| B3 form preparation and submit | PASS | Ordinary typed preparation plus existing L6 special-authority submit, before/after evidence, receipt, FinalGate | Controlled non-sensitive form only |
| B4 upload/download | PASS | Approved upload root, download quarantine, file hashes, receipt, FinalGate | Controlled fixture only |
| B5 login checkpoint | PASS | Credential-bearing ordinary session input blocks before execution | No real login or credential lease exercised |
| B6 changed-page recovery | PASS | Old target disappears, stale target fails honestly, re-observed replacement target completes | Deterministic DOM change |
| B7 browser failure recovery | PASS | Missing target is classified and the authorized corrected target succeeds with timeline continuity | No browser process crash recovery |
| B8 kill/revocation boundary | PASS | Revoked/expired authority blocks next action, safe close remains possible, closed session blocks, fresh mission has no form-state leak | Close/revocation boundary, not OS-process restart |

Repeatability:

```text
runs = 10
passes = 10
failures = 0
median_duration = 11.606 seconds
p95_duration = 37.127 seconds
human_interventions = 0
silent_success = 0
duplicate_material_side_effects = 0
cross_mission_contamination = 0
```

## Reliability And Recovery

Proven:

```text
induced targeted-test failure = detected honestly
stale workspace mutation = blocked
atomic workspace mutation and rollback = proven
changed browser target = recovered
browser credential boundary = blocked
browser revocation/expiry = rechecked before each non-close step
browser contract expansion after open = blocked
browser max-step and max-tab limits = enforced
closed browser session = cannot act
fresh mission = no prior form-state leakage
timeline chains = verified
certified local telemetry = verified
replay = evidence-only / no re-execution
```

Not yet proven:

```text
real-model coding agent
coding mutation resumed across a process restart
browser session restored across a process restart
multi-hour soak
public SaaS mutation
```

## Scores

| Domain | Before | After | Evidence decision |
| --- | ---: | ---: | --- |
| Coding / Workspace | 5.5 | 7.5 | Repeated controlled inspect/edit/test/repair/regression/rollback backend task passes; no real-model agent certification |
| Browser | 6.5 | 7.5 | Full controlled live browser task set passes; process-restart continuity and public SaaS task corpus remain unproven |
| Reliability | 6.0 | 7.5 | Repeated induced-failure, stale-state, kill/revocation, evidence, and isolation proof passes; no long soak or full process-restart convergence |
| Overall real-world product power | 5.4 | 5.7 | Existing unweighted scorecard method with only evidence-supported domain increases |

No domain is raised to `8.0`.

## Certification Status

```text
backend_certification = PASS
agent_level_certification = NOT_RUN
browser_controlled_live_certification = PASS
browser_public_saas_certification = NOT_RUN
wave_full_lock = BLOCKED_BY_UNMET_8_10_GATES
```
