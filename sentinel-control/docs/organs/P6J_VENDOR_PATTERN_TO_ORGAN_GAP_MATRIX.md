# P6J Vendor Pattern To Organ Gap Matrix

Date: 2026-05-09

## Matrix

| Organ | Source-backed patterns | Current Sentinel rewrites | Gaps closed now | Deferred gaps |
| --- | --- | --- | --- | --- |
| Browser | OpenClaw browser/control plane, JARVIS browser/sidecar awareness, CloakBrowser P0-P5 power classification | BrowserReliabilityProfile, BrowserSessionContinuityPolicy, BrowserPowerGovernor, BrowserMisuseClassifier, BrowserDetectionBench, BrowserComplianceGate | Cloak-like powers are classified, not deleted | BrowserFinalGateAdapter, special-authority stealth sandbox |
| External API | OpenClaw connector/plugin manifest, OpenJarvis cost/rate routing, financial-services connector workflows, TradingAgents data vendor fallback | ExternalAPIAllowlist, APICostEstimator, APIPrivacyRiskClassifier, ExternalAPIDryRunPlanner, TradingAgentsDataVendorRoute | API organ now explicitly maps vendor fallback power | live read-only API sandbox with credential refs |
| Channel | OpenClaw channel adapters, Hermes context reuse, JARVIS approval lifecycle/templates | ChannelMessageDraft, ChannelSendGate, InboundChannelMessage, RecipientProvenance, ChannelRateLimitPolicy | Inbound context remains untrusted and draft-first lifecycle is source-backed | limited authorized send runtime |
| Credentials | JARVIS vault/sidecar secret-risk, OpenClaw plugin/channel credentials, Hermes external-account skills | CredentialRef, ScopedCredentialGrant, CredentialVaultPolicy, CredentialTraceRedactor, revoke_credential_grant | Raw secrets remain blocked from prompt/memory/workspace/vendor harvest | real vault adapter behind Red Lane special authority |
| Capital | financial-services procedures, OpenJarvis cost routing, Hermes memory, TradingAgents outcome memory | CapitalOpportunity, SignalLedger, AdaptiveOperatingEnvelope, BudgetReallocator, DynamicSpendPolicy, CapitalRiskReview | TradingAgents outcome memory is recognized as future capital-learning input | CapitalAnalysisBench, spend promotion |
| Spend | financial-services human review boundary, JARVIS approval/kill switch, OpenClaw receipt/action kernel lessons | SpendAuthorityEnvelope, SpendRequest, FakeSpendProvider, SpendReceipt, SubscriptionGuard, RefundCancelPath, SpendKillSwitch | Fake provider stays the only executable spend surface | real provider adapter after OrganBench and special authority |
| Trading | TradingAgents risk debate/portfolio manager, financial-services evidence/review boundary | TradingSpecialAuthority, BrokerContract, AssetPolicy, PositionSizingPolicy, MaxLossPolicy, StopLossPolicy, PaperTradeProvider, TradingReceipt | Paper provider is bound to authority asset scope and max leverage | real broker adapter after special authority and OrganBench |
| TradingAgents Harvest | Trading desk role graph, five-tier rating parser, vendor fallback, outcome memory | TradingAgentsFirmPlan, TradingAgentsRoleAssignment, TradingAgentsSignalParser, TradingAgentsDataVendorRoute, TradingOutcomeMemoryEntry | TradingAgents is now official P6J source evidence | OrganBench trading fixtures |

## High-Power Surface Classification And Promotion

| Surface | Capability path |
| --- | --- |
| browser session continuity / public read-only browsing | authorized when mission authority fits |
| fingerprint consistency / data vendor fallback / dynamic budget reallocation | evaluated before use |
| detection research / dry-run request planning / fake providers / paper trading | sandboxed capability |
| live API calls | capability promotion path |
| live channel send | capability promotion path |
| real payment execution | capability promotion path |
| real trading execution | capability promotion path |
| stealth browser operation | capability promotion path |
| scoped credential use | capability promotion path |

## Black Lane Misuse Objectives

These are blocked as objectives, not because the underlying capability is
deleted:

```text
fake identity
KYC bypass
credential theft or raw secret extraction
illegal spam or deceptive identity
unlawful evasion
unauthorized scraping outside lawful authority
vendor runtime bridge
profit guarantee
budget overrun or unbacked signal spend
```

## Alignment Verdict

P6C-P6I.6 are no longer generic organ shells. Each one has a source-backed
mechanism, a Sentinel rewrite, an explicit control layer, and a promotion path.
No gap required new external power in P6J. P6J1 reframes the old defensive
surface language into a power-first capability map: high-power surfaces are
classified and unlockable through explicit authority, evals, receipts, kill
switches, and FinalGate; Black Lane misuse objectives remain blocked.
