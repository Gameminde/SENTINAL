# Repository Presentation Cleanup For OpenAI Review V1

## Verdict

```text
ROOT_GITHUB_PRESENTATION_CLEANUP = APPLIED
active_product = Sentinel Control
root_redditpulse_visible = false
runtime_behavior_changed = false
provider_calls = 0
browser_runs = 0
FIXED_PROVEN = unchanged
```

## Scope

This cleanup is presentation-only. It makes the GitHub repository read as one
Sentinel product instead of several unrelated startup projects living at the
root.

## Changes

- Rewrote the root `README.md` around the current Sentinel Cognitive OS identity.
- Recreated `sentinel-control/WORKSPACE_MAP.md` as the active product map.
- Moved the old `RedditPulse` tree to `archive/prototypes/redditpulse-cueidea/`.
- Added archive notes explaining that prototypes are historical material, not active product surfaces.
- Added `.gitattributes` so archived prototypes do not dominate GitHub language statistics.
- Kept all untracked runtime and temporary Sentinel mission directories untouched.

## Archive Truth

```text
archived_prototype = archive/prototypes/redditpulse-cueidea
active_product_root = sentinel-control
history_preserved_by_git_move = true
prototype_deleted = false
prototype_product_claim_removed_from_root = true
```

## Sentinel Truth Preserved

```text
canonical_spine_campaign = SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1
canonical_browser_backend = sentinel_chromium
cloak_status = optional_external_backend
fixed_proven_count = 0/65
```

## Validation

Validation for this cleanup should prove:

- Markdown/docs contain no raw local paths, secrets or provider payloads.
- The root GitHub view exposes Sentinel Control as the primary project.
- Archived prototype material remains available for provenance.
- No runtime source, proof ledger or live mission artifact was rewritten.
