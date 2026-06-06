# Agent Comparison Matrix

## Current Competitive Truth - 2026-06-06

This section supersedes the April matrix for current planning. The April
matrix remains below as the historical forensic baseline.

| System | Current Source Truth | Power Sentinel Should Harvest | Where Sentinel Leads | Where Sentinel Trails |
| --- | --- | --- | --- | --- |
| Hermes Agent | Large agent platform with decomposed loop/tool guardrails, persistent CDP, durable Kanban workers, desktop/TUI/web/channels/voice/skills | Durable worker DAGs, execution intercepts, persistent supervised browser leases | Authority, receipts, FinalGate, memory-not-authority | Product surface, channels, skills, persistent agents, multi-agent runtime |
| OpenJarvis | Hybrid local/cloud orchestration, proactive agents, research loop, spec-search learning, inter-framework evals | Strategy routing from measured cost/latency/quality receipts; recursive context economy | Authority and action provability | Hardware/local routing, proactive operation, worker strategies, benchmark comparison |
| JARVIS | Workflow engine, workflow editor, sidecar OCR/capture, realtime voice, provider breadth | Versioned workflow IR, device-local capture, realtime transport, secure filesystem primitives | Safer authority model and action evidence | Workflow breadth, voice, desktop/sidecar productization |
| gptme | Local-first unconstrained agent with persistent agents and background jobs | Long-lived local mission and operator handoff patterns | Governance | Continuous autonomous operation and local execution ergonomics |
| Letta | Stateful memory-first agents with skills and subagents | Durable semantic/entity memory and continual-learning evaluation | Memory authority boundaries | Product-grade persistent memory |
| UI-TARS Desktop | Multimodal GUI/browser/remote computer operator | Visual grounding and target verification for desktop actions | Governance and receipts | Live computer-use reach |
| DeerFlow | Subagent, memory, sandbox, skill, and channel super-agent harness | Worker orchestration and long-running research | Governance | General multi-agent runtime and skill/channel reach |
| Webwright | Browser workflows compiled into rerunnable programs and logs | Governed reusable browser procedures | Existing governed browser stack | Long-horizon code-as-action efficiency |
| Microsoft Agent Framework | Durable, restartable, checkpointed multi-agent workflows with HITL/time travel | Durable workflow and automatic replan runtime | Mission authority and receipts | Workflow durability and general worker orchestration |
| Agent Zero | Full Linux desktop agent with browser, host connector, projects, plugins, scheduler, and subordinate agents | Product workspace, operator intervention, workspace time travel, and full-system task ergonomics | Narrow explicit authority and provable action chain | Broad host reach, desktop cowork, plugins, scheduling, and product usability |
| oh-my-pi | Native high-performance agent harness with persistent execution kernels, LSP/debugger, hash-anchored edits, parallel worktree subagents, and curated memory | Harness efficiency, typed worker outputs, interruption-time rules, and content-addressed editing | Mission-level authority and cross-organ receipts | Coding harness success rate, execution ergonomics, debugger/LSP depth |
| OpenClaw official-current | Large multi-channel personal agent platform with gateway, sessions, cron, skills, nodes, approvals, and broad UI | Channel/product reach, stable sessions, cron UX, and explicit execution approval surfaces | Authority model, receipts, FinalGate, and memory-not-authority | User reach, integrations, scheduled operation, skill ecosystem, and product surface |

Current Sentinel priority:

```text
1. persistent semantic memory and cognitive continuity
2. durable mission workflows plus automatic replan
3. authority-inheriting multi-agent worker fleet
4. production mission daemon and proactive scheduler
5. model-amplifying execution harness
6. governed skill and reusable procedure fabric
7. hardware-aware local/cloud model routing
8. real channel reach
9. permissioned desktop sidecar
10. realtime voice
```

Date: 2026-04-26
Mode: source-only forensic comparison.

