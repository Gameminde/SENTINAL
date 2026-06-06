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

### June 6, 2026 Refresh

Agent Lab has been refreshed against current upstream source before Sentinel's
next power wave.

- Hermes Agent, OpenJarvis, and JARVIS source-only snapshots were
  fast-forwarded to current official upstream heads.
- The historical OpenClaw Baseten specimen remains pinned; the active official
  `openclaw/openclaw` project is now tracked as a separate current specimen
  because it has diverged by more than 5,000 commits.
- gptme, Letta, UI-TARS Desktop, DeerFlow, Webwright, and Microsoft Agent
  Framework were admitted as new source-only power specimens.
- Agent Zero and oh-my-pi were also admitted after a power-focused GitHub
  discovery pass.

Current synthesis:

```text
Sentinel leads on authority, receipts, FinalGate, and memory-not-authority.
Competitors lead on durable workflows, persistent memory, multi-agent workers,
desktop/voice reach, channels, skills, and long-running product operation.
```

Current reports:

- `audits/TRENDING_AGENT_ADMISSION_MATRIX_2026_06_06.md`
- `audits/final/2026-06-06_agent_lab_vendor_refresh_delta_report.md`
- `audits/final/2026-06-06_sentinel_competitive_power_delta_and_roadmap.md`

Sprint A created the research workspace, audit docs, benchmark plan, and Sentinel integration notes.

Sprint B1 cloned OpenClaw source for static audit only. No dependencies were installed and no runtime was executed.

Sprint B2 added the OpenClaw dependency audit and a read-only static plugin/skill scanner. The scanner generated JSON and Markdown reports without installing dependencies, running OpenClaw, executing skills, or connecting accounts.

Sprint B2.5 locked scanner report consistency: one scanner command now generates both canonical outputs, the Markdown report is generated from the JSON report, and tests compare totals/risk counts/decision counts across both files.

Fresh clone note, verified on 2026-04-26:

- vendor `source/` folders are ignored by git;
- this clone may contain canonical scanner reports without containing `vendors/openclaw/source`;
- B2.5 artifact consistency can be verified from the committed reports and scanner tests;
- a fresh scanner rerun requires restoring the OpenClaw source snapshot first, without installing dependencies or running OpenClaw.

Current local state after 2026-04-26 restoration:

- `vendors/openclaw/source` is present locally;
- it is checked out at `a2288c2b09e621f89a915960398f58e200b3b69d`;
- the B2.5 scanner was rerun from that source;
- no dependencies were installed and OpenClaw was not run.

Sprint B3 added a fake-only OpenClaw runtime benchmark harness. It uses controlled fixtures to test prompt injection, external-send requests, plugin send capability, package install requests, secret access, browser form submission, filesystem traversal, and memory/policy override attempts. It does not run OpenClaw or execute any real skill/plugin.

## Source Snapshot

Original baseline checked on April 24-26, 2026; refresh checked on June 6,
2026:

- OpenClaw: https://github.com/basetenlabs/openclaw-baseten
- OpenClaw official-current: https://github.com/openclaw/openclaw
- Hermes Agent: https://github.com/nousresearch/hermes-agent
- OpenJarvis: https://github.com/open-jarvis/OpenJarvis
- JARVIS: https://github.com/vierisid/jarvis
- AgentMemory: https://github.com/rohitg00/agentmemory
- OpenClaw marketplace risk reference: https://www.theverge.com/news/874011/openclaw-ai-skill-clawhub-extensions-security-nightmare
- gptme: https://github.com/gptme/gptme
- Letta: https://github.com/letta-ai/letta
- UI-TARS Desktop: https://github.com/bytedance/UI-TARS-desktop
- DeerFlow: https://github.com/bytedance/deer-flow
- Webwright: https://github.com/microsoft/Webwright
- Microsoft Agent Framework: https://github.com/microsoft/agent-framework
- Agent Zero: https://github.com/agent0ai/agent-zero
- oh-my-pi: https://github.com/can1357/oh-my-pi

## Layout

- `vendors/` - vendor clones or source snapshots, later only
- `audits/` - capability matrix, failure matrix, reuse strategy, and vendor notes
- `benchmarks/` - safe benchmark task specs
- `adapters/` - future experimental adapters, not production code
- `sentinel_integration_notes/` - what Sentinel might build after audits

## Current Vendor Status

| Vendor | Local Source | Status |
| --- | --- | --- |
| OpenClaw historical Baseten specimen | `vendors/openclaw/source`; ignored in fresh clones | Pinned historical snapshot |
| OpenClaw official-current | `vendors/openclaw-official/source`; ignored in fresh clones | New current source-only specimen at `e974d988` |
| Hermes Agent | `vendors/hermes-agent/source`; ignored in fresh clones | Refreshed source-only at `ebed881d` |
| OpenJarvis | `vendors/openjarvis/source`; ignored in fresh clones | Refreshed source-only at `bb904804` |
| JARVIS | `vendors/jarvis/source`; ignored in fresh clones | Refreshed source-only at `20bf2b79` |
| gptme | `vendors/gptme/source`; ignored in fresh clones | New source-only power specimen |
| Letta | `vendors/letta/source`; ignored in fresh clones | New source-only memory specimen |
| UI-TARS Desktop | `vendors/ui-tars-desktop/source`; ignored in fresh clones | New source-only computer-use specimen |
| DeerFlow | `vendors/deer-flow/source`; ignored in fresh clones | New source-only super-agent harness specimen |
| Webwright | `vendors/webwright/source`; ignored in fresh clones | New source-only long-horizon browser specimen |
| Microsoft Agent Framework | `vendors/microsoft-agent-framework/source`; ignored in fresh clones | New source-only durable workflow specimen |
| Agent Zero | `vendors/agent-zero/source`; ignored in fresh clones | New source-only desktop/full-system specimen at `f9d8167a` |
| oh-my-pi | `vendors/oh-my-pi/source`; ignored in fresh clones | New source-only high-performance agent harness specimen at `4ae58e1a` |
| AgentMemory | `vendors/agentmemory/source`; ignored in fresh clones | Static memory audit completed from local source snapshot |

## OpenClaw Sprint B2 Artifacts

- `audits/openclaw_dependency_audit.md`
- `audits/openclaw_scanner_report.json`
- `audits/openclaw_scanner_report.md`
- `tools/openclaw_static_scanner/scanner.py`
- `tools/openclaw_static_scanner/tests/test_scanner.py`

## OpenClaw Sprint B3 Artifacts

- `benchmarks/openclaw_fake_runtime/fake_channel_messages.jsonl`
- `benchmarks/openclaw_fake_runtime/fake_plugin_manifests/`
- `benchmarks/openclaw_fake_runtime/fake_skills/`
- `benchmarks/openclaw_fake_runtime/expected_results.json`
- `benchmarks/openclaw_fake_runtime/benchmark_runner.py`
- `benchmarks/openclaw_fake_runtime/reports/openclaw_fake_benchmark_report.md`

## AgentMemory Memory Lab Artifacts

- `vendors/agentmemory/README.md`
- `audits/agentmemory_static_memory_audit.md`
- `sentinel_integration_notes/agentmemory_to_sentinel.md`

## North Star

Sentinel should learn from the hands, eyes, memory, and routing ideas in other agent systems, while keeping Sentinel's core difference: evidence, policy, approval, and trace before action.
