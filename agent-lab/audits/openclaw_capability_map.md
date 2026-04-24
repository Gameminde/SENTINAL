# OpenClaw Capability Map

Status: static source audit completed on 2026-04-24. Source cloned to `agent-lab/vendors/openclaw/source` at commit `a2288c2b0`. No install or runtime test yet.

## Source-Backed Observations

- OpenClaw is a TypeScript/JavaScript pnpm monorepo with Node `>=22.12.0`.
- Source size observed: `4,881` files / `41,400,764` bytes.
- There are `30` `openclaw.plugin.json` manifests under `extensions/`.
- There are `52` bundled `SKILL.md` files under `skills/`.
- Channel plugin pattern is source-backed through manifests plus `api.registerChannel`.
- Gateway/control-plane pattern is source-backed through `src/gateway/server.impl.ts`, `src/gateway/server-methods-list.ts`, and `src/gateway/client.ts`.
- Plugin API can register tools, hooks, HTTP handlers/routes, channels, gateway methods, CLI registrars, services, providers, and commands.
- Exec approval machinery exists in source through `src/infra/exec-approvals.ts`, `src/agents/bash-tools.exec.ts`, gateway methods, and UI approval overlay.
- Browser control can launch a local Chrome-family browser with CDP through `src/browser/chrome.ts`.

## Key Source Refs

- `agent-lab/vendors/openclaw/source/package.json`
- `agent-lab/vendors/openclaw/source/pnpm-workspace.yaml`
- `agent-lab/vendors/openclaw/source/src/plugins/manifest.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/loader.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/registry.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/server.impl.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/server-methods-list.ts`
- `agent-lab/vendors/openclaw/source/src/agents/tool-policy.ts`
- `agent-lab/vendors/openclaw/source/src/infra/exec-approvals.ts`
- `agent-lab/vendors/openclaw/source/ui/src/ui/views/exec-approval.ts`
- `agent-lab/vendors/openclaw/source/src/browser/chrome.ts`

## Benchmark Priorities

1. Dependency audit before install.
2. Channel adapter boundaries using fake inbound messages only.
3. Skill manifest structure and scanner prototype.
4. Exec approval behavior in a container, later only.
5. Filesystem path boundary tests.
6. Browser/CDP sandbox plan, later only.
7. Live canvas/session concept, read-only first.

## Sentinel Position

- TAKE: channel adapter pattern, gateway/control-plane idea, exec approval UI concept, tool-profile concept, skill readiness report.
- REWRITE: plugin loader, skill system, channel send workflows, browser executor, shell/runtime executor, memory plugins, plugin install/update.
- AVOID NOW: marketplace installs, unrestricted plugin tools, host shell, real messaging accounts, real browser profiles, background services, allow-always approvals.