| Vendor | Commit | Core strength | Source-backed mechanism | High-risk surface | Sentinel rewrite |
| --- | --- | --- | --- | --- | --- |
| OpenClaw | `a2288c2b09e621f89a915960398f58e200b3b69d` | Runtime, channels, skills, gateway, approval UI patterns | Canonical scanner: `agent-lab/audits/openclaw_scanner_report.json`; static audit: `agent-lab/audits/openclaw_static_audit.md` | 83 scanned items; 52 blocked, 29 needs review, 2 draft-only in B2.5 scanner | Keep scanner/policy ideas. Do not bridge runtime. |
| Hermes Agent | `35c57cc46b88710a98c4d43107b87b4ab828e3eb` | Memory, skills, delegation, prompt composition, tool hooks | `AIAgent` init and budgets (`run_agent.py:844-946`), memory setup (`run_agent.py:1596-1704`), skill prompt index (`prompt_builder.py:621-708`), dispatcher hooks (`model_tools.py:498-630`) | Memory/plugin injection, external providers, skill auto-maintenance, messaging extras, Google Workspace skill install path | Rewrite memory and skills as permissioned, scanned, non-policy context. |
| OpenJarvis | `484d0f090b127a9b8a00f02d64c35428cb7be706` | Local-first routing, hardware-aware model choice, learning metrics, skill import | `recommend_engine`, `recommend_model`, `estimated_download_gb` (`core/config.py:209-300`), learning weights (`core/config.py:667-675`), `AgentConfigEvolver` (`learning/agents/agent_evolver.py:52-223`) | Skill import/sync from remote sources, direct skill run, learned config mutation, many channel extras | Rewrite CostRouter and SkillImporter with budget caps, sandbox scan, and approval gates. |
| JARVIS | `7b66f0d3c77a4d050d56ff98b5723fd00b9fb937` | Daemon, authority model, approval lifecycle, sidecar, desktop/browser awareness | `AuthorityEngine.checkAuthority` (`authority/engine.ts:61-175`), `ApprovalManager` (`authority/approval.ts:31-196`), sidecar JWT/enrollment (`sidecar/manager.ts:28-277`), sidecar RPC (`sidecar/handlers.go:15-67`) | Terminal shell, browser submit, desktop control, screenshots, clipboard, sidecar config mutation, token handling | Rewrite PermissionedSidecar and AuthorityGate with critical-action hard blocks and explicit user approval. |

## Cross-Agent Pattern Synthesis

| Pattern | Vendors showing it | Forensic conclusion | Sentinel target |
| --- | --- | --- | --- |
| Prompt/context assembly | Hermes, JARVIS | Both inject contextual memory/profile/role data into prompts. Hermes scans project context for injection; JARVIS labels user profile as untrusted (`roles/prompt-builder.ts:149-157`). | Sentinel prompt compiler must label every context block by trust level and source. |
| Memory as behavior substrate | Hermes, JARVIS | Durable memory is powerful but can poison future sessions if interpreted as instructions. | Memory is context only; policy lives in signed config. |
| Skills/plugins | OpenClaw, Hermes, OpenJarvis | Skills create leverage and supply-chain risk. | Skills require manifest, static scan, sandbox eval, risk class, approval, trace. |
| Channels/external messaging | OpenClaw, Hermes, OpenJarvis, JARVIS | Channel sends create reputation, privacy, and compliance risk. | Outbound communication is draft-only until approval and compliance gates exist. |
| Browser/desktop control | OpenClaw, JARVIS | App-specific templates make agents useful but can send or submit real-world actions. | Browser is read-only first; submit/send/publish are critical actions. |
| Local/cloud/cost routing | Hermes, OpenJarvis | Cost control is an architecture concern, not a UI afterthought. | Budget per run; route by risk, evidence depth, model capability, and spend cap. |

## Historical April Ranking For Sentinel Rewrites

1. Now: CueIdea-backed evidence normalization, GTM pack quality, trace ledger, firewall, skill scanner.
2. Next: CostRouter, memory context with source/trust labels, plugin manifest scanner.
3. Later: read-only browser sandbox, permissioned sidecar, channel adapters.
4. Avoid for now: shell execution, browser submit, real outbound messages, desktop automation, vendor bridges.
