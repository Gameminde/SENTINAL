# SENTINAL

**Sentinel Control is a maximum-power controlled agentic operating system.**

The idea is simple and aggressive:

```text
Unleash intelligence.
Control authority.
Prove every action.
```

This repository is where Sentinel is being built from the old CueIdea /
RedditPulse evidence engine into a real controlled-agent runtime: Brain,
Memory, Authority, Organs, Receipts, FinalGate, and eventually live browser,
API, desktop, shell sandbox, credentials, and plugin power.

The repository name is `SENTINAL`, but the product name used in the code and
docs is **Sentinel Control**.

This repo contains **two apps plus one research lab**:

1. `RedditPulse/` - the existing CueIdea market-validation app and evidence engine.
2. `sentinel-control/` - the new Sentinel Control product: evidence-backed GTM packs, decision agents, approvals, trace logs, and AgentOps Firewall.
3. `agent-lab/` - a research-only lab for studying agent runtimes such as OpenClaw without mixing vendor runtime code into production.

If you are continuing development, start here. This README explains what the project is, why it exists, how the folders connect, what is production, what is research, how to run things, and what to build next.

## Current Snapshot - 2026-05-26

Sentinel now has a real default-off internal action loop and a hardened control
plane. The next credibility milestone is not just browser read-only. The next
phase is to turn Sentinel into a runnable Power Kernel that controls many agents
and many real actuators: browser, shell/code, API, desktop, channels,
credentials, spend/trading, security testing, scheduler, and plugin fabric.

Current public/local checkpoint after the latest repairs:

```text
remote = https://github.com/Gameminde/SENTINAL
branch = main
latest_repair_commit = 37b0bea runtime: consolidate cognition memory scanners and repair test truth
audit_remediation_commit = a2137f0 runtime: remediate audit safety findings
credential_foundation_commit = 23dd2bd runtime: add mission authority and credential foundation
brain_native_feedback_commit = 07c0e09 runtime: lock brain native candidates and memory feedback
```

Current state lock:

```text
current_phase = MISSION_AUTHORITY_AND_CREDENTIAL_VAULT_FOUNDATION_LOCKED
latest_repair = COGNITION_MEMORY_SCANNER_CONSOLIDATION_LOCKED
previous_runtime_phase = BRAIN_NATIVE_ACTION_FEEDBACK_LOOP_LOCKED
next_documented_phase = BROWSER_OPERATOR_AGENT_L4_L5_LIVE
latest_visible_power_milestone = SENTINEL_OPERATOR_SHELL_WITH_REAL_RUN_ARTIFACTS
```

What is real today:

```text
BrainCognitionLoop native proposal source = CLOSED / opt-in
OrganDispatcher bridge = CLOSED / opt-in
DelegatedActionGate = CLOSED
L2 local artifact executor = CLOSED / opt-in
L3 reversible workspace executor = CLOSED / opt-in
Browser ReadOnly + Preparation + Semantic Extraction wrappers = CLOSED / opt-in
Low-risk FinalGate receipts = CLOSED
RoleLoopMemoryBridge feedback = CLOSED
Replan-ready packet = CLOSED
Mission authority grants foundation = CLOSED
Credential refs/grants/proofs foundation = CLOSED / metadata-only
Organ/cognition/memory safety scanners = CLOSED / shared canonical scanner
AgentRuntime default-off = CLOSED
Power Lab operator shell = CLOSED
```

What is deliberately still not real:

```text
Live browser backend = NOT_STARTED
Browser submit/login/upload/download/private session = NOT_STARTED
Real credential storage or credential use by organs = NOT_STARTED
API mutation = NOT_STARTED
Channel send = NOT_STARTED
Desktop action = NOT_STARTED
Shell/process execution = NOT_STARTED
Payment/spend/trading = NOT_STARTED
Provider fallback or AUTO routing = NOT_APPROVED
Durable memory/EventBus WAL = NOT_STARTED
Automatic replan execution = NOT_STARTED
```

The honest power score right now:

```text
Control plane = strong
Internal closed-loop runtime = real
Local action power = real but limited
Browser/web power = prepared, not live yet
Next milestone = Sentinel can open a real web page and bring back evidence
```

Start here for the current truth:

```text
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/reviews/COGNITION_MEMORY_SCANNER_CONSOLIDATION_LOCK_REPORT.md
sentinel-control/docs/reviews/TEST_SUITE_TRUTH_REPAIR_LOCK_REPORT.md
sentinel-control/docs/reviews/MISSION_AUTHORITY_AND_CREDENTIAL_VAULT_FOUNDATION_REPORT.md
sentinel-control/docs/reviews/BRAIN_NATIVE_CANDIDATE_SOURCE_AND_MEMORY_FEEDBACK_LOCK_REPORT.md
sentinel-control/docs/organs/ORGAN_EXECUTION_EXPANSION_ROADMAP.md
```

Recommended next build sequence:

```text
1. BROWSER_OPERATOR_AGENT_L4_L5_LIVE
2. SHELL_CODE_APP_BUILDER_SANDBOX_V0
3. SKILL_PLUGIN_FABRIC_V0
4. CREDENTIAL_VAULT_REAL_STORAGE_AND_SESSION_BROKER
5. API_CHANNEL_DEVOPS_CONTROLLED_MUTATION
6. DESKTOP_VISION_OCR_SIDECAR
7. FINANCE_SPEND_TRADING_SPECIAL_AUTHORITY
8. CONTINUOUS_MULTI_AGENT_MISSION_ORCHESTRATOR
```

The doctrine:

```text
Sentinel should have dangerous powers.
Those powers must enter through authority, gates, receipts, rollback posture,
FinalGate, replay, and audit.
Power is allowed. Unsafe authority is not.
```

## Archived Snapshot - 2026-05-25

This repository is the full Sentinel working tree. It includes the legacy
CueIdea/RedditPulse evidence product, the Sentinel Control runtime, and Agent
Lab, which is the forensic lab used to study external agent systems before
rewriting useful powers into Sentinel-native contracts.

Current public GitHub checkpoint:

```text
remote = https://github.com/Gameminde/SENTINAL
branch = main
latest_runtime_lock_commit = 07c0e09 runtime: lock brain native candidates and memory feedback
previous_runtime_loop_commit = 634d709 runtime: close brain to organ runtime loop
```

Current state lock:

```text
current_phase = BRAIN_NATIVE_ACTION_FEEDBACK_LOOP_LOCKED
previous_phase = BRAIN_TO_ORGAN_RUNTIME_CLOSED_LOOP_LOCKED
next_phase = MISSION_AUTHORITY_AND_CREDENTIAL_VAULT_FOUNDATION
```

Important current truth:

```text
Brain native candidate source = CLOSED
OrganDispatcher runtime bridge = CLOSED
DelegatedActionGate = CLOSED
L2 local artifact execution = CLOSED / explicit opt-in
L3 reversible workspace execution = CLOSED / explicit opt-in
Browser ReadOnly + Preparation + Semantic Extraction = CLOSED / explicit opt-in
Receipts + FinalGate = CLOSED
Memory feedback via RoleLoopMemoryBridge.build(...) = CLOSED
Replan-ready packet = CLOSED
Durable memory persistence = NOT_STARTED
Automatic replan execution = NOT_STARTED
AgentRuntime default-off = CLOSED
Provider expansion immediate = NO-GO
fallback routing = NOT_STARTED / NOT_APPROVED
AUTO model routing = NOT_STARTED / NOT_APPROVED
L5/L6/L7 dangerous execution = NOT_STARTED / NOT_APPROVED
```

Current native runtime loop:

```text
AgentRuntime.run
-> BrainCognitionLoop.run(...) when explicitly enabled
-> BrainCognitionResult.proposal_artifacts
-> OrganDispatcher
-> DelegatedActionGate
-> L2/L3/browser perception executor request
-> receipt
-> FinalGate certificate
-> RoleLoopMemoryBridge.build(...) memory feedback
-> replan-ready packet
```

Boundaries still held:

```text
Everything remains default-off.
No new root authority path.
No memory-as-authority.
No receipt-as-authority.
No automatic replan execution.
No durable memory persistence yet.
No browser submit/login/upload/download/private session/credential.
No API mutation.
No channel send.
No desktop action.
No shell/process execution.
No provider fallback or AUTO routing.
```

Historical model-execution, provider, budget, and performance closure details
remain in `sentinel-control/docs/CURRENT_STATE_LOCK.md`. They are still valid
as historical locks, but the current public phase is now the Brain-native
action feedback loop lock above.

Start with:

```text
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/reviews/BRAIN_NATIVE_CANDIDATE_SOURCE_AND_MEMORY_FEEDBACK_LOCK_REPORT.md
sentinel-control/docs/reviews/BRAIN_TO_ORGAN_RUNTIME_CLOSED_LOOP_LOCK_REPORT.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/docs/organs/ORGAN_EXECUTION_EXPANSION_ROADMAP.md
sentinel-control/docs/specs/sentinel-real-model-execution-backend/requirements.md
sentinel-control/docs/specs/sentinel-real-model-execution-backend/design.md
sentinel-control/docs/specs/sentinel-real-model-execution-backend/tasks.md
.kiro/specs/sentinel-performance-runtime-foundation/requirements.md
.kiro/specs/sentinel-performance-runtime-foundation/design.md
.kiro/specs/sentinel-performance-runtime-foundation/tasks.md
```

Useful current verification commands:

```powershell
cd sentinel-control/services/sentinel-core
python -m pytest tests/test_real_model_execution_groq.py -q -rs
python -m pytest tests/test_real_model_execution_openrouter.py -q -rs
python -m pytest tests/test_real_model_execution_nvidia.py -q -rs
python -m pytest tests/test_real_model_execution_backend.py -q
python -m pytest tests/test_openai_compatible_provider_base.py -q
python -m pytest tests/test_model_provider_catalog.py -q
python -m pytest tests/test_runtime_model_execution_wiring.py -q -rs
python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q
python -m pytest tests/perf/bench -q
python -m pytest tests/perf/ -m "not slow" -q
```

Latest accepted model-execution budget verification before this README update:

```text
tests/test_real_model_execution_backend.py = 28 passed
tests/test_openai_compatible_provider_base.py = 8 passed
tests/test_model_provider_catalog.py = 10 passed
tests/test_runtime_model_execution_wiring.py = 9 passed
tests/test_llm_backed_decision_cycle.py + tests/test_agent_runtime.py = 21 passed
tests/test_final_gate_registry.py + tests/test_browser_organ_final_gate.py = 22 passed
git diff --check = clean
secret scan = no real gsk_, nvapi-, sk-or-v1, or raw Bearer provider key in visible repo files
```

Latest local Phase F full-lock benchmark evidence:

```text
timestamp = 2026-05-16T21:56:36.273773+00:00
gate_passed = true
total_iterations = 120
startup = 30 iterations, p50 12 ms, p95 17 ms, p99 27 ms
single_tool = 30 iterations, p50 3 ms, p95 4 ms, p99 4 ms
multi_tool = 30 iterations, p50 1 ms, p95 1 ms, p99 2 ms
browser_heavy = 30 iterations, p50 35 ms, p95 51 ms, p99 57 ms
```

Latest local Phase F required verification before this README update:

```text
tests/perf/bench = 30 passed
tests/perf/ -m "not slow" = 177 selected tests passed; 6 slow tests deselected
tests/test_agent_runtime.py = 14 passed
tests/perf/bench/test_core_final_gate_performance_receipts.py = 8 passed
```

Latest residual cleanup verification before this README update:

```text
tests/test_agent_runtime.py = 14 passed
tests/perf/ -m "not slow" = passed
tests/test_kill_switch_reactive_property.py = 10 passed
tests/test_mission_runner_browser_operator_route_rejected.py = 10 passed
```

Open backlog items that remain intentionally open:

```text
P-B-PERF-01
P-B-PERF-02
P-C-RUNTIME-01
P-D-RUNTIME-01
P-D-BATCH-01
P-D-BROWSER-01
REAL_PROVIDER_ADAPTER_SUCCESS = CLOSED by Groq provider evidence
RUNTIME_MODEL_EXECUTION_WIRING = CLOSED by Wave 9 runtime validation
MODEL_EXECUTION_BUDGET_GOVERNANCE = CLOSED by 074ca1c
P-C-RUNTIME-01-ACTIONBUDGET-DEFER = CLOSED by 074ca1c
P-C-RUNTIME-01-MISSIONBUDGET-DEFER = CLOSED by 074ca1c
PRODUCTION_PROVIDER_ROUTING = OPEN
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER = SPLIT / PARTIAL
```

If an older consumer cannot represent split deferrals, keep the old broad
`LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` open with the attached note that
provider adapter success, runtime wiring, and budget governance are closed,
while production routing remains open.

Core governance rule:

```text
Agent Lab harvests powers.
Sentinel rewrites them behind authority, risk, receipts, replay, kill switch,
promotion gates, and FinalGate.
Vendor runtime code is not imported as production runtime.
No phase is called fully locked unless its runtime and benchmark obligations are actually proven.
```

## Executive Summary

CueIdea/RedditPulse already validates ideas by collecting market signals, competitors, pain points, willingness-to-pay indicators, and opportunity gaps.

Sentinel Control is the new product layer on top of that evidence. It takes an idea or an imported CueIdea report, builds an evidence ledger, researches the market, debates the decision, generates a GTM pack, proposes safe actions, sends those actions through the AgentOps Firewall, and records a trace log.

Agent Lab is the R&D area. It studies powerful agent systems and turns their risky runtime patterns into safe Sentinel requirements: scan, score, preview, approve, trace, then execute only what is allowed.

The north star is simple:

```text
Idea
  -> evidence
  -> decision
  -> GTM pack
  -> risk review
  -> user approval
  -> safe execution
  -> trace log
```

## Why This Exists

Most agent products try to impress users by doing more actions automatically.

Sentinel Control is different. It is built around proof and control:

- It should not be a generic chatbot.
- It should not blindly execute tasks.
- It should not auto-send emails in v1.
- It should not auto-modify production code.
- It should not run shell commands as a product feature in v1.
- It should turn market evidence into a business decision and a useful GTM operating package.
- It should make every risky action pass through policy, dry-run preview, approval, and trace logging.

The first commercial wedge is **Sentinel GTM Operator**.

The long-term platform moat is **AgentOps Firewall**.

## The Two Apps, Without Confusion

This repo intentionally has two app areas.

### App 1: RedditPulse / CueIdea

`RedditPulse/` is the existing market intelligence product.

It answers questions like:

- Is this startup idea showing real demand?
- What pain points are repeated in communities?
- What competitors or alternatives already exist?
- Are there willingness-to-pay signals?
- Which segments or niches look promising?

Think of RedditPulse/CueIdea as the **evidence engine**.

### App 2: Sentinel Control

`sentinel-control/` is the new agent product.

It answers questions like:

- Given this evidence, should we build, pivot, niche down, kill, or research more?
- What is the best ICP?
- What should the positioning be?
- What landing copy, outreach drafts, interview script, and 7-day validation plan should we use?
- Which actions are safe?
- Which actions need approval?
- What trace proves how the agent made the decision?

Think of Sentinel Control as the **decision and controlled-execution layer**.

### Research Lab: Agent Lab

`agent-lab/` is not a third production app.

It is a research workspace for studying external agent runtimes. The goal is to learn from their architecture without importing their risks.

Think of Agent Lab as the **runtime safety research lab**.

## How The Pieces Connect

The intended product flow is:

```text
RedditPulse / CueIdea
  market validation, competitor signals, pain, WTP, trends

        feeds evidence into

Sentinel Control
  EvidenceItem records, research agent, debate engine, GTM pack generator

        controlled by

AgentOps Firewall
  policy, risk score, dry-run preview, approval gate, trace ledger

        informed by

Agent Lab
  scanner research, capability maps, failure modes, future runtime blueprint
```

Important rule:

`agent-lab` does not directly feed vendor code into `sentinel-control`. It produces audits, scanners, benchmark plans, and integration requirements only.

## Repository Map

```text
.
|-- README.md
|-- .gitignore
|
|-- RedditPulse/
|   |-- app/                    # Existing CueIdea Next.js app
|   |-- engine/                 # Python market scraping, scoring, validation
|   |-- migrations/             # Database migrations
|   |-- sql/                    # SQL setup and schema helpers
|   |-- scripts/                # Local/VPS helper scripts
|   |-- docs/                   # CueIdea product, UX, data, and architecture docs
|   |-- tests/                  # Python tests
|   |-- README.md
|   `-- WORKSPACE_MAP.md
|
|-- sentinel-control/
|   |-- apps/web/               # Sentinel Control Next.js dashboard
|   |-- services/sentinel-core/ # Python agent core
|   |-- packages/evals/         # Safety and business-quality eval datasets
|   |-- supabase/migrations/    # Sentinel database schema
|   |-- docs/                   # Sentinel product/security/deployment docs
|   |-- preview/                # Static preview fallback
|   |-- README.md
|   `-- WORKSPACE_MAP.md
|
`-- agent-lab/
    |-- audits/                 # Capability maps, failure modes, OpenClaw audits
    |-- benchmarks/             # Safe benchmark plans
    |-- tools/                  # Static scanners and lab tooling
    |-- adapters/               # Future experimental adapter notes
    |-- vendors/                # Vendor placeholders; source clones are ignored
    |-- sentinel_integration_notes/
    |-- README.md
    `-- AGENT_LAB_PLAN.md
```

