# Power Actuator Fabric Wave 1 Spec

Date: 2026-06-05

Status: execution-wave specification

## Mission

Sentinel is not an IDE and not a single browser agent. Sentinel is the control
plane for autonomous power. The Power Actuator Fabric turns real-world powers
into Sentinel-native actuators that can be planned, gated, executed, measured,
certified, replayed, and fed back into memory.

The core rule is unchanged:

```text
MissionAuthorityEnvelope
-> AgentRuntime / MissionRuntime
-> OrganDispatcher
-> DelegatedActionGate
-> runtime_execution / organ adapter
-> receipt
-> FinalGate
-> memory feedback / ledger
```

No Brain output, memory entry, receipt, provider response, skill prompt, MCP
tool, plugin, sidecar, or browser page may become authority.

## AgentLab Harvest Sources

AgentLab is the source of power patterns, not production runtime code.

| Source | Take | Rewrite | Avoid |
| --- | --- | --- | --- |
| OpenClaw | Plugin/channel breadth, exec approval lifecycle, tool registry, skill scanner, browser observability. | Sentinel manifests, risk classifier, dry-run previews, fake adapters first, approval cards with evidence refs. | Vendor runtime import, ambient plugin authority, postinstall/script execution, direct channel send. |
| JARVIS | Sidecar enrollment, permission lifecycle, desktop/system capability manifests, audit trail. | Signed sidecar manifest, revocation, capability scopes, screen sanitizer, per-RPC receipts. | Authority levels as-is, unrestricted desktop tools, prompt webapp templates as executable instructions. |
| OpenJarvis | Hardware/cost-aware routing, trace-backed learning scores, local execution discipline. | CostRouter with quality/cost/latency/privacy/risk fit, improvement proposals only. | Auto-writing agent config, unscanned skill import, implicit fallback routing. |
| Hermes | Context quarantine, memory compression, prompt injection scanning, hook pipeline. | Pre-context sweep, memory-as-data only, fail-closed policy hook chain. | Skill prompts or memory entries as hidden policy. |
| AgentMemory | Durable structured memory patterns. | Evidence refs, feedback refs, retention and trust classes. | Memory that grants tools, scopes, credentials, or approvals. |
| TradingAgents | Specialized domain operators and risk ledgers. | Paper/fake adapters first, special authority contracts later. | Real broker/spend execution in Wave 1. |
| Chrome DevTools / CloakBrowser | Browser instrumentation, page targets, network/console/performance signals, controlled sessions. | Existing Sentinel Browser Operating Subsystem as one actuator family. | Raw CDP firehose, uncontrolled MCP/WebMCP, durable browser private data. |

## Wave 1 Actuator Families

Wave 1 creates a shared fabric across these families:

```text
browser
shell_sandbox
code_execution
external_api
channel
workspace
credential_ref
```

Family truth at the start of Wave 1:

| Family | Starting State | Wave 1 Target |
| --- | --- | --- |
| `browser` | Live browser L4/L5/L6 plus hardened live backend helpers. | Treat browser as first actuator in PowerRuntime; promote new backend helpers through explicit runtime opt-in. |
| `workspace` | L2/L3 local artifact and reversible workspace execution. | PowerRuntime step target with receipt refs and rollback posture. |
| `shell_sandbox` | Not promoted as product organ. | Real sandboxed command execution for safe dev/build/test commands only. |
| `code_execution` | Not promoted as product organ. | Code execution through shell sandbox and contained interpreter commands only. |
| `external_api` | Models and read-only reality clients exist, but no broad governed mutation organ. | Read/write API organ with method/domain authority and body quarantine. |
| `channel` | Draft stores and channel models exist, no governed send fabric. | Draft plus explicit-authority send adapter shape. |
| `credential_ref` | Grant/ref/proof foundation exists, no durable secret vault. | Metadata-only credential refs in Wave 1; no durable secret storage. |

## Canonical Models

### `PowerActuatorCapabilityLevel`

```text
L2_LOCAL_ARTIFACT
L3_REVERSIBLE_WORKSPACE
L4_EXTERNAL_PERCEPTION
L5_CONTROLLED_EXTERNAL_ACTION
L6_SENSITIVE_DELEGATED_ACTION
L7_CRITICAL_SPECIAL_AUTHORITY
```

