from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from sentinel.shared.models import SentinelModel


class EvidenceBindingStatus(StrEnum):
    CHECKED = "checked"
    BLOCKED = "blocked"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class EvidenceBindingVerdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    WEAK_SUPPORT = "WEAK_SUPPORT"
    CONTRADICTED = "CONTRADICTED"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INVENTED_EVIDENCE_REF = "INVENTED_EVIDENCE_REF"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"


class EvidenceBoundClaim(SentinelModel):
    claim_id: str
    claim_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    contradicted_by_refs: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    critical: bool = False


class EvidenceVerificationResult(SentinelModel):
    status: EvidenceBindingStatus
    verdict: EvidenceBindingVerdict
    claims: list[EvidenceBoundClaim] = Field(default_factory=list)
    invented_evidence_refs: list[str] = Field(default_factory=list)
    missing_evidence_claim_ids: list[str] = Field(default_factory=list)
    contradictions: list[dict[str, list[str] | str]] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    can_grant_authority: bool = False
    can_approve_execution: bool = False


class EvidenceVerifier:
    def __init__(self, *, available_evidence_refs: set[str] | list[str] | tuple[str, ...]) -> None:
        self._available_evidence_refs = set(available_evidence_refs)

    def verify_claims(self, claims: list[EvidenceBoundClaim]) -> EvidenceVerificationResult:
        invented_refs = _dedupe(
            [
                ref
                for claim in claims
                for ref in [*claim.evidence_refs, *claim.contradicted_by_refs]
                if ref not in self._available_evidence_refs
            ]
        )
        missing_evidence = [claim.claim_id for claim in claims if claim.critical and not claim.evidence_refs]
        contradictions = [
            {"claim_id": claim.claim_id, "evidence_refs": claim.contradicted_by_refs}
            for claim in claims
            if claim.contradicted_by_refs
        ]
        uncertainty = _dedupe([item for claim in claims for item in claim.uncertainty])

        if invented_refs:
            verdict = EvidenceBindingVerdict.INVENTED_EVIDENCE_REF
            status = EvidenceBindingStatus.BLOCKED
        elif contradictions:
            verdict = EvidenceBindingVerdict.CONTRADICTED
            status = EvidenceBindingStatus.CHECKED
        elif missing_evidence:
            verdict = EvidenceBindingVerdict.MISSING_EVIDENCE
            status = EvidenceBindingStatus.NEEDS_MORE_EVIDENCE
        elif any(not claim.evidence_refs for claim in claims):
            verdict = EvidenceBindingVerdict.WEAK_SUPPORT
            status = EvidenceBindingStatus.CHECKED
        else:
            verdict = EvidenceBindingVerdict.SUPPORTED
            status = EvidenceBindingStatus.CHECKED

        return EvidenceVerificationResult(
            status=status,
            verdict=verdict,
            claims=claims,
            invented_evidence_refs=invented_refs,
            missing_evidence_claim_ids=missing_evidence,
            contradictions=contradictions,
            uncertainty=uncertainty,
            can_grant_authority=False,
            can_approve_execution=False,
        )

    def verify_proposal_claims(
        self,
        proposals: list[dict[str, object]],
    ) -> EvidenceVerificationResult:
        claims = [
            EvidenceBoundClaim(
                claim_id=str(proposal.get("proposal_id") or f"proposal_{index}"),
                claim_summary=str(proposal.get("safe_summary") or proposal.get("objective_summary") or "proposal"),
                evidence_refs=[str(ref) for ref in proposal.get("evidence_refs", []) if ref],
                uncertainty=[str(item) for item in proposal.get("uncertainty", []) if item],
                critical=_proposal_requires_evidence(proposal),
            )
            for index, proposal in enumerate(proposals)
        ]
        if not claims:
            return EvidenceVerificationResult(
                status=EvidenceBindingStatus.CHECKED,
                verdict=EvidenceBindingVerdict.SUPPORTED,
            )
        return self.verify_claims(claims)


def _proposal_requires_evidence(proposal: dict[str, object]) -> bool:
    level = str(proposal.get("action_level_candidate") or "")
    risk = str(proposal.get("risk_class") or "").lower()
    return level not in {"", "L0"} or risk not in {"", "low"}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
