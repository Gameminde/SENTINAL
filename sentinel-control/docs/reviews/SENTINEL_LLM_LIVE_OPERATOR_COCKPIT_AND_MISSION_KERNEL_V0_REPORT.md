# Sentinel LLM Live Operator Cockpit And Mission Kernel V0 Report

Recorded at: 2026-06-06

## Verdict

```text
SENTINEL_LLM_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0 = LOCKED
previous_phase = COMPETITIVE_GAP_DELTA_LOCKED
next_phase = PERSISTENT_SEMANTIC_MEMORY_V1
measurement_doctrine = product power under provable authority
```

This wave supersedes the older `MISSION_DAEMON_AND_OPERATOR_SHELL_V0` wording.
The product surface is not a mission-file CLI database. It is an LLM-backed
live cockpit over an internal mission kernel.

## Commit Index

```text
297ba38 docs: define llm live operator cockpit and mission kernel v0
413016c runtime: add llm live operator core models
3583312 runtime: add llm operator prompt frame v0
a36a371 runtime: add llm operator conversation adapter v0
aad1522 runtime: add deterministic operator test mode
e53c660 runtime: add llm live operator conversational intake v0
3adb564 runtime: add llm live operator mission kernel v0
4b2e1d8 runtime: add llm live cockpit mission replay
fa5bf08 runtime: connect llm live cockpit conversation to mission kernel
d8c7475 runtime: bridge llm live operator missions to power runtime
0d7ccc4 runtime: add llm live operator agentruntime bridge v0
8975ba7 runtime: add llm live operator cockpit cli
51da8cf test: add llm live operator cockpit product gauntlet
8a6c717 docs: add llm live operator cockpit quickstart and transcripts
9ff5328 docs: lock llm live operator cockpit and mission kernel v0
714d1aa runtime: remediate llm live operator cockpit audit findings
```

## What Is Real Runtime

```text
python -m sentinel cockpit --run-root <dir> --model-contract <UserModelContract.json>
python -m sentinel chat --run-root <dir> --model-contract <UserModelContract.json>
```

The cockpit now:

```text
loads an explicit UserModelContract
uses a cataloged OpenAI-compatible/local provider client
supports Ollama-style local OpenAI-compatible chat without raw credential storage
rejects missing remote provider credentials without network calls
rejects unsupported selected models without fallback
validates structured LLM output before creating mission state
creates MissionDraft and MissionAuthoritySummary as data, not authority
requires explicit start confirmation
creates internal MissionRecord entries
queues missions
supports pause/resume/kill/status/timeline/replay from conversation
bridges to PowerRuntime V0 through injected executors only
offers a default-off AgentRuntime bridge through public runtime API only
persists safe mission events with a hash-chained timeline
reconstructs replay without re-executing actions
```

## What Is LLM-Backed

```text
OperatorPromptRenderer builds the safe prompt text.
OperatorConversationFrame includes safe state, structured output schema, and forbidden surfaces.
OperatorLLMConversationAdapter builds RealModelRequest using the explicit user model contract.
OperatorCatalogModelClient maps the explicit contract to a cataloged provider/backend/model.
OpenAI-compatible provider responses are parsed as structured JSON.
Raw provider response and reasoning are hash-only metadata, not durable text.
```

## Deterministic Test Mode

```text
deterministic_test_mode = CLOSED / non-product
```

It exists only for tests and local smoke checks:

```text
python -m sentinel cockpit --run-root <dir> --deterministic-test-mode
```

It cannot execute, cannot grant authority, and cannot silently replace LLM mode.

## Local-Only / Still Not Production

```text
Mission store = local filesystem JSON + JSONL
Mission queue = local in-process kernel
Replay = local evidence timeline reconstruction
Production daemon service = NOT_STARTED
Web dashboard = NOT_STARTED
Voice runtime = NOT_STARTED
Persistent semantic memory retrieval = NOT_STARTED / next
Real Telegram/Slack/Gmail connectors = NOT_STARTED
Durable credential vault = NOT_STARTED
Generic browser private login/session = NOT_STARTED
Payment/spend/trading = NOT_STARTED
Desktop sidecar = NOT_STARTED
Provider fallback/AUTO routing = NOT_APPROVED
```

## Conversation Example