The level describes the real-world effect class. It never grants authority by
itself.

### `PowerActuatorPromotionState`

```text
DOCS_ONLY
CONTRACT_TEST_LOCKED
RUNTIME_GOVERNED_BUT_BACKEND_THIN
LIVE_RUNTIME
DEFAULT_OFF_RUNTIME_OPT_IN
DEFERRED_SPECIAL_AUTHORITY
BLOCKED
```

Promotion state is evidence, not permission.

### `PowerActuatorRiskProfile`

Fields:

```text
risk_profile_id
family
capability_level
side_effect_class
externality
reversibility
sensitivity
credential_touch
network_touch
filesystem_touch
human_contact_touch
spend_or_trade_touch
authority_required
approval_required
finalgate_required
rollback_or_disable_required
max_runtime_seconds
max_output_bytes
data_not_instruction = true
can_grant_authority = false
```

### `PowerActuatorContract`

Fields:

```text
contract_id
mission_id
family
organ_kind
capability_level
promotion_state
allowed_domains
allowed_roots
allowed_methods
allowed_commands
allowed_channels
allowed_recipients
credential_ref_ids
rate_limit
cost_limit
timeout_ms
output_cap_bytes
risk_profile
kill_switch_binding
rollback_policy
receipt_required = true
finalgate_required = true
memory_feedback_allowed = true
authority_effect = "none"
can_grant_authority = false
can_approve_future_execution = false
data_not_instruction = true
```

The contract is an executor input, not authority. It must be checked against
the `MissionAuthorityEnvelope` and delegated lane.

### `PowerActuatorRequest`

Fields:

```text
request_id
mission_id
step_id
family
organ_kind
capability_level
contract_ref
request_hash
intent_summary_hash
input_refs
candidate_ref
authority_envelope_ref
delegated_lane_ref
idempotency_key
dry_run_required
timeout_ms
data_not_instruction = true
authority_effect = "none"
```

No raw prompt, raw reasoning, provider override, credential value, bearer token,
or hidden tool payload may appear.

### `PowerActuatorReceipt`

Fields:

```text
receipt_id
request_id
mission_id
step_id
family
organ_kind
capability_level
status
started_at
ended_at
duration_ms
input_hash
output_hash
artifact_refs
evidence_refs
before_state_hash
after_state_hash
diff_hash
exit_code
blocked_reason
failure_summary_hash
rollback_attempted
rollback_success
kill_switch_checked
credential_proof_refs
finalgate_certificate_ref
data_not_instruction = true
authority_effect = "none"
can_grant_authority = false
can_approve_future_execution = false
```

Receipts measure what happened. They cannot approve future execution.

### `PowerActuatorFinalGateCertificate`

Fields:

```text
certificate_id
receipt_id
mission_id
family
decision
certified
reasons
receipt_hash
unsafe_payload_findings
authority_drift_findings
credential_findings
rollback_findings
data_not_instruction = true
authority_effect = "none"
```

FinalGate certifies a completed result. It does not create new authority.

### `PowerActuatorKillSwitchBinding`

Fields:

```text
binding_id
mission_id
family
organ_kind
kill_switch_ref
revocation_ref
check_before_start = true
check_before_side_effect = true
check_after_side_effect = true
abort_remaining_steps_on_trigger = true
cleanup_required
```

### `PowerActuatorRollbackPolicy`

Fields:

```text
policy_id
family
rollback_mode
requires_before_state
requires_after_state
requires_hash_readback
cleanup_mode
quarantine_mode
irreversible_boundary_marker
manual_recovery_required
```

For irreversible or external actions, rollback posture becomes disable,
quarantine, pause, or manual recovery. It must not pretend reversibility.

## Family Contracts

### Browser

Uses existing Browser Operating Subsystem organs and live backend helpers.

Allowed Wave 1 promotions:

```text
browser_l4_readonly
browser_l5_session_open_observe_interact_close
browser_l6_non_sensitive_form_submit
browser_l6_upload_download_quarantine
browser_l6_js_sandbox
browser_devtools_hash_only_metadata
browser_visual_grounding_from_live_session
browser_replay_timeline
browser_failure_recovery_request
```

Still blocked:

```text
generic private session
generic credentialed login
payment checkout
account creation
raw CDP firehose
uncontrolled MCP/WebMCP
raw response body capture outside quarantine
```

### Shell Sandbox

Inspired by OpenClaw exec approval and Open Interpreter style power, rewritten
as a Sentinel sandbox organ.

Allowed first commands:

```text
python -m pytest
python -m compileall
npm test
npm run build
node --version
python --version
```

Default deny:

```text
rm -rf
curl | bash
powershell download-exec
sudo/admin elevation
credential dump
network scanners
process kill outside sandbox
filesystem mutation outside allowed root
```

Required proof:

```text
command hash
argv hash
cwd containment proof
env scrub proof
exit code
stdout/stderr hash and capped preview
file diff/hash receipt
timeout/kill proof
FinalGate certificate
```

### Code Execution

Code execution is not a separate unsafe interpreter surface in Wave 1. It is a
contracted mode over the shell sandbox and workspace roots.

Allowed:

```text
compile/test/build commands in allowlist
temporary sandbox files
artifact hashes
bounded logs
```

Blocked:

```text
arbitrary eval server
network package install
unbounded subprocess tree
host credential access
shell escape via model text
```

### External API

Inspired by OpenClaw channels and gateway methods, rewritten as a governed API
organ.

Allowed:

```text
GET/HEAD with explicit domain/vendor/method authority
POST/PUT/PATCH/DELETE only with explicit mutation authority
body quarantine when enabled
credential_ref metadata only
rate-limit ledger
```

Blocked:

```text
raw token persistence
unknown domains
unbounded response bodies
hidden webhook registration
provider/model override
payment/trading endpoints unless future special authority exists
```

### Channel

Inspired by OpenClaw channel manifests and JARVIS app templates, rewritten as
draft/send split.

Modes:

```text
draft_only
send_with_explicit_authority
```

Send requires:

```text
recipient policy
channel authority
rate limit
identity/compliance check
preview evidence
receipt
FinalGate
```

Blocked:

```text
spam
deceptive identity
credential capture
unapproved broadcast
send from memory
send from raw model output
```

### Workspace

Uses existing L2/L3 executors. Wave 1 makes them PowerRuntime step targets.

Required:

```text
path containment
post-write readback hash
rollback attempt/success separation
receipt refs
FinalGate refs
```

### Credential Ref

Wave 1 uses credential references and proofs as metadata only.

Allowed:

```text
credential_ref_id
grant scope checks
proof refs
revocation/expiry/max-use metadata
```

Blocked:

```text
durable secret storage
raw secret value in prompt/context/memory/receipt
global enable credentials switch
credential proof as future permission
```

## Power Runtime Spine

Wave 1 requires a `PowerRuntime` layer that can run a mission graph:

```text
PowerMissionPlan
-> PowerMissionGraph
-> ordered PowerMissionStep execution
-> per-step actuator dispatch
-> receipts / FinalGate refs
-> timeline
-> memory feedback packet
```

It must support:

```text
dependencies
retry budget
pause/abort
kill switch check
blocked state
partial state
receipt refs
FinalGate refs
memory feedback refs
```

## Promotion Rules

No actuator can promote from contract to runtime unless it has:

```text
capability map
failure-mode map
Gate policy
contract
request model
receipt
FinalGate
kill switch posture
rollback/disable posture
targeted tests
secret scan
docs truth update
```

## Wave 1 Commit Sequence

```text
1. docs: define power actuator fabric wave 1
2. runtime: add sentinel power mission runtime v0
3. runtime: add sandbox shell and code execution organ v1
4. runtime: add governed external api organ v1
5. runtime: add governed channel draft and send organ v1
6. runtime: add power actuator fabric orchestration demo
7. runtime: remediate power actuator fabric audit findings (if needed)
```

## Non-Scope

```text
desktop sidecar
durable credential vault
real payment/spend/trading provider
generic private browser sessions
uncontrolled MCP/WebMCP
provider fallback/AUTO routing
global autonomous mode
plugin marketplace install
```

## Acceptance

Wave 1 is locked only when Sentinel can run a multi-actuator mission with:

```text
browser + shell sandbox + code execution + API + channel + workspace
```

under one mission authority envelope, with receipts, FinalGate certificates,
timeline reconstruction, memory feedback context, and no default-on dangerous
surface.
