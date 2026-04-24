# Agent Lab

Research-only workspace for studying open-source agent runtimes without merging them into Sentinel Control production code.

## Purpose

Agent Lab exists to understand the useful runtime patterns behind projects like OpenClaw, Hermes Agent, OpenJarvis, and JARVIS, then decide what Sentinel should take, rewrite, or avoid.

This lab is separate from `sentinel-control` by design.

## Rules

- Do not copy vendor code into Sentinel.
- Do not run unknown skills, extensions, or sidecars with broad permissions.
- Do not connect real email, real browser profiles, crypto wallets, SSH keys, production accounts, or private credentials.
- Use sandbox accounts and test folders only.
- Treat every external skill or extension as untrusted until audited.
- Any future execution benchmark must have an expected output, a sandbox path, a permission model, and an audit log.

## Current Scope

Sprint A created the research workspace, audit docs, benchmark plan, and Sentinel integration notes.

Sprint B1 cloned OpenClaw source for static audit only. No dependencies were installed and no runtime was executed.

Sprint B2 added the OpenClaw dependency audit and a read-only static plugin/skill scanner. The scanner generated JSON and Markdown reports without installing dependencies, running OpenClaw, executing skills, or connecting accounts.

Sprint B2.5 locked scanner report consistency: one scanner command now generates both canonical outputs, the Markdown report is generated from the JSON report, and tests compare totals/risk counts/decision counts across both files.

## Source Snapshot

Checked on April 24, 2026:

- OpenClaw: https://github.com/basetenlabs/openclaw-baseten
- Hermes Agent: https://github.com/nousresearch/hermes-agent
- OpenJarvis: https://github.com/open-jarvis/OpenJarvis
- JARVIS: https://github.com/vierisid/jarvis
- OpenClaw marketplace risk reference: https://www.theverge.com/news/874011/openclaw-ai-skill-clawhub-extensions-security-nightmare

## Layout

- `vendors/` - vendor clones or source snapshots, later only
- `audits/` - capability matrix, failure matrix, reuse strategy, and vendor notes
- `benchmarks/` - safe benchmark task specs
- `adapters/` - future experimental adapters, not production code
- `sentinel_integration_notes/` - what Sentinel might build after audits

## Current Vendor Status

| Vendor | Local Source | Status |
| --- | --- | --- |
| OpenClaw | `vendors/openclaw/source` | Static audit and read-only scanner completed |
| Hermes Agent | none | Not cloned |
| OpenJarvis | none | Not cloned |
| JARVIS | none | Not cloned |

## OpenClaw Sprint B2 Artifacts

- `audits/openclaw_dependency_audit.md`
- `audits/openclaw_scanner_report.json`
- `audits/openclaw_scanner_report.md`
- `tools/openclaw_static_scanner/scanner.py`
- `tools/openclaw_static_scanner/tests/test_scanner.py`

## North Star

Sentinel should learn from the hands, eyes, memory, and routing ideas in other agent systems, while keeping Sentinel's core difference: evidence, policy, approval, and trace before action.
