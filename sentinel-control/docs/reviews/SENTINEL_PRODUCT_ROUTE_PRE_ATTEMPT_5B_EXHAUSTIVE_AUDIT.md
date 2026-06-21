# SENTINEL PRODUCT ROUTE PRE-ATTEMPT 5B EXHAUSTIVE AUDIT

Audit pack:

```text
SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1
PRE_ATTEMPT_5B_EXHAUSTIVE_PRODUCT_ROUTE_AUDIT
```

Base commit:

```text
2f7c078b6c24c41321617d4b47e31a58d852c023
```

## Audit Verdict

```text
decision = ATTEMPT_5B_READY
provider calls during audit = 0
source code changes during audit = 0
Pack 4 started = NO
push performed = NO
```

Attempt 5B is structurally ready only with the corrected filesystem layout:

```text
Sentinel run root:
  C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5b-<timestamp>\runs

Disposable external workspace:
  C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
```

Attempt 5 failed because its workspace was under `.sentinel-runs`, which is intentionally blocked by `ProductExecutionBinding`.

## Evidence Summary

Repository state:

```text
HEAD = 2f7c078b6c24c41321617d4b47e31a58d852c023
branch = experimental/real-model-lab-freeze-v1
working tree before report = clean
```

Focused fake-provider validation:

```text
py -3.13 -m pytest -q tests/test_cli_runtime_host_product_wiring_pack1b.py
result = 12 passed

py -3.13 -m pytest -q tests/test_cockpit_mission_understanding_protocol_v2.py
result = 21 passed

py -3.13 -m pytest -q tests/operator/test_product_nervous_system_pack3.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py
result = 31 passed
```

External workspace audit:

```text
workspace = C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
exists = true
directory = true
git clean = true
frozen commit = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
outside .sentinel-runs = true
outside Downloads = true
outside Sentinel source repo = true
```

Binding dry check:

```text
workspace_ref = workspace:C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
model_contract_ref prefix = model_contract:aliyun_dashscope:aliyun_openai_compatible_chat:deepseek-v4-pro
capability_id = read_only_research
operation = inspect_repository
binding_hash_present = true
```

Input dry checks:

```text
model-contract.json first bytes = 7B 0D 0A
authority-scope.json first bytes = 7B 0D 0A
mission-script.txt first bytes = 55 6E 64
strict JSON load = STRICT_JSON_OK
script nonempty turns = 2
```

## Full Route Audit

