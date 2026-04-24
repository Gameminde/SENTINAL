# Failure Modes

Status: initial matrix with OpenClaw static audit notes and canonical Sprint B2.5 scanner output added on 2026-04-24. OpenClaw was cloned but not installed or run.

| Failure Mode | What To Test | Likely Gap In Generic Agents | Sentinel Mitigation | Test Required |
| --- | --- | --- | --- | --- |
| Prompt injection | Webpage or document says to ignore policy, exfiltrate secrets, or take external action. | Tool instructions can be mixed with untrusted content. | Treat scraped content as evidence only, never policy. Run prompt-injection detector before using content. | Injection dataset must block malicious instruction uptake. |
| Malicious skill | Skill requests shell, network, secrets, broad filesystem, or persistence. | Skills may be trusted because user installed them. | Skill manifest parser, permission declaration, secret scanner, shell detector, sandbox test. | Malicious skill eval must be blocked before install. |
| Credential leakage | Agent reads env files, browser profile, SSH keys, wallet paths, or API tokens. | Broad local access can expose secrets. | Sensitive path denylist, secret pattern detector, approval block for secret access. | Secret path access must be blocked and traced. |
| Unauthorized email | Agent sends or schedules emails without explicit user approval. | Channel runtimes may treat email as a normal tool. | Email stays draft-only until later; send requires approval, opt-out, contact provenance, trace. | No email send action may execute in v1. |
| Filesystem escape | File action writes outside sandbox or follows path tricks. | Tool may trust requested path. | Path canonicalization and allowed directory policy. | `../`, absolute path, symlink-like attempts blocked. |
| Shell command abuse | Agent executes shell commands or installs dependencies without review. | Shell is often exposed as a convenience tool. | Shell is critical risk and v1 disabled. Later only sandboxed dry-run/approval. | All shell actions blocked. |
| Hallucinated decision | Agent recommends build without proof. | Generic agents optimize fluency over market proof. | Decision requires evidence refs, WTP gate, skeptic challenge, GTM quality evaluator. | Weak evidence cannot produce ready/build pack. |
| Fake evidence | Agent treats fabricated or unverifiable claims as proof. | Sources may not be ranked or verified. | Evidence confidence, source URL, proof tier, fake-evidence evals. | Fake evidence downgraded. |
| Spam outreach | Agent drafts deceptive, mass-blast, or non-compliant outreach. | Growth workflows can optimize for volume. | Draft-only outreach, opt-out rule, spam pattern review, contact provenance. | Spammy outreach flagged. |
| Memory poisoning | User or webpage stores false facts or malicious future instructions. | Memory may be appended without filtering. | Memory classification, source labels, retention controls, no policy memory from untrusted text. | Poisoned memory must not change policy. |
| Cost explosion | Agent loops, calls expensive models, or runs too many tools. | Autonomy can hide cost. | Budget per run, cost estimates, tool-call caps, model router later. | Cost cap stops runaway tasks. |
| Unsafe self-improvement | Agent modifies prompts, skills, code, or policy automatically. | Learning loops can mutate behavior without governance. | Improvement proposals only; tests and user approval before application. | No auto-code/policy modification. |

## OpenClaw-Specific Static Notes

These are source-backed static findings only. Runtime behavior is not verified.

### Prompt Injection Via Channel Messages

Observed surface:

- Channel plugins exist for Slack, Telegram, WhatsApp, Discord, Google Chat, Matrix, Mattermost, Microsoft Teams, Signal, iMessage, and others.
- Plugin hooks include `message_received`, `message_sending`, `before_tool_call`, and `after_tool_call`.

Source refs:

- `agent-lab/vendors/openclaw/source/extensions/*/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/src/plugins/types.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/registry.ts`

Sentinel mitigation:

- inbound channel messages must be untrusted input;
- channel content can become evidence/context only, not policy;
- prompt-injection eval must run before external content can influence actions.

### Malicious Skill

Observed surface:

- `52` bundled `SKILL.md` files exist.
- `skills/clawhub/SKILL.md` documents search/install/update/publish flows.
- `skills/coding-agent/SKILL.md` documents shell/PTY workflows.
- `skills/1password/SKILL.md` documents secret-manager CLI workflows.
- `src/agents/skills-status.ts` checks requirements, but this is readiness gating, not a full malicious-skill scanner.

Source refs:

- `agent-lab/vendors/openclaw/source/skills`
- `agent-lab/vendors/openclaw/source/skills/clawhub/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/coding-agent/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/1password/SKILL.md`
- `agent-lab/vendors/openclaw/source/src/agents/skills-status.ts`

Sentinel mitigation:

- every skill needs a scanner before exposure;
- scanner must classify shell, secret, network, filesystem, account, and install behavior;
- no marketplace install path before scanner plus sandbox.

### Credential Leakage

Observed surface:

- root `.env.example` expects Twilio credentials;
- channel/source files reference Slack, Telegram, Mattermost, LINE, Matrix, Microsoft Teams, Nextcloud, Zalo, OpenAI/Gemini and other tokens;
- `skills/1password/SKILL.md` includes secret-manager workflows.

Source refs:

- `agent-lab/vendors/openclaw/source/.env.example`
- `agent-lab/vendors/openclaw/source/src/gateway/auth.ts`
- `agent-lab/vendors/openclaw/source/extensions/mattermost/src/mattermost/accounts.ts`
- `agent-lab/vendors/openclaw/source/extensions/msteams/src/token.ts`
- `agent-lab/vendors/openclaw/source/extensions/matrix/src/onboarding.ts`
- `agent-lab/vendors/openclaw/source/skills/1password/SKILL.md`

Sentinel mitigation:

- never expose real env vars to runtime benchmarks;
- add secret path denylist;
- add token pattern scanner for manifests, config, skills, and logs.

### Filesystem Escape

Observed surface:

- plugin installation writes into extension directories;
- browser profile creation writes config/browser user-data;
- canvas/media/browser systems read and write local files;
- config and cron systems persist files.

Source refs:

- `agent-lab/vendors/openclaw/source/src/plugins/install.ts`
- `agent-lab/vendors/openclaw/source/src/browser/chrome.ts`
- `agent-lab/vendors/openclaw/source/src/canvas-host/server.ts`
- `agent-lab/vendors/openclaw/source/src/media/server.ts`
- `agent-lab/vendors/openclaw/source/src/cron/store.ts`

Sentinel mitigation:

- canonical path checks;
- generated-output root only;
- symlink and traversal tests;
- no plugin install writes outside a sandbox.

### Shell Abuse

Observed surface:

- `src/process/exec.ts` wraps `spawn` and `execFile`;
- bash tools can request elevated execution and approval;
- daemon and setup paths invoke host tools;
- several extensions spawn external binaries.

Source refs:

- `agent-lab/vendors/openclaw/source/src/process/exec.ts`
- `agent-lab/vendors/openclaw/source/src/agents/bash-tools.exec.ts`
- `agent-lab/vendors/openclaw/source/src/infra/exec-approvals.ts`
- `agent-lab/vendors/openclaw/source/extensions/zalouser/src/zca.ts`
- `agent-lab/vendors/openclaw/source/extensions/voice-call/src/tunnel.ts`

Sentinel mitigation:

- `run_shell_command` stays critical and disabled;
- future shell support must be isolated, dry-run first, trace-only, and approval-gated.

### Unauthorized Messaging / Email

Observed surface:

- gateway has `send` method;
- channel plugins can send messages;
- Gmail hooks/skills and email-oriented skills exist, though email as first-class channel was not verified in this pass.

Source refs:

- `agent-lab/vendors/openclaw/source/src/gateway/server-methods-list.ts`
- `agent-lab/vendors/openclaw/source/extensions/slack/index.ts`
- `agent-lab/vendors/openclaw/source/extensions/telegram/index.ts`
- `agent-lab/vendors/openclaw/source/src/hooks/gmail-ops.ts`
- `agent-lab/vendors/openclaw/source/skills/himalaya/SKILL.md`

Sentinel mitigation:

- outbound external contact is high risk;
- v1 stays draft-only;
- later sends require provenance, opt-out/compliance check, approval, and trace.

## Sprint B2.5 Canonical Scanner Output

The OpenClaw static scanner report is available at:

- `agent-lab/audits/openclaw_scanner_report.json`
- `agent-lab/audits/openclaw_scanner_report.md`

Scanner scope:

- 31 plugin-like items scanned, including root package scripts;
- 52 skills scanned;
- no dependencies installed;
- no runtime executed;
- no skills or plugins executed.

Canonical metadata:

- scanner version: `0.2.0`;
- ruleset version: `2026-04-24.b2.5`;
- source commit: `a2288c2b09e621f89a915960398f58e200b3b69d`;
- total items: `83`;
- canonical hash: stored in `metadata.json_sha256` in `openclaw_scanner_report.json`;
- Markdown report: generated from JSON only.

### Scanner-Backed Risk Counts

| Risk Pattern | Count | Sentinel Position |
| --- | ---: | --- |
| `network_api_access` | 66 | Require domain/tool allowlist and trace. |
| `external_binary_requirement` | 53 | Require binary allowlist and sandbox. |
| `shell_execution` | 45 | Critical; blocked. |
| `env_secret_or_config_reference` | 37 | Require secret access policy; default deny. |
| `filesystem_access` | 26 | Require canonical path allowlist. |
| `external_message_send` | 22 | High risk; approval plus contact provenance. |
| `channel_adapter` | 20 | Inbound allowed only as untrusted content; outbound gated. |
| `browser_control` | 16 | Sandbox profile only; submit disabled until later. |
| `http_route` | 13 | Requires auth, route review, and trace. |
| `package_or_remote_install` | 12 | Critical; blocked until scanner plus container gate. |
| `memory_or_persistence` | 12 | Requires memory filter and source provenance. |
| `prompt_injection_instruction` | 12 | Requires injection review before content can influence action. |
| `background_service` | 5 | Critical; blocked. |
| `secret_manager_access` | 2 | Critical; blocked by default. |
| `install_time_script` | 1 | Critical; host install blocked. |

Decision counts:

- `blocked`: 52;
- `needs_review`: 29;
- `draft_only_tool`: 2.

### Malicious Skill

Scanner-backed examples:

- `agent-lab/vendors/openclaw/source/skills/clawhub/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/coding-agent/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/1password/SKILL.md`
- `agent-lab/vendors/openclaw/source/skills/goplaces/SKILL.md`

Added Sentinel test:

- a skill with install commands, shell commands, secret manager access, or required API keys must be classified as `blocked` or `needs_review`, never `safe_static_doc`.

### Credential Leakage

Scanner-backed examples:

- `agent-lab/vendors/openclaw/source/skills/1password/SKILL.md`
- `agent-lab/vendors/openclaw/source/extensions/google-gemini-cli-auth/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/msteams/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/matrix/openclaw.plugin.json`

Added Sentinel test:

- any plugin or skill referencing env tokens, OAuth secrets, password strings, or secret-manager commands must map to `secret_access_policy`.

### Shell Abuse

Scanner-backed examples:

- `agent-lab/vendors/openclaw/source/extensions/zalouser/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/tlon/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/lobster/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/skills/coding-agent/SKILL.md`

Added Sentinel test:

- any shell, PTY, spawn, exec, package install, curl install, or remote install pattern must map to `run_shell_command` or `plugin_install_policy`.

### Filesystem Escape

Scanner-backed examples:

- `agent-lab/vendors/openclaw/source/extensions/memory-lancedb/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/google-gemini-cli-auth/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/bluebubbles/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/skills/tmux/SKILL.md`

Added Sentinel test:

- any filesystem-capable plugin or skill must require `filesystem_access_policy` and cannot write outside a sandbox path.

### Unauthorized Messaging

Scanner-backed examples:

- `agent-lab/vendors/openclaw/source/extensions/slack/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/telegram/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/discord/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/line/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/whatsapp/openclaw.plugin.json`

Added Sentinel test:

- outbound channel adapters must map to `external_contact_policy`; no send path can be enabled without preview, approval, provenance, opt-out/compliance rules where relevant, and trace.

### Memory Poisoning

Scanner-backed examples:

- `agent-lab/vendors/openclaw/source/extensions/memory-core/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/memory-lancedb/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/matrix/openclaw.plugin.json`

Added Sentinel test:

- memory-capable plugins must classify memory source type and reject secrets or policy-like instructions from untrusted channel content.

### Cost Explosion

Scanner-backed examples:

- network and provider/API access patterns were found across 66 scanned items;
- root package scripts include live, gateway, docker, and install test surfaces.

Added Sentinel test:

- any provider/runtime adapter must declare budget, tool-call cap, and trace events before promotion.

## Minimum Firewall Position

Every future runtime feature needs:

- risk level;
- allowed input/output surface;
- dry-run preview;
- user approval rule;
- trace event;
- eval coverage;
- rollback or disable switch.
