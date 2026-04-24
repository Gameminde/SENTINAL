import { ApprovalStatus, ActionRow, AgentRow, EvidenceRow, FirewallPolicyRow, ProjectCard } from "@/lib/types";

export const agents: AgentRow[] = [
  {
    name: "Opportunity Agent",
    role: "reads CueIdea signals and filters pain, WTP, and competitor complaints",
    status: "complete",
    note: "7 direct signals, 4 adjacent signals, 2 WTP markers.",
  },
  {
    name: "Research Agent",
    role: "adds competitor and market context before any decision",
    status: "running",
    note: "Ranked sources and isolated repeated buyer pain.",
  },
  {
    name: "Debate Orchestrator",
    role: "forces a skeptical pass before GTM output is allowed",
    status: "complete",
    note: "Decision landed on niche down, not build-first.",
  },
  {
    name: "GTM Operator",
    role: "writes the pack only if evidence and risk are acceptable",
    status: "ready",
    note: "Drafts generated. Approval needed for next step.",
  },
  {
    name: "Firewall",
    role: "enforces policy, dry-run, and approval routing",
    status: "reviewing",
    note: "One action blocked, two drafts pending, one folder allowed.",
  },
];

export const evidence: EvidenceRow[] = [
  {
    id: "ev_001",
    source: "Reddit / r/freelance",
    proofTier: "direct",
    summary: "Freelancers repeatedly complain about chasing unpaid invoices and awkward follow-ups.",
    confidence: 92,
    freshness: "2h ago",
    actionRefs: ["A-101", "A-104"],
    quote: "I hate chasing late payments every month.",
    url: "https://example.com/reddit/1",
    details: {
      excerpt: "The pain is recurring, concrete, and tied to a clear workflow breakdown.",
      methodology: "Direct complaint extraction from repeated pain language.",
      tags: ["pain", "invoice", "follow-up"],
    },
  },
  {
    id: "ev_002",
    source: "G2 review cluster",
    proofTier: "adjacent",
    summary: "Users want better relationship-aware reminders, not just generic billing nudges.",
    confidence: 78,
    freshness: "5h ago",
    actionRefs: ["A-101"],
    details: {
      excerpt: "The complaint is adjacent to the buyer pain but still useful for wedge shaping.",
      methodology: "Normalized review complaints and grouped repeated themes.",
      tags: ["competitor gap", "reminders"],
    },
  },
  {
    id: "ev_003",
    source: "Product Hunt comments",
    proofTier: "adjacent",
    summary: "People ask for faster onboarding and less manual setup in billing tools.",
    confidence: 65,
    freshness: "1d ago",
    actionRefs: ["A-102"],
    details: {
      excerpt: "This signal helps the positioning angle but is not direct proof of WTP.",
      methodology: "Comment theme aggregation across launch threads.",
      tags: ["onboarding", "workflow"],
    },
  },
  {
    id: "ev_004",
    source: "StackOverflow / GitHub",
    proofTier: "supporting",
    summary: "Automation is desirable, but integration complexity remains a recurring concern.",
    confidence: 61,
    freshness: "1d ago",
    actionRefs: ["A-102"],
    details: {
      excerpt: "Supporting evidence only; useful for execution risk.",
      methodology: "Cross-source technical friction scan.",
      tags: ["integration", "risk"],
    },
  },
  {
    id: "ev_005",
    source: "Reddit / r/freelance",
    proofTier: "direct",
    summary: "At least one user says they would pay for automated payment reminders if it saved awkward follow-ups.",
    confidence: 88,
    freshness: "5h ago",
    actionRefs: ["A-101", "A-104"],
    quote: "I would pay for something that chases invoices without sounding robotic.",
    details: {
      excerpt: "Strong WTP phrasing tied to a painful, repeated workflow.",
      methodology: "Direct willingness-to-pay language detection.",
      tags: ["wtp", "pricing"],
    },
  },
  {
    id: "ev_006",
    source: "Hacker News",
    proofTier: "adjacent",
    summary: "Discussion around manual ops and workflow automation suggests the category is timely.",
    confidence: 58,
    freshness: "1d ago",
    actionRefs: ["A-103"],
    details: {
      excerpt: "Timing signal only; no product-specific proof.",
      methodology: "Trend and discussion context extraction.",
      tags: ["trend", "timing"],
    },
  },
  {
    id: "ev_007",
    source: "Competitor complaints",
    proofTier: "direct",
    summary: "Existing tools track invoices but do not handle relationship-aware reminders.",
    confidence: 90,
    freshness: "2h ago",
    actionRefs: ["A-103"],
    details: {
      excerpt: "This is a clean wedge signal and feeds the competitor gap section.",
      methodology: "Complaint cluster from competitor review extraction.",
      tags: ["competitor complaint", "gap"],
    },
  },
];

