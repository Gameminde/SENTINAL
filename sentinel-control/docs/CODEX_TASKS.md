# Codex Tasks

## Sprint 1

- Create standalone `sentinel-control` workspace.
- Add product and security docs.
- Add Python core models and enums.
- Add trace ledger with in-memory and Supabase repository interfaces.
- Add AgentOps Firewall policies, risk scoring, approval gate, and dry-run preview.
- Add Supabase migration SQL.
- Add unit tests for models, trace ledger, and firewall.

## Sprint 2 Preview

- Add CueIdea Bridge.
- Normalize CueIdea validations into `EvidenceItem`.
- Start Research Agent skeleton.
- Add evidence ledger UI mock.

## Sprint 2 Acceptance

- CueIdea validation payloads normalize into Sentinel `EvidenceItem`.
- Direct proof and adjacent proof are separated via `metadata.proof_tier`.
- WTP and pricing signals are explicitly tagged.
- The bridge works through a testable transport interface.
- Research Agent can generate research questions and rank evidence without live web calls.
- Evidence Ledger UI shape is documented before frontend implementation.

## Sprint 3 Preview

- Add deterministic Debate Engine.
- Add GTM Pack Generator.
- Add safe file executor.
- Add email draft executor.
- Route all execution through Firewall.

## Sprint 3 Acceptance

- Debate includes a skeptical challenge.
- Debate cannot return `build` when WTP evidence is missing.
- GTM Pack sections all carry `evidence_refs`.
- Outreach remains draft-only.
- File writes stay inside `data/generated_projects`.
- Executors cannot bypass Firewall review.

## Sprint 4 Preview

- Add the Sentinel web app shell.
- Add dashboard, agents, firewall, customers, and generated project pages.
- Use local demo state for workflow verification.
- Match the concept's control-room layout and density.

## Sprint 4 Acceptance

- The web app loads with a left rail, top bar, evidence ledger, firewall panel, and execution board.
- At least one row selection, one tab-like filter, and one approval-related state change are interactive.
- Dashboard pages preserve the control-room feel from the accepted concept.

## Sprint 5 Preview

- Add eval datasets for safe actions, dangerous actions, weak ideas, strong ideas, spammy outreach, compliant outreach, prompt injection, and fake evidence.
- Add an eval runner that exercises Firewall, Debate, outreach review, prompt-injection detection, fake-evidence downgrading, and trace integrity.
- Add a trace viewer page for local runs.
- Add local estimated cost tracking per run.

## Sprint 5 Acceptance

- Dangerous actions remain blocked by evals.
- Weak evidence cannot produce a build decision.
- Outreach drafts are checked for spam patterns and opt-out language.
- Prompt injection in scraped or user-provided text is detected.
- Fake evidence is downgraded instead of treated as proof.
- Runs expose trace events and estimated costs in the dashboard.

## Sprint 5B Preview

- Add user feedback capture for actions, generated assets, evidence, and runs.
- Store feedback as local run data and append `feedback_recorded` trace events.
- Add an eval-results dashboard page.

## Sprint 5B Acceptance

- Users can mark an action or generated asset as useful, weak, approved, or rejected.
- Feedback persists in the local run store.
- Feedback appears in the trace ledger.
- Eval datasets are visible in the dashboard with case counts and coverage labels.

## Sprint 6 Preview

- Add learning layer v0 for feedback summaries, memory entries, prompt versions, and improvement proposals.
- Add Execution Board derived from local run state.
- Add watchlist updates for competitor, WTP, and risk signals.
- Add paid-run quote preparation without payment execution.

## Sprint 6 Acceptance

- Learning proposals describe observed problems, evidence, patch suggestion, risk, and tests without mutating production code.
- Execution Board shows ideas, generated packs, approval needs, outreach drafts, interviews, monitoring, and decisions.
- Watchlist updates persist locally and append `watchlist_updated` trace events.
- Paid-run quote prep persists locally and appends `paid_quote_prepared` trace events.
- Payments remain disabled in v1.

## Sprint 7A Preview

- Connect CueIdea in read-only mode.
- Import a CueIdea validation by `idea_validations.id` when local env credentials exist.
- Allow pasted CueIdea report JSON for sandbox testing without live credentials.
- Normalize imported CueIdea evidence into Sentinel evidence rows.
- Generate local GTM Pack files only inside `data/generated_projects`.

