# LLM Live Operator Cockpit Quickstart

Status: `SENTINEL_LLM_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0`

This is the first user-facing Sentinel cockpit. The user speaks naturally. The
LLM interprets and proposes structured operator artifacts. Sentinel validates,
stores, queues, governs, executes through existing runtimes, and records proofs.

## Product Shape

```text
User dialogue
-> structured MissionDraft
-> MissionAuthoritySummary
-> explicit start confirmation
-> internal MissionKernel record
-> timeline / replay / receipts / FinalGate refs
```

The user does not need to manually create mission JSON for the primary product
flow. Mission records are internal kernel state.

## Start The Cockpit

Product LLM mode requires an explicit `UserModelContract`:

```powershell
py -3.13 -m sentinel cockpit --run-root .\runs --model-contract .\model-contract.json
```

The cockpit also has a deterministic test mode for offline smoke tests:

```powershell
py -3.13 -m sentinel cockpit --run-root .\runs --deterministic-test-mode
```

Deterministic test mode is not the product brain. It exists only for tests and
repeatable local smoke checks.

## Example Conversation

```text
Sentinel: Bonjour, je suis la. Qu'est-ce que tu veux faire ?
User: Sentinel t'es la ?
Sentinel: Oui, je suis la. Qu'est-ce que tu veux faire ?

User: Je veux lancer un business de formation IA.
Sentinel: Tres bien. Je vais clarifier la mission avant de commencer.

User: Marche cible: freelancers and small agencies. Budget: 500 euros. Autonomie: recherche, analyse, rapport, drafts. Pas de paiement ni envoi reel sans confirmation.
Sentinel: Mission prete. Je peux commencer ?

User: Oui commence.
Sentinel: Mission lancee et mise en file controlee.

User: Qu'est-ce que tu fais ?
Sentinel: Mission <id> status: queued.

User: Montre la timeline.
Sentinel: 0:mission_created:Mission created.
Sentinel: 1:mission_queued:Mission queued.

User: Replay.
Sentinel: Replay
Sentinel: Mission created.
Sentinel: Mission queued.
```

## Slash Commands

```text
/help       show local cockpit commands
/status     explain current mission status
/timeline   show safe mission timeline events
/replay     reconstruct evidence timeline without re-executing actions
/pause      pause the active mission
/resume     resume the active mission
/kill       kill the active mission
/missions   list known missions
/exit       leave the cockpit
```

V0 supports status, timeline, replay, pause, resume, kill, and exit in the
local cockpit. Additional slash-command polish remains product work.

## Boundaries

The LLM may:

```text
think
ask
explain
draft
summarize
propose
```

The LLM may not:

```text
execute
grant authority
unlock credentials
call organs directly
override provider/backend/model
bypass Gate, PowerRuntime, AgentRuntime, receipts, FinalGate, or memory boundaries
```

No raw prompts, provider responses, hidden reasoning, raw credentials, or raw
secrets are persisted by the operator layer.
