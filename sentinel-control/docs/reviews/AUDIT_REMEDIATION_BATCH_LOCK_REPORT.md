# Sentinel Audit Remediation Batch Lock Report

Date: 2026-05-26

Base commit before this batch: `f05ce70` (`runtime: consolidate organ safety scanner`)

This report covers the bounded remediation batch launched after the external
deep-dive audit. The batch closes code-level defects that can be fixed without
adding new execution power. It does not activate CloakBrowser, Browser L5,
provider defaults, shell/API/channel/desktop execution, or credential use.

## Scope

Implemented in this batch:

- Browser Read-Only deterministic request identity.
- Browser Read-Only preflight purity for dict contracts and lanes.
- Browser Read-Only fetch timeout enforcement.
- EventBus O(1) append fast path with full-chain audit on dirty ledger mutation.
- L2/L3 explicit symlink-component blocking reasons.
- OrganDispatcher contract builders no longer swallow programmer `TypeError`.
- DelegatedActionGate budget parsing blocks malformed numeric budgets safely.
- Existing test-suite hygiene fixes: OpenAI-compatible provider test can run
  standalone, and role-loop memory bridge default-off assertion now matches the
  current opt-in memory feedback architecture.

Already closed by the previous scanner pack:

- Organ scanner return type inconsistency.
- Forbidden key inconsistency across Gate/L2/L3/Runtime/FinalGate/Browser.
- Secret regex duplication across organ scanners.
- Gate superset of downstream forbidden surfaces.

## Findings Truth Table

| Audit finding | Status | Evidence | Limitation |
|---|---:|---|---|
| C-01 runtime.py oversized | NOT_STARTED | No runtime decomposition in this batch. | Needs `AGENT_RUNTIME_DECOMPOSITION_LOCK`; high regression risk if mixed with safety fixes. |
| C-02 final_gate.py oversized | NOT_STARTED | No FinalGate decomposition in this batch. | Needs `CORE_FINAL_GATE_DECOMPOSITION_LOCK`; should be mechanical and test-heavy. |
| C-03 no default live LLM provider path | NOT_STARTED | No provider activation or fallback added. | Needs explicit provider activation contract; no AUTO/fallback routing was introduced. |
| C-04 `_scan_forbidden_payload` return type inconsistency | CLOSED | `tests/test_organ_safety_scanner_consolidation.py`. | Closed in `f05ce70`. |
| C-05 EventBus O(n^2) append verification | CLOSED | `tests/test_audit_remediation_batch_lock.py::test_eventbus_append_uses_fast_path_when_chain_not_dirty`; trace hash tests still pass. | Full-chain audit still runs when the private ledger list is externally mutated or when `verify_chain()` is called. |
| C-06 durable WAL/persistence | NOT_STARTED | No WAL or durable EventBus persistence added. | Needs a safe durable store pack because naive WAL could persist raw prompt/response/reasoning. |
| H-01 duplicated organ safety scanners | CLOSED | `tests/test_organ_safety_scanner_consolidation.py`. | Closed in `f05ce70`; local model firewalls preserved. |
| H-02 duplicated secret regex | CLOSED | Shared scanner exposes `SHARED_SECRET_LIKE_PATTERN`. | Closed in `f05ce70`. |
| H-03 Gate weaker than downstream keys | CLOSED | Gate superset test in scanner consolidation suite. | Closed in `f05ce70`. |
| H-04 Browser request ID time-dependent | CLOSED | `test_browser_readonly_request_id_is_deterministic_from_content_not_time`. | Request identity excludes timing fields; receipts still record created timestamps. |
| H-05 Browser preflight mutates request | CLOSED | `test_browser_readonly_preflight_does_not_mutate_dict_contract_or_lane`. | Internal helper parses local copies; public Pydantic validation may still normalize dicts on construction. |
| H-06 OrganDispatcher broad exception swallowing | CLOSED | `test_dispatch_contract_builder_does_not_swallow_programmer_type_errors`; no `except Exception` remains in `organ_dispatch.py`. | Browser fetcher exceptions are still converted to failed receipts inside the browser organ, intentionally. |
| H-07 Browser fetch timeout missing | CLOSED | `test_browser_readonly_fetch_timeout_blocks_without_hanging`. | Timeout wraps the provided sync fetcher with a daemon worker; it blocks the organ result path without killing arbitrary user code. |
| H-08 authority invariant dead stub | NOT_STARTED | `InvariantChecker.check_authority()` remains intentional stub. | Needs `AUTHORITY_DRIFT_INVARIANT_LOCK`; must align with existing mission authority/gate chokepoints. |
| M-01 duplicated `utc_now()` | NOT_STARTED | No shared time utility migration. | Low-risk cleanup pack; not a runtime safety blocker. |
| M-02 duplicated dedupe helpers | NOT_STARTED | No shared collection utility migration. | Low-risk cleanup pack. |
| M-03 duplicated firewall assertion helpers | NOT_STARTED | Local model firewalls intentionally preserved. | A shared helper can be added later without weakening explicit validators. |
| M-04 L3 `_mutated_content()` coverage | CLOSED_BY_EXISTING_CODE | Existing implementation handles replace, append, JSON metadata, reversible metadata. | No new code required. |
| M-05 `FinalGate_checks` naming | NOT_STARTED | Field left unchanged for compatibility. | Rename needs migration/alias pack. |
| M-06 Browser injection regex limitations | PREPARED | Browser content remains data-not-instruction; regexes are heuristic flags. | Needs multilingual/adversarial injection heuristic pack if desired. |
| M-07 Gate budget `int()` crash on malformed values | CLOSED | `test_delegated_gate_budget_parser_treats_malformed_budget_as_exhausted`. | Malformed action/token budgets fail closed as exhausted. |
| M-08 dispatch rate limiting | PREPARED | `OrganRuntimeExecutionConfig.max_action_count` exists but dispatcher throttling is not changed in this batch. | Needs small `ORGAN_DISPATCH_RATE_LIMIT_LOCK` to avoid altering dispatch aggregation semantics silently. |
| L-05 symlink bypass ambiguity | CLOSED | L2/L3 symlink-component tests in audit batch; existing symlink escape tests still pass. | On Windows, symlink tests skip if OS privilege is unavailable. |