## Sprint 7A Acceptance

- CueIdea import does not write back to CueIdea.
- Imported runs include `cueidea_imported`, `evidence_recorded`, `decision_created`, and `action_proposed` trace events.
- Imported evidence separates direct, adjacent, WTP/pricing, competitor gap, trend, and community signals.
- UI exposes `/dashboard/cueidea` for local testing.
- Pack file generation writes only to `data/generated_projects` and records `action_executed` plus `asset_generated` traces.

## Sprint 7B Acceptance

- Real CueIdea credentials are wired through ignored local env files and documented through `.env.example`.
- One completed CueIdea validation imports successfully from Supabase in read-only mode.
- Imported Sentinel runs sync back to Sentinel Supabase tables when `SENTINEL_ENABLE_SUPABASE_SYNC=true`.
- GTM Pack files include real CueIdea report sections when present.
- Prospect/source extraction is available in the imported run UI.
- API routes include a user boundary before hosting.
- Deployment plan is documented and keeps later-only features disabled.

## Sprint 8 Preview

- Add business-quality eval datasets.
- Add GTM Pack quality evaluator.
- Add GTM Pack quality status: `draft`, `needs_revision`, `ready`.
- Add dashboard quality score on run detail.
- Keep all execution capabilities unchanged.

## Sprint 8 Acceptance

- Weak GTM Packs are flagged `needs_revision`.
- Strong example packs are marked `ready`.
- Missing WTP does not silently pass.
- ICP, positioning, landing copy, outreach, competitor gaps, roadmap, WTP, and evidence coverage are scored.
- Run detail page shows GTM Pack Quality Score and section-level blockers.
- No new risky actions are enabled.

## Parallel Agent Lab Sprint A

- Create sibling workspace `../agent-lab`.
- Keep vendor/runtime research separate from Sentinel production.
- Add lab folders for vendors, audits, benchmarks, adapters, and Sentinel integration notes.
- Add vendor slots for OpenClaw, Hermes Agent, OpenJarvis, and JARVIS.
- Add capability matrix for OpenClaw, Hermes Agent, OpenJarvis, JARVIS, Sentinel current, and Sentinel target.
- Add vendor-specific audit maps for channel, learning, cost-router, and desktop/sidecar patterns.
- Add failure-mode matrix for prompt injection, malicious skills, credential leakage, unauthorized email, filesystem escape, shell command abuse, hallucinated decisions, fake evidence, spam outreach, memory poisoning, cost explosion, and unsafe self-improvement.
- Add reuse strategy with `TAKE`, `REWRITE`, and `AVOID`.
- Add benchmark plan using sandbox resources only.

## Parallel Agent Lab Sprint A Acceptance

- No vendor code is copied into Sentinel.
- No external runtime is run with real accounts, real browser profiles, SSH keys, wallets, or production credentials.
- Every benchmark uses sandbox resources.
- Every capability maps to Sentinel target architecture.
- Every risky feature has a proposed Firewall mitigation.

## Parallel Agent Lab Sprint B1 - OpenClaw Static Audit

- Clone OpenClaw source into `../agent-lab/vendors/openclaw/source`.
- Do not install dependencies.
- Do not run OpenClaw.
- Do not connect real accounts.
- Fill `audits/vendor_clone_checks.md`.
- Create `audits/openclaw_static_audit.md`.
- Update `audits/openclaw_capability_map.md`.
- Update `audits/CAPABILITY_MATRIX.md` with source-backed OpenClaw observations only.
- Update `audits/FAILURE_MODES.md` with OpenClaw-specific risks.
- Create `sentinel_integration_notes/openclaw_to_sentinel.md`.

## Parallel Agent Lab Sprint B1 Acceptance

- OpenClaw is cloned but not run.
- No dependencies are installed.
- No accounts or secrets are connected.
- Findings cite local source paths.
- Every reusable pattern has a Sentinel Firewall implication.

## Sprint 1 Acceptance

- Every decision run can write trace records.
- Every proposed action can be stored before execution.
- Firewall blocks disabled and out-of-policy actions.
- Tests run without real Supabase.
