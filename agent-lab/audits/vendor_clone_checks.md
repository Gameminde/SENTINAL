# Vendor Clone Checks

Use this file before cloning or running any vendor runtime.

## Template

```text
Project:
Repository:
Date checked:
Expected size:
Primary language/runtime:
Dependency manager:
Install commands reviewed:
Commands to avoid:
Network required:
Secrets required:
Sandbox directory:
Known high-risk permissions:
Run decision: clone only / install allowed / run allowed / blocked
Notes:
```

## Current Status

OpenClaw, Hermes Agent, OpenJarvis, JARVIS, TradingAgents, and AgentMemory are approved for source clone only. No install or runtime execution is approved.

## OpenClaw

```text
Project: OpenClaw
Repository: https://github.com/basetenlabs/openclaw-baseten
Date checked: 2026-04-24
Expected size: cloned shallow source is 4,881 files / 41,400,764 bytes at commit a2288c2b0
Primary language/runtime: TypeScript/JavaScript monorepo, Node >=22.12.0, plus mobile/desktop surfaces in apps/
Dependency manager: pnpm 10.23.0 via packageManager and pnpm-workspace.yaml
Install commands reviewed: root package scripts, pnpm-workspace.yaml, root postinstall, plugin install path, docker setup scripts
Commands to avoid: pnpm install, npm install, pnpm dev, pnpm start, pnpm build, pnpm test, pnpm gateway:dev, pnpm ui:dev, pnpm android:run, pnpm ios:run, docker compose, plugin install/update, skill execution, channel login, browser/canvas launch
Network required: yes for clone only; no runtime network approved
Secrets required: none for static audit
Sandbox directory: agent-lab/vendors/openclaw/source
Known high-risk permissions: channels, skills/extensions, filesystem, shell, browser/canvas, messaging-account integrations, possible secrets/env usage
Run decision: clone only
Notes: Source cloned into agent-lab/vendors/openclaw/source for static audit only. Treat source as untrusted. Do not install dependencies, run scripts, connect accounts, or execute skills/extensions during Sprint B1.
```

## Hermes Agent

```text
Project: Hermes Agent
Repository: https://github.com/nousresearch/hermes-agent
Date checked: 2026-04-26
Expected size: cloned source is 2,585 files / 67,523,148 bytes at commit 35c57cc46b88710a98c4d43107b87b4ab828e3eb
Primary language/runtime: Python package with gateway/plugins/skills plus optional Node bridge scripts
Dependency manager: pyproject.toml / setuptools; optional extras for messaging, cron, google, web, rl, voice
Install commands reviewed: pyproject scripts and extras, Google Workspace skill setup script, WhatsApp bridge package.json
Commands to avoid: pip install, uv install, python run_agent.py, hermes, hermes-agent, hermes-acp, plugin execution, skill setup, OAuth setup, messaging bridge start, gateway start
Network required: yes for clone only; no runtime network approved
Secrets required: none for static audit
Sandbox directory: agent-lab/vendors/hermes-agent/source
Known high-risk permissions: memory plugins, skills, Google Workspace scopes, messaging gateways, tool hooks, external providers, optional RL/web services
Run decision: clone only
Notes: Treat source as untrusted. Do not install dependencies, run scripts, connect accounts, execute skills, or start gateways.
```

## OpenJarvis

```text
Project: OpenJarvis
Repository: https://github.com/open-jarvis/OpenJarvis
Date checked: 2026-04-26
Expected size: cloned source is 1,774 files / 30,714,956 bytes at commit 484d0f090b127a9b8a00f02d64c35428cb7be706
Primary language/runtime: Python package with optional Rust, Tauri frontend, and bundled Node bridges
Dependency manager: pyproject.toml / hatchling / uv.lock; frontend package.json
Install commands reviewed: pyproject extras, skill CLI, channel bridges
Commands to avoid: pip install, uv sync, jarvis CLI, skill install/sync/run, model pull/download, channel login/start, dashboard/server start, Tauri/npm install
Network required: yes for clone only; no runtime network approved
Secrets required: none for static audit
Sandbox directory: agent-lab/vendors/openjarvis/source
Known high-risk permissions: skill import from GitHub/Hermes/OpenClaw, channel integrations, browser extra, cloud model credentials, local engine downloads
Run decision: clone only
Notes: Source-only audit for CostRouter, skill import, learning, and routing mechanisms.
```

