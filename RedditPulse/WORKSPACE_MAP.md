# Workspace Map

This repository has two main working surfaces:

- `app/` is the live Next.js product for `cueidea.me`
- the repo root is the Python market engine, deployment scripts, SQL history, and docs

## Work Zones

- UI and product surface: `app/src/app/`, `app/src/lib/`, `app/src/app/components/`
- Runtime shell and worker: `app/worker.ts`, `app/scripts/`
- Python engine: `engine/`, `validate_idea.py`, `enrich_idea.py`, `generate_report.py`, `run_scan.py`, `scraper_job.py`
- Database history: `migrations/`, `sql/`, `schema_queue.sql`
- VPS helpers: `scripts/vps/`
- Tests: `tests/`, `app/src/lib/*.test.ts`, `app/src/app/**/*test*`
- Strategy docs and audits: `docs/`, plus the root markdown docs

## Read First

1. `README.md`
2. `PRODUCT_BLUEPRINT.md`
3. `PRODUCT_OPERATING_MODEL.md`
4. `SYSTEM_CARTOGRAPHY.md`
5. `docs/cueidea_system_handbook_2026-04-08.md`

## Safe To Ignore While Building

- `app/.next/`
- `app/node_modules/`
- `*.log`
- `*.tsbuildinfo`
- `__pycache__/`
- `.pytest_cache/`

## Suggested Build Order

1. Product surface: `app/src/app/dashboard/`, `app/src/app/radar/`, `app/src/app/startup-ideas/`
2. Validation flow: `app/src/app/dashboard/validate/`, `engine/multi_brain.py`, `validate_idea.py`
3. Reports and evidence: `app/src/app/dashboard/reports/`, `app/src/lib/evidence.ts`
4. Scraping and data flow: `engine/*scraper*.py`, `scraper_job.py`, `run_scan.py`
5. Infra and deployments: `scripts/vps/`, `migrations/`, `sql/`
