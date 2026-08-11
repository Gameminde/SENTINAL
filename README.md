<div align="center">

# SENTINEL CONTROL

### A cognitive operating system that gives AI a governed digital body.

Sentinel is built around a simple split:

```text
MODEL = reasoning / strategy / invention
SENTINEL = body / senses / runtime / proof / authority / laws
```

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-experimental-orange.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Architecture](https://img.shields.io/badge/architecture-local--first-111111.svg)
![Runtime](https://img.shields.io/badge/runtime-evidence--driven-success.svg)

`COMPUTER` | `BROWSER` | `CODE` | `MEMORY` | `WORKERS` | `MISSIONS` | `SKILLS`

[Contributing](CONTRIBUTING.md) | [Security](SECURITY.md) | [Apache-2.0](LICENSE)

</div>

---

## What Is Sentinel?

Sentinel Control is an experimental cognitive operating system for AI models.
It is not intended to end as a generic chatbot, a browser automation wrapper or
a list of disconnected tools.

The model supplies intelligence: reasoning, language, exploration, judgment and
discovery. Sentinel supplies the persistent operating layer: mission state,
world state, memory, browser and computer organs, governed capabilities,
authority boundaries, receipts, replay, cleanup and revocation.

The goal is to let a model act with much more useful power while keeping real
effects subordinate to explicit human authority and audit-ready proof.

## North Star

```text
maximum freedom in cognition
maximum power inside governed sandboxes
explicit authority at real-world effect boundaries
receipts, evidence, replay and kill always preserved
```

The model can reason, search, imagine, compare, simulate, build, recover and
propose new capabilities inside mission scope. It cannot silently create its
own permission, hide evidence, use credentials outside their grant, tamper with
proof, replay side effects or disable revocation.

## Current Engineering Focus

Sentinel is being compressed into one canonical product spine:

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

Current branch focus:

```text
campaign = SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1
canonical workspace spine = local compressed and tested
browser read-only route = connected to canonical spine
canonical browser backend = sentinel_chromium
CloakBrowser = optional external backend, not required
FIXED_PROVEN = 0/65
```

Recent sovereign browser work proved the local physical gate for
`sentinel_chromium`:

```text
sequential launches = 5/5
usable context/page/observation = 5/5
close/cleanup/baseline restore = passed
provider calls during physical gate = 0
```

The first sovereign C5B real-model attempt with NVIDIA MiniMax M3 reached the
provider and canonical normalizer, but stopped before browser dispatch because
the response did not normalize into a `CanonicalDecision`. That result is
preserved as an honest failure, not hidden as browser success.

## Cognitive Frontiers

Sentinel is being built across several organs and operating layers:

- **Browser Cortex**: semantic browser state, navigation, search, evidence,
  session continuity, recovery and proof.
- **Computer Cortex**: desktop, windows, applications, processes, files,
  devices and machine state under governed control.
- **Mission Studios**: isolated workspaces that combine editors, terminals,
  browsers, notebooks, simulations, workers and generated tools.
- **Skill Genesis**: model-proposed capabilities tested in sandboxes before
  governed promotion.
- **Physical and Industrial Cortex**: future authorized interaction with
  instruments, robots, sensors and industrial systems.

These are development targets, not inflated production claims.

## Repository Layout

```text
sentinel-control/        Active Sentinel product code, runtime, tests and docs.
agent-lab/               Research-only comparator and audit workspace.
PLAN/                    Historical strategy notes and architecture drafts.
archive/prototypes/      Archived prototypes, not active Sentinel products.
.kiro/                   Local spec and planning material when present.
```

Archived prototypes are kept for provenance and design memory. They are not
presented as active startups or active product surfaces in this repository.

## Core Directories

```text
sentinel-control/services/sentinel-core/
  sentinel/operator/          RuntimeHost, RootMissionRuntime, ProductActionKernel,
                              authority, receipts, browser routing and model clients.
  sentinel/agent/             Organ implementations, model execution and legacy surfaces.
  tests/                      Deterministic probes and regression gates.

sentinel-control/docs/
  roadmaps/                   Current product and completion roadmaps.
  reviews/deep_power_audit/   Canonical truth reports, ledgers and proof bundles.
```

## Proof Tiers

```text
T0_STATIC_INSPECTED
T1_LOCAL_DETERMINISTIC_CANDIDATE
T2_LIVE_BODY_PROVEN
T3_REAL_MODEL_PRODUCT_PROVEN
T4_FROZEN_HOLDOUT_GENERALIZATION_PROVEN
T5_SUSTAINED_LONG_HORIZON_PROVEN
```

Sentinel does not claim product success from local or deterministic tests alone.
Live body proof, real-model proof and holdout proof remain separate gates.

## What Sentinel Does Not Claim Yet

Sentinel is experimental and pre-release. It does not currently claim universal
production-grade computer use, completed Mission Studios, unrestricted OS
control, live money execution, universal public-site login automation,
production secret-vault integration, physical-system control or perfect
long-horizon reliability.

The project is intentionally trying to increase capability without weakening
the control plane around that capability.

## Start Here

- [`sentinel-control/WORKSPACE_MAP.md`](sentinel-control/WORKSPACE_MAP.md)
- [`sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md`](sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md)
- [`sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json`](sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json)
- [`sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE_REPORT.md`](sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE_REPORT.md)

## Contributing

Contributions are welcome around perception, mission reliability, recovery,
evidence, replay, model-facing state quality, governed skills, tests and
documentation.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before proposing large new capability
surfaces. Security-sensitive findings should follow [`SECURITY.md`](SECURITY.md).

## License

Sentinel Control is licensed under the [Apache License 2.0](LICENSE).