| Step | Owner file/function | Required inputs | Produced outputs | Failure modes | Current evidence | Attempt 5B preflight validation | Fake-provider coverage | Remaining untested risk |
|---|---|---|---|---|---|---|---|---|
| CLI cockpit entry | `sentinel/cli.py::_run_cockpit_command` | `--model-contract`, `--authority-scope`, `--workspace`, `--script`, `--json` | product route setup or safe block | missing contract, invalid scope, invalid workspace, host failure | static trace and CLI tests | validate all paths before CLI | `test_cli_runtime_host_product_wiring_pack1b.py` | provider behavior not covered |
| UserModelContract load | `sentinel/cli.py::_load_user_model_contract` | BOMless JSON | typed `UserModelContract` | JSON/validation failure | strict JSON dry check | byte check and strict load | CLI wiring tests | real price/cost metadata may remain approximate |
| Authority scope load | `sentinel/cli.py::_load_authority_approval_scope` | BOMless approval JSON | typed `MissionAuthorityApprovalScope` | missing fields, validation failure | strict JSON dry check | byte check and strict load | workspace binding tests | none known |
| ProductExecutionBinding | `sentinel/operator/product_execution_binding.py::build_product_execution_binding` | workspace path, run root, approval scope, contract | `workspace:<abs>`, stable model contract ref | not found, not directory, sensitive root, inside run root, outside scope | external binding dry check passed | check external workspace path and allowed scope | Pack 3.4/CLI tests | setup can regress if workspace placed under `.sentinel-runs` |
| Host construction | `sentinel/operator/runtime_host.py::SentinelRuntimeHost.__init__` | factories, run root | host owns kernel/lifecycle/daemon/coordinator/dispatcher | missing provider factories in LLM mode | static trace | require factories selected | CLI product wiring test | none known |
| Cockpit construction | `sentinel/operator/cockpit.py::LLMLiveOperatorCockpit` | host lifecycle, scope, binding, model client | cockpit session | missing product binding later blocks LLM start | static trace | verify workspace binding exists | CLI tests | provider output quality |
| Cockpit V2 parsing | `sentinel/operator/llm_adapter.py`, `structured_output.py` | provider visible JSON | V2 draft, summary, or safe V2 diagnostics | malformed JSON/object, unknown fields, missing V2 fields | Pack 3.5 tests | expected parse stage `mission_understanding_v2_validation` | V2 tests and CLI Pack 3.5 tests | real model may still return invalid V2 |
| Sentinel-owned draft/summary | `structured_output.py::_validate_mission_understanding_v2` | narrow V2 object | internal `MissionDraft`, `MissionAuthoritySummary` | unsupported capability, missing title/objective/capability | static trace and tests | no direct preflight after provider-free stage | V2 tests | model may ask clarification |
| Deterministic approval | `cockpit.py::handle` and `_start` | stored draft/summary, approval turn | lifecycle `create_mission` call | no draft, no scope, binding mismatch | V2 approval test | script turn 2 exact approval | V2 and CLI tests | none known |
| Mission creation | `mission_lifecycle_service.py::create_mission` | draft, summary, scope, policy, workspace/model refs | `MissionRecord`, authority, request, queue event | authority issue failure, request persist failure, enqueue failure | lifecycle tests | request refs dry-bound | lifecycle tests | none known |
| Execution request | `MissionExecutionRequest` | capability, operation, workspace ref, model ref, envelope ref | hash-bound request | hash mismatch, fallback refs if binding absent | binding dry check | assert no `snapshot:operator_session` or `model_contract:operator_session` | CLI wiring tests | none known |
| Daemon claim | `runtime_host.py::pump_daemon_once` | queued mission, active authority | claimed request, daemon status running | inactive authority, missing request, host not started | runtime host tests | event/counter after run only | runtime host tests | real run may block later |
| Coordinator | `mission_execution_coordinator.py::decide` | verified request | persisted routing decision | request hash mismatch, unknown capability, health failed, op unsupported | Pack 3 tests | static and fake run | Pack 3 tests | none known |
| Dispatcher | `unified_execution_dispatcher.py::dispatch` | request, decision, authority | adapter execution and closeout | unknown adapter, mismatch, inactive authority, proof failure | Pack 3 tests | fake run only | Pack 3 tests | real provider action sequence may block |
| ReadOnlyResearchAdapter | `unified_execution_dispatcher.py::ReadOnlyResearchAdapter.execute` | `workspace:<abs>`, factories | read-only spine result refs | non-workspace ref, missing path, adapter exception | static trace | binding proves dispatchable workspace ref | Pack 3 tests | real model may choose bad actions |
| Provider decision client | `read_only_model_clients.py::ReadOnlyProviderDecisionClient` | context, explicit contract | typed `ReadOnlyDecision` | schema invalid, blocked provider outcome, timeout | static trace | no provider-free validation beyond fake | fake product wiring tests | real provider decision validity |
| Read-only actions | `read_only_operator_spine.py::run` | typed decisions | observations, receipts | path block, sensitive path, max turns, gate failure | Pack 3/read-only tests | no source mutation | Pack 3 tests | real model may waste turns |
| Report lane | `read_only_model_clients.py::ReadOnlyProviderReportClient` | evidence context, explicit contract | typed report result | report schema invalid, unknown evidence, timeout | static trace | no provider-free validation beyond fake | Pack 3 tests | real provider report validity |
| Proof verification | `unified_execution_dispatcher.py::_verify_completed_proof` | receipt refs, report refs, FinalGate refs | completed or blocked closeout | missing/tampered refs, unknown evidence, rejected FinalGate | Pack 3 tests | post-run only | Pack 3 tests | none known |
| FinalGate | `read_only_operator_spine.py::_record_finalgate` and dispatcher verification | receipts/report | accepted or rejected certificate | persistence failure, proof rejection | Pack 3 tests | post-run only | Pack 3 tests | none known |
| Mission terminal | `unified_execution_dispatcher.py::_persist_closeout` | verified closeout | `COMPLETED` or `BLOCKED` | transition failure | Pack 3 tests | post-run only | Pack 3 tests | none known |
| Replay | `read_only_operator_spine.py::build_replay` | existing events/artifacts | replay view with zero deltas | artifact verification failure | Pack 3 tests | post-terminal only | Pack 3 tests | only applicable if mission terminalizes |

