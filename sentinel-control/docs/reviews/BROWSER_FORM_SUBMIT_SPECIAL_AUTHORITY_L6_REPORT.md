# Browser Form Submit Special Authority L6 Report

Recorded at: 2026-05-31

Pack:

```text
BROWSER_FORM_SUBMIT_SPECIAL_AUTHORITY_L6
```

## Current State

Sentinel now has a live browser stack with:

- governed browser observation;
- persistent browser sessions;
- L5 click/type/fill/select/hover/wait;
- L5 trajectory planning and self-healing target recovery;
- L6 non-sensitive form submit as a separate special-authority organ.

The important boundary is structural: generic L5 click did not become submit.
Submit has its own contract, receipt, FinalGate certificate, sensitive-field
scanner, and CLI workflow.

## Models And Contracts Added

Implemented in:

```text
sentinel/agent/organs/browser_form_submit_special_authority_l6.py
```

Models:

- `BrowserFormSubmitStatus`
- `BrowserFormSubmitFinalGateDecision`
- `BrowserFormSubmitContract`
- `BrowserFormSubmitRequest`
- `BrowserFormSubmitSafetyValidationResult`
- `BrowserFormSubmitReceipt`
- `BrowserFormSubmitFinalGateCertificate`
- `BrowserFormSubmitResult`
- `BrowserFormSubmitFinalGate`
- `BrowserFormSubmitSpecialAuthorityL6`

The contract requires:

- mission id match;
- allowed domain match;
- explicit `allow_form_submit = true`;
- mission tool `browser_form_submit_l6_special_authority`;
- mission action `browser_form_submit_special_authority`;
- receipt and FinalGate posture.

## Execution Path

The organ consumes an existing `BrowserSessionManagerL5Live` session and calls a
special-authority session method. The manager captures:

- before accessibility snapshot hash;
- before screenshot artifact id;
- after accessibility snapshot hash;
- after screenshot artifact id;
- form-state hash summary.

The submitted form values are not persisted in the L6 receipt or result.

## Sensitive Surface Blocking

Blocked before submit:

- password fields;
- credential/token/secret markers;
- API-key/authorization/bearer markers;
- payment/card/CVV/bank markers;
- upload/file fields;
- unsafe operator notes such as provider/model override or browser login.

Still not implemented:

```text
browser login = NOT_STARTED
credentialed session broker = NOT_STARTED
payment submit = NOT_STARTED
upload/download = NOT_STARTED
arbitrary JavaScript = NOT_STARTED
```

## CLI

Added:

```text
python -m sentinel browser-submit-demo --mission <file.json> --url <https-url> --run-root <dir> --input-name Email --text <value> --submit-name Send
```

The CLI opens a scoped browser session, types into a field, runs the L6 submit
organ, writes a safe result artifact, and closes the session.

## Truth Table

| Segment | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Non-sensitive form submit | CLOSED | `test_l6_submits_non_sensitive_form_with_before_after_evidence` | Uses existing live browser session |
| Special authority required | CLOSED | `test_l6_requires_special_authority_and_explicit_contract` | Mission files must opt into the L6 action/tool |
| Login/payment/credential block | CLOSED | `test_l6_blocks_login_credential_and_payment_forms` | Separate credential/login pack required |
| Raw form value durability | CLOSED | `test_l6_does_not_persist_raw_form_values` | Existing L5 type receipt stores only text hash |
| Provider/model override block | CLOSED | `test_l6_blocks_provider_override_and_dangerous_browser_payloads` | Scanner remains conservative |
| Generic L5 submit | BLOCKED | L5 session action enum still excludes submit | L6 only |
| Credentialed browser sessions | NOT_STARTED | No vault resolver or login broker used | Next pack |

## Verification

Fresh verification run during this pack:

```text
python -m pytest tests/test_browser_form_submit_special_authority_l6.py -q
python -m pytest tests/test_browser_trajectory_planner_l5.py tests/test_browser_form_submit_special_authority_l6.py -q
python -m pytest tests/test_sentinel_power_lab_runtime_v0.py tests/test_organ_safety_scanner_consolidation.py -q
python -m pytest tests/test_browser_session_manager_l5_live.py tests/test_browser_operator_agent_l4_l5_live.py tests/test_agent_browser_operator_runtime_integration.py tests/test_agent_browser_operator_runtime_minicorpus.py -q
python -m pytest tests -k browser -q
```

Result:

```text
5 passed
11 passed
23 passed
31 passed
403 passed with -k browser
```

## Next Pack

```text
BROWSER_LOGIN_CREDENTIAL_SESSION_BROKER_L6
```

The next browser pack should add credential/session continuity through the
Mission Authority and Credential Vault foundation. It must not store raw secrets
in prompts, memory, receipts, or browser artifacts.
