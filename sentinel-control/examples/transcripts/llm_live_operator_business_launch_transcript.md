# LLM Live Operator Business Launch Transcript

This transcript shows the intended product experience for
`SENTINEL_LLM_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0`.

```text
Sentinel: Bonjour, je suis la. Qu'est-ce que tu veux faire ?

User: Sentinel t'es la ?
Sentinel: Oui, je suis la. Qu'est-ce que tu veux faire ?

User: Je veux lancer un business de formation IA.
Sentinel: Tres bien. Je vais t'aider a definir une mission controlee. Quel est le marche cible ?

User: Freelancers and small agencies.
Sentinel: Budget approximatif ?

User: 500 euros.
Sentinel: Niveau d'autonomie autorise ?

User: Recherche, analyse, rapport, drafts. Pas de paiement ni envoi reel sans confirmation.
Sentinel: Mission prete. Je peux commencer ?

User: Oui commence.
Sentinel: Mission lancee et mise en file controlee.

User: Qu'est-ce que tu fais ?
Sentinel: Mission <id> status: queued.

User: Pause.
Sentinel: Mission paused.

User: Reprends.
Sentinel: Mission resumed.

User: Montre la timeline.
Sentinel: 0:mission_created:Mission created.
Sentinel: 1:mission_queued:Mission queued.
Sentinel: 2:mission_paused:Mission paused.
Sentinel: 3:mission_queued:Mission resumed.

User: Replay.
Sentinel: Replay
Sentinel: Mission created.
Sentinel: Mission queued.
Sentinel: Mission paused.
Sentinel: Mission resumed.
```

Internal effects:

```text
MissionDraft created
MissionAuthoritySummary validated
MissionRecord persisted
MissionEvent timeline hash chain appended
Replay reconstructed from evidence only
No direct organ execution from chat text
No raw prompt/provider response persistence
```
