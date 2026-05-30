# Browser Trajectory Planner And Self-Healing L5 Report

Recorded at: 2026-05-31

Pack:

```text
BROWSER_TRAJECTORY_PLANNER_AND_SELF_HEALING_L5
```

## Current State

Sentinel already had a live browser operator, a persistent browser session
manager, and a CloakBrowser primary adapter with Playwright compatibility. This
pack adds a planning layer above those pieces: it converts observed browser
accessibility evidence into ranked, hash-bound L5 target attempts, then executes
through the session manager with deterministic recovery if the first target
misses.

This is still governed browser power. The pack does not add submit/login,
credentialed browsing, upload/download, arbitrary JavaScript, channel send, API
mutation, shell, desktop, payment, spend, or trading.

## Models And Contracts Added

Implemented in:

```text
sentinel/agent/organs/browser_trajectory_planner_l5.py
```

Models:

- `BrowserTrajectoryActionKind`
- `BrowserTrajectoryStatus`
- `BrowserTrajectoryContract`
- `BrowserTrajectoryRequest`
- `BrowserTrajectoryPlanStep`
- `BrowserTrajectoryPlan`
- `BrowserTrajectoryReceipt`
- `BrowserTrajectorySafetyValidationResult`
- `BrowserTrajectoryResult`
- `BrowserTrajectoryPlannerL5`

The contract is explicit and mission-bound. It requires allowed domains,
allowed action kinds, source observation hashes, session refs, receipt posture,
and FinalGate posture. The typed text payload is never persisted as raw text;
only a `text_hash` is carried in plan and receipt data.

## Harvest Signal

This pack follows the local Agent Lab direction: browser power should be a live
operator surface, not just read-only evidence. The harvested pattern is not a
vendor runtime import. The pattern is:

```text
observe -> rank targets -> execute bounded action -> recover on miss -> receipt
```

The Sentinel rewrite keeps target planning separate from backend execution and
routes actual action through the existing session manager.

## Target Ranking

The planner consumes `BrowserAccessibilitySnapshot.refs` from the live session
manager and ranks candidates by:

- requested role;
- target name hint;
- objective summary tokens;
- element enabled/disabled posture;
- field-like role compatibility;
- stable selector/ref ordering.

The ranking is deterministic. It produces hashed plan metadata and reasons
without storing raw secrets or raw typed text.

## Self-Healing Recovery

If a first ranked target fails, the planner tries the next ranked candidate up
to the configured attempt budget. Each attempt is represented in the plan and
the final result records the execution receipt from the successful or final
attempt.

Recovery is bounded. It does not create authority, expand the mission envelope,
or infer permission from page content.

## CLI

Added:

```text
python -m sentinel browser-trajectory-demo --mission <file.json> --url <https-url> --run-root <dir> --target-role textbox --target-hint Email --text <value>
```

The CLI opens a scoped browser session, captures an accessibility snapshot,
runs the trajectory planner, writes a safe result artifact, and closes the
session.

## Boundaries Held

```text
Browser submit = BLOCKED
Browser login = BLOCKED
Credentialed session = NOT_STARTED
Upload/download = BLOCKED
Arbitrary JavaScript = BLOCKED
API mutation = BLOCKED
Channel send = BLOCKED
Shell/process = BLOCKED
Desktop action = BLOCKED
Payment/spend/trading = BLOCKED
Provider fallback/AUTO routing = BLOCKED
Authority expansion = BLOCKED
Raw typed text durability = BLOCKED
```

## Truth Table

| Segment | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Trajectory target ranking | CLOSED | `test_trajectory_ranks_accessible_targets_and_hashes_plan` | Uses AX refs and deterministic heuristics, not a learned policy yet |
| Source snapshot binding | CLOSED | `test_trajectory_blocks_unbound_or_mismatched_observation` | Requires caller to provide source snapshot metadata |
| Self-healing target recovery | CLOSED | `test_trajectory_execute_self_heals_wrong_target_name_and_preserves_state` | Recovery is bounded to ranked candidates |
| Session manager integration | CLOSED | `BrowserSessionManagerL5Live.snapshot_for_session(...)` and trajectory execution test | Live backend still depends on installed browser backend |
| CLI trajectory demo | CLOSED | CLI subcommand implemented and compile-checked | Manual live URL validation remains operator-run |
| Raw typed text durability | CLOSED | `test_trajectory_blocks_unsafe_payloads_and_does_not_persist_raw_text` | Hashes are stored; raw text is not |
| Submit/login/credential routes | NOT_STARTED | Safety tests and scanner boundaries | Separate special-authority L6 pack required |

## Verification

Fresh verification run during this pack:

```text
python -m pytest tests/test_browser_trajectory_planner_l5.py -q
python -m pytest tests/test_browser_session_manager_l5_live.py tests/test_browser_operator_agent_l4_l5_live.py tests/test_agent_browser_operator_runtime_integration.py tests/test_agent_browser_operator_runtime_minicorpus.py -q
python -m pytest tests/test_organ_safety_scanner_consolidation.py -q
python -m pytest tests/test_sentinel_power_lab_runtime_v0.py -q
python -m pytest tests -k browser -q
python -m compileall -q sentinel
git diff --check
```

Result:

```text
6 passed
31 passed
16 passed
7 passed
398 passed with -k browser
compileall OK
git diff --check OK
secret/provider-key scan clean
```

## Next Pack

```text
BROWSER_FORM_SUBMIT_SPECIAL_AUTHORITY_L6
```

The next pack should promote submit-grade browser power explicitly, not smuggle
submit through generic click/type. It should require stronger authority,
before/after evidence, form intent proof, forbidden field detection, and a
separate FinalGate posture.
