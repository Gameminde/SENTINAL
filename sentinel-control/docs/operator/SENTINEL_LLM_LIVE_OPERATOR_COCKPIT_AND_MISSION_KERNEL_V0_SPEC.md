# Sentinel LLM Live Operator Cockpit And Mission Kernel V0 Spec

Recorded at: 2026-06-06

## Doctrine

```text
Python is the kernel/infrastructure.
The LLM is the conversational brain.
Sentinel is the authority operating system.
```

This pack supersedes the older names:

```text
MISSION_DAEMON_AND_OPERATOR_SHELL_V0
SENTINEL_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0
```

The implementation target is:

```text
SENTINEL_LLM_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0
```

The user-facing product must not be a deterministic parser, a toy REPL, a CLI
database, or an IDE. The product surface is a live LLM-backed cockpit. The
Python layer stores state, enforces authority, queues work, persists safe
timeline events, invokes existing runtimes, and proves outcomes.

## Product Flow

```text
natural user dialogue
-> LLM-backed operator understanding
-> structured MissionDraft
-> clarification questions
-> MissionAuthoritySummary
-> user confirmation
-> Sentinel validation
-> MissionKernel
-> PowerRuntime / AgentRuntime
-> organs
-> receipts
-> FinalGate
-> memory refs
-> timeline
-> replay
-> LLM status explanation
```

The expected experience:

```text
User: Sentinel t'es la ?
Sentinel: Oui, je suis la. Qu'est-ce que tu veux faire ?

User: Je veux lancer un business de formation IA.
Sentinel: Tres bien. Je vais clarifier la mission, le marche cible, le budget, les contraintes et ton niveau d'autonomie autorise. Ensuite je pourrai demarrer une mission controlee.
```

## Existing Components To Reuse

```text
UserModelContract
model_execution provider/registry/coordinator contracts
BrainCognitionLoop
LLM role-loop contracts
AgentRuntime
PowerRuntime V0
MissionAuthorityEnvelope
OrganDispatcher
DelegatedActionGate
FinalGate
RoleLoopMemoryBridge
Mission cancellation / kill-switch concepts
PowerRuntime timeline and receipt refs
shared safety scanners and redaction helpers
```

The operator layer must not duplicate these systems. It translates natural
conversation into validated operator artifacts and then hands control to the
existing Sentinel kernel.

## Core Types

```text
LLMLiveOperatorCockpit
OperatorConversationSession
OperatorMessage
OperatorConversationFrame
OperatorPromptRenderer
OperatorLLMConversationAdapter
OperatorLLMDecisionResult
OperatorStructuredOutputValidator
OperatorIntent
OperatorTurnResult
OperatorSafetySummary
MissionDraft
MissionClarificationQuestion
MissionAuthoritySummary
MissionStartProposal
MissionStartDecision
MissionKernel
MissionRecord
MissionQueue
MissionRunStore
MissionEvent
MissionTimeline
MissionTimelineHash
MissionReplayView
OperatorVisibleMissionStatus
OperatorCommand
OperatorCommandResult
```

## Conversation States

```text
IDLE
GREETING
UNDERSTANDING_REQUEST
ASKING_CLARIFICATIONS
DRAFTING_MISSION
AWAITING_START_CONFIRMATION
MISSION_QUEUED
MISSION_RUNNING
MISSION_PAUSED
MISSION_KILLED
MISSION_COMPLETED
MISSION_FAILED
MISSION_BLOCKED
```

## Mission Statuses

```text
DRAFT
READY_TO_START
QUEUED
RUNNING
PAUSED
CANCEL_REQUESTED
KILLED
COMPLETED
FAILED
BLOCKED
REVOKED
```

## LLM Mode

Product mode is `llm_operator_mode`. It requires an explicit
`UserModelContract`.

Rules:

```text
no hidden default provider
no provider fallback
no AUTO routing
no provider/backend/model override
no key auto-detection
no raw prompt durability
no raw provider response durability
no raw reasoning durability
```

If no explicit model contract is configured, `llm_operator_mode` fails closed
with a clear message.

The LLM may output only structured operator artifacts:

```text
OperatorReply
MissionDraft
MissionClarificationQuestion
MissionAuthoritySummary
MissionStartProposal
MissionPlanProposal
OperatorStatusExplanation
```

The LLM may think, ask, explain, draft, summarize, and propose. It may not
execute, grant authority, unlock credentials, call organs directly, or bypass
Gate, PowerRuntime, AgentRuntime, receipts, FinalGate, or memory boundaries.

## Deterministic Test Mode

`deterministic_test_mode` exists only for tests and offline smoke. It must be
clearly marked non-product. It can answer simple greetings, generate a simple
mission draft, and ask clarifications, but it cannot execute, grant authority,
or silently replace `llm_operator_mode`.

## Mission Kernel

The MissionKernel is internal infrastructure:

```text
local run store
JSON mission records
JSONL event stream
hash-chained timeline
mission queue
pause/resume/kill
timeline/replay
PowerRuntime bridge
AgentRuntime bridge
receipt refs
FinalGate refs
memory feedback refs
```

The kernel persists only safe structured data. It must reject path traversal,
detect timeline tampering, and redact secret-like material before persistence.

## Non-Scope

This pack does not implement:

```text
durable credential vault
generic browser private login/session
payment/spend/trading
desktop sidecar
unrestricted shell
unbounded API mutation
real Telegram/Slack/Gmail connector
provider fallback/AUTO routing
global neural fabric
skill marketplace execution
new dangerous actuator family
web dashboard
voice runtime
```

Voice and web dashboard may be prepared by type shape only; they are not live
runtime surfaces in V0.

## Lock Criteria

Do not call this locked unless:

```text
LLM mode requires explicit UserModelContract
deterministic mode is test-only
cockpit command works
LLM-backed conversation creates mission draft
clarification works
authority summary works
start confirmation works
mission kernel persists mission record
timeline hash chain works
replay works without re-execution
pause/resume/kill work
PowerRuntime bridge works
AgentRuntime bridge is controlled/default-off
receipt/FinalGate/memory refs are preserved
no direct organ bypass exists
no provider fallback/AUTO exists
raw prompts/provider responses/reasoning are not persisted
product gauntlet passes
self-audit completed
docs updated truthfully
```
