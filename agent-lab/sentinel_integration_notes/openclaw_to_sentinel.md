# OpenClaw To Sentinel Notes

Status: source-backed static notes only. OpenClaw was cloned but not installed or run.

## What Sentinel Might Reuse Conceptually

### Channel Adapter Pattern

OpenClaw's channel plugins use manifests plus entrypoints that register channels through a plugin API.

Source refs:

- `agent-lab/vendors/openclaw/source/extensions/slack/openclaw.plugin.json`
- `agent-lab/vendors/openclaw/source/extensions/slack/index.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/registry.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/types.ts`

Sentinel rewrite:

- `ChannelAdapterManifest`
- `channel_id`
- `inbound_event_schema`
- `outbound_action_schema`
- `required_secrets`
- `allowed_actions`
- `firewall_policy_refs`
- `trace_event_types`

No real channel should be connected before auth, tenant isolation, source provenance, external-contact policy, and approval gates are implemented.

### Gateway / Control Plane Pattern

OpenClaw centralizes methods/events around a gateway. Sentinel can use the same control-plane idea for agent runs and approvals, but with business evidence and risk as first-class entities.

Source refs:

- `agent-lab/vendors/openclaw/source/src/gateway/server-methods-list.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/server.impl.ts`
- `agent-lab/vendors/openclaw/source/src/gateway/client.ts`

Sentinel rewrite:

- every gateway method maps to a `tool_name`;
- every method has a policy record;
- every method emits trace records;
- every external side effect produces a dry-run preview first.

### Exec Approval UI

OpenClaw has an approval overlay for exec requests.

Source refs:

- `agent-lab/vendors/openclaw/source/ui/src/ui/views/exec-approval.ts`
- `agent-lab/vendors/openclaw/source/src/agents/bash-tools.exec.ts`
- `agent-lab/vendors/openclaw/source/src/infra/exec-approvals.ts`

Sentinel rewrite:

- approval cards must include evidence refs, risk score, policy result, dry-run preview, source data, and expected output;
- approvals must be scoped and expire;
- `allow-always` should not exist for high-impact actions in early versions.

## Skill Manifest Scanner Requirements

Before any OpenClaw-style skill or plugin bridge exists, Sentinel needs a scanner that extracts:

- manifest id, version, source, author if present;
- declared channels/providers/tools/services/hooks/http routes;
- config schema and sensitive fields;
- required env vars;
- required binaries;
- shell command strings;
- filesystem read/write hints;
- network endpoints/domains;
- package manager commands;
- postinstall scripts;
- secret-looking strings;
- prompt-injection-like instructions;
- external account operations.

Scanner should classify:

- `safe_static_doc`
- `draft_only_tool`
- `requires_secrets`
- `external_contact`
- `filesystem_write`
- `browser_control`
- `shell_execution`
- `background_service`
- `blocked`

OpenClaw source refs:

- `agent-lab/vendors/openclaw/source/src/plugins/manifest.ts`
- `agent-lab/vendors/openclaw/source/src/plugins/install.ts`
- `agent-lab/vendors/openclaw/source/src/agents/skills-status.ts`
- `agent-lab/vendors/openclaw/source/skills/*/SKILL.md`

## Firewall Policies Needed Before Any Bridge

Required policies:

- `channel_receive_message`: medium, stores inbound content as untrusted evidence/context.
- `channel_send_message`: high, approval required, external contact policy required.
- `install_plugin`: critical, disabled until scanner and dependency sandbox exist.
- `enable_plugin`: high/critical depending on declared permissions.
- `register_plugin_tool`: high, requires manifest scan and allowlist.
- `register_http_route`: high, requires auth, path, and handler review.
- `register_background_service`: critical, disabled until runtime sandbox exists.
- `run_shell_command`: critical, disabled by default.
- `browser_launch`: high, sandbox profile only.
- `browser_submit_form`: high, disabled until later.
- `read_secret`: critical, disabled by default.
- `memory_write`: medium, requires secret filter and provenance.
- `config_write`: high, approval required.

## Evals Required Before Promotion

Channel adapter evals:

- inbound prompt injection through Slack/Telegram-style messages;
- unauthorized sender attempts command;
- fake identity in forwarded message metadata;
- outbound message requires preview and approval;
- external contact provenance missing blocks send.

Skill/plugin evals:

- manifest with shell command is critical;
- manifest with env secrets is high/critical;
- plugin registering HTTP route requires review;
- plugin registering background service is blocked;
- npm install/postinstall is blocked;
- path traversal in plugin install is blocked;
- plugin tool cannot bypass Firewall by changing name.

Browser/runtime evals:

- browser read-only summary works in sandbox profile;
- form submit is blocked;
- real profile path is rejected;
- shell execution is blocked;
- filesystem writes outside sandbox are blocked.

Memory evals:

- secrets are not stored;
- untrusted channel content cannot become policy memory;
- prompt-injection memory cannot alter future approvals.

## Promotion Rule

Nothing from OpenClaw moves into Sentinel until it has:

1. product value;
2. capability map;
3. failure map;
4. Firewall policy;
5. dry-run design;
6. approval rule;
7. trace schema;
8. eval dataset;
9. passing test result;
10. rollback/disable switch.

## Immediate Recommendation

Do not build an OpenClaw bridge yet.

Next useful work:

1. dependency audit of OpenClaw lockfile and postinstall surfaces;
2. static plugin/skill scanner prototype in Agent Lab only;
3. safe benchmark plan for channel adapter shape with fake messages only;
4. compare OpenClaw exec approval UI with Sentinel Firewall approval board.

## Sprint B2 Addendum: Scanner And Policy Requirements

Sprint B2 created:

- `agent-lab/audits/openclaw_dependency_audit.md`
- `agent-lab/tools/openclaw_static_scanner/scanner.py`
- `agent-lab/audits/openclaw_scanner_report.json`
- `agent-lab/audits/openclaw_scanner_report.md`

### SkillScanner v0 Requirements

Sentinel's future scanner should:

- parse plugin manifests and skill metadata before install or enable;
- read source text without executing it;
- emit canonical JSON and Markdown from the same scanner run;
- include scanner version, ruleset version, scan timestamp, source commit, source path, total count, and report hash;
- extract required env vars, required binaries, package install commands, shell patterns, filesystem access hints, network/API references, browser-control hints, memory/persistence hints, and external-contact operations;
- classify each item as `safe_static_doc`, `draft_only_tool`, `needs_review`, or `blocked`;
- map every detected risk to a Firewall policy;
- preserve source file refs in the report;
- produce JSON for automated evals and Markdown for human review.
- pass consistency tests that compare JSON and Markdown counts before any report is accepted.

Minimum blocking rules:

- shell/exec/PTY: `blocked`;
- package install or remote install command: `blocked`;
- secret-manager access: `blocked`;
- background service registration: `blocked`;
- external send capability: `needs_review` until approval flow exists;
- env secret requirement: `needs_review` or `blocked` depending on tool;
- browser control: `needs_review` and sandbox-only later;
- memory write: `needs_review` with secret filter and provenance rules.

### ChannelAdapterManifest v0 Requirements

Any Sentinel channel adapter inspired by OpenClaw must declare:

- `channel_id`;
- inbound event schema;
- outbound action schema;
- required env variables and secrets;
- send/read capability flags;
- rate limit defaults;
- allowed sender/account scope;
- external-contact policy reference;
- prompt-injection review policy reference;
- trace event types;
- dry-run preview fields for outbound messages.

Outbound send remains disabled until:

- user identity and tenant isolation are complete;
- contact provenance is stored;
- approval cards include preview and risk score;
- opt-out/compliance text rules exist where relevant;
- `external_contact_policy` tests pass.

### PluginRiskClassifier Requirements

The classifier should combine:

- declared manifest capabilities;
- detected source patterns;
- dependency/install requirements;
- required secrets;
- side-effect class;
- source trust level;
- runtime sandbox availability;
- prior eval results.

Classifier output must include:

- risk level;
- Sentinel decision;
- required Firewall policies;
- required eval datasets;
- promotion blockers;
- trace schema requirements.

### Promotion Rule From Scanned Plugin To Experimental Adapter

A scanned OpenClaw-style plugin can become a Sentinel experimental adapter only if:

1. scanner decision is not `blocked`;
2. every detected risk maps to a policy;
3. a dry-run preview exists for every side effect;
4. user approval is required for medium/high/critical impact;
5. all external data is labeled untrusted;
6. no real secrets are needed for local tests;
7. tests cover bypass attempts;
8. trace records are written for scan, review, approval, and execution;
9. rollback/disable switch exists;
10. the adapter adds GTM Operator or AgentOps Firewall value.
