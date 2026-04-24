# OpenClaw Dependency Audit

Date checked: 2026-04-24

Scope: static dependency and install-surface audit only. OpenClaw source was read from `agent-lab/vendors/openclaw/source`. Dependencies were not installed and OpenClaw was not run.

## Source Files Inspected

- `agent-lab/vendors/openclaw/source/package.json`
- `agent-lab/vendors/openclaw/source/pnpm-lock.yaml`
- `agent-lab/vendors/openclaw/source/pnpm-workspace.yaml`
- `agent-lab/vendors/openclaw/source/scripts/postinstall.js`
- `agent-lab/vendors/openclaw/source/packages/clawdbot/scripts/postinstall.js`
- `agent-lab/vendors/openclaw/source/Dockerfile`
- `agent-lab/vendors/openclaw/source/Dockerfile.sandbox`
- `agent-lab/vendors/openclaw/source/Dockerfile.sandbox-browser`
- `agent-lab/vendors/openclaw/source/docker-compose.yml`
- `agent-lab/vendors/openclaw/source/.env.example`

## Package Overview

- Runtime: Node.js `>=22.12.0`
- Package manager: `pnpm@10.23.0`
- Workspaces: root, `ui`, `packages/*`, `extensions/*`
- Package type: ESM
- Root binary: `openclaw` via `openclaw.mjs`
- Root package includes compiled `dist/**`, `extensions/**`, `skills/**`, `scripts/postinstall.js`, and `patches/**`

## Root Scripts With Install Or Runtime Impact

High-impact scripts:

- `postinstall`: runs `node scripts/postinstall.js`
- `start`: runs `node scripts/run-node.mjs`
- `dev`: runs `node scripts/run-node.mjs`
- `gateway:dev`: runs gateway in dev mode with channels skipped
- `gateway:watch`: runs gateway watcher
- `android:install` and `android:run`: install and start Android app through Gradle/ADB
- `ios:build`, `ios:run`, `ios:open`: invoke Xcode tooling through shell commands
- `mac:package`, `mac:restart`: invoke macOS packaging/restart shell scripts
- `ui:install`: runs UI install helper
- `prepack`: builds root and UI
- `test:docker:*`: runs Docker-based e2e scripts
- `test:install:*`: runs install smoke/e2e Docker scripts

Scripts that must not run outside a container during Agent Lab work:

- `postinstall`
- `start`
- `dev`
- `gateway:*`
- `android:*`
- `ios:*`
- `mac:*`
- `ui:install`
- `prepack`
- `test:docker:*`
- `test:install:*`

## Postinstall Behavior

`scripts/postinstall.js` uses Node `fs`, `path`, and `child_process.spawnSync`.

Observed behavior:

- skips when `OPENCLAW_SKIP_POSTINSTALL`, `CLAWDBOT_SKIP_POSTINSTALL`, `VITEST`, or `NODE_ENV=test` is set;
- attempts to setup git hooks when a `.git` directory is present;
- tries shell completion install only if `dist/cli/completions/install.js` exists;
- detects the package manager from npm lifecycle environment;
- applies a fallback patch flow for non-pnpm managers against `node_modules` when relevant.

Risk classification:

- Host install risk: critical.
- Container-only install risk: high, acceptable only after an explicit benchmark plan.

The postinstall path is not necessarily malicious, but it is install-time code execution and must be treated as untrusted in Agent Lab.

## Native And Built Dependencies

Declared `onlyBuiltDependencies` in `package.json` and `pnpm-workspace.yaml`:

- `@lydell/node-pty`
- `@matrix-org/matrix-sdk-crypto-nodejs`
- `@napi-rs/canvas`
- `@whiskeysockets/baileys`
- `authenticate-pam`
- `esbuild`
- `node-llama-cpp`
- `protobufjs`
- `sharp`

Additional platform/binary surfaces found in lockfile:

- `@esbuild/*`
- `@img/sharp-*`
- `@node-llama-cpp/*`
- `@rolldown/binding-*`
- `@whiskeysockets/libsignal-node`

Sentinel implication:

- native dependency install must remain container-only;
- no native dependency should be installed on the host Agent Lab machine during the audit phase;
- any future benchmark image must use throwaway state, no real browser profile, no real messaging accounts, and no production env variables.

