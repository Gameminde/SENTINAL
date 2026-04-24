# Sentinel Control

Local-first workspace for the Sentinel Control product family.

This repo is organized around three active areas:

- `apps/web/` - the Next.js UI for Sentinel Control
- `services/sentinel-core/` - the Python agent core, firewall, debate, and execution logic
- `packages/evals/` - JSONL datasets for Sentinel safety and quality evaluations
- `supabase/migrations/` - database schema for runs, evidence, actions, traces, and policies

Supporting material:

- `docs/` - product, security, and implementation docs
- `preview/` - static preview fallback for browser checks

Related local workspace:

- `../agent-lab/` - research-only lab for studying external agent runtimes without integrating them into Sentinel production

Sprint 8 adds the GTM Pack Quality layer. The dashboard can import CueIdea validations, generate local GTM files, and score each pack against business-quality gates before it is considered ready.

Use `apps/web/.env.example` as the hosted/dev environment template. Real local credentials live in `apps/web/.env.local`, which is ignored by git.

## Start Here

1. `WORKSPACE_MAP.md`
2. `docs/PRODUCT_SPEC.md`
3. `docs/SECURITY_MODEL.md`
4. `docs/CODEX_TASKS.md`
5. `docs/FIREWALL_POLICIES.md`
6. `docs/DEPLOYMENT_PLAN.md`
7. `docs/FULL_PROGRESS_REPORT.md`

## Working Rule

Edit source, not generated output. The generated directories are ignored and can be recreated when needed.

High-impact capabilities remain disabled in v1: email sending, browser form submission, shell execution, code modification, unrestricted filesystem access, and payments.
