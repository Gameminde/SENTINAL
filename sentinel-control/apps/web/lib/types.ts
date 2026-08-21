export type RiskLevel = "low" | "medium" | "high" | "critical";
export type ApprovalStatus = "not_required" | "pending" | "approved" | "rejected" | "blocked";
export type RunDepth = "quick" | "standard" | "deep";
export type RunMode = "canonical_public" | "sandbox_hypothesis";
export type RunVerdict = "build" | "pivot" | "niche_down" | "kill" | "research_more";
export type FeedbackTargetType = "action" | "asset" | "evidence" | "run";
export type FeedbackRating = "useful" | "weak" | "approved" | "rejected";
export type WatchlistStatus = "monitoring" | "needs_review" | "interview" | "validated" | "archived";
export type PaidQuoteStatus = "draft" | "ready" | "payment_disabled";
export type GTMPackQualityStatus = "draft" | "needs_revision" | "ready";
export type MissionType = "gtm" | "research_summary";
export type MissionMode = "safe" | "operator" | "power" | "autonomous";
export type MissionStatus = "planned" | "running" | "paused" | "escalated" | "completed" | "failed" | "stopped" | "revoked";
export type MissionActionRoute = "auto_execute" | "log_and_continue" | "escalate" | "block";
export type ReversibilityLevel = "read_only" | "draft" | "local_write_reversible" | "state_mutating_recoverable" | "irreversible";
export type ExternalityLevel = "internal_local" | "internal_connected_system" | "external_private" | "external_public";
export type SensitivityLevel = "public" | "internal" | "personal" | "secret" | "financial" | "identity";
export type MissionConfidenceLevel = "high" | "medium" | "low" | "unknown";

export interface EvidenceRow {
  id: string;
  source: string;
  proofTier: "direct" | "adjacent" | "supporting";
  summary: string;
  confidence: number;
  freshness: string;
  actionRefs: string[];
  quote?: string;
  url?: string;
  details: {
    excerpt: string;
    methodology: string;
    tags: string[];
  };
}

export interface ActionRow {
  id: string;
  tool: string;
  title: string;
  intent: string;
  risk: RiskLevel;
  approvalStatus: ApprovalStatus;
  requiresApproval: boolean;
  blocked?: boolean;
  dryRun: {
    whyNeeded: string;
    preview: Record<string, string>;
    evidenceUsed: string[];
  };
  sourceNotes: string[];
}

export interface ProjectCard {
  id: string;
  name: string;
  status: string;
  updatedAt: string;
  description: string;
  files: string[];
}

export interface AgentRow {
  name: string;
  role: string;
  status: string;
  note: string;
}

export interface FirewallPolicyRow {
  tool: string;
  risk: RiskLevel;
  autoAllowed: boolean;
  approval: boolean;
  disabled: boolean;
  scope: string;
}

export interface RunStageRow {
  key: string;
  label: string;
  detail: string;
  active?: boolean;
}

export interface RunSummaryRow {
  title: string;
  status: string;
  runId: string;
  startedAt: string;
  verdict: string;
  confidence: number;
  riskScore: number;
  riskLabel: string;
}

export interface GeneratedAssetRow {
  id: string;
  assetType: string;
  title: string;
  content: string;
  filePath?: string;
  evidenceRefs: string[];
  createdAt: string;
}

export interface TraceLogRow {
  id: string;
  eventType: string;
  message: string;
  createdAt: string;
  actionId?: string;
}

export interface CostLineRow {
  label: string;
  tokens: number;
  estimatedCents: number;
}

export interface CostSummaryRow {
  currency: "USD";
  totalCents: number;
  lines: CostLineRow[];
  note: string;
}

export interface FeedbackEntryRow {
  id: string;
  targetType: FeedbackTargetType;
  targetId: string;
  rating: FeedbackRating;
  note?: string;
  createdAt: string;
}

export interface WatchlistItemRow {
  id: string;
  label: string;
  signalType: "competitor" | "wtp" | "community" | "risk";
  status: WatchlistStatus;
  summary: string;
  source: string;
  evidenceRefs: string[];
  updatedAt: string;
  note?: string;
}

export interface PaidRunQuoteRow {
  id: string;
  runId: string;
  label: string;
  amountCents: number;
  status: PaidQuoteStatus;
  lineItems: string[];
  createdAt: string;
}

export interface ProspectSourceRow {
  id: string;
  label: string;
  sourceType: "community" | "competitor" | "review_site" | "search" | "direct_source" | "unknown";
  source: string;
  url?: string;
  whyRelevant: string;
  evidenceRefs: string[];
}

export interface CueIdeaReportSummaryRow {
  validationId?: string;
  status?: string;
  importedAt: string;
  executiveSummary: string;
  icp?: string;
  positioning?: string;
  pricing?: string;
  competitorLandscape?: string;
  distribution?: string;
  rawSectionKeys: string[];
}

export interface GTMSectionQualityRow {
  name: string;
  score: number;
  passed: boolean;
  message: string;
}

export interface GTMPackQualityRow {
  score: number;
  status: GTMPackQualityStatus;
  sectionScores: GTMSectionQualityRow[];
  blockers: string[];
  warnings: string[];
}

export interface ExecutionBoardCardRow {
  id: string;
  title: string;
  description: string;
  meta: string;
  href: string;
  tone: "neutral" | "good" | "warn" | "bad";
}

export interface ExecutionBoardColumnRow {
  id: string;
  title: string;
  cards: ExecutionBoardCardRow[];
}