export const actions: ActionRow[] = [
  {
    id: "A-101",
    tool: "prepare_email_draft",
    title: "Draft outreach to validate WTP",
    intent: "Validate interest from target ICP",
    risk: "medium",
    approvalStatus: "pending",
    requiresApproval: true,
    dryRun: {
      whyNeeded: "Test willingness to pay before broader build work.",
      preview: {
        subject: "Quick question about invoice follow-ups",
        body: "I'm validating a lightweight workflow for chasing late invoices. Would you be open to 10 minutes of feedback?",
      },
      evidenceUsed: ["ev_001", "ev_005"],
    },
    sourceNotes: ["Direct pain language", "Direct WTP phrasing"],
  },
  {
    id: "A-102",
    tool: "create_file",
    title: "Write GTM Pack sections",
    intent: "Persist a local first-customer pack",
    risk: "low",
    approvalStatus: "not_required",
    requiresApproval: false,
    dryRun: {
      whyNeeded: "Create a portable pack for review and handoff.",
      preview: {
        path: "./data/generated_projects/ai-invoice-chasing/00_VERDICT.md",
        content: "Niche down first, build only after WTP proof.",
      },
      evidenceUsed: ["ev_001", "ev_002", "ev_005"],
    },
    sourceNotes: ["Allowed path only", "Evidence referenced"],
  },
  {
    id: "A-103",
    tool: "send_email",
    title: "Send pilot invite",
    intent: "External contact",
    risk: "high",
    approvalStatus: "blocked",
    blocked: true,
    requiresApproval: true,
    dryRun: {
      whyNeeded: "Blocked in v1; drafts only.",
      preview: {
        to: "not executed",
        subject: "Pilot invitation",
        body: "Would you like to try this?",
      },
      evidenceUsed: ["ev_007"],
    },
    sourceNotes: ["V1-disabled action", "Would bypass policy"],
  },
  {
    id: "A-104",
    tool: "create_folder",
    title: "Create generated project folder",
    intent: "Store local project docs",
    risk: "low",
    approvalStatus: "approved",
    requiresApproval: false,
    dryRun: {
      whyNeeded: "Create the project root before writing docs.",
      preview: {
        path: "./data/generated_projects/ai-invoice-chasing",
      },
      evidenceUsed: ["ev_001", "ev_005"],
    },
    sourceNotes: ["Allowed path only", "Project root"],
  },
];

export const firewallPolicies: FirewallPolicyRow[] = [
  { tool: "create_folder", risk: "low", autoAllowed: true, approval: false, disabled: false, scope: "./data/generated_projects" },
  { tool: "create_file", risk: "low", autoAllowed: true, approval: false, disabled: false, scope: "./data/generated_projects" },
  { tool: "prepare_email_draft", risk: "medium", autoAllowed: false, approval: true, disabled: false, scope: "draft-only" },
  { tool: "send_email", risk: "high", autoAllowed: false, approval: true, disabled: true, scope: "disabled in v1" },
  { tool: "browser_submit_form", risk: "high", autoAllowed: false, approval: true, disabled: true, scope: "disabled in v1" },
  { tool: "run_shell_command", risk: "critical", autoAllowed: false, approval: true, disabled: true, scope: "disabled in v1" },
  { tool: "modify_code", risk: "critical", autoAllowed: false, approval: true, disabled: true, scope: "disabled in v1" },
];

