# OpenClaw Static Audit

Date: 2026-04-24

Scope: static source audit only.

Source:

- Repository: `https://github.com/basetenlabs/openclaw-baseten`
- Local path: `agent-lab/vendors/openclaw/source`
- Commit: `a2288c2b0`
- Clone type: shallow clone
- Size observed: `4,881` files / `41,400,764` bytes

No install, build, test, runtime, account connection, skill execution, browser launch, or channel login was performed.

## Repo Structure Summary

Top-level source areas:

- `src/` - core TypeScript runtime, gateway, agents, channels, plugins, browser, memory, terminal, config, daemon, CLI.
- `extensions/` - plugin packages with `openclaw.plugin.json` manifests and `index.ts` entrypoints.
- `skills/` - bundled `SKILL.md` skill folders.
- `ui/` - Lit/Vite control UI.
- `apps/` - Android, iOS, macOS, and shared app surfaces.
- `packages/` - workspace packages such as `clawdbot` and `moltbot`.
- `scripts/` - build, test, setup, sandbox, auth, release, and packaging scripts.
- `Dockerfile`, `Dockerfile.sandbox`, `Dockerfile.sandbox-browser`, `docker-compose.yml` - container surfaces.

Source refs:

- `agent-lab/vendors/openclaw/source/package.json`
- `agent-lab/vendors/openclaw/source/pnpm-workspace.yaml`
- `agent-lab/vendors/openclaw/source/src`
- `agent-lab/vendors/openclaw/source/extensions`
- `agent-lab/vendors/openclaw/source/skills`
- `agent-lab/vendors/openclaw/source/apps`

## Package Scripts

Dependency manager:

- `packageManager`: `pnpm@10.23.0`
- Node engine: `>=22.12.0`
- Workspace packages: `.`, `ui`, `packages/*`, `extensions/*`

High-impact scripts observed in `package.json`:

- `postinstall`: runs `node scripts/postinstall.js`.
- `dev`, `start`, `openclaw`: run `node scripts/run-node.mjs`.
- `gateway:dev`, `gateway:dev:reset`, `gateway:watch`: start gateway runtime paths.
- `build`: bundles canvas/UI, compiles TypeScript, writes build metadata.
- `prepack`: runs full build and UI build.
- `ui:dev`, `ui:install`, `ui:build`: run UI helper script.
- `test:docker:*`: runs multiple Docker live/onboarding/plugin/QR/network flows.
- `android:run`, `ios:run`, `mac:*`: run mobile/desktop build or app launch flows.
- `plugins:sync`: syncs plugin versions.
- `test:live`: requires live model tests through env flags.

Static decision:

- Do not run `pnpm install`; it would trigger `postinstall` and native dependency installation.
- Do not run `dev`, `start`, `gateway:*`, `ui:*`, mobile/desktop, Docker, live tests, or plugin commands in Sprint B1.

Source refs:

- `agent-lab/vendors/openclaw/source/package.json`
- `agent-lab/vendors/openclaw/source/pnpm-workspace.yaml`
- `agent-lab/vendors/openclaw/source/scripts/postinstall.js`

## Dependency Surface

Notable runtime dependencies from `package.json`:

- messaging/channels: `@slack/bolt`, `@slack/web-api`, `@line/bot-sdk`, `grammy`, `@whiskeysockets/baileys`, `signal-utils`.
- servers/network: `express`, `hono`, `ws`, `undici`.
- browser/media: `playwright-core`, `sharp`, `file-type`, `pdfjs-dist`, `@mozilla/readability`.
- terminal/process: `@lydell/node-pty`.
- model/runtime: `@mariozechner/pi-agent-core`, `@mariozechner/pi-ai`, `@mariozechner/pi-coding-agent`, `ollama`.
- storage/memory: `sqlite-vec`.

Native/built dependencies listed in `pnpm.onlyBuiltDependencies` include:

- `@lydell/node-pty`
- `@matrix-org/matrix-sdk-crypto-nodejs`
- `authenticate-pam`
- `node-llama-cpp`
- `sharp`
- `@whiskeysockets/baileys`

Static implication:

- dependency install has native binary and postinstall risk;
- no dependency installation should happen until a separate dependency audit is complete.

Source refs:

- `agent-lab/vendors/openclaw/source/package.json`
- `agent-lab/vendors/openclaw/source/pnpm-workspace.yaml`

## Channel Adapter Locations

OpenClaw has bundled channel plugins under `extensions/`, each with `openclaw.plugin.json` and usually an `index.ts`.

Manifests observed: `30`.

Channel plugin IDs observed:

- `bluebubbles`
- `discord`
- `googlechat`
- `imessage`
- `line`
- `matrix`
- `mattermost`
- `msteams`
- `nextcloud-talk`
- `nostr`
- `signal`
- `slack`
- `telegram`
- `tlon`
- `twitch`
- `whatsapp`
- `zalo`
- `zalouser`

Provider/plugin IDs observed:

- `copilot-proxy`
- `google-antigravity-auth`
- `google-gemini-cli-auth`
- `minimax-portal-auth`
- `qwen-portal-auth`

Memory plugin IDs observed:

- `memory-core`
- `memory-lancedb`

Representative channel registration pattern:

- `extensions/slack/index.ts` calls `api.registerChannel({ plugin: slackPlugin })`.
- `extensions/telegram/index.ts` calls `api.registerChannel({ plugin: telegramPlugin })`.
- `extensions/whatsapp/index.ts` calls `api.registerChannel({ plugin: whatsappPlugin })`.

Source refs:

- `agent-lab/vendors/openclaw/source/extensions/slack/index.ts`
- `agent-lab/vendors/openclaw/source/extensions/telegram/index.ts`
- `agent-lab/vendors/openclaw/source/extensions/whatsapp/index.ts`
- `agent-lab/vendors/openclaw/source/extensions/*/openclaw.plugin.json`

## Gateway / Control Plane Architecture

The gateway is a central control plane with WebSocket/HTTP methods, auth, plugin loading, node registry, channel manager, browser server, cron service, and exec approval manager.

Static observations:

- `src/gateway/server.impl.ts` starts the gateway and wires config, channels, plugins, nodes, cron, browser, canvas, auth, and exec approvals.
- `src/gateway/server-methods-list.ts` defines base methods such as `config.get`, `config.set`, `exec.approvals.get`, `exec.approval.request`, `node.invoke`, `cron.add`, `send`, `agent`, `browser.request`, `chat.send`, and session operations.
- `src/gateway/auth.ts` supports token/password auth, Tailscale identity paths, and local-direct request checks.
- `src/gateway/client.ts` is a WebSocket client with auth token/password, device identity, scopes, permissions, reconnect logic, and event frames.
- `src/gateway/server-plugins.ts` merges plugin gateway methods into the base gateway methods.

Source refs:

- `agent-lab/vendors/openclaw/source/src/gateway/server.impl.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/server-methods-list.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/auth.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/client.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/server-plugins.ts`

## Skill / Extension Mechanism

Extension/plugin system:

- `src/plugins/manifest.ts` defines `openclaw.plugin.json` with `id`, `configSchema`, `kind`, `channels`, `providers`, `skills`, `name`, `description`, `version`, and UI hints.
- `src/plugins/discovery.ts` discovers plugins from config paths, workspace `.openclaw/extensions`, global config extensions, and bundled plugin directories.
- `src/plugins/loader.ts` uses `jiti` to load TypeScript/JavaScript plugin modules and calls `register` or `activate`.
- `src/plugins/registry.ts` exposes plugin API capabilities: register tools, hooks, HTTP handlers/routes, channels, gateway methods, CLI registrars, services, providers, and commands.
- `src/plugins/install.ts` can install plugins from npm specs, archives, paths, dirs, or files; package installs may run `npm install --omit=dev --silent` if plugin dependencies exist.

Skill system:

- `skills/` contains `52` bundled `SKILL.md` files.
- `src/agents/skills-status.ts` evaluates skill eligibility from metadata requirements such as binaries, env vars, config paths, OS, allowlist, and per-skill config.
- `src/cli/skills-cli.ts` lists and reports skill readiness and points users toward `clawhub`.
- `skills/clawhub/SKILL.md` documents searching, installing, updating, and publishing skills via `clawhub`.
- `skills/coding-agent/SKILL.md` instructs shell/PTY execution for coding agents.
- `skills/1password/SKILL.md` includes 1Password CLI workflows and secret-handling guidance.

Source refs:

- `agent-lab/vendors/openclaw/source/src/plugins/manifest.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/discovery.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/loader.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/registry.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/install.ts`
- `agent-lab/vendors/openclaw/source/src/agents/skills-status.ts`
- `agent-lab/vendors/openclaw/source/src/cli/skills-cli.ts`
- `agent-lab/vendors/openclaw/source/skills/clawhub/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/coding-agent/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/1password/SKILL.md`

## Permission Model Found

Static permission/control mechanisms observed:

- Plugin enablement uses global plugin enabled flag, allowlist, denylist, load paths, slots, and per-plugin entries in `src/plugins/config-state.ts`.
- Bundled plugins are disabled by default unless configured or selected for a slot, based on `BUNDLED_ENABLED_BY_DEFAULT` being empty in source.
- Tool profiles exist in `src/agents/tool-policy.ts`, including `minimal`, `coding`, `messaging`, and `full`.
- Tool groups include `group:fs`, `group:runtime`, `group:messaging`, `group:ui`, `group:automation`, `group:openclaw`, and others.
- Optional plugin tools require an allowlist match in `src/plugins/tools.ts`.
- Exec approvals exist through `src/infra/exec-approvals.ts`, `src/agents/bash-tools.exec.ts`, gateway methods, and UI approval overlay.
- Config docs describe `commands.bash` as disabled by default and requiring `tools.elevated`.

Static limitation:

- The plugin API can register broad capability types. Sentinel should not treat plugin registration as sufficient permission proof.
- Runtime behavior of these controls was not tested in Sprint B1.

Source refs:

- `agent-lab/vendors/openclaw/source/src/plugins/config-state.ts`
- `agent-lab/vendors/openclaw/source/src/agents/tool-policy.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/tools.ts`
- `agent-lab/vendors/openclaw/source/src/infra/exec-approvals.ts`
- `agent-lab/vendors/openclaw/source/src/agents/bash-tools.exec.ts`
- `agent-lab/vendors/openclaw/source/ui/src/ui/views/exec-approval.ts`
- `agent-lab/vendors/openclaw/source/src/config/schema.ts`

## Filesystem Access Points

Observed static filesystem surfaces:

- Config read/write and migration in gateway startup.
- Plugin discovery from workspace/global/bundled extension folders.
- Plugin install copies packages/files to extension directories.
- Skill discovery/status checks `SKILL.md` and requirements.
- Cron store and run logs write JSON/log files.
- Browser profile creation writes OpenClaw Chrome user-data under config dir.
- Canvas host reads/writes/serves local files and has path checks.
- Media store/server and browser download paths read/write local artifacts.
- Channel integrations may read token/session files.

Representative source refs:

- `agent-lab/vendors/openclaw/source/src/plugins/install.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/discovery.ts`
- `agent-lab/vendors/openclaw/source/src/config/config.ts`
- `agent-lab/vendors/openclaw/source/src/cron/store.ts`
- `agent-lab/vendors/openclaw/source/src/cron/run-log.ts`
- `agent-lab/vendors/openclaw/source/src/browser/chrome.ts`
- `agent-lab/vendors/openclaw/source/src/canvas-host/server.ts`
- `agent-lab/vendors/openclaw/source/src/media/server.ts`
- `agent-lab/vendors/openclaw/source/extensions/zalo/src/token.ts`
- `agent-lab/vendors/openclaw/source/extensions/googlechat/src/accounts.ts`

## Shell / Exec Usage Points

Observed static execution surfaces:

- `src/process/exec.ts` wraps `execFile` and `spawn`.
- `src/agents/bash-tools.exec.ts` exposes command execution with host/node/gateway paths and approval flows.
- `src/infra/exec-approvals.ts` parses shell command segments and evaluates allowlists.
- `src/daemon/*.ts` uses `systemctl`, `launchctl`, `schtasks`, node runtime probing, and service inspection.
- `src/hooks/gmail-setup-utils.ts` invokes `gcloud`, `brew`, and `tailscale`.
- `src/hooks/gmail-ops.ts` invokes `gog`.
- `src/browser/chrome.ts` launches Chrome/Brave/Edge/Chromium with CDP args.
- `extensions/zalouser/src/zca.ts` spawns the `zca` binary.
- `extensions/lobster/src/lobster-tool.ts` spawns workflow commands.
- `extensions/voice-call/src/tunnel.ts` and `src/webhook.ts` spawn `ngrok` and `tailscale`.
- `src/commands/signal-install.ts` uses `unzip`/`tar`.

Static implication:

- OpenClaw has meaningful built-in command execution surfaces. Sentinel should keep `run_shell_command` critical and disabled until a separate sandbox and approval design exists.

Source refs:

- `agent-lab/vendors/openclaw/source/src/process/exec.ts`
- `agent-lab/vendors/openclaw/source/src/agents/bash-tools.exec.ts`
- `agent-lab/vendors/openclaw/source/src/infra/exec-approvals.ts`
- `agent-lab/vendors/openclaw/source/src/daemon/systemd.ts`
- `agent-lab/vendors/openclaw/source/src/daemon/launchd.ts`
- `agent-lab/vendors/openclaw/source/src/daemon/schtasks.ts`
- `agent-lab/vendors/openclaw/source/src/hooks/gmail-setup-utils.ts`
- `agent-lab/vendors/openclaw/source/src/hooks/gmail-ops.ts`
- `agent-lab/vendors/openclaw/source/src/browser/chrome.ts`
- `agent-lab/vendors/openclaw/source/extensions/zalouser/src/zca.ts`
- `agent-lab/vendors/openclaw/source/extensions/lobster/src/lobster-tool.ts`
- `agent-lab/vendors/openclaw/source/extensions/voice-call/src/tunnel.ts`

## Network / API Usage Points

Observed static network surfaces:

- Gateway WebSocket client/server and gateway HTTP routes.
- Channel APIs for Slack, Telegram, Discord, Matrix, Mattermost, Google Chat, LINE, WhatsApp, Signal, iMessage, Zalo, Nextcloud Talk, Nostr, Microsoft Teams, Twitch, and voice-call integrations.
- OAuth/device-code providers for Google Gemini CLI, Google Antigravity, Qwen, Minimax, GitHub Copilot.
- Browser CDP WebSocket/HTTP calls.
- Memory embedding APIs for OpenAI and Gemini.
- TTS/STT/voice-call APIs including Twilio/Plivo/Telnyx/OpenAI realtime/audio paths.
- Proxy support through `undici` in Telegram/Zalo.

Representative source refs:

- `agent-lab/vendors/openclaw/source/src/gateway/client.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/server.impl.ts`
- `agent-lab/vendors/openclaw/source/src/browser/chrome.ts`
- `agent-lab/vendors/openclaw/source/src/memory/embeddings-openai.ts`
- `agent-lab/vendors/openclaw/source/src/memory/embeddings-gemini.ts`
- `agent-lab/vendors/openclaw/source/src/tts/tts.ts`
- `agent-lab/vendors/openclaw/source/extensions/google-gemini-cli-auth/oauth.ts`
- `agent-lab/vendors/openclaw/source/extensions/google-antigravity-auth/index.ts`
- `agent-lab/vendors/openclaw/source/extensions/qwen-portal-auth/oauth.ts`
- `agent-lab/vendors/openclaw/source/extensions/mattermost/src/mattermost/monitor.ts`
- `agent-lab/vendors/openclaw/source/extensions/voice-call/src/providers/twilio.ts`

## Env / Secrets Required