export interface SentinelRunRecord {
  id: string;
  userId: string;
  inputIdea: string;
  niche?: string;
  depth: RunDepth;
  status: string;
  verdict: RunVerdict;
  confidence: number;
  riskScore: number;
  riskLabel: string;
  createdAt: string;
  updatedAt: string;
  summary: RunSummaryRow;
  stages: RunStageRow[];
  agents: AgentRow[];
  evidence: EvidenceRow[];
  actions: ActionRow[];
  generatedAssets: GeneratedAssetRow[];
  traceRecords: TraceLogRow[];
  cost: CostSummaryRow;
  feedback: FeedbackEntryRow[];
  watchlist: WatchlistItemRow[];
  paidQuote?: PaidRunQuoteRow;
  prospectSources: ProspectSourceRow[];
  cueideaReport?: CueIdeaReportSummaryRow;
  canonicalMission?: CanonicalProductMissionRow;
  gtmQuality: GTMPackQualityRow;
  project: ProjectCard;
}

export interface CreateRunInput {
  idea: string;
  niche?: string;
  depth: RunDepth;
  userId?: string;
  mode?: RunMode;
  targetOrigin?: string;
  providerId?: string;
  backendId?: string;
  modelId?: string;
}

export interface CanonicalProductMissionRow {
  rootMissionId: string;
  status: string;
  currentStage: string;
  selectedProvider: string;
  selectedModel: string;
  authorityScope: {
    grantedAuthorities: string[];
    browserAllowedOrigins: string[];
    publicWebReadOnly: boolean;
  };
  modelVisibleAffordances: string[];
  completedActions: Array<{
    receiptId: string;
    capability: string;
    operation: string;
    status: string;
    materialAction: boolean;
    evidenceRefs: string[];
  }>;
  evidenceRefs: string[];
  terminalAnswer?: string;
  terminalBlocker?: string;
  cleanupStatus: string;
  proofRootId?: string;
  proofRootVerified: boolean;
  replaySideEffectsReexecuted: boolean;
}

export interface CreateFeedbackInput {
  targetType: FeedbackTargetType;
  targetId: string;
  rating: FeedbackRating;
  note?: string;
}

export interface MissionTypeRow {
  id: MissionType;
  label: string;
  description: string;
  status: "enabled" | "disabled" | "lab_only";
  allowedActions: string[];
  allowedTools: string[];
  blackZoneActions: string[];
}

export interface MissionAuthorityEnvelopeRow {
  id: string;
  userId: string;
  missionType: MissionType;
  missionTitle: string;
  missionObjective: string;
  successCriteria: string[];
  mode: MissionMode;
  allowedSystems: string[];
  allowedTools: string[];
  allowedActions: string[];
  forbiddenActions: string[];
  allowedPaths: string[];
  allowedDomains: string[];
  allowedAccounts: string[];
  allowedDataTypes: string[];
  maxDurationMinutes: number;
  maxActions: number;
  maxCostUsd: number;
  maxRecipients: number;
  riskAppetiteScore: number;
  escalationTriggers: string[];
  rollbackPreference: string;
  traceLevel: string;
  emergencyStopEnabled: boolean;
  sourceRunId?: string;
  createdAt: string;
  expiresAt?: string;
  revokedAt?: string;
}

export interface MissionStateRow {
  missionId: string;
  status: MissionStatus;
  currentStep?: string;
  actionCount: number;
  costUsed: number;
  startedAt?: string;
  updatedAt: string;
  endedAt?: string;
}

export interface MissionActionRow {
  id: string;
  missionId: string;
  actionType: string;
  tool: string;
  intent: string;
  target?: string;
  expectedOutput: string;
  reversibility: ReversibilityLevel;
  externality: ExternalityLevel;
  sensitivity: SensitivityLevel;
  estimatedCost: number;
  confidence: MissionConfidenceLevel;
  riskScore: number;
  route: MissionActionRoute;
  evidenceRefs: string[];
  createdAt: string;
  executedAt?: string;
}

export interface MissionArtifactRow {
  id: string;
  missionId: string;
  artifactType: string;
  path: string;
  evidenceRefs: string[];
  status: string;
  createdByActionId?: string;
  canRollback: boolean;
  createdAt: string;
}

export interface MissionTraceEventRow {
  id: string;
  missionId: string;
  eventType: string;
  actor: "sentinel" | "user" | "system";
  actionId?: string;
  summary: string;
  target?: string;
  impact?: string;
  reversible: boolean;
  cost: number;
  timestamp: string;
}

export interface EscalationRequestRow {
  id: string;
  missionId: string;
  actionId: string;
  reason: string;
  userQuestion: string;
  actionPreview: Record<string, string>;
  impactSummary: string;
  options: Array<"approve_once" | "allow_for_this_mission" | "deny" | "take_over">;
  resolution?: "approve_once" | "allow_for_this_mission" | "deny" | "take_over";
  createdAt: string;
  resolvedAt?: string;
}

export interface MissionRecord {
  envelope: MissionAuthorityEnvelopeRow;
  state: MissionStateRow;
  actions: MissionActionRow[];
  artifacts: MissionArtifactRow[];
  traceEvents: MissionTraceEventRow[];
  escalations: EscalationRequestRow[];
  missionType: MissionTypeRow;
  reviewer: {
    ready: boolean;
    issues: Array<{ code: string; severity: "low" | "medium" | "high" | "critical"; message: string }>;
  };
}
