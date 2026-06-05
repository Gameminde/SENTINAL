# SANDBOX_SHELL_CODE_ORGAN_V1 Report

Recorded at: 2026-06-05

## Current State

`SANDBOX_SHELL_CODE_ORGAN_V1` is implemented as the first real shell/code
actuator for the Power Actuator Fabric. It is not an unrestricted shell. It
executes only allowlisted development commands through `subprocess.run` with
`shell=False`.

## Files Added / Updated

```text
sentinel-control/services/sentinel-core/sentinel/agent/organs/sandbox_shell_code_organ_v1.py
sentinel-control/services/sentinel-core/tests/test_sandbox_shell_code_organ_v1.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/__init__.py
```

## Allowed V1 Command Prefixes

```text
python -m pytest
python -m compileall
npm test
npm run build
node --version
python --version
```

## Safety Contract

```text
shell=True = FORBIDDEN
command string interpolation = FORBIDDEN
cwd escape outside project_root = BLOCKED
forbidden shell metacharacters = BLOCKED
non-allowlisted command = BLOCKED
secret-like command/env values = BLOCKED
env = scrubbed allowlist only
timeout = enforced
stdout/stderr durable data = hash + redacted excerpt only
file diff receipt = CLOSED
artifact hashes = CLOSED
kill switch pre-execution block = CLOSED
FinalGate certificate = CLOSED
PowerRuntime executor adapter = CLOSED
```

## Non-Scope

```text
unrestricted host shell = NOT_STARTED
arbitrary Python code execution = NOT_STARTED
dependency install authority = NOT_STARTED
networked shell commands = NOT_STARTED
desktop/process/app launch = NOT_STARTED
API/channel/payment/trading execution = NOT_STARTED
credential use = NOT_STARTED
provider fallback/AUTO routing = NOT_APPROVED
```

## Verification

```text
py -3.13 -m pytest tests/test_sandbox_shell_code_organ_v1.py -q = 7 passed
```

## Next Recommended Pack

```text
EXTERNAL_API_READ_WRITE_ORGAN_V1
```
