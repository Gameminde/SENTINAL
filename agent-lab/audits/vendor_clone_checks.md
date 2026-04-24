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

OpenClaw is approved for source clone only. No install or runtime execution is approved.

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
