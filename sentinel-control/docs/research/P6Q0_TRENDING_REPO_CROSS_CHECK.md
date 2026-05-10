# P6Q0 Trending Repo Cross-Check

Date: 2026-05-10

## Purpose

This document is a market and method cross-check only. It does not override
AgentLab.

```text
AgentLab = deep source
GitHub trends = external signal
Sentinel rewrite = implementation rule
```

## Repos Checked

GitHub metadata was checked on 2026-05-10 for recent activity and broad signal.

| Repo | Signal | Sentinel lesson |
| --- | --- | --- |
| `langchain-ai/langgraph` | Resilient language agents as graphs | Long missions need durable graph state and checkpoint-like continuity |
| `openai/openai-agents-python` | Lightweight multi-agent workflows | Handoffs, tracing, and workflow boundaries should stay first-class |
| `browser-use/browser-use` | Browser automation for AI agents | Browser organs need action abstraction and compact browser state |
| `trycua/cua` | Computer-use agent infrastructure, sandboxes, benchmarks | Desktop power should be benchmarked and sandboxed before broad promotion |
| `ChromeDevTools/chrome-devtools-mcp` | Chrome DevTools for coding agents | MCP/browser tooling can expose precise browser diagnostics without full browser dump |
| `upstash/context7` | Up-to-date code documentation for LLMs | Context retrieval should be current, scoped, and decision-specific |
| `infiniflow/ragflow` | RAG engine fused with agent capabilities | Retrieval is becoming the context layer of agents, not a side feature |
| `mem0ai/mem0` | Universal memory layer for AI agents | Memory must be typed, sourced, and retrievable without becoming authority |
| `OpenHands/OpenHands` | AI-driven development agent | Coding/runtime agents need workspace state, action receipts, and terminal/file context compression |
| `aaif-goose/goose` | Extensible agent that can install, execute, edit, and test with any LLM | Extensibility and execution power are product differentiators, but need authority and receipts |
| `n8n-io/n8n` | Workflow automation with many integrations | Integrations win through breadth, but broad integration surfaces require routing and trace discipline |
| `activepieces/activepieces` | AI agents, MCPs, workflow automation, many connectors | MCP and workflow ecosystems are becoming standard tool surfaces for agents |

## Cross-Check Conclusions

### 1. Graphs And Checkpoints Are Winning

Modern agents are moving from single prompt loops to graph or workflow runtimes.
Sentinel already has phase locks, receipts, workspaces, and Brain L4 modules.
P6R should make the LLM decision frame a graph node input, not a full mission
dump.

### 2. Browser And Desktop Are Becoming Core Powers

Browser and computer-use repos are highly active. This validates Sentinel's
organ strategy, but it also increases urgency for context economy because
browser/desktop observations can be huge.

### 3. MCP And Connectors Are Tool Surface Multipliers

MCP makes tool ecosystems easier to expose. That is power, but also prompt
pressure. Sentinel needs `ToolSurfaceRouter` before adding more surfaces.

### 4. Memory And RAG Are Becoming The Context Layer

Context7, RAGFlow, and mem0 signal that the market is converging on scoped
retrieval instead of full prompt history. Sentinel should use receipts,
workspace snapshots, memory, and evidence refs as retrieval substrates.

### 5. User-Selected Model Is Product-Correct

Many current tools support many providers. Sentinel should not force a model.
It should optimize context, tool exposure, retries, and quality around the
user-selected model.

## Rejected Direction

P6Q0 rejects this path:

```text
follow trending repos directly
clone runtime ideas blindly
add Code/Shell because it is powerful
promote Desktop L6 before measuring context pressure
```

P6Q0 accepts this path:

```text
AgentLab-first analysis
trend cross-check
Sentinel-native rewrite
context economy before stronger L6 promotions
```