## Browser, Shell, Messaging, Credential, And File Packages

Browser/runtime:

- `playwright-core`
- Docker browser image installs Chromium, Xvfb, noVNC, Socat, and Websockify
- browser CLI and CDP surfaces were already noted in B1 static audit

Shell/process:

- `@lydell/node-pty`
- `child_process` usage in source, including `spawn`, `execFile`, and shared `runCommandWithTimeout` helpers
- platform service tooling for launchd/systemd/schtasks

Messaging/channels:

- `@slack/bolt`
- `@slack/web-api`
- `@line/bot-sdk`
- `grammy`
- `@grammyjs/runner`
- `@whiskeysockets/baileys`
- `discord-api-types`
- Matrix-related packages
- Signal/Zalo/Twitch/Teams/Google Chat/Mattermost channel extension source

Network/API:

- `express`
- `hono`
- `undici`
- `ws`
- `@aws-sdk/client-bedrock`
- `openai` and `@anthropic-ai/sdk` appear in lockfile provider surfaces

Credentials/auth:

- `.env.example` contains Twilio WhatsApp credential variables;
- source references gateway tokens/passwords, Slack tokens, Telegram tokens, Discord bot tokens, Google OAuth client secrets, Gemini OAuth secrets, Mattermost tokens, Matrix auth, Microsoft Teams tokens, and provider keys;
- skills include secret-manager and API-key oriented instructions.

Local files/state:

- config/state directories;
- browser user-data/profile paths;
- plugin install paths;
- memory stores;
- logs and trace-like session files;
- media/canvas file serving paths.

## Docker Surfaces

`Dockerfile`:

- starts from `node:22-bookworm`;
- installs Bun with `curl -fsSL https://bun.sh/install | bash`;
- enables Corepack;
- runs `pnpm install --frozen-lockfile`;
- runs `pnpm build` and `pnpm ui:build`;
- starts gateway as non-root `node`.

`Dockerfile.sandbox`:

- starts from `node:22-bookworm`;
- installs `bash`, `ca-certificates`, `curl`, `git`, `jq`, `python3`, and `ripgrep`;
- default command sleeps.

`Dockerfile.sandbox-browser`:

- installs Chromium, Xvfb, noVNC, Socat, Websockify and related browser/runtime packages;
- exposes browser/VNC ports;
- starts `openclaw-sandbox-browser`.

Docker decision:

- static audit: allowed;
- dependency install: blocked on host;
- dependency install in container: allowed later only with a written benchmark plan;
- runtime: blocked until scanner, policy mapping, and sandbox benchmark gates are complete.

## Install Risk Level

Install risk outside container: critical.

Reasons:

- install-time code execution via root `postinstall`;
- native dependencies and prebuilt binaries;
- shell/process packages;
- browser/CDP packages;
- messaging/channel packages requiring external accounts;
- credential-heavy provider and channel configuration;
- plugin/skill installation and dynamic loading surfaces.

Container-only install later: conditionally allowed.

Required before container install:

- pin source commit;
- use throwaway container and volume;
- use fake/sandbox env only;
- pass static scanner;
- block network except explicitly measured dependency retrieval;
- keep real credentials absent;
- record installed native binaries and postinstall effects.

Runtime decision: blocked.

## Final Decision

- Clone/read source: allowed and completed.
- Dependency install on host: blocked.
- Dependency install in container: allowed later only after a benchmark plan and explicit gate.
- Runtime execution: blocked.
- Skills/plugins execution: blocked.
- Real channels/accounts: blocked.

## Sentinel Takeaways

TAKE:

- channel adapter pattern;
- gateway/control-plane pattern;
- live session/control UI concept;
- approval-card concept for high-impact actions.

REWRITE:

- plugin loader;
- skill system;
- browser executor;
- channel send workflows;
- filesystem/runtime execution;
- memory plugins;
- dependency install process.

AVOID:

- host install during audit;
- unrestricted skills;
- marketplace installs without scanner;
- shell by default;
- real messaging accounts in early benchmarks;
- real browser profiles;
- allow-always approval for high-impact actions.
