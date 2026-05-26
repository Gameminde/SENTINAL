# Sentinel Power Lab Runtime V0 Report

Date: 2026-05-26

Status: locked locally after implementation and targeted verification.

## Objective

Make Sentinel runnable as a real operator shell without adding any new
dangerous actuator.

This pack turns the existing internal runtime into a visible local execution
surface:

```text
mission file -> CLI/operator shell -> AgentRuntime.run() -> run artifacts
```

## Files Added

```text
sentinel-control/services/sentinel-core/sentinel/power_lab.py
sentinel-control/services/sentinel-core/sentinel/cli.py
sentinel-control/services/sentinel-core/sentinel/__main__.py
sentinel-control/services/sentinel-core/tests/test_sentinel_power_lab_runtime_v0.py
sentinel-control/docs/reviews/SENTINEL_POWER_LAB_RUNTIME_V0_REPORT.md
```

## Files Updated

```text
sentinel-control/services/sentinel-core/pyproject.toml
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/organs/ORGAN_EXECUTION_EXPANSION_ROADMAP.md
```

## Implemented Runtime Surface

The new operator shell supports:

- `python -m sentinel run --mission <file.json> --run-root <dir>`;
- installed script entry point `sentinel = sentinel.cli:main`;
- structured JSON mission files;
- `MissionAuthorityEnvelope` construction from the mission file;
- default-off runtime execution config;
- optional existing L2/L3 or L4 browser-perception organ dispatch depending on
  preset;
- run directory creation;
- safe input artifact;
- trace artifact;
- result summary artifact;
- Power Kernel status artifact;
- optional replan, organ dispatch, and memory feedback artifacts when present.

## Artifact Contract

Each run writes:

```text
input.mission.json
trace.events.json
result.summary.json
power_kernel_status.json
```

When available, it may also write:

```text
replan.packet.json
organ.dispatch.result.json
memory.feedback.result.json
```

All artifacts are measurement data only.

## Presets

Implemented:

- `lab_local`;
- `browser_perception`;
- `operator_browser_l5_template`;
- `full_power_template`.

Important distinction:

```text
operator_browser_l5_template and full_power_template are non-executing
templates in V0.
```

## Boundaries Held

```text
No new dangerous actuator.
No browser submit.
No browser login.
No upload/download.
No arbitrary browser JavaScript.
No credential value storage.
No credential use by organs.
No API mutation.
No channel send.
No shell/process execution.
No desktop action.
No payment/spend/trading.
No provider fallback.
No AUTO routing.
No model/provider/backend override.
No memory/receipt/certificate as authority.
```

## Status Table

| Segment | Status | Evidence |
|---|---:|---|
| CLI entry point | CLOSED | `test_power_lab_cli_entrypoint_runs_mission` |
| JSON mission file loading | CLOSED | `test_power_lab_input_builds_real_authority_envelope` |
| AgentRuntime invocation | CLOSED | `test_power_lab_runs_json_mission_and_writes_artifacts` |
| Run artifacts | CLOSED | `test_power_lab_runs_json_mission_and_writes_artifacts` |
| Default-off dangerous power | CLOSED | `test_power_lab_default_preset_does_not_enable_dangerous_power` |
| Explicit L2/L3 opt-in config | CLOSED | `test_power_lab_can_enable_existing_local_organs_only_with_explicit_opt_in` |
| Secret-like mission rejection | CLOSED | `test_power_lab_rejects_secret_like_input_without_echoing_secret` |
| Dangerous action preflight rejection | CLOSED | `test_power_lab_rejects_forbidden_dangerous_actions` |
| Live browser backend | NOT_STARTED | separate pack |
| Shell/code sandbox | NOT_STARTED | separate pack |
| Real credential storage/use | NOT_STARTED | separate pack |
| Continuous multi-agent orchestrator | NOT_STARTED | separate pack |

## Next Pack

```text
BROWSER_OPERATOR_AGENT_L4_L5_LIVE
```

Alternative if we want builder power before browser power:

```text
SHELL_CODE_APP_BUILDER_SANDBOX_V0
```

Recommended next move:

```text
BROWSER_OPERATOR_AGENT_L4_L5_LIVE
```

Reason:

```text
It produces the first visible external power while keeping submit/login/payment
blocked in v0.
```
