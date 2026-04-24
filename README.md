# SENTINAL

SENTINAL is a product workspace for two connected apps and one research lab.

This is not one single app. It is a monorepo-style workspace that contains:

1. `RedditPulse/` - the existing CueIdea market-validation app and evidence engine.
2. `sentinel-control/` - the new Sentinel Control app for GTM packs, agent decisions, approvals, and the AgentOps Firewall.
3. `agent-lab/` - a research-only lab for studying agent runtimes such as OpenClaw without mixing vendor code into production.

## What This Repository Is

The repository is the evolution path from CueIdea into Sentinel Control.

`RedditPulse` is the current market intelligence and idea validation system. It gathers market signals, validates ideas, scores demand, analyzes competitors, and produces evidence.

`Sentinel Control` is the next product layer. It takes evidence from CueIdea/RedditPulse, researches deeper, debates before deciding, generates GTM packs, proposes actions, runs them through a Firewall, and keeps trace logs.

`Agent Lab` is the R&D area. It does not power the product directly. It studies agent runtime patterns, scans risky plugin/skill behavior, and documents what Sentinel should take, rewrite, or avoid.

## Simple Mental Model

```text
RedditPulse / CueIdea
    Evidence engine, market validation, demand signals, competitors, WTP signals

        feeds into

Sentinel Control
    Decision agent, GTM pack generator, safe execution, approval flow, trace ledger

        protected and informed by

Agent Lab
    Runtime research, skill scanner, failure modes, future AgentOps Firewall ideas
```

## Repository Map

```text
.
|-- RedditPulse/
|   |-- app/                    # Existing CueIdea Next.js app
|   |-- engine/                 # Python scraping, scoring, analysis, enrichment
|   |-- migrations/             # Database migrations
|   |-- sql/                    # SQL setup and schema helpers
|   |-- scripts/                # Local and VPS automation scripts
|   |-- docs/                   # CueIdea product, data, UX, and architecture docs
|   `-- tests/                  # Python tests
|
|-- sentinel-control/
|   |-- apps/web/               # New Sentinel Control Next.js dashboard
|   |-- services/sentinel-core/ # Python agent core, firewall, trace ledger, GTM logic
|   |-- packages/evals/         # Safety and business-quality eval datasets
|   |-- supabase/migrations/    # Sentinel database schema
|   |-- docs/                   # Sentinel product/security/deployment docs
|   `-- preview/                # Static preview fallback
|
`-- agent-lab/
    |-- audits/                 # Capability maps, failure modes, OpenClaw audits
    |-- benchmarks/             # Safe benchmark plans
    |-- tools/                  # Static scanners and lab tooling
    |-- adapters/               # Future experimental adapter notes
    |-- vendors/                # Vendor placeholders, source clones ignored
    `-- sentinel_integration_notes/
```

## Which App Should You Run?

Use `RedditPulse/app` when you want the existing CueIdea website and validation product.

Use `sentinel-control/apps/web` when you want the new Sentinel Control dashboard and agent workflow.

Use `agent-lab` only for research, audits, scanner tests, and future runtime planning.

## App 1: RedditPulse / CueIdea

Path:

```text
RedditPulse/
```

Purpose:

- validate startup ideas;
- scrape Reddit and other market sources;
- identify pain, demand, trends, competitors, WTP signals, and opportunity gaps;
- power the current CueIdea website and dashboard;
- provide the evidence layer that Sentinel can reuse.

Important files:

- `RedditPulse/README.md`
- `RedditPulse/WORKSPACE_MAP.md`
- `RedditPulse/DOCUMENTATION.md`
- `RedditPulse/PRODUCT_BLUEPRINT.md`
- `RedditPulse/SYSTEM_CARTOGRAPHY.md`
- `RedditPulse/app/package.json`
- `RedditPulse/requirements-scraper.txt`

Run the web app:

```bash
cd RedditPulse/app
npm install
npm run dev
```

Run Python validation tooling:

```bash
cd RedditPulse
python -m pip install -r requirements-scraper.txt
python run_validation_test.py
```

Local files intentionally not tracked:

- `RedditPulse/.env`
- `RedditPulse/app/.env.local`
- `RedditPulse/.git/`
- `RedditPulse/.gitnexus/`
- `RedditPulse/.claude/`
- `RedditPulse/app/node_modules/`
- `RedditPulse/app/.next/`

