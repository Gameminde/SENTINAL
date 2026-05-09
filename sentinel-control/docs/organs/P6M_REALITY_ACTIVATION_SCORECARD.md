# P6M Reality Activation Scorecard

Date: 2026-05-09

## Phase

```text
phase = P6M_REALITY_ACTIVATION_FOR_EXISTING_ORGANS
previous_phase = P6L_FULL_LOCKED
next_phase = P6N_CODE_SHELL_AGENTLAB_HARVEST
```

## Goal

Stop collecting organ contracts and make the existing organs do scoped real
work. P6M activates low-risk reality lanes while keeping high-risk actions in
test-mode, paper-mode, or proposal-only mode.

Core rule:

```text
Green/Blue = real scoped action
Orange/Red = test-mode, paper-mode, proposal, or special-authority path
Black = blocked misuse objective
```

## Implemented Reality Layer

```text
sentinel/organs/reality_activation.py
```

Implemented adapters:

```text
RealityBrowserReader
ExternalAPIRealityClient
LocalChannelDraftStore
EnvCredentialRefResolver
DesktopWorkspaceOperator
CapitalRealityIntegrator
ReadOnlyMarketDataProvider
TradingRealityPaperRunner
SpendTestModeProvider
```

## Organ Activation

| Organ | P6M reality behavior | Boundary |
| --- | --- | --- |
| Browser | read allowlisted public pages, extract text/links, receipt | no login, stealth, bypass, or mutation |
| External API | allowlisted `GET` / `HEAD`, response receipt | no mutation API |
| Channel | write real local draft files with receipts | no live send |
| Credentials | resolve scoped env-var refs, redact receipts | no raw secret logging or storage |
| Desktop | real workspace list/read/write/create under scoped root | no host control, no shell/process |
| Capital | consume real receipts into signal ledger and spend proposal | no live spend |
| Trading | read market data and paper trade only | no real broker execution |
| Spend | test-mode provider only | no real payment by default |

## Verification

```text
P6M targeted tests = 8 passed
full sentinel-core tests = not run by instruction
```

Command:

```bash
python -m pytest tests/test_p6_existing_organs_reality_activation.py -v --tb=short
```

## Boundaries

```text
no new organ family
no real payment
no real trading
no live channel send
no account creation
no credential secret logging
no browser power expansion
no host desktop control
no shell/process execution
no authority expansion
```