```text
Sentinel: Bonjour, je suis la. Qu'est-ce que tu veux faire ?
User: Je veux lancer un business de formation IA.
Sentinel: Tres bien. Je vais clarifier la mission avant de commencer.
User: Oui commence.
Sentinel: Mission lancee et mise en file controlee.
User: Qu'est-ce que tu fais ?
Sentinel: Mission <id> status: queued.
User: Montre la timeline.
Sentinel: 0:mission_created:Mission created.
Sentinel: 1:mission_queued:Mission queued.
User: Replay.
Sentinel: Replay ...
```

## Product Gauntlet

The gauntlet covers:

```text
greeting -> business mission draft -> authority summary -> start -> timeline -> replay
vague request -> clarification required -> no mission record
LLM direct organ call attempt -> rejected
LLM authority grant attempt -> rejected
pause -> resume -> kill
two active missions -> disambiguation request
secret-like text -> redacted before persistence
missing PowerRuntime executor -> blocked and replayable
PowerRuntime receipt/FinalGate/memory refs -> surfaced in replay
kill switch -> remaining PowerRuntime steps aborted
```

## Self-Audit Findings And Fixes

```text
Finding: CLI LLM mode loaded UserModelContract but had no product model client.
Fix: Added OperatorCatalogModelClient and wired it into `sentinel cockpit/chat`.

Finding: Local OpenAI-compatible providers with no credential env, such as Ollama, could not be used by the base provider.
Fix: OpenAICompatibleChatProvider now omits Authorization only when credential_env is None.

Finding: docs/quickstart listed /help and /missions, but CLI did not handle them.
Fix: Added local read-only cockpit commands /help and /missions.
```

## Boundaries Preserved

```text
conversation text becomes authority = BLOCKED
LLM output becomes authority = BLOCKED
mission draft bypasses authority = BLOCKED
start without confirmation = BLOCKED
chat command calls organs directly = BLOCKED
cockpit bypasses PowerRuntime/AgentRuntime public APIs = BLOCKED
provider fallback/AUTO introduced = BLOCKED
model/backend/provider override introduced = BLOCKED
memory becomes authority = BLOCKED
receipt becomes authority = BLOCKED
FinalGate becomes future permission = BLOCKED
raw secret persistence = BLOCKED
raw credential persistence = BLOCKED
raw prompt persistence = BLOCKED
raw provider response persistence = BLOCKED
raw reasoning persistence = BLOCKED
timeline tamper detection = CLOSED
mission store path traversal rejection = CLOSED
kill switch behavior = CLOSED
pause/resume behavior = CLOSED
operator output redaction = CLOSED
```

## Tests Run

```text
py -3.13 -m pytest tests/test_llm_live_operator_models_v0.py tests/test_llm_operator_prompt_frame_v0.py -q
result: 15 passed

py -3.13 -m pytest tests/test_llm_operator_adapter_v0.py tests/test_llm_operator_model_client_v0.py tests/test_operator_deterministic_test_mode_v0.py -q
result: 18 passed

py -3.13 -m pytest tests/test_llm_live_operator_conversation_intake_v0.py tests/test_llm_live_operator_mission_kernel_v0.py -q
result: 22 passed

py -3.13 -m pytest tests/test_llm_live_operator_cockpit_flow_v0.py tests/test_llm_live_operator_power_runtime_bridge_v0.py -q
result: 15 passed

py -3.13 -m pytest tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_llm_live_operator_cockpit_cli_v0.py -q
result: 17 passed

py -3.13 -m pytest tests/test_llm_live_operator_replay_v0.py tests/test_llm_live_operator_product_gauntlet_v0.py -q
result: 16 passed

py -3.13 -m pytest tests/test_sentinel_power_runtime_v0.py tests/test_power_fabric_orchestration_demo.py -q
result: 13 passed

py -3.13 -m pytest tests/test_agent_runtime.py tests/test_brain_to_organ_runtime_closed_loop.py -q
result: 24 passed

py -3.13 -m pytest tests/test_openai_compatible_provider_base.py tests/test_llm_operator_model_client_v0.py -q
result: 12 passed

python -m compileall -q sentinel
result: passed, with pre-existing SyntaxWarning in sentinel/organs/browser/cloak_backend.py

git diff --check
result: OK

git show --check HEAD
result: OK
```

## Next Recommended Phase

```text
PERSISTENT_SEMANTIC_MEMORY_V1
```

Reason:

```text
Sentinel now has a LLM live cockpit and mission kernel over the power fabric.
The next product-power gap is durable recall: the cockpit must remember prior
missions, user preferences, entities, decisions, evidence, receipts, and
lessons without memory becoming authority.
```