## Known Blockers Matrix

| Attempt | Root cause | Fix type | Fixed by | Proof it cannot recur | Remaining recurrence risk |
|---|---|---|---|---|---|
| Attempt 1 | fragmented script turns | experiment setup | runbook requires exactly two nonempty turns | script preflight count and turn length checks | low, if wrapper enforces |
| Attempt 2 | broad cockpit schema failure | source/protocol | Pack 3.3 protocol V2 and Pack 3.5 activation | V2 tests and CLI product prompt checks | model may still fail V2, but diagnostic will be correct |
| Attempt 3 | missing explicit workspace binding | source | Pack 3.4 | binding dry check and CLI workspace tests | low |
| Attempt 4B | BOM in `model-contract.json` | experiment setup | BOMless writer runbook | byte checks `!= EF BB BF`, strict JSON load | low |
| Attempt 4C | legacy cockpit validation active | source | Pack 3.5 commit `2f7c078...` | CLI fake-provider test proves `mission_understanding_v2_validation` | low |
| Attempt 5 | workspace inside `.sentinel-runs` | experiment setup | Attempt 5B layout change | external workspace binding dry check passed | low if workspace is external |

## Attempt 5B Filesystem Layout

Recommended:

```text
workspace = C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
run root = C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5b-<timestamp>\runs
```

Allowed:

```text
C:\Users\youcefcheriet\sentinel-workspaces\<attempt-id>-click
```

Forbidden:

```text
C:\Users\youcef cheriet\.sentinel-runs\...
C:\Users\youcefcheriet\sentinal\...
C:\Users\youcef cheriet\Downloads\...
credential/secrets directories
the CLI run-root directory
any `.codex`, `.ssh`, `.aws`, `.azure`, `.gnupg`, `.password-store` path
```

Proof for recommended path:

```text
exists = true
directory = true
canonical absolute path = true
outside run-root = true
outside .sentinel-runs = true
outside credential/download directories = true
inside approval scope = true
git clean = true
frozen commit = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
```

## Input File Audit

Required files:

```text
model-contract.json
authority-scope.json
mission-script.txt
```

Required checks:

```powershell
[System.IO.File]::ReadAllBytes($modelContractPath)[0..2] -ne 0xEF,0xBB,0xBF
[System.IO.File]::ReadAllBytes($authorityScopePath)[0..2] -ne 0xEF,0xBB,0xBF
[System.IO.File]::ReadAllBytes($scriptPath)[0..2] -ne 0xEF,0xBB,0xBF
py -3.13 -c "import json,pathlib; json.loads(pathlib.Path(r'<model>').read_text(encoding='utf-8')); json.loads(pathlib.Path(r'<scope>').read_text(encoding='utf-8')); print('STRICT_JSON_OK')"
```

Dry results:

```text
model-contract.json first bytes = 7B 0D 0A
authority-scope.json first bytes = 7B 0D 0A
mission-script.txt first bytes = 55 6E 64
strict JSON = STRICT_JSON_OK
script nonempty turns = 2
```

Mission script must be exactly:

```text
Understand this repository deeply. Map its major packages and responsibilities. Trace how commands are declared, registered, parsed and executed. Identify at least one high-impact architectural risk, defect or maintainability gap. Produce an evidence-linked technical report with prioritized engineering recommendations. Use governed read-only research only.
Oui, commence cette mission avec le périmètre et l’autorité approuvés.
```

No API key, endpoint URL, raw prompt, raw response, raw reasoning, or provider wrapper may be persisted in these input files.

## Authority Scope Shape

Expected shape:

```json
{
  "user_id": "operator_user",
  "allowed_systems": ["local_workspace"],
  "allowed_tools": ["read_only_observation"],
  "allowed_actions": ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
  "forbidden_actions": ["payment", "send_email", "credential_access", "shell", "write_file"],
  "allowed_paths": ["C:\\Users\\youcefcheriet\\sentinel-workspaces\\attempt5b-click"],
  "allowed_domains": [],
  "allowed_accounts": [],
  "allowed_data_types": [],
  "browser_v3_authority_grants": [],
  "credential_grants": [],
  "max_duration_minutes": 20,
  "max_actions": 12,
  "max_cost_usd": 0.0
}
```

