# Sentinel Interactive Exploration Trajectory Quality Audit V1

Status: COMPLETED_WITH_REMEDIATION
Primary run: `C:\Users\youcefcheriet\.sentinel-runs\self-exploration\20260616-213422`
No provider call executed during this audit.

## Executive Summary

The 24-turn self-exploration run proved that a real model can navigate a frozen repository snapshot with bounded read-only tools. It did not prove deep architecture understanding.

The trajectory was safe enough for a read-only experiment, but inefficient and shallow:

- 24 exploration turns.
- 27 total model calls including report stages.
- 84,612 cumulative tokens.
- 23 evidence entries.
- 19 unique evidence-content hashes.
- 4 exact duplicate evidence entries.
- 1 failed finish action costing 5,817 tokens.
- Stage A report produced.
- Stage B report failed empty.

## Action Distribution

| Action | Count | Quality note |
|---|---:|---|
| `list_directory` | 13 | overused; repeated same directory multiple times |
| `read_file_segment` | 7 | useful but focused on CLI/entrypoints |
| `search_text` | 3 | one exact duplicate query |
| `finish_exploration` | 1 | invalid shape; rejected before final report |

## Evidence Novelty

| Metric | Value |
|---|---:|
| Total evidence entries | 23 |
| Unique content hashes | 19 |
| Exact duplicate entries | 4 |
| Productive as recorded by old harness | 23 |
| Productive under new novelty model | 19 or fewer |

Exact duplicate examples:

- E11 duplicated E6 for `sentinel-control/services/sentinel-core/sentinel`.
- E13 duplicated E6 for the same target.
- E20 duplicated E6 for the same target.
- E21 duplicated E17 for `add_parser`.

## Token Economics

| Metric | Value |
|---|---:|
| Exploration input tokens | 43,739 |
| Exploration output tokens | 30,691 |
| Exploration total tokens | 74,430 |
| Full run cumulative tokens | 84,612 |
| Failed finish action tokens | 5,817 |
| Exact duplicate-observation token estimate | 14,573 |
| Duplicate plus failed-finish waste estimate | 20,390 |

Approximate token waste from exact duplicate observations and failed finish: 27.4 percent of exploration tokens.

## Coverage Reconstruction

| Category | Coverage level in 24-turn run |
|---|---|
| Entrypoint | implementation read |
| Mission lifecycle | not visited |
| Authority path | not visited |
| AgentRuntime | not visited |
| PowerRuntime | not visited |
| Telemetry | not visited |
| Receipts | not visited |
| FinalGate | not visited |
| Replay | not visited |
| Memory | not visited |
| Worker Fleet | not visited |
| Daemon/Scheduler | not visited |
| Browser or organ path | directory-only |
| Credential special authority | not visited |
| Financial/account special authority | not visited |

Files directly read:

- `README.md`
- `sentinel/__init__.py`
- `sentinel/__main__.py`
- `sentinel/cli.py`

## Trajectory Failure Modes

1. The agent favored directory browsing over call-path tracing.
2. Repeated directory evidence was treated as productive.
3. The finish action mixed report fields into a strict action envelope.
4. No generic depth gate existed before remediation.
5. Context included repeated evidence and boilerplate instead of a compact coverage map.

## Remediation Applied

The interactive harness now includes:

- `novelty_status` on evidence entries.
- Duplicate content and duplicate target detection.
- Generic finish depth gate.
- Coverage categories based on evidence, not model claims.
- Nonproductive-loop pressure for duplicate evidence.
- Tests for duplicate evidence and depth-gated finish.

## New Novelty Model

A turn is productive only when it contributes at least one of:

- new content hash
- new target or file segment
- new symbol or search relationship
- new evidence-linked fact
- supported hypothesis revision
- rejected hypothesis
- new validated finding candidate
- new maturity classification evidence

Duplicate evidence is marked `DUPLICATE_EVIDENCE` or `DUPLICATE_TARGET`.

## Remaining Limits

- Near-duplicate semantic observations are not yet clustered.
- Coverage categories are generic and evidence-based, but not proof of deep correctness.
- A future context compiler should transmit a coverage map and last relevant turns instead of repeated historical observations.

## Recommendation

Do not run another full self-exploration until:

1. Stage B has a segmented diagnostic lane.
2. Depth-gated exploration is used.
3. Duplicate evidence is shown to the model as already known.
4. Token budgets include novelty and coverage metrics, not only turn count.
