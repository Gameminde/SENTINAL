# SENTINAL

SENTINAL is the repository for the Sentinel Control product workspace.

Sentinel Control is a proof-backed business decision and controlled execution system for AI agents. The short-term product is the Sentinel GTM Operator. The long-term platform moat is the AgentOps Firewall.

The core idea is simple:

1. Turn an idea or CueIdea signal into evidence.
2. Use research and debate before recommending action.
3. Generate a useful GTM pack with clear proof.
4. Score every proposed action through policy and risk.
5. Require preview, approval, and trace before execution.

## Repository Layout

```text
.
├── sentinel-control/              # Product code and local app
│   ├── apps/web/                  # Next.js dashboard
│   ├── services/sentinel-core/    # Python agent core
│   ├── packages/evals/            # Safety and business-quality datasets
│   ├── supabase/migrations/       # Supabase schema
│   ├── docs/                      # Product, security, deployment, and progress docs
│   └── preview/                   # Static preview fallback
│
└── agent-lab/                     # Research-only runtime lab
    ├── audits/                    # Runtime audits and failure matrices
    ├── benchmarks/                # Safe benchmark plans
    ├── tools/                     # Static scanners and lab tooling
    ├── adapters/                  # Future experimental adapter notes
    └── sentinel_integration_notes/
```

## Product Direction

Sentinel is not a generic chatbot.

The product has two connected tracks:

- `Sentinel GTM Operator`: turns raw ideas into evidence-backed GTM packs, ICPs, positioning, landing copy, outreach drafts, interview scripts, prospect sources, and 7-day validation plans.
- `AgentOps Firewall`: controls what agents can do with files, browser actions, code, APIs, email, channels, secrets, shell commands, and other high-impact tools.

## Current Status

Completed foundation:

- Product and security specs.
- Python core models and enums.
- Trace Ledger.
- AgentOps Firewall v0.
- Supabase schema and sync.
- CueIdea Bridge.
- Research agent skeleton.
- Multi-agent debate engine.
- GTM Pack generator.
- Safe file and draft executors.
- Learning and feedback layer.
- Web dashboard.
- Business-quality evaluator.
- Agent Lab workspace.
- OpenClaw static audit.
- OpenClaw dependency audit.
- OpenClaw static plugin/skill scanner.
- Canonical scanner report consistency lock.

## Sentinel Control

Main path:

```text
sentinel-control/
```

Important files:

- `sentinel-control/README.md`
- `sentinel-control/WORKSPACE_MAP.md`
- `sentinel-control/docs/PRODUCT_SPEC.md`
- `sentinel-control/docs/SECURITY_MODEL.md`
- `sentinel-control/docs/FIREWALL_POLICIES.md`
- `sentinel-control/docs/GTM_OPERATOR_SPEC.md`
- `sentinel-control/docs/CODEX_TASKS.md`
- `sentinel-control/docs/FULL_PROGRESS_REPORT.md`

### Local Web App

```bash
cd sentinel-control/apps/web
npm install
npm run dev
```

Environment template:

```text
sentinel-control/apps/web/.env.example
```

Real local credentials should stay in:

```text
sentinel-control/apps/web/.env.local
```

That file is ignored by git.

### Python Core

```bash
cd sentinel-control/services/sentinel-core
python -m pip install -e ".[dev]"
pytest
```

The core includes:

- shared schemas;
- trace ledger;
- firewall policy engine;
- CueIdea bridge;
- research and source ranking;
- debate engine;
- GTM pack generation;
- safe execution primitives;
- eval runner;
- learning and feedback modules.

### Supabase

Migration:

```text
sentinel-control/supabase/migrations/001_sentinel_core.sql
```

Expected environment variables:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Never commit real Supabase credentials.

## Agent Lab

Main path:

```text
agent-lab/
```

Agent Lab is research-only. It studies external agent runtimes without integrating vendor code into Sentinel production.

Current OpenClaw findings:

- OpenClaw source was cloned locally for static audit only.
- Dependencies were not installed.
- Runtime was not executed.
- Skills and plugins were not executed.
- Real accounts were not connected.

The actual OpenClaw vendor source is excluded from this repository. Agent Lab keeps the audit artifacts, scanner code, fixtures, and reports.

Important files:

- `agent-lab/README.md`
- `agent-lab/AGENT_LAB_PLAN.md`
- `agent-lab/audits/openclaw_static_audit.md`
- `agent-lab/audits/openclaw_dependency_audit.md`
- `agent-lab/audits/openclaw_scanner_report.md`
- `agent-lab/audits/openclaw_scanner_report.json`
- `agent-lab/tools/openclaw_static_scanner/scanner.py`
- `agent-lab/tools/openclaw_static_scanner/tests/test_scanner.py`

### Run Agent Lab Scanner Tests

```bash
python -B -m unittest discover -s agent-lab/tools/openclaw_static_scanner/tests
```

### Regenerate Canonical OpenClaw Scanner Reports

This command expects an OpenClaw source checkout at `agent-lab/vendors/openclaw/source`.

```bash
python agent-lab/tools/openclaw_static_scanner/scanner.py --source agent-lab/vendors/openclaw/source --out agent-lab/audits/openclaw_scanner_report.json --markdown-out agent-lab/audits/openclaw_scanner_report.md
```

## Safety Model

High-impact actions remain disabled or approval-gated in v1:

- email sending;
- browser form submission;
- shell execution;
- production code modification;
- unrestricted filesystem access;
- real payment flows;
- real channel/message sending;
- plugin marketplace install.

Every future execution feature must pass through:

- evidence;
- risk score;
- permission policy;
- dry-run preview;
- user approval;
- trace log;
- eval coverage.

## Development Rules

- Do not commit `.env`, `.env.local`, API keys, tokens, or service role keys.
- Do not commit generated GTM packs from `sentinel-control/data/generated_projects`.
- Do not commit Python caches, Next build outputs, `node_modules`, or local virtual environments.
- Do not commit third-party runtime source clones under `agent-lab/vendors/*/source`.
- Keep Agent Lab research separate from Sentinel production code.

## North Star

Sentinel should become the system that turns raw business ideas into proof-backed decisions and controlled agent actions. It should learn from powerful agent runtimes, but keep Sentinel's core difference intact: evidence, policy, approval, and trace before action.