export const projects: ProjectCard[] = [
  {
    id: "ai-invoice-chasing",
    name: "AI Invoice Chasing",
    status: "Pack generated",
    updatedAt: "18 May",
    description: "Narrow wedge for freelancers and small agencies with recurring late-payment pain.",
    files: ["00_VERDICT.md", "01_EVIDENCE.md", "02_ICP.md", "05_OUTREACH_MESSAGES.md"],
  },
  {
    id: "client-followup",
    name: "Client Follow-up OS",
    status: "Needs approval",
    updatedAt: "17 May",
    description: "Draft-only outreach pack pending approval before any external contact.",
    files: ["00_VERDICT.md", "04_LANDING_PAGE_COPY.md", "06_INTERVIEW_SCRIPT.md"],
  },
  {
    id: "service-ops",
    name: "Service Ops Gap",
    status: "Monitoring",
    updatedAt: "16 May",
    description: "Competitor weakness cluster being tracked for timing and positioning.",
    files: ["08_WATCHLIST.md", "trace.json"],
  },
];

export const runStages = [
  { key: "evidence", label: "Evidence", detail: "7/7 collected" },
  { key: "debate", label: "Debate", detail: "Complete" },
  { key: "pack", label: "GTM Pack", detail: "Generated" },
  { key: "firewall", label: "Firewall", detail: "Reviewing" },
  { key: "approval", label: "Approval", detail: "Pending" },
];

export const runSummary = {
  title: "Expand ACME in Manufacturing Segment",
  status: "Run in progress",
  runId: "GR-2025-05-18-1427",
  startedAt: "18 May 2025, 2:27 PM",
  verdict: "Proceed with guardrails",
  confidence: 78,
  riskScore: 36,
  riskLabel: "Moderate",
};

export const executionColumns = [
  {
    title: "Ideas",
    count: 6,
    cards: [
      { title: "AI Invoice Chasing", meta: "78", description: "Strong direct pain and clean WTP phrasing." },
      { title: "Client Follow-up OS", meta: "65", description: "Promising but still narrow on buyer reachability." },
      { title: "Public Sector Expansion", meta: "41", description: "Too broad for v1 execution." },
    ],
  },
  {
    title: "Packs",
    count: 4,
    cards: [
      { title: "AI Invoice Chasing Pack", meta: "Generated 18 May", description: "Includes verdict, evidence, ICP, outreach and roadmap." },
      { title: "Client Follow-up Brief", meta: "Draft", description: "Waiting on WTP proof before file creation." },
    ],
  },
  {
    title: "Needs Approval",
    count: 3,
    cards: [
      { title: "Launch ABM Campaign", meta: "A-101", description: "Medium risk and approval required." },
      { title: "LinkedIn Sponsored Content", meta: "A-102", description: "Drafted but not executed." },
      { title: "Discount > 15%", meta: "A-103", description: "Blocked by policy in v1." },
    ],
  },
  {
    title: "Drafts",
    count: 2,
    cards: [
      { title: "Email: Intro to ACME Leadership", meta: "Draft", description: "Evidence-backed, user approval pending." },
      { title: "LinkedIn Message", meta: "Draft", description: "Short, narrow, and referenced to direct pain." },
    ],
  },
  {
    title: "Done",
    count: 5,
    cards: [
      { title: "Project Folder Created", meta: "18 May", description: "Safe file write inside generated projects." },
      { title: "Research Brief", meta: "Completed", description: "Ranked evidence and competitor gaps." },
    ],
  },
];
