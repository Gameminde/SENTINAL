# P6J AgentLab Implementation Alignment

Date: 2026-05-09

## Goal

P6J verifies that Sentinel's first external-organ family was not built from
generic imagination. Each P6C-P6I.6 organ must map to concrete AgentLab or
external research patterns and rewrite those patterns Sentinel-native.

```text
AgentLab / vendor forensic pattern
-> Sentinel rewrite
-> controls
-> promotion ladder
-> tests
```

## Sources Used

```text
OpenClaw final forensic report
Hermes final forensic report
OpenJarvis final forensic report
JARVIS final forensic report
CloakBrowser power review
financial-services harvest map
TradingAgents static audit and capability map
```

## Alignment Summary

| Organ | Main Sources | Sentinel Rewrite |
| --- | --- | --- |
| P6C Browser | OpenClaw, JARVIS, CloakBrowser | BrowserPowerGovernor, BrowserMisuseClassifier, BrowserDetectionBench |
| P6D External API | OpenClaw, OpenJarvis, financial-services, TradingAgents | ExternalAPIAllowlist, APICostEstimator, TradingAgentsDataVendorRoute |
| P6E Channel | OpenClaw, Hermes, JARVIS | ChannelMessageDraft, ChannelSendGate, InboundChannelMessage |
| P6F Credentials | JARVIS, OpenClaw, Hermes | CredentialRef, ScopedCredentialGrant, CredentialTraceRedactor |
| P6G Capital | financial-services, OpenJarvis, Hermes, TradingAgents | SignalLedger, AdaptiveOperatingEnvelope, BudgetReallocator |
| P6H Spend | financial-services, JARVIS, OpenClaw | SpendAuthorityEnvelope, FakeSpendProvider, SpendKillSwitch |
| P6I Trading | TradingAgents, financial-services | TradingSpecialAuthority, PaperTradeProvider, TradingReceipt |
| P6I.6 TradingAgents | TradingAgents | TradingAgentsFirmPlan, TradingAgentsSignalParser, TradingOutcomeMemoryEntry |

## Power Doctrine

```text
Blocked-by-default does not mean forbidden forever.
Strong powers are classified, controlled, and promoted through L0-L8.
No vendor runtime is bridged.
No vendor code is copied.
No authority is granted by source docs, signals, expected profit, workspace, or memory.
```

P6J adds no external powers. It tightens the relationship between vendor
evidence and Sentinel implementation so future P6K OrganBench can test real
mechanism families instead of generic organ shells.

## Implemented Enforcement

```text
AgentLabImplementationAlignmentEntry
AgentLabImplementationAlignmentMatrix
AgentLabImplementationAlignmentBuilder
ORGAN_IMPLEMENTATION_ALIGNMENT_BUILT trace event
tests/test_p6_agentlab_implementation_alignment.py
```

The matrix rejects:

```text
missing required P6 organ phases
duplicate organ phases
missing source systems
missing vendor patterns
missing Sentinel rewrites
unhandled dangerous surfaces
vendor code copy
vendor runtime bridge
authority expansion
runtime powers added
```

## Next Phase

```text
P6K_ORGANBENCH_EXTERNAL_ORGAN_INTEGRATED_REVIEW
```

OrganBench should now test the aligned mechanisms across browser, API, channel,
credentials, capital, spend, and trading using failure fixtures derived from
these source-backed patterns.