Root `.env.example` contains Twilio WhatsApp credentials:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM`

Additional env/secrets observed in source or skills include:

- gateway: `OPENCLAW_GATEWAY_TOKEN`, `OPENCLAW_GATEWAY_PASSWORD`.
- model/search: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `BRAVE_API_KEY`, `FIRECRAWL_API_KEY`, `APIFY_API_TOKEN`.
- channels: `TELEGRAM_BOT_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `MATTERMOST_BOT_TOKEN`, `MATTERMOST_URL`, `LINE_CHANNEL_ACCESS_TOKEN`, `NEXTCLOUD_TALK_BOT_SECRET`, `MATRIX_ACCESS_TOKEN`, `MATRIX_PASSWORD`, `MSTEAMS_APP_ID`, `MSTEAMS_APP_PASSWORD`, `MSTEAMS_TENANT_ID`, `ZALO_BOT_TOKEN`.
- skills/integrations: `TRELLO_API_KEY`, `TRELLO_TOKEN`, `THINGS_AUTH_TOKEN`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `ELEVENLABS_API_KEY`.

Source refs:

- `agent-lab/vendors/openclaw/source/.env.example`
- `agent-lab/vendors/openclaw/source/src/gateway/auth.ts`
- `agent-lab/vendors/openclaw/source/src/wizard/onboarding.finalize.ts`
- `agent-lab/vendors/openclaw/source/src/channels/plugins/onboarding/telegram.ts`
- `agent-lab/vendors/openclaw/source/src/channels/plugins/onboarding/slack.ts`
- `agent-lab/vendors/openclaw/source/extensions/mattermost/src/mattermost/accounts.ts`
- `agent-lab/vendors/openclaw/source/extensions/line/src/channel.ts`
- `agent-lab/vendors/openclaw/source/extensions/nextcloud-talk/src/accounts.ts`
- `agent-lab/vendors/openclaw/source/extensions/matrix/src/onboarding.ts`
- `agent-lab/vendors/openclaw/source/extensions/msteams/src/token.ts`
- `agent-lab/vendors/openclaw/source/skills/summarize/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/trello/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/things-mac/SKILL.md`

## Sandbox Risks

High-risk areas for any future benchmark:

- plugin install can download packages and run dependency installs;
- plugin runtime can register tools, HTTP handlers/routes, gateway methods, services, hooks, channels, and providers;
- skills can instruct shell, external CLI installation, secret access, API calls, and account operations;
- channel integrations can receive prompt-injection payloads from external messages;
- channel integrations can send external messages;
- browser control can launch local browser profiles and CDP;
- shell/exec paths can spawn host commands;
- config writes can change behavior persistently;
- memory plugins can persist and retrieve user/context data;
- gateway exposes powerful methods that require strict auth and client scoping.

## Sentinel Can TAKE

- Channel adapter shape: plugin registers a channel with a normalized runtime API.
- Gateway/control-plane idea: central methods, events, nodes, sessions, approval queue.
- Exec approval UI concept: queue, command preview, allow-once/allow-always/deny.
- Tool profile concept: minimal/messaging/coding/full capability profiles.
- Plugin manifest concept: separate manifest from code entrypoint.
- Skill readiness reporting: detect missing bins/env/config before exposing a skill.

## Sentinel Must REWRITE

- Plugin loader: no dynamic `jiti` module loading into production without scanner and sandbox.
- Skill system: Sentinel skills need manifest permissions, source trust, tests, and Firewall policies before exposure.
- Channel send workflows: all external contact must be draft/preview/approval-gated.
- Browser executor: sandbox profile, no submit by default, trace every action.
- Shell/runtime execution: critical risk, separate sandbox, no host default.
- Memory plugins: secret-safe summaries and provenance labels.
- Plugin install/update: no npm pack/install until scanner and dependency audit exist.

## Sentinel Should AVOID For Now

- unrestricted plugin tools;
- marketplace installs;
- host shell execution;
- direct messaging account connections;
- real browser profile automation;
- background services;
- desktop/mobile sidecars;
- config writes from channels;
- allow-always approvals without expiration/scope.

## Next Static Audit Step

Create `openclaw_dependency_audit.md` before any install:

- inspect `pnpm-lock.yaml`;
- list native dependencies and postinstall scripts;
- list packages with network/crypto/credential access;
- decide whether a container-only install is acceptable.
