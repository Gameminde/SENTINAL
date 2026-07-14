# SENTINEL_BROWSER_CORTEX_REAL_CALIBRATION_ON_NON_HOLDOUT_SITES_V1_REPORT

## Verdict

```text
BROWSER_CORTEX_REAL_CALIBRATION_ON_NON_HOLDOUT_SITES_V1
= VALID_CALIBRATION_MEASURED + QUALITY_GATE_FAIL

runtime_behavior_modified = no
provider_calls_consumed = 46
deterministic_decision_client = no
fixture_backend = no
playwright_fallback = no
frozen_holdout_used = no
push = no
```

This tranche measured the real provider/product browser path and stopped without
fixing failures. The result is an honest quality failure dominated by the real
browser body/session path, not by deterministic corpus overfitting.

## Provenance Reconciliation

```text
Pack 1B Stage A commit = 20f0bae9b7777407f50e16682f0111072ba37879
baseline artifact runtime_commit = afe40f8f9893416ceb59489f7ceb62b2ba499150
actual provider-run HEAD = f1aa694 docs: align calibration provider identity
runtime tree hash = 88c0b4ef4127711a1442bd236fe704eb039a4279
```

The `runtime_commit = afe40f8` value in the Pack 1B baseline artifact is a
historical baseline metadata label carried by the same-corpus artifact. It is
not the executable code identity for this calibration. The existing Pack 1B
baseline artifact was not rewritten.

Safe hashes recorded:

```text
Pack 1B embedded baseline_artifact_hash = 481f56a86751d8a12f4d53487c2018d0705dd0a8d0e005a0e47be50bc62339f6
Pack 1B baseline artifact file_sha256 = 4eff79456e57c01a5db96658806626b59482be7ade9e4a9a91dc1cb7134d0c61
Pack 1B corpus manifest hash = 64b5bbb2b5c258f8adac33716478cae73b86b23dcb981d9239acd5c2aa1efb84
Pack 1B fixture bundle hash = a463324578c36f00959fb99e12686031bf511025b2363b57cc594436706d83ee
non-holdout calibration manifest sha256 = ff0089daeeac3452aa2d4a2da25e5edc98382ad1ae3e762ed6cf69fdc03c69b3
result artifact sha256 = da290bf6372acc4dc40a47b56d60ffbbdb027687620674d1a90a2e0d5c95d764
ledger summary sha256 = 58b06a1e83992ecc55c2b8fddbbf3bdfb1afe299b65e8d5d20cd813a5e8eb876
```

## Calibration Set

Frozen holdout domains were not opened or used:

```text
alibaba.com
wikipedia.org
github.com
arxiv.org
books.toscrape.com
```

The non-holdout calibration manifest froze 12 tasks across 6 public,
unauthenticated, read-only sites:

```text
webscraper.io
demoblaze.com
developer.mozilla.org
quotes.toscrape.com
scrapethissite.com
service-public.fr
```

Coverage includes commerce/catalog search, non-commerce information search,
multilingual content, positive and negative result tasks, duplicate/variant
results, numeric constraints, query refinement, dynamic pages, missing fields,
and multi-result comparison. The evaluator did not require one exact action
trajectory.

## Readiness Gate

```text
git worktree clean before provider run = yes
provider configuration present = yes
exact provider/model pinned = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
credential values printed = no
endpoint values printed = no
Cloak readiness passed = yes
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
silent fallback = disabled
profile material persisted = false
mission authority = read-only public-Web calibration
login/payment/contact/download/upload = forbidden
```

Readiness passed before provider use, so this was not a pre-provider
`VALID_INFRA_BLOCKED` stop.

## Execution Path

The calibration attempted the required product route:

```text
RuntimeHost
-> ModelLedProductActionKernelTaskLoop
-> real provider/model decision
-> ProductModelNativeDecisionClient
-> BrowserEnvironmentState / skill context
-> model-selected browser skill
-> ProductActionKernel
-> RealBrowserControlRuntime
-> BrowserSessionManager
-> Cloak backend
-> receipts / FinalGate / replay where reached
```

No deterministic decision client, fixture backend, Playwright fallback, or direct
ProductActionKernel-only shortcut was used.