## Safety Proof

- No CloakBrowser backend was added.
- No Browser L5 click/type/submit/login path was added.
- No provider activation, provider expansion, fallback, or AUTO routing was added.
- No API mutation, channel send, shell, desktop, payment, or credential use was added.
- No credential value storage was added.
- No runtime default-on behavior was added.
- Browser Read-Only remains L4 perception data only.
- EventBus persistence remains `NOT_STARTED`; this avoids accidental durable raw prompt/response/reasoning leakage.

## Files Modified

- `sentinel-control/services/sentinel-core/sentinel/shared/events.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_readonly_organ_v1.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/delegated_action_gate.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/local_artifact_executor.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/reversible_workspace_executor.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/organ_dispatch.py`
- `sentinel-control/services/sentinel-core/tests/test_audit_remediation_batch_lock.py`
- `sentinel-control/services/sentinel-core/tests/test_llm_role_loop_to_memory_bridge_integration.py`
- `sentinel-control/services/sentinel-core/tests/test_openai_compatible_provider_base.py`

## Next Packs

1. `EVENTBUS_DURABLE_WAL_SAFE_RECEIPTS_LOCK`
2. `ORGAN_DISPATCH_RATE_LIMIT_LOCK`
3. `AUTHORITY_DRIFT_INVARIANT_LOCK`
4. `PROVIDER_ACTIVATION_CONTRACT_LOCK`
5. `AGENT_RUNTIME_DECOMPOSITION_LOCK`
6. `CORE_FINAL_GATE_DECOMPOSITION_LOCK`
7. `CLOAKBROWSER_CONTROLLED_BACKEND_SPEC`
