# P6R5 Failure Modes And Proof Gaps

Date: 2026-05-10

## Failure Modes

| Failure | Why it matters | Current protection | Remaining gap |
| --- | --- | --- | --- |
| Module pile without loop | Components pass unit tests but do not think together | P5L integrated review and P6R frame flow | Need P7 runtime loop |
| Raw context flooding | Stronger organs overwhelm the LLM | P6Q measurement and P6R compact frame | Need P6S to obey frame discipline |
| Authority loss in compression | Context compression drops constraints | authority card in P6R | Need end-to-end frame verifier in runtime |
| Receipt refs not replayable | LLM sees refs but system cannot recover evidence | receipt graph doctrine | Need runtime receipt store integration |
| Over-reliance on selected LLM quality | Cheap or weak model makes poor decisions | verifier, evidence refs, FinalGate | Need model-specific eval profiles |
| Tool surface explosion | Too many tools invite confused plans | ToolSurfaceRouter | Need live tool schema budget enforcement |
| Desktop context amplifier | Workspace trees/diffs grow fast | P6R decision frames | Need compact workspace cards in P6S |
| Long mission state drift | Mission history changes or contradicts itself | workspace versions, belief state | Need long-horizon mission benchmark |
| Learning becomes hidden policy | Memory/skills silently steer actions | memory is non-authoritative doctrine | Need continuity runtime with explicit provenance |
| Tracing gaps | Cannot explain why an action happened | traces and receipts | Need live tracing around model calls |

## Proof Gaps

Still not proven:

```text
live LLM runtime wiring
end-to-end long mission benchmark
Desktop Workspace L6
Browser Controlled Navigation L6
API Authenticated Read L6
Channel Provider Draft L6
continuous learning / continuity runtime
production UI
full regression after P6R
live cost telemetry
long-context comparison benchmark
```

## P6S-Specific Risks

Desktop Workspace L6 can fail if it:

```text
dumps raw workspace trees into the LLM
dumps full file contents without top-k need
lets file receipts become authority
does not create rollback refs
does not preserve path containment proof
does not connect mutation receipts to workspace updates
does not use P6R decision frames
```

## Required P6S Proof

P6S should prove:

```text
workspace file read/write/create/list is L6-scoped
workspace root containment uses robust path checks
mutations create receipts
rollback refs are emitted for writes/creates
workspace cards are compact
raw file dumps are excluded by default
LLMDecisionFrame includes only relevant workspace summaries and receipt refs
FinalGate-compatible evidence exists for each mutation
```

## No-Go Conditions For P6S

Stop before locking P6S if:

```text
P6S bypasses P6R context engine
P6S adds host desktop control outside workspace file operations
P6S adds shell/process execution
P6S exposes raw credentials or secrets
P6S grants authority through workspace content
P6S has no rollback receipt path
P6S cannot prove compact context under realistic workspace load
```

## Go Conditions For P6S

Proceed if:

```text
P6S uses P6R frames as the default model context boundary
P6S keeps exact workspace artifacts outside the prompt
P6S includes receipt refs and rollback refs
P6S remains limited to workspace file operations
P6S adds no new organ family
P6S adds no Code/Shell harvest
P6S expands no authority
```
