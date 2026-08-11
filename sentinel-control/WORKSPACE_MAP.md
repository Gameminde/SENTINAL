# Sentinel Control Workspace Map

Sentinel Control is the active product in this repository. It is being built as
a cognitive operating system: the model is the mind; Sentinel owns state,
runtime, authority, proof, memory, recovery and organs.

## Repository Context

- `../README.md` - GitHub-facing product overview.
- `../agent-lab/` - research-only comparator and audit workspace.
- `../archive/prototypes/` - archived prototypes, not active product surfaces.
- `../PLAN/` - historical strategy and architecture notes.
- `../.kiro/` - local spec and planning material.

## Sentinel Control Layout

- `services/sentinel-core/` - main Python runtime, operator kernel, organs and tests.
- `docs/` - roadmaps, specs, reviews, proof reports and truth ledgers.
- `tests/` - root-level fixtures and evaluation assets when present.
- `apps/`, `packages/`, `preview/`, `supabase/` - optional or future product surfaces when present in a given checkout.

## Current Canonical Spine

```text
public request
-> RuntimeHost
-> RootMissionRuntime
-> ProductModelNativeDecisionClient
-> ExecutableCapabilityGraph
-> authority gate
-> ProductActionKernel
-> organ backend
-> receipt
-> CanonicalState
-> MissionProofRoot
-> cleanup / replay
```

## Active Organ Priorities

1. Workspace and code execution under the canonical spine.
2. Browser Organ through `sentinel_chromium` as the canonical backend.
3. Channel, worker, memory, world model and computer/desktop organs after spine convergence.
4. Authentic proof, replay, cleanup and live proof-tier graduation.

## What Is Not Active Product

- `archive/prototypes/redditpulse-cueidea/` is archived historical prototype code.
- `agent-lab/` is research-only and must not be copied into Sentinel without a governed adapter or rewrite.
- `PLAN/archive/` contains historical planning snapshots.