## TradingAgents

```text
Project: TradingAgents
Repository: https://github.com/TauricResearch/TradingAgents
Date checked: 2026-05-09
Expected size: cloned source is 100 files / 5,079,309 bytes at commit 7e9e7b83c7fcc18d941300b253c6ed24d985788d
Primary language/runtime: Python package using LangGraph, LangChain, yfinance, Alpha Vantage adapters, CLI, Docker
Dependency manager: pyproject.toml / setuptools / uv.lock
Install commands reviewed: pyproject scripts, README CLI, Dockerfile, docker-compose.yml, provider key setup
Commands to avoid: pip install, uv sync, tradingagents CLI, python main.py, python -m cli.main, docker compose, data provider calls, LLM provider calls, broker/trading execution
Network required: yes for clone only; no runtime network approved
Secrets required: none for static audit
Sandbox directory: agent-lab/vendors/tradingagents/source
Known high-risk permissions: LLM provider API keys, Alpha Vantage key, yfinance network access, trading decision generation, persisted decision logs, checkpoint databases
Run decision: clone only
Notes: Source-only audit for trading role topology, bull/bear debate, risk debate, structured decision schemas, data vendor fallback, checkpoint/resume, and outcome reflection memory.
```

## JARVIS

```text
Project: JARVIS
Repository: https://github.com/vierisid/jarvis
Date checked: 2026-04-26
Expected size: cloned source is 556 files / 5,481,611 bytes at commit 7b66f0d3c77a4d050d56ff98b5723fd00b9fb937
Primary language/runtime: Bun/TypeScript daemon plus Go sidecar
Dependency manager: package.json / bun.lock / Go modules
Install commands reviewed: package scripts, install.sh, Dockerfile, sidecar package manifests
Commands to avoid: bun install, bun run start/dev/test/setup, install.sh, jarvis CLI, jarvis-sidecar, Docker build/run, Google setup, browser/desktop/terminal tools
Network required: yes for clone only; no runtime network approved
Secrets required: none for static audit
Sandbox directory: agent-lab/vendors/jarvis/source
Known high-risk permissions: sidecar terminal/filesystem/desktop/browser/clipboard/screenshot, browser templates with send flows, daemon persistence, JWT sidecar enrollment
Run decision: clone only
Notes: Source-only audit for daemon, authority, approval, sidecar, desktop/browser awareness, and workflow mechanisms.
```

## AgentMemory

```text
Project: AgentMemory
Repository: https://github.com/rohitg00/agentmemory
Date checked: 2026-05-19
Expected size: cloned shallow source only; commit 68fddd418e1bbcc41d32a1c61b7a78d91eb7c4dc
Primary language/runtime: TypeScript/Node package with iii runtime integration, REST API, MCP server, viewer, hooks, provider integrations, local-first storage
Dependency manager: package.json / npm
Install commands reviewed: README npm/npx flows, MCP setup, Codex/OpenClaw/Hermes integrations, Docker/iii runtime notes
Commands to avoid: npm install, npx @agentmemory/agentmemory, agentmemory server, agentmemory demo, agentmemory connect, agentmemory mcp, Docker compose, MCP client setup, viewer/server start, filesystem watcher, provider-backed graph/consolidation/compression, replay import from real histories
Network required: yes for clone only; no runtime network approved
Secrets required: none for static audit
Sandbox directory: agent-lab/vendors/agentmemory/source
Known high-risk permissions: persistent memory capture, raw prompt/tool/result observation, context injection, MCP/REST memory tools, local file compression/import, filesystem watcher, replay import, provider keys for graph/consolidation, broad host-agent integrations
Run decision: clone only
Notes: Source-only audit for Sentinel memory lab. Treat source as untrusted. Harvest mechanisms only; do not bridge AgentMemory runtime or copy vendor code into Sentinel.
```