## App 2: Sentinel Control

Path:

```text
sentinel-control/
```

Purpose:

- turn ideas and CueIdea signals into evidence-backed GTM packs;
- generate ICP, positioning, landing copy, outreach drafts, interview scripts, prospect sources, and 7-day validation plans;
- score proposed actions through the AgentOps Firewall;
- require dry-run previews, approval, and trace logging before execution;
- become the controlled business-agent layer on top of CueIdea evidence.

Important files:

- `sentinel-control/README.md`
- `sentinel-control/WORKSPACE_MAP.md`
- `sentinel-control/docs/PRODUCT_SPEC.md`
- `sentinel-control/docs/SECURITY_MODEL.md`
- `sentinel-control/docs/FIREWALL_POLICIES.md`
- `sentinel-control/docs/GTM_OPERATOR_SPEC.md`
- `sentinel-control/docs/FULL_PROGRESS_REPORT.md`

Run the web app:

```bash
cd sentinel-control/apps/web
npm install
npm run dev
```

Run the Python core tests:

```bash
cd sentinel-control/services/sentinel-core
python -m pip install -e ".[dev]"
pytest
```

Environment template:

```text
sentinel-control/apps/web/.env.example
```

Real local credentials should stay in:

```text
sentinel-control/apps/web/.env.local
```

## Research Lab: Agent Lab

Path:

```text
agent-lab/
```

Purpose:

- study external agent runtime projects safely;
- audit capabilities and failure modes;
- build static scanners for plugins and skills;
- decide what Sentinel should take, rewrite, or avoid.

Agent Lab is not production code. It is research-only.

Current OpenClaw work:

- source was cloned locally for static audit only;
- dependencies were not installed;
- runtime was not executed;
- skills and plugins were not executed;
- real accounts were not connected;
- vendor source clone is ignored by this repo.

Important files:

- `agent-lab/README.md`
- `agent-lab/AGENT_LAB_PLAN.md`
- `agent-lab/audits/openclaw_static_audit.md`
- `agent-lab/audits/openclaw_dependency_audit.md`
- `agent-lab/audits/openclaw_scanner_report.md`
- `agent-lab/tools/openclaw_static_scanner/scanner.py`
- `agent-lab/tools/openclaw_static_scanner/tests/test_scanner.py`

Run Agent Lab scanner tests:

```bash
python -B -m unittest discover -s agent-lab/tools/openclaw_static_scanner/tests
```

Regenerate OpenClaw scanner reports:

```bash
python agent-lab/tools/openclaw_static_scanner/scanner.py --source agent-lab/vendors/openclaw/source --out agent-lab/audits/openclaw_scanner_report.json --markdown-out agent-lab/audits/openclaw_scanner_report.md
```

## Current Product Status

RedditPulse / CueIdea:

- Existing app and engine are included.
- Next.js app is under `RedditPulse/app`.
- Python market validation engine is under `RedditPulse/engine`.
- Migrations, SQL helpers, docs, tests, and VPS scripts are included.

Sentinel Control:

- Product and security specs are written.
- Python core schemas, Trace Ledger, Firewall, CueIdea Bridge, debate engine, GTM pack generator, execution layer, learning layer, evals, and dashboard exist.
- High-risk execution remains disabled or approval-gated.

Agent Lab:

- OpenClaw static audit is complete.
- Dependency audit is complete.
- Static plugin/skill scanner exists.
- Scanner reports are canonical and consistency-tested.

## Safety And Execution Rules

High-impact actions are disabled or gated in v1:

- email sending;
- browser form submission;
- shell execution;
- production code modification;
- unrestricted filesystem access;
- payment flows;
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

## Git Hygiene

Do not commit:

- `.env`, `.env.local`, API keys, tokens, or service role keys;
- generated GTM packs from `sentinel-control/data/generated_projects`;
- Python caches, Next build outputs, `node_modules`, or virtual environments;
- third-party vendor runtime clones under `agent-lab/vendors/*/source`;
- RedditPulse local state such as `.gitnexus`, `.claude`, and working proxy files.

## North Star

RedditPulse proves market demand and gathers evidence.

Sentinel Control turns that evidence into business decisions, GTM packs, and controlled agent actions.

Agent Lab helps Sentinel learn from powerful agent runtimes without importing their risks.

The final product direction is clear: evidence first, decision second, action only with policy, approval, and trace.