## Aggregate Result

```text
tasks_total = 12
provider_decision_calls = 46
model_native_intent_accepted_count = 46
top_level_task_outcomes = 12 exception_preserved
top_level_exception_class = FileNotFoundError
missions_created_in_ledger = 45
dispatch_completed = 3
dispatch_blocked = 41
browser/product receipts in ledger = 46
loop task completions = 0
finish emitted = 0
replay side effects = 0
hard boundary violations = 0
raw secret exposure = 0
```

Ledger-level action counts:

```text
real_browser_control:real_browser.search = 41
real_browser_control:real_browser.extract_product_cards = 1
real_browser_control:real_browser.verify_extraction = 1
sentinel_loop:summarize_evidence = 1
```

Ledger-level blocked reasons:

```text
real_browser_search_session_open_failed = 40
real_browser_search_control_not_found = 1
```

The important interpretation is that the provider/model path was alive enough
to choose safe model-native browser skills, but the real browser body path did
not reliably open/control sessions on non-holdout public sites.

## Quality Gate

```text
tasks_measured_non_infra = 0/12
end_to_end_grounded_completion_rate = 0.0
search_materiality_precision = 1.0
unsupported_claims = 0
raw_secret_exposure = 0
hard_boundary_violations = 0
replay_side_effects = 0
repeated_identical_action_without_new_evidence = 0
body_vs_mind_failure_classification_complete = true
quality_gate_pass = false
```

`search_materiality_precision = 1.0` here only means the artifact did not record
false material search success. It does not mean search quality passed; no task
completed a grounded public-Web calibration mission.

## Body vs Mind

The observed failures are classified as body/infrastructure failures:

```text
body_failure = true
mind_failure = false
evidence_failure = false
infrastructure_failure = true
```

Do not blame the model for the failed quality gate. The model received enough
context to produce browser-skill intents, but Sentinel did not provide a stable
real browser body/session path for those intents.

## Suspicious Local Claims Re-Evaluation

The three suspicious local Pack 1B claims could not be fully evaluated because
the real body failed before semantic extraction on public sites.

```text
non-commerce observations becoming commerce_product = not reproduced; no live semantic entities extracted
duplicate canonical URLs surviving = not measured; no live canonical entity set
deterministic trajectories overstating freedom/fluidity = supported by evidence; live trajectories collapsed into repeated browser search/session failures
```

The real calibration therefore confirms that deterministic local corpus success
overstated real fluidity. It does not yet provide enough public-site entity data
to validate or falsify the commerce ontology and duplicate-resolution concerns.

## Safety / Persistence

```text
raw provider output persisted = false
raw provider reasoning persisted = false
raw DOM persisted = false
raw screenshot persisted = false
cookies/session/profile material persisted = false
credential values persisted = false
endpoint values persisted = false
artifact safety scan hits = 0
```

The results artifact records provider response shapes and hashes only. Some
safe shape keys include `raw_provider_response` because the internal provider
wrapper names its sanitized parsed response field that way; no raw provider text
or reasoning content was persisted.

## Artifacts

```text
SENTINEL_BROWSER_CORTEX_REAL_CALIBRATION_NON_HOLDOUT_MANIFEST_V1.json
SENTINEL_BROWSER_CORTEX_REAL_CALIBRATION_ON_NON_HOLDOUT_SITES_V1_PROVENANCE.json
SENTINEL_BROWSER_CORTEX_REAL_CALIBRATION_ON_NON_HOLDOUT_SITES_V1_RESULTS.json
SENTINEL_BROWSER_CORTEX_REAL_CALIBRATION_ON_NON_HOLDOUT_SITES_V1_LEDGER_SUMMARY.json
```

## Next Decision

Do not run the frozen holdout yet.

The next correction should target the class exposed by this measurement:

```text
REAL_BROWSER_BODY_SESSION_OPEN_AND_PUBLIC_SITE_ACTUATION_STABILITY_V1
```

The fix should reproduce and explain `real_browser_search_session_open_failed`
without provider calls first, then prove a local/public non-holdout body-level
search before spending another real-provider calibration run.