## What Is Production And What Is Research

`RedditPulse/` is the existing product codebase and evidence source.

`sentinel-control/` is the new product being built. This is where product features should go.

`agent-lab/` is research-only. It can contain audits, scanners, fake benchmarks, and design notes. It must not become a shortcut for adding risky runtime features into Sentinel.

## Current Product Status

### RedditPulse / CueIdea

Included in this repo:

- Existing CueIdea Next.js app under `RedditPulse/app`.
- Python market validation and scraping engine under `RedditPulse/engine`.
- Migrations and SQL helpers.
- Local/VPS scripts.
- Docs and workspace maps.
- Python tests.

Role in the larger system:

- Source of market evidence.
- Existing website/product foundation.
- Future input provider for Sentinel runs.

### Sentinel Control

Included in this repo:

- Product docs.
- Security model.
- Firewall policy docs.
- Python shared schemas.
- Trace Ledger.
- AgentOps Firewall v0.
- CueIdea Bridge.
- Research/debate scaffolding.
- GTM Pack generation.
- GTM quality scoring and business-quality eval gates.
- Safe execution layer for allowed local file/draft workflows.
- Supabase migration.
- Next.js dashboard.
- Auth boundary and deployment planning docs.

Role in the larger system:

- New product direction.
- Turns evidence into GTM deliverables.
- Keeps risky execution behind policy, preview, approval, and trace.

### Agent Lab

Included in this repo:

- Research lab docs.
- OpenClaw static audit.
- OpenClaw dependency audit.
- OpenClaw static plugin/skill scanner.
- Canonical scanner reports.
- Capability and failure matrices.
- Sentinel integration notes.

Role in the larger system:

- Learn from external agent runtimes.
- Build future AgentOps Firewall requirements.
- Keep risky runtime experiments separate from product code.

Current Agent Lab boundary:

- OpenClaw source was cloned locally for static audit only.
- Vendor source clones are ignored by git.
- Dependencies were not installed.
- Runtime was not executed.
- Skills/plugins were not executed.
- Real accounts were not connected.

## How To Continue Development

Read these first:

1. `README.md` - this root handoff.
2. `sentinel-control/README.md` - Sentinel Control app instructions.
3. `sentinel-control/WORKSPACE_MAP.md` - Sentinel folder map and build zones.
4. `sentinel-control/docs/FULL_PROGRESS_REPORT.md` - detailed progress report.
5. `agent-lab/AGENT_LAB_PLAN.md` - Agent Lab current sprint status.
6. `RedditPulse/README.md` and `RedditPulse/WORKSPACE_MAP.md` - CueIdea/RedditPulse context.

Then choose your work area:

- Improving idea validation or existing CueIdea behavior: work in `RedditPulse/`.
- Improving GTM packs, decisions, firewall, traces, dashboard, or Sentinel product behavior: work in `sentinel-control/`.
- Auditing external agent runtimes, scanners, fake benchmarks, or future runtime safety research: work in `agent-lab/`.

## Run Commands

### Run RedditPulse / CueIdea Web App

```bash
cd RedditPulse/app
npm install
npm run dev
```

### Run RedditPulse Python Validation Tooling

```bash
cd RedditPulse
python -m pip install -r requirements-scraper.txt
python run_validation_test.py
```

### Run Sentinel Control Web App

```bash
cd sentinel-control/apps/web
npm install
npm run dev
```

### Run Sentinel Python Core Tests

```bash
cd sentinel-control/services/sentinel-core
python -m pip install -e ".[dev]"
pytest
```

### Run Agent Lab Scanner Tests

```bash
python -B -m unittest discover -s agent-lab/tools/openclaw_static_scanner/tests
```

### Regenerate Agent Lab OpenClaw Scanner Reports

