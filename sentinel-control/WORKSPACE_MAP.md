# Workspace Map

This is the local development tree for Sentinel Control.

## Root Layout

- `apps/` - application surfaces
- `services/` - backend core system
- `docs/` - product and build docs
- `preview/` - standalone static preview
- `packages/` - shared eval datasets and future shared packages
- `supabase/` - database migrations

## Sibling Workspaces

- `../agent-lab/` - research-only workspace for auditing external agent runtimes such as OpenClaw, Hermes Agent, OpenJarvis, and JARVIS. It is not production code and does not feed vendor code directly into Sentinel.

## Main Build Zones

### `apps/web/`

The live Next.js app.

- `app/` - routes and pages
- `components/` - shared UI pieces
- `lib/` - app-local helpers and data shapes
- `public/` - static assets
- `worker.ts` - background worker entry

Current dashboard surfaces include Agents, CueIdea, Firewall, Customers, Evidence, Traces, Evals, Execution, Billing, and Generated Projects.

### `services/sentinel-core/`

The agent core.

- `sentinel/shared/` - models, enums, and DB helpers
- `sentinel/learning/` - trace ledger and memory-related code
- `sentinel/firewall/` - policy, approval, dry-run, and scoring
- `sentinel/decision/` - research, ranking, and debate logic
- `sentinel/execution/` - GTM pack generation, GTM quality scoring, and safe executors
- `sentinel/cueidea_bridge/` - adapter from CueIdea to Sentinel evidence
- `tests/` - unit tests for the core system

### `docs/`

Primary docs used to steer implementation:

- `PRODUCT_SPEC.md`
- `SECURITY_MODEL.md`
- `FIREWALL_POLICIES.md`
- `GTM_OPERATOR_SPEC.md`
- `CODEX_TASKS.md`
- `EVIDENCE_LEDGER_UI_MOCK.md`
- `DEPLOYMENT_PLAN.md`
- `FULL_PROGRESS_REPORT.md`

### `packages/evals/`

Evaluation assets used by the Sentinel core tests.

- `datasets/` - JSONL datasets for action safety, idea strength, outreach quality, prompt injection, fake evidence, and GTM business quality
- `datasets/business_quality/` - GTM Pack quality cases for vague ICP, weak positioning, missing WTP, weak outreach, bad competitor gaps, unrealistic roadmaps, and strong examples

### `supabase/migrations/`

Database schema and migration history.

## Generated Output To Ignore

- `apps/web/.next/`
- `apps/web/*.log`
- `apps/web/*.tsbuildinfo`
- `apps/web/node_modules/`
- `services/sentinel-core/**/*.pyc`
- `services/sentinel-core/**/__pycache__/`
- `services/sentinel-core/.pytest_cache/`

## What We Keep Building

1. Product docs and safety rules.
2. Core models, firewall, and trace ledger.
3. CueIdea bridge and research/debate layers.
4. GTM pack generation and safe execution.
5. Dashboard UI and run-time review surfaces.
6. Eval datasets, trace viewing, and run cost visibility.
7. Learning memory, watchlists, execution board, and paid-run prep.
8. CueIdea read-only import and local GTM pack file generation.
9. GTM Pack quality scoring and business-quality eval gates.
