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

Every project listed in the refresh table below, plus TradingAgents and
AgentMemory, is approved for source clone only. No install or runtime execution
is approved.

## Refresh Status - 2026-06-06

The following source-only snapshots were refreshed or admitted. No dependency
was installed and no vendor runtime was executed.

| Project | Official Repository | Snapshot | Decision |
| --- | --- | --- | --- |
| Hermes Agent | https://github.com/nousresearch/hermes-agent | `ebed881d46c4d39a7723a0bdbb70b53429f65e26` | refreshed source-only |
| OpenJarvis | https://github.com/open-jarvis/OpenJarvis | `bb904804302dd7a6f81698b49bf38dd22f06e3de` | refreshed source-only |
| JARVIS | https://github.com/vierisid/jarvis | `20bf2b79657002fa2668a2ecf4ff5c6611d9bd4b` | refreshed source-only |
| gptme | https://github.com/gptme/gptme | `7355b1820342a43cda846cd88cee291b77b6f2dc` | admitted source-only |
| Letta | https://github.com/letta-ai/letta | `1131535716e8a31c9a437f8695e25ac98f203a24` | admitted source-only |
| UI-TARS Desktop | https://github.com/bytedance/UI-TARS-desktop | `e9f3387288da4af2ad99972da2ac916cdabce093` | admitted source-only |
| DeerFlow | https://github.com/bytedance/deer-flow | `9a5de8d6a5a75c9f277a79d36b90407e3029a1ba` | admitted source-only |
| Webwright | https://github.com/microsoft/Webwright | `4a46f282ec37f27d6003cc498a977939d62d9015` | admitted source-only |
| Microsoft Agent Framework | https://github.com/microsoft/agent-framework | `fa9e08657618a6cf50818f7069ee4af3d5c725e6` | admitted source-only |
| OpenClaw official-current | https://github.com/openclaw/openclaw | `e974d988113c657af324ceb3878158e717dd5994` | admitted source-only; historical Baseten specimen retained separately |
| Agent Zero | https://github.com/agent0ai/agent-zero | `f9d8167a0004632ea7d8b37f585f392c39865919` | admitted source-only |
| oh-my-pi | https://github.com/can1357/oh-my-pi | `4ae58e1abcaf1b3dbcded5e71afd5aacf794f944` | admitted source-only |

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
