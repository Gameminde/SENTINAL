# Organ Safety Scanner Consolidation Lock Report

Date: 2026-05-26

Pack: `ORGAN_SAFETY_SCANNER_CONSOLIDATION_LOCK`

## Current State

This pack consolidates Sentinel organ payload scanning into a canonical shared scanner while preserving local model firewalls and organ-specific validators.

No new organ power was added. No browser backend, Browser L5, provider activation, EventBus persistence, runtime decomposition, or FinalGate decomposition was implemented.

## Findings Treated

- Duplicated organ safety scanners across Gate, L2, L3, runtime execution, low-risk FinalGate, and browser organs.
- Conflicting `_scan_forbidden_payload` return contracts: some returned `list[str]`, others returned `dict[str, list[str]]`.
- Duplicated secret-like regex patterns.
- Inconsistent forbidden key coverage between DelegatedActionGate and downstream executors.
- DelegatedActionGate was less strict than downstream L2/L3/runtime/browser/finalgate blockers for several external-action markers.

## Files Migrated

- `sentinel/agent/organs/delegated_action_gate.py`
- `sentinel/agent/organs/runtime_execution.py`
- `sentinel/agent/organs/local_artifact_executor.py`
- `sentinel/agent/organs/reversible_workspace_executor.py`
- `sentinel/agent/organs/low_risk_finalgate.py`
- `sentinel/agent/organs/browser_readonly_organ_v1.py`
- `sentinel/agent/organs/browser_preparation_organ_v1.py`
- `sentinel/agent/organs/browser_semantic_extraction_organ_v1.py`

`organ_dispatch.py` was reviewed for this pack. It does not own a local forbidden payload scanner; it remains routed through ProposalBridge, DelegatedActionGate, and runtime execution validation.

## Canonical Scanner

Created:

- `sentinel/agent/organs/safety_scanner.py`

Exports:

- `OrganSafetyScanCategory`
- `OrganSafetyScanResult`
- `SHARED_SECRET_LIKE_PATTERN`
- `SHARED_FORBIDDEN_SECRET_KEYS`
- `SHARED_PROVIDER_OVERRIDE_KEYS`
- `SHARED_AUTHORITY_EXPANSION_KEYS`
- `SHARED_EXTERNAL_ACTION_KEYS`
- `SHARED_BROWSER_DANGEROUS_KEYS`
- `SHARED_CREDENTIAL_DANGEROUS_KEYS`
- `SHARED_NEGATIVE_CONTROL_SAFE_KEYS`
- `scan_forbidden_payload_flat(...)`
- `scan_forbidden_payload_categorized(...)`
- `scan_secret_like_text(...)`
- `scan_provider_override(...)`
- `scan_forbidden_external_surfaces(...)`
- `merge_scan_results(...)`
- `dedupe_scan_findings(...)`

## Flat vs Categorized Contract

`scan_forbidden_payload_flat(payload, path="$") -> list[str]`

- Always returns a deterministic list of safe paths.
- Used by DelegatedActionGate, L2, and L3 where only a flat reject list is required.

`scan_forbidden_payload_categorized(payload, path="$") -> dict[str, list[str]]`

- Always returns a deterministic category map.
- Used by runtime execution, low-risk FinalGate, and browser organs where provider overrides and forbidden external surfaces must be distinguished.

There is no same-name scanner with divergent return types in the migrated organ files.

## Gate Superset Proof

DelegatedActionGate now uses `scan_forbidden_payload_flat(...)`, backed by the shared superset of downstream dangerous markers.

The required dangerous keys are covered at the shared scanner level, including:

- `api_call`
- `network_call`
- `external_network`
- `send_now`
- `send_email`
- `channel_send`
- `browser_submit`
- `browser_login`
- `upload_file`
- `download_file`
- `shell`
- `terminal`
- `process`
- `credential`
- `token`
- `bearer`
- `api_key`
- `provider_override`
- `backend_override`
- `model_override`
- `authority_expansion`
- `delegated_lane_creation`
- `mission_envelope_expansion`
- `payment`
- `spend`
- `trade`
- `desktop_action`

Test evidence:

- `test_external_network_api_call_send_now_detected_at_gate`
- `test_gate_forbidden_keys_are_superset_of_downstream_dangerous_keys`

## Local Model Firewalls Preserved

Local model firewalls remain in place. This pack only replaces duplicated recursive scanner implementations used by validation functions.

Existing authority and execution firewalls remain local to:

- DelegatedActionGate models and lane models.
- L2 executor models and receipts.
- L3 executor models and receipts.
- Low-risk FinalGate models and certificates.
- Browser ReadOnly, Preparation, and Semantic Extraction models.

## Tests Added

Created:

- `tests/test_organ_safety_scanner_consolidation.py`

Coverage:

- Flat scanner return contract.
- Categorized scanner return contract.
- No conflicting same-name scanner return types.
- Secret-like detection without secret echo.
- Provider/backend/model override detection.
- Authority expansion detection.
- Gate detection of external network/API/send markers.
- Gate superset over downstream dangerous keys.
- L2/L3 shared scanner usage.
- Runtime/FinalGate categorized scanner usage.
- Browser organ detection of dangerous browser surfaces.
- Negative-control list safety.
- Deterministic scan results.

## Risks Closed

| Risk | Status |
| --- | --- |
| SCANNER_RETURN_TYPE_INCONSISTENCY | CLOSED |
| FORBIDDEN_KEY_INCONSISTENCY | CLOSED |
| SECRET_PATTERN_DUPLICATION | CLOSED |
| GATE_SUPERSET_DOWNSTREAM_BLOCKERS | CLOSED |
| LOCAL_MODEL_FIREWALLS_PRESERVED | CLOSED |

## Risks Reported For Later Packs

| Risk | Status | Later Pack |
| --- | --- | --- |
| CloakBrowser backend missing | NOT_STARTED | `CLOAKBROWSER_CONTROLLED_BACKEND_SPEC` |
| Browser L5 active interaction | NOT_STARTED | `BROWSER_L5_NAVIGATION_CLICK_TYPE_CONTROLLED` |
| Browser fetch timeout hardening | NOT_STARTED | `BROWSER_READONLY_PREFLIGHT_AND_TIMEOUT_HARDENING` |
| EventBus O(n^2) append verification | NOT_STARTED | `EVENTBUS_APPEND_PERFORMANCE_LOCK` |
| Symlink containment proof/hardening | NOT_STARTED | `PATH_CONTAINMENT_SYMLINK_PROOF` |
| Runtime decomposition | NOT_STARTED | future maintainability pack |
| FinalGate decomposition | NOT_STARTED | future maintainability pack |

## Lock Status

- `SCANNER_RETURN_TYPE_INCONSISTENCY = CLOSED`
- `FORBIDDEN_KEY_INCONSISTENCY = CLOSED`
- `SECRET_PATTERN_DUPLICATION = CLOSED`
- `GATE_SUPERSET_DOWNSTREAM_BLOCKERS = CLOSED`
- `LOCAL_MODEL_FIREWALLS_PRESERVED = CLOSED`
- `CLOAKBROWSER_READINESS = STILL_BLOCKED_BY_BROWSER_BACKEND_PACKS`

## No-New-Power Statement

This pack does not enable browser submit/login, API mutation, channel send, shell/desktop/payment, provider activation, fallback/AUTO routing, CloakBrowser, EventBus persistence, runtime decomposition, or FinalGate decomposition.

The scanner consolidation tightens validation and standardizes evidence of rejection. It does not grant authority, create execution lanes, or change AgentRuntime default behavior.
