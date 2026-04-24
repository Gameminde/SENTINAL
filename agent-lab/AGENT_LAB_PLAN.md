# Agent Lab Plan

## Mission

Build a controlled research lab for agent runtimes. The lab studies capabilities, failure modes, and reusable architecture patterns without integrating risky execution into Sentinel Control.

## Current Decision

Keep this workspace separate from `sentinel-control`.

Sentinel remains focused on:

1. GTM Pack quality.
2. Evidence-backed business decisions.
3. AgentOps Firewall controls.
4. Safe local execution only.

Agent Lab focuses on:

1. Runtime research.
2. Capability benchmarking.
3. Failure-mode mapping.
4. Future runtime blueprinting.

## Sprint A - Lab Setup

Status: in progress.

Tasks:

- Create isolated workspace structure.
- Add README and safety rules.
- Add capability matrix.
- Add failure matrix.
- Add reuse strategy.
- Add benchmark plan.
- Add Sentinel integration notes.

Acceptance:

- No vendor code is copied into Sentinel.
- Every benchmark uses sandbox resources.
- Every risky feature has a proposed Sentinel Firewall mitigation.

## Sprint B - Capability Matrix

Status: started with OpenClaw Sprint B1 static audit.

Tasks:

- Fill in observations for OpenClaw, Hermes Agent, OpenJarvis, and JARVIS.
- Map each capability to Sentinel current and Sentinel target.
- Mark each capability as Take, Rewrite, Avoid, or Later.

Acceptance:

- No capability enters Sentinel target without a policy implication.
- Every execution feature has a Firewall position.

## Sprint B1 - OpenClaw Static Audit

Status: completed.

Completed:

- cloned OpenClaw source into `vendors/openclaw/source`;
- recorded clone decision in `audits/vendor_clone_checks.md`;
- created `audits/openclaw_static_audit.md`;
- updated `audits/openclaw_capability_map.md`;
- updated `audits/CAPABILITY_MATRIX.md` with source-backed OpenClaw observations;
- updated `audits/FAILURE_MODES.md` with OpenClaw-specific risk notes;
- created `sentinel_integration_notes/openclaw_to_sentinel.md`.

Acceptance:

- OpenClaw was not run.
- Dependencies were not installed.
- No real accounts were connected.
- Findings cite local source paths.
- Reusable patterns include Sentinel Firewall implications.

## Sprint B2 - OpenClaw Dependency Audit And Static Scanner

Status: completed.

Completed:

- created `audits/openclaw_dependency_audit.md`;
- inspected root package scripts, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, postinstall scripts, Dockerfiles, env example, native dependency declarations, and browser/messaging/credential surfaces;
- built `tools/openclaw_static_scanner/` as a read-only Python scanner;
- added scanner fixtures for safe plugin, shell plugin, env-secret plugin, channel-send plugin, secret-manager skill, package-install skill, and prompt-injection skill;
- added unit tests for scanner risk classification and output schema;
- generated `audits/openclaw_scanner_report.json`;
- created `audits/openclaw_scanner_report.md`;
- updated `audits/FAILURE_MODES.md` with scanner-backed OpenClaw findings;
- updated `sentinel_integration_notes/openclaw_to_sentinel.md` with SkillScanner, ChannelAdapterManifest, PluginRiskClassifier, and promotion requirements.

Acceptance:

- OpenClaw was not run.
- Dependencies were not installed.
- Skills and plugins were not executed.
- Scanner reads files only.
- Scanner flags shell, secrets, network, filesystem, install commands, browser, channel send, background service, memory, and prompt-injection patterns.
- High-risk skills/plugins are classified as `blocked` or `needs_review`.
- No pattern is promoted to Sentinel without Firewall policy implications.

## Sprint B2.5 - Scanner Report Consistency Lock

Status: completed.

Completed:

- upgraded `tools/openclaw_static_scanner/scanner.py` to `scanner_version` `0.2.0`;
- added `ruleset_version` `2026-04-24.b2.5`;
- added canonical report metadata: scan timestamp, source commit, source path, total items, and JSON content hash;
- changed scanner CLI so one command generates both `audits/openclaw_scanner_report.json` and `audits/openclaw_scanner_report.md`;
- made the Markdown report generated from the JSON report only;
- added machine-readable Markdown count comments for consistency checks;
- added consistency tests comparing JSON totals, risk counts, and Sentinel decision counts against Markdown;
- added risk-threshold and Sentinel decision explanations to the generated Markdown report;
- regenerated the canonical OpenClaw scanner report from source commit `a2288c2b09e621f89a915960398f58e200b3b69d`.

Canonical scanner result:

- total items: 83;
- plugins/root-script items: 31;
- skills: 52;
- risk counts: `critical` 52, `high` 29, `medium` 2;
- Sentinel decisions: `blocked` 52, `needs_review` 29, `draft_only_tool` 2;
- JSON report hash: recorded in `audits/openclaw_scanner_report.json` under `metadata.json_sha256`.

Acceptance:

- One canonical scanner JSON exists.
- One Markdown report exists and is generated from that JSON.
- No contradictory scanner counts remain in current B2.5 outputs.
- Consistency tests pass.
- Scanner results are reproducible from one command.

## Sprint C - Failure Matrix

Tasks:

- Analyze prompt injection.
- Analyze malicious skills.
- Analyze credential leakage.
- Analyze unauthorized external actions.
- Analyze filesystem escape.
- Analyze shell abuse.
- Analyze memory poisoning.
- Analyze cost explosion.
- Analyze unsafe self-improvement.

Acceptance:

- Each failure has a Sentinel mitigation.
- Each mitigation has a test requirement.

## Sprint D - Runtime Blueprint

Tasks:

- Decide whether to build browser sandbox.
- Decide whether to build desktop sidecar.
- Decide whether to build channel adapters.
- Decide whether to build skill scanner.
- Decide whether to build local model/cost router.

Acceptance:

- No advanced runtime feature can move forward without a risk class, dry-run design, approval rule, and trace schema.

## Do Not Do Yet

- Do not run vendor sidecars.
- Do not connect real accounts.
- Do not enable browser submit.
- Do not enable email send.
- Do not enable shell execution.
- Do not enable desktop automation.
- Do not add vendor code to Sentinel.