Authority audit:

```text
allowed_paths = exact external workspace
allowed_actions = read_only_research action set only
forbidden_actions preserve write/delete/shell/payment/send/credential blocks
no credential directory authority
no broad user-profile approval
no browser/channel/desktop/finance authority
```

## Cockpit V2 Activation Audit

Proven current route:

```text
CLI product route
-> LLMLiveOperatorCockpit(require_mission_understanding_v2=True)
-> OperatorConversationEngine
-> OperatorLLMConversationAdapter
-> validate_operator_structured_output(required_protocol_version="cockpit_mission_understanding_v2")
```

Expected schema-failure diagnostics now:

```text
protocol_version = cockpit_mission_understanding_v2
parse_stage = mission_understanding_v2_validation
```

Not expected:

```text
legacy_operator_decision_validation
```

The provider-facing prompt explicitly says not to emit:

```text
legacy OperatorLLMDecisionResult
MissionStartProposal
OperatorIntent
MissionDraft
MissionAuthoritySummary
```

Fake-provider proof:

```text
tests/test_cli_runtime_host_product_wiring_pack1b.py = 12 passed
tests/test_cockpit_mission_understanding_protocol_v2.py = 21 passed
```

## Deterministic Approval Audit

After a valid V2 draft:

```text
provider call count before approval = 1 cockpit mission-understanding call
provider call count added by approval turn = 0
```

The approval turn uses:

```text
stored MissionDraft
stored MissionAuthoritySummary
ProductExecutionBinding.workspace_ref
ProductExecutionBinding.model_contract_ref
MissionAuthorityApprovalScope
```

Proof path:

```text
LLMLiveOperatorCockpit.handle()
-> _is_start_confirmation()
-> _start()
-> MissionLifecycleService.create_mission()
```

## Dispatchability Audit

Dry binding produced:

```text
workspace_ref = workspace:C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
model_contract_ref prefix = model_contract:aliyun_dashscope:aliyun_openai_compatible_chat:deepseek-v4-pro
capability_id = read_only_research
operation = inspect_repository
```

The following Attempt 5 blockers should not recur with this layout:

```text
workspace_ref_not_dispatchable = not expected
workspace_sensitive_path_blocked = not expected
workspace_inside_run_root = not expected
workspace_outside_approved_scope = not expected
model_contract:operator_session fallback = not expected
snapshot:operator_session fallback = not expected
```

## Capture Wrapper Audit

Attempt 5B wrapper must persist:

```text
cli-stdout.jsonl
cli-stderr.txt
cli-exit-code.txt
cli-command-shape.txt
started-at.txt
ended-at.txt
preflight-result.json
workspace-fingerprint-before.txt
workspace-fingerprint-after.txt
```

Wrapper rule:

```text
Do not use `$ErrorActionPreference='Stop'` around native commands.
Capture native command exit codes manually.
Continue analysis even when exit code is nonzero.
```

This is required because earlier wrapper attempts failed before provider use due PowerShell native-command stderr behavior and unsupported `utf8NoBOM` encoding in Windows PowerShell.

## Safety Scan Rules

Scan run artifacts outside cloned repository content.

Included:

```text
preflight-result.json
model-contract.json
authority-scope.json
mission-script.txt
cli-stdout.jsonl
cli-stderr.txt
cli-exit-code.txt
cli-command-shape.txt
started-at.txt
ended-at.txt
workspace-fingerprint-before.txt
workspace-fingerprint-after.txt
run-root mission artifacts
```

Excluded:

```text
workspace-click cloned repository source text
```

Patterns:

```text
API key
Authorization
raw_prompt
raw_response
raw_reasoning
reasoning_content
provider wrapper payload
fallback/AUTO outside benign metadata keys
provider-native tool material
```

Benign matches:

```text
doctrine text saying not to persist raw material
test marker strings proving non-persistence
metadata value `routing_policy = explicit_user_model_contract_only`
```

Unsafe matches:

```text
literal API key
Authorization header
raw provider wrapper body
raw prompt text persisted as artifact
raw reasoning or reasoning_content persisted as artifact
provider-native tool payload
fallback/AUTO routing selection
```

## Readiness Matrix

| Check | Status | Evidence | Blocking risk | Required action |
|---|---|---|---|---|
| source clean | PASS | HEAD `2f7c078...`, git clean before report | none | keep source unchanged |
| input BOMless | PASS | dry byte checks no BOM | low | use `.NET UTF8Encoding(false)` |
| strict JSON load | PASS | `STRICT_JSON_OK` | low | run before CLI |
| script turns | PASS | 2 nonempty turns | low | freeze script |
| external workspace | PASS | `C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click` | low | do not place under `.sentinel-runs` |
| workspace approval scope | PASS | binding dry check passed | low | exact workspace in `allowed_paths` |
| model contract | PASS | Aliyun/DeepSeek typed contract loads | low | no endpoint/key in JSON |
| provider env presence | PASS WITH RUNBOOK | key file available; env not kept exported after attempts | medium if forgotten | set process-scoped env only immediately before CLI |
| V2 route activation | PASS | Pack 3.5 fake tests | model may fail schema | classify with V2 diagnostics |
| approval deterministic | PASS | V2 approval test | none known | no third turn |
| request creation | PASS | lifecycle and CLI tests | real provider must first produce valid V2 | inspect run artifacts |
| daemon claim | PASS | runtime host tests | none known | check event sequence |
| dispatcher dispatchability | PASS | Pack 3 tests and binding dry check | real model action quality | inspect dispatch events |
| read-only adapter readiness | PASS | Pack 3 tests | model may choose invalid action | preserve failure honestly |
| report lane readiness | PASS | Pack 3 tests | model may output invalid report schema | inspect report lane counters |
| FinalGate proof verification | PASS | Pack 3 tests | proof may fail if report refs bad | no false success |
| replay purity | PASS | Pack 3 tests | only applicable after terminal closeout | measure zero deltas |
| capture wrapper | PASS WITH RUNBOOK | corrected wrapper constraints identified | native PowerShell quirks | use no native-command abort |
| safety scan | PASS WITH RUNBOOK | scan rules defined | false positives from docs/tests | classify benign vs unsafe |

## Decision

```text
ATTEMPT_5B_READY
```

Reason:

```text
No source blocker remains for the product route.
The known Attempt 5 setup blocker is fixed by moving the disposable workspace outside `.sentinel-runs`.
Fake-provider tests cover V2, deterministic approval, request creation, dispatcher handoff, proof closeout, and focused runtime/lifecycle paths.
```

Remaining risk is not structural readiness. The remaining risk is real-model behavior:

```text
DeepSeek may fail V2 mission-understanding JSON.
DeepSeek may choose weak or invalid read-only decisions.
DeepSeek may produce an invalid report lane payload.
```

Those failures are acceptable evidence for Attempt 5B as long as they are captured safely and terminalized honestly.

## Exact Attempt 5B Runbook

Do not execute during this audit.

1. Use source commit:

```text
2f7c078b6c24c41321617d4b47e31a58d852c023
```

2. Ensure:

```text
git status --short --untracked-files=all = clean
```

3. Use workspace:

```text
C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
```

4. Use run root:

```text
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5b-<timestamp>
```

5. Generate BOMless files:

```text
model-contract.json
authority-scope.json
mission-script.txt
```

6. Set process-scoped env only:

```powershell
$env:SENTINEL_CERT_MODEL_API_KEY = <temporary key>
$env:SENTINEL_ALIYUN_DASHSCOPE_BASE_URL = <Aliyun OpenAI-compatible endpoint>
```

7. Execute exactly once:

```powershell
py -3.13 -m sentinel.cli cockpit `
  --run-root <RUN_ROOT>\runs `
  --model-contract <RUN_ROOT>\model-contract.json `
  --authority-scope <RUN_ROOT>\authority-scope.json `
  --workspace C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click `
  --script <RUN_ROOT>\mission-script.txt `
  --json
```

8. Remove env immediately after command, regardless of exit code.

9. Analyze, do not retry.

## Confirmation

```text
no provider call executed during this audit
no source code changed during this audit
no Pack 4 started
no push performed
```
