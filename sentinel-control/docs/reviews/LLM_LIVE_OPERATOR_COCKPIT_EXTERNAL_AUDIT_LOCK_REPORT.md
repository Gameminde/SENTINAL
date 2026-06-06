# LLM Live Operator Cockpit External Audit Lock Report

Recorded at: 2026-06-06

Baseline HEAD:

```text
b362f3bd7ca23c1070e4118bf56e3415a597ba97
```

## Verdict

```text
LLM_LIVE_OPERATOR_COCKPIT_EXTERNAL_AUDIT_LOCK = CLOSED
recommendation = GO / scoped to PERSISTENT_SEMANTIC_MEMORY_V1
```

The audit found and remediated real cockpit boundary defects before the next
product-power pack. No new actuator family was added.

## Scope

Audited:

- LLM output authority boundaries;
- direct organ execution from cockpit;
- provider fallback/AUTO and provider/backend/model override paths;
- raw prompt/provider/reasoning persistence;
- mission store tamper detection;
- pause/resume/kill lifecycle correctness;
- PowerRuntime bridge boundaries;
- AgentRuntime bridge default-off behavior;
- Ollama/local provider endpoint safety;
- conversation injection resistance.

## Findings Closed

### COCKPIT-DRAFT-SECRET-LEAK = CLOSED

Issue:

- `OperatorConversationFrame` redacted the current user message but summarized
  `current_draft` fields directly into the LLM prompt payload.
- `OperatorLLMDecisionResult.safe_model_dump()` and
  `OperatorTurnResult.safe_model_dump()` could dump raw mission draft and
  secondary structured text.

Fix:

- Redacted current draft title/objective/constraints/expected artifacts before
  prompt frame hashing/payload rendering.
- Added recursive operator redaction for safe dumps and event metadata.
- Extended safe dumps for intent, clarification questions, authority summary,
  start proposal, mission draft metadata, and turn metadata.

### MISSION-TERMINAL-RESURRECTION = CLOSED

Issue:

- `MissionKernel.pause/resume/kill/enqueue/update_status` allowed terminal
  missions to be reopened.
- `OperatorPowerRuntimeBridge` and `OperatorAgentRuntimeBridge` could run after
  a mission had been killed.

Fix:

- Added terminal mission status guard in `MissionKernel`.
- Cockpit resume/pause/kill now returns a safe refusal when a terminal mission
  cannot change state.
- PowerRuntime and AgentRuntime bridges fail closed before invoking runtime or
  injected executors when the operator mission is already terminal.

### TIMELINE-TAMPER-VISIBILITY = CLOSED

Issue:

- Replay showed tamper status, but `/timeline` rendered loaded events without
  a hash-chain integrity flag.

Fix:

- `/timeline` now verifies the event hash chain and exposes
  `timeline_summary.tampered`.
- A tampered timeline includes an integrity warning in the user-visible reply.

### LOCAL-PROVIDER-NON-LOOPBACK = CLOSED

Issue:

- Default Ollama/LM Studio catalog entries are localhost, but an injected local
  provider catalog could point a local backend at a non-loopback URL.

Fix:

- `OperatorCatalogModelClient` rejects local/local-none/local-runtime backends
  whose endpoint host is not loopback before any HTTP call.

## Confirmed Controls

```text
LLM output cannot become authority = CLOSED
No direct organ execution from cockpit = CLOSED
No provider fallback/AUTO = CLOSED
No provider/backend/model override = CLOSED
No raw prompt persistence = CLOSED
No raw provider response persistence = CLOSED
No raw reasoning persistence = CLOSED
Mission store tamper detection = CLOSED
Pause/resume/kill correctness = CLOSED
PowerRuntime bridge boundaries = CLOSED
AgentRuntime bridge default-off = CLOSED
Ollama/local provider path safety = CLOSED
Conversation injection resistance = CLOSED
```

## Evidence

Code evidence:

- `sentinel/operator/safety.py` keeps operator artifacts data-not-authority.
- `sentinel/operator/llm_frame.py` rejects unsafe direct execution text and
  redacts current draft prompt summaries.
- `sentinel/operator/structured_output.py` hashes raw provider response and raw
  reasoning instead of retaining them.
- `sentinel/operator/model_client.py` pins provider/backend/model to the
  explicit `UserModelContract` and enforces loopback for local endpoints.
- `sentinel/operator/kernel.py` enforces terminal mission lifecycle.
- `sentinel/operator/power_bridge.py` and `sentinel/operator/agent_bridge.py`
  block terminal missions before runtime invocation.
- `sentinel/cli.py` uses safe turn dumps for cockpit output and exposes
  timeline tamper status.

Independent sidecar:

- One sidecar audit completed and identified terminal mission resurrection,
  timeline tamper visibility, and local provider endpoint hardening.
- A second LLM/provider sidecar disconnected; local scans and targeted tests
  covered that axis.

## Tests Run

```text
py -3.13 -m pytest tests/test_llm_live_operator_models_v0.py tests/test_llm_operator_prompt_frame_v0.py tests/test_llm_operator_adapter_v0.py tests/test_llm_operator_model_client_v0.py tests/test_operator_deterministic_test_mode_v0.py -q
Result: 37 passed

py -3.13 -m pytest tests/test_llm_live_operator_conversation_intake_v0.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_llm_live_operator_cockpit_flow_v0.py -q
Result: 35 passed

py -3.13 -m pytest tests/test_llm_live_operator_power_runtime_bridge_v0.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_llm_live_operator_replay_v0.py tests/test_llm_live_operator_cockpit_cli_v0.py tests/test_llm_live_operator_product_gauntlet_v0.py -q
Result: 42 passed

python -m compileall -q sentinel
Result: exit code 0
```

Total targeted cockpit/operator tests in final verification:

```text
114 passed
```

## Scans Run

```text
direct organ execution scan over sentinel/operator = no matches
secret/Bearer/API key scan over operator code = no production matches
provider fallback/AUTO/model override scan = explicit contract-only references
raw prompt/provider/reasoning scan = prompt in-memory only, response/reasoning hash only
```

Secret-like strings remain only in regression tests that assert redaction.

## Boundaries Preserved

```text
No new execution surface added
No generic browser login/payment/API/channel/shell/desktop added
No durable credential vault added
No provider fallback/AUTO routing added
No raw credential storage added
No direct organ bypass added
No memory-as-authority added
No receipt-as-authority added
No FinalGate-as-future-permission added
```

## Next Recommended Phase

```text
PERSISTENT_SEMANTIC_MEMORY_V1
```

Reason:

- The LLM cockpit is now externally audited and hardened enough to safely attach
  durable semantic recall as context-only memory.
- Memory must remain evidence-linked and non-authoritative.