```bash
python agent-lab/tools/openclaw_static_scanner/scanner.py --source agent-lab/vendors/openclaw/source --out agent-lab/audits/openclaw_scanner_report.json --markdown-out agent-lab/audits/openclaw_scanner_report.md
```

Note: the source path above expects a local vendor clone that is intentionally ignored by git.

## Environment Files

Do not commit real credentials.

Common local env locations:

```text
RedditPulse/.env
RedditPulse/app/.env.local
sentinel-control/apps/web/.env.local
```

Use examples/templates where available:

```text
sentinel-control/apps/web/.env.example
```

Supabase credentials are expected to come from environment variables, not source code.

## Safety And Product Rules

Sentinel v1 must keep these disabled or approval-gated:

- autonomous email sending;
- browser form submission;
- shell execution;
- production code modification;
- unrestricted filesystem access;
- payment flows;
- real channel/message sending;
- skill marketplace installation;
- desktop sidecar control.

Every future execution feature must have:

- evidence;
- risk score;
- permission policy;
- dry-run preview;
- explicit user approval when required;
- trace log;
- eval coverage;
- tests.

No feature should be added as "just an assistant capability" unless it maps to one of:

1. Sentinel GTM Operator.
2. AgentOps Firewall.
3. Controlled research inside Agent Lab.

## Current Known Gaps

The strongest next product risk is not architecture. It is output quality.

The next developer should focus on:

- making generated GTM packs more useful and less generic;
- improving ICP specificity;
- improving WTP and pricing evidence handling;
- improving competitor gap quality;
- making outreach drafts evidence-backed and non-spammy;
- making 7-day roadmaps measurable and realistic;
- testing packs with real founder/agency ideas;
- keeping all risky execution disabled until security gates are complete.

Technical gaps still to treat carefully:

- hosted staging needs final auth/user isolation checks;
- Supabase sync must keep service role keys server-side only;
- Research Agent quality must improve beyond simple wrappers;
- Agent Lab B3 fake benchmarks should come before any runtime bridge;
- payments, email sending, browser automation, desktop automation, and skill marketplace are later-only features.

## Recommended Next Work

### Product Track

1. Run 10 real idea inputs through Sentinel.
2. Score GTM Pack quality with the business-quality evaluator.
3. Improve weak sections before adding new execution features.
4. Add private staging only after auth and user isolation are verified.
5. Test willingness to pay manually before adding payment integration.

### Engineering Track

1. Keep Python and Next tests passing.
2. Keep Supabase migrations explicit and reviewed.
3. Add evals for every new agent behavior.
4. Preserve trace logging for every run, decision, action proposal, and generated asset.
5. Keep file writes constrained to allowed generated-project paths.

### Agent Lab Track

1. Continue with fake benchmarks only.
2. Do not install or run vendor runtimes on the host.
3. Build scanner-backed requirements before any adapter.
4. Promote nothing into Sentinel without Firewall policy implications.

## Definition Of Done For New Work

A change is not complete unless the relevant items are true:

- The feature maps to GTM Operator, AgentOps Firewall, or Agent Lab research.
- Docs explain the behavior if it changes product direction or safety behavior.
- Tests or evals cover the new behavior.
- No secrets are committed.
- Risky actions remain blocked or approval-gated.
- Generated actions have dry-run previews.
- Important outputs reference evidence or explicit evidence gaps.
- Trace records exist for decisions/actions/assets.
- README or workspace docs are updated if the developer path changes.

## Git Hygiene

Do not commit:

- `.env`, `.env.local`, API keys, tokens, service role keys, or secrets;
- generated GTM packs from `sentinel-control/data/generated_projects`;
- Python caches, Next build outputs, `node_modules`, or virtual environments;
- third-party vendor runtime clones under `agent-lab/vendors/*/source`;
- RedditPulse local state such as `.gitnexus`, `.claude`, and working proxy files.

Before pushing, check:

```bash
git status --short
git diff --check
```

For large future changes, include a short commit message that names the affected area:

```text
sentinel-control: improve GTM quality evaluator
agent-lab: add fake channel benchmark
RedditPulse: update validation parser
```

## North Star

RedditPulse proves market demand and gathers evidence.

Sentinel Control turns that evidence into business decisions, GTM packs, and controlled agent actions.

Agent Lab helps Sentinel learn from powerful agent runtimes without importing their risks.

The final product direction is:

```text
proof before recommendation
decision before execution
permission before impact
trace before trust
```
