# Cognition Memory Scanner Consolidation Lock Report

Date: 2026-05-26

Base commit: `a2137f0` (`runtime: remediate audit safety findings`)

## Purpose

The previous scanner lock unified executor and browser organ firewalls, but
Brain, memory, proposal bridge, and credential authority foundation still
carried independent recursive scanners and secret patterns. This lock applies
one safety contract across both cognition and body metadata without adding
execution power.

## Canonical Contract

The canonical scanner is now:

- `sentinel/shared/safety_scanner.py`

The former path:

- `sentinel/agent/organs/safety_scanner.py`

remains as a compatibility re-export for existing organ imports. The shared
location avoids an invalid foundational dependency from
`sentinel.organs.credentials` into `sentinel.agent.organs`.

## Migrated Surfaces

- `sentinel/agent/brain/cognition_loop.py`
- `sentinel/agent/llm/memory_bridge.py`
- `sentinel/agent/llm/memory_replay.py`
- `sentinel/agent/llm/memory_retrieval.py`
- `sentinel/agent/llm/memory_slots.py`
- `sentinel/agent/organs/proposal_bridge.py`
- `sentinel/organs/credentials/foundation.py`

Each validator now calls `scan_forbidden_payload_flat(...)` from the same
shared source. Local recursive scanner functions, duplicate forbidden-key
tables, and duplicate secret regexes were removed from those modules.

## Superset Preservation

The shared scanner adds blockers that previously existed only outside the
first organ scanner lock:

- `revert_files`, formerly protected by memory replay.
- `credential_value` and `secret_value`, formerly protected by credential
  foundation.
- `sk-` secret-like values at length 16 or greater, preserving the stricter
  credential foundation threshold.

Descriptive negative-control fields such as `forbidden_substeps` remain safe
data: listing an action as forbidden is not misread as requesting it.

## Status

| Finding | Status | Evidence | Limitation |
|---|---|---|---|
| Brain scanner duplication | CLOSED | Shared-scanner identity and validator tests. | Local model authority firewalls remain intentionally local. |
| Memory scanner duplication | CLOSED | Bridge/replay/retrieval/slots regression tests. | Durable memory persistence remains separate work. |
| Proposal bridge scanner duplication | CLOSED | Proposal bridge regressions and negative-control test. | Proposal remains data, not permission. |
| Credential foundation scanner duplication | CLOSED | Credential safety and legacy-secret-threshold tests. | Real secret storage/use remains not started. |
| Cross-layer scanner placement | CLOSED | Shared canonical module plus compatibility export. | Existing import path remains for compatibility. |
| Secret firewall weakening risk | CLOSED | Regression covers the stricter credential `sk-` threshold. | Scanner flags metadata only; it does not resolve secrets. |

## Verification Evidence

Executed:

```text
python -m pytest tests/test_cognition_memory_scanner_consolidation_lock.py tests/test_organ_safety_scanner_consolidation.py tests/test_brain_cognition_loop_wiring.py tests/test_llm_minimal_epistemic_memory_bridge.py tests/test_llm_role_loop_to_memory_bridge_integration.py tests/test_llm_memory_replay_and_checkpoints_v0.py tests/test_llm_safe_memory_retrieval_v0.py tests/test_llm_hot_context_slots_v0.py tests/test_llm_proposal_artifacts_and_evidence_verifier.py tests/test_organ_proposal_bridge.py tests/test_mission_authority_and_credential_vault_foundation.py -q
```

Result: `228 passed`.

## Safety Statement

- No new Root Authority path.
- No credential value storage or credential use by an organ.
- No provider activation, fallback, or AUTO routing.
- No browser submit/login, API mutation, channel send, shell, desktop, or
  payment execution.
- No default-on runtime behavior.

## Next Audit Remediation

The next material non-capability repair is
`EVENTBUS_DURABLE_WAL_SAFE_RECEIPTS_LOCK`, which must persist only safe
receipt/event metadata and must explicitly exclude raw prompt, provider
response, reasoning, and secret material.
