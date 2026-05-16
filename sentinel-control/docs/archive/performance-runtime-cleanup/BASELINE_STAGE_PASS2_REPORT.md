# Baseline Stage Pass 2 Report

## Scope

Manual patch pass for the Phase A-E performance-runtime baseline.

Rules honored:

- No commit.
- No Phase F implementation.
- No `git add .`.
- No broad-directory staging.
- `runtime.py` and `runner.py` were not staged as whole worktree files.
- Browser/organ/full-system-audit files remain excluded from the baseline index.

## EOF Whitespace Fix

Fixed the cached diff check issue in:

- `.kiro/specs/sentinel-performance-runtime-foundation/design.md`

Action:

- Removed the new blank line at EOF.
- Re-staged the file with `git add -f`.
- No content change beyond the EOF whitespace cleanup.

Result:

- `git diff --cached --check` now exits `0` with no output.

## shared/events.py Decision

Staged:

- `sentinel-control/services/sentinel-core/sentinel/shared/events.py`

Classification:

- Cross-phase dependency included intentionally.

Reason:

- Staged perf modules/tests import `sentinel.shared.events`.
- Without it, the Phase A-E baseline index is incomplete.

Content review:

- Reviewed the file content.
- Searched for obvious secret/generated markers: `SECRET`, `TOKEN`, `PASSWORD`, `PRIVATE KEY`, `BEGIN`, `api_key`, `sk-`, `ghp_`, `AKIA`, `Bearer`.
- No matches found.
- File contains shared event primitives/enums plus additive performance event types.

## runtime.py Manual Patch Staging

Staged path:

- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`

Staging method:

- Manual index patch via generated index content and `git update-index --cacheinfo`.
- The worktree file remains dirty (`MM`) because unrelated/full-system-audit hunks are intentionally unstaged.

Staged performance-runtime hunks:

- Imports needed by perf runtime integration:
  - `asyncio`
  - `uuid`
  - `TYPE_CHECKING`
  - `Callable`
  - `ConfigDict`
  - `SentinelModel`
  - `AgentContext`
- TYPE_CHECKING imports for:
  - `ContextBuildCache`
  - `LLMDecisionFrameCache`
  - `PromptFrameCache`
  - `TokenBudgetGovernor`
  - `CostProfiler`
  - `LatencyProfiler`
  - `AsyncOrganScheduler`
  - `SubmissionAck`
  - `BackpressureController`
  - `OrganAuthorityEnvelope`
  - `OrganDryRunReceipt`
  - `OrganKillSwitch`
- `_ToolCallSchedulerAction`.
- Optional default-off constructor injections for:
  - latency profiler
  - cost profiler
  - context build cache
  - prompt frame cache
  - decision frame cache
  - token budget governor
  - async organ scheduler
  - backpressure controller
- Stored injected fields for the same default-off integrations.
- `ContextBuildCache` integration at the real `ContextBuilder.build` call site.
- `LatencyProfiler` instrumentation around:
  - context build
  - context compression
  - cognitive-cycle orient
  - controlled tool-call paths
- Scheduler path eligibility for non-browser controlled tool calls.
- `_route_local_tool_call_through_scheduler`.
- `_build_decision_frame_cached`.
- `_render_prompt_text_cached`.
- `_enforce_frame_budget`.

Explicitly excluded runtime.py hunks:

- `CoreFinalGate` import.
- `_final_gate` field.
- `_assert_memory_not_authority_boundary`.
- Memory-not-authority phase transition checks.
- Original allowed-actions capture for memory-not-authority enforcement.
- `_apply_final_gate`.
- Return wrapping through `_apply_final_gate`.
- Full-system-audit fallback return wrapping.
- Unrelated final-gate / browser / full-system-audit behavior.

Index verification:

- Cached diff scan found no staged occurrences of:
  - `CoreFinalGate`
  - `_assert_memory_not_authority_boundary`
  - `_apply_final_gate`
  - `full-system`
  - `memory-not-authority`

Additional syntax check:

- Compiled the staged index version of `runtime.py` directly from `git show :path`.
- Result: staged syntax OK.

## runner.py Manual Patch Staging

Staged path:

- `sentinel-control/services/sentinel-core/sentinel/mission/runner.py`

Staging method:

- Manual index patch via generated index content and `git update-index --cacheinfo`.
- The worktree file remains dirty (`MM`) because revocation/browser-route hunks are intentionally unstaged.

Staged performance-runtime hunks:

- TYPE_CHECKING imports for:
  - `ColdReceiptStore`
  - `HotMissionCache`
  - `ReceiptIndex`
  - `LatencyProfiler`
- Optional default-off constructor injections for:
  - latency profiler
  - hot cache
  - cold store
  - receipt index
- Stored profiler/hot/cold/index fields.
- `run_mission` profiler start/stop wrapper.
- Hot cache set/evict wrapper behavior.
- Original mission body moved behind `_do_run_mission` without revocation/cancellation additions.

Explicitly excluded runner.py hunks:

- `CancellationToken`.
- `MissionRevokedException`.
- `BrowserOperatorRouteRejected`.
- `cancellation_token` propagation.
- Revocation polling.
- `MissionStatus.REVOKED` terminal branch.
- `_check_revocation`.
- Browser operator route exception wrapping.

Index verification:

- Cached diff scan found no staged occurrences of:
  - `CancellationToken`
  - `MissionRevokedException`
  - `BrowserOperatorRouteRejected`
  - `REVOKED`
  - `_check_revocation`
  - `revocation`
  - `browser_operator_route_adapter_failed`

Additional syntax check:

- Compiled the staged index version of `runner.py` directly from `git show :path`.
- Result: staged syntax OK.

## Cached Diff State

Command:

```bash
git diff --cached --stat
```

Summary:

```text
69 files changed, 23642 insertions(+), 19 deletions(-)
```

Key staged categories:

- `.kiro/specs/sentinel-performance-runtime-foundation/*` spec/report/backlog files.
- `sentinel-control/services/sentinel-core/pyproject.toml`.
- `sentinel/perf/*`.
- `tests/perf/*`.
- `sentinel/shared/events.py`.
- Manual partial index content for:
  - `sentinel/agent/runtime.py`
  - `sentinel/mission/runner.py`

Command:

```bash
git diff --cached --check
```

Result:

```text
exit 0, no output
```

## Tests Run

From:

```text
sentinel-control/services/sentinel-core
```

Command:

```bash
python -m pytest tests/perf/ -m "not slow" -q
```

Result:

```text
exit 0
100%
```

Command:

```bash
python -m pytest tests/test_agent_runtime.py -q
```

Result:

```text
14 passed
exit 0
```

Important note:

- The pytest commands run against the current worktree, while `runtime.py` and `runner.py` are partially staged in the index.
- To reduce this risk, the staged index versions of both files were separately syntax-compiled from `git show :path`.

## Remaining Unstaged Files Summary

Expected intentionally unstaged categories:

- Baseline planning/report docs:
  - `sentinel-control/docs/BASELINE_PLAN.md`
  - `sentinel-control/docs/BASELINE_STAGING_AUDIT.md`
  - `sentinel-control/docs/BASELINE_STAGE_PASS1_REPORT.md`
- Current lock doc:
  - `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- Runtime files with intentionally excluded hunks:
  - `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
  - `sentinel-control/services/sentinel-core/sentinel/mission/runner.py`
- Browser/organ/full-system-audit tracked files.
- Browser/organ/full-system-audit untracked files.
- Gate/final-gate/revocation tests and modules.
- Temporary/generated local files:
  - `sentinel-control/services/sentinel-core/_junit.xml`
  - `sentinel-control/services/sentinel-core/_tmp_cold_store_smoke.py`

Do not include these in the Phase A-E baseline commit unless separately triaged and approved.

## Final Verdict

READY_TO_COMMIT.

The staged baseline index is clean under `git diff --cached --check`, includes the accepted `shared/events.py` cross-phase dependency, stages only manual performance-runtime hunks from `runtime.py` and `runner.py`, and leaves unrelated browser/organ/full-system-audit changes out of the baseline index.

No commit was made.

Phase F was not started.
