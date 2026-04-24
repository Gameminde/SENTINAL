from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict(StrEnum):
    BUILD = "build"
    PIVOT = "pivot"
    NICHE_DOWN = "niche_down"
    KILL = "kill"
    RESEARCH_MORE = "research_more"


class EvidenceType(StrEnum):
    PAIN = "pain"
    WTP = "wtp"
    COMPETITOR_COMPLAINT = "competitor_complaint"
    TREND = "trend"
    PRICING = "pricing"
    COMMUNITY_SIGNAL = "community_signal"
    DIRECT_PROOF = "direct_proof"
    ADJACENT_PROOF = "adjacent_proof"


class ApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class TraceEventType(StrEnum):
    RUN_STARTED = "run_started"
    EVIDENCE_RECORDED = "evidence_recorded"
    DECISION_CREATED = "decision_created"
    ACTION_PROPOSED = "action_proposed"
    FIREWALL_REVIEWED = "firewall_reviewed"
    APPROVAL_RECORDED = "approval_recorded"
    ACTION_EXECUTED = "action_executed"
    ASSET_GENERATED = "asset_generated"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"

