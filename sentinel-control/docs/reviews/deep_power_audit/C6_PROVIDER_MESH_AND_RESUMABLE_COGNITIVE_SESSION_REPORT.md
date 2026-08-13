# C6 Provider Mesh And Resumable Cognitive Session Report

## Verdict

```text
C6_PROVIDER_MESH_AND_RESUMABLE_COGNITIVE_SESSION
= IMPLEMENTED_LOCAL_CANDIDATE
```

C6 adds a Sentinel-owned provider mesh around the canonical decision loop. It does not call OpenRouter or any real provider in this tranche, and it does not relaunch C5B/NVIDIA.

## Provider Configuration

```text
primary = openrouter / z-ai/glm-5.2
fallback_1 = openrouter / moonshotai/kimi-k2.7-code
fallback_2 = openrouter / qwen/qwen3.5-plus-02-15
experimental = openrouter / nvidia/minimaxai/minimax-m3
openrouter/auto = forbidden
```

OpenRouter is now a generic OpenAI-compatible provider option, not mandatory and not an automatic router.

## Local Proof

The injected proof exercised:

```text
provider A produces a decision
-> browser action completes and creates a receipt
-> provider A raises controlled 429
-> provider turn terminalizes only that turn
-> root cognitive state is checkpointed
-> provider B resumes from the next decision
-> previous browser action is not replayed
-> model-selected finish completes the mission
```

Observed local counters:

```text
provider_calls = 0
browser_runs = 0
provider_decision_turns = 3
material_actions = 1
browser_open_count = 1
receipt_count = 1
fallback_silent = false
FIXED_PROVEN = 0/65
```

## Boundaries Preserved

```text
CanonicalDecision remains internal IR
Model Freedom Intent Bridge remains common
ProductActionKernel remains effect boundary
previous receipts are not replayed
fallback provenance is explicit
raw provider material persisted = false
```

## Validation

```text
pytest c6 provider mesh injected test = passed
pytest openrouter catalog explicit model test = passed
pytest openrouter canonical decision transport test = passed
pytest canonical core + C5 physical browser group = passed
pytest model provider catalog + NVIDIA provider tests = passed
compileall sentinel = passed
```

## Next Truth

C6 is not a real OpenRouter proof yet. The next live tranche should configure OpenRouter key and budget, then run a bounded real provider mesh mission without `openrouter/auto` and without replaying C5B/NVIDIA.
