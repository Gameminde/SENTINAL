# Deployment Plan

## Current Mode

Sentinel Control is local-first. Development and validation happen in `apps/web` and `services/sentinel-core` before any VPS or production domain changes.

## Local Dev Gate

- `pytest` in `services/sentinel-core` must pass.
- `npx tsc --noEmit` in `apps/web` must pass.
- `npm run build --silent` in `apps/web` must pass.
- `/dashboard/cueidea` smoke test must import one CueIdea validation in read-only mode.
- Generated files must stay inside `data/generated_projects`.

## Environment Variables

Required for real CueIdea import:

- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CUEIDEA_SUPABASE_URL`
- `CUEIDEA_SUPABASE_SERVICE_ROLE_KEY`

Required before hosted auth enforcement:

- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SENTINEL_REQUIRE_AUTH=true`
- `SENTINEL_ENABLE_SUPABASE_SYNC=true`

Local-only default:

- `SENTINEL_REQUIRE_AUTH=false`

## Staging Gate

1. Create a staging environment separate from the production CueIdea app.
2. Apply Sentinel Supabase migration if tables are missing.
3. Set `SENTINEL_REQUIRE_AUTH=true`.
4. Import one known CueIdea validation by id.
5. Confirm user-scoped APIs only return the authenticated user's Sentinel runs.
6. Confirm generated project writes remain local to the app instance.
7. Confirm no email sending, payment execution, browser submission, shell execution, or code mutation exists.

## Production Gate

Production deploy happens only after staging passes.

- Deploy app with server-only service role keys.
- Keep CueIdea import read-only.
- Keep `send_email`, `browser_submit_form`, `run_shell_command`, and `modify_code` disabled.
- Keep payments disabled until a dedicated billing sprint.
- Record trace events for import, decision, action proposal, pack generation, and approval changes.

## Later-Only Features

These are not active in the current build:

- payment integration
- email sending
- browser automation
- autonomous code modification
- advanced standalone AgentOps Firewall product features
