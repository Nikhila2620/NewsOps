"""
NewsOps Revision 2 - Evidence Evaluator.

Evaluates claims against available evidence and applies trust rules:
- community_signal cannot yield status=supported
- contradicted requires non-empty confidence_rationale
- review_required auto-escalates when confidence < 0.70 or contradicted
"""

from typing import List
from ..contracts.claim import Claim
from ..contracts.enums import ClaimType, EvidenceStatus, EvidenceType
from ..contracts.evidence import Evidence
from ..contracts.verification import VerificationResult


def evaluate_claim(
    claim: Claim,
    available_evidence: List[Evidence],
    trust_tier: int = 2,
) -> VerificationResult:
    """
    Evaluate a single claim against available evidence.
    """
    cid = getattr(claim, "claim_id", getattr(claim, "id", "claim-unknown"))
    if not available_evidence:
        return VerificationResult(
            claim_id=cid,
            status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
            confidence=0.3,
            rationale="No evidence available for evaluation.",
            evidence=[],
            review_required=True,
        )

    TYPE_WEIGHTS = {
        EvidenceType.PRIMARY_SOURCE: 1.0,
        EvidenceType.INDEPENDENT_REPORTING: 0.80,
        EvidenceType.SECONDARY_COMMENTARY: 0.55,
        EvidenceType.COMMUNITY_SIGNAL: 0.30,
        EvidenceType.USER_PROVIDED: 0.25,
    }

    supported_weight = 0.0
    contradicted_weight = 0.0

    for ev in available_evidence:
        weight = TYPE_WEIGHTS.get(ev.evidence_type, 0.5)
        # community_signal cannot support
        if ev.evidence_type == EvidenceType.COMMUNITY_SIGNAL:
            if ev.status == EvidenceStatus.SUPPORTED:
                supported_weight += weight * 0.4
            elif ev.status == EvidenceStatus.CONTRADICTED:
                contradicted_weight += weight
        elif ev.status == EvidenceStatus.SUPPORTED:
            supported_weight += weight
        elif ev.status == EvidenceStatus.CONTRADICTED:
            contradicted_weight += weight

    total_weight = supported_weight + contradicted_weight

    if total_weight == 0:
        final_status = EvidenceStatus.INSUFFICIENT_EVIDENCE
        confidence = 0.35
        rationale = "Evidence found but no supported or contradicted signals detected."
    elif supported_weight > contradicted_weight * 1.5:
        all_community = all(e.evidence_type == EvidenceType.COMMUNITY_SIGNAL for e in available_evidence)
        if all_community:
            final_status = EvidenceStatus.INSUFFICIENT_EVIDENCE
            confidence = 0.45
            rationale = "Community signals alone cannot verify claim as supported without primary or independent source."
        else:
            final_status = EvidenceStatus.SUPPORTED
            confidence = min(0.95, 0.50 + (supported_weight / (total_weight + 0.01)) * 0.45)
            rationale = f"Evidence supports claim: {supported_weight:.2f} support weight vs {contradicted_weight:.2f} contradiction weight."
    elif contradicted_weight > supported_weight:
        final_status = EvidenceStatus.CONTRADICTED
        confidence = min(0.90, 0.50 + (contradicted_weight / (total_weight + 0.01)) * 0.40)
        rationale = f"Evidence contradicts claim: {contradicted_weight:.2f} contradiction weight vs {supported_weight:.2f} support weight."
    else:
        final_status = EvidenceStatus.INSUFFICIENT_EVIDENCE
        confidence = 0.45
        rationale = f"Mixed signals: insufficient decisive evidence (support={supported_weight:.2f}, contradict={contradicted_weight:.2f})."

    # Trust tier adjustment
    if trust_tier == 1:
        confidence = min(0.98, confidence * 1.1)
    elif trust_tier == 3:
        confidence = confidence * 0.85

    confidence = round(confidence, 3)

    return VerificationResult(
        claim_id=cid,
        status=final_status,
        confidence=confidence,
        rationale=rationale,
        evidence=available_evidence,
        review_required=confidence < 0.70 or final_status in (EvidenceStatus.CONTRADICTED, EvidenceStatus.INSUFFICIENT_EVIDENCE),
    )


def evaluate_story(
    story_id: str,
    claims: List[Claim],
    evidence_pool: List[Evidence],
    trust_tier: int = 2,
) -> List[VerificationResult]:
    """Evaluate all claims for a story against the evidence pool."""
    results = []
    for claim in claims:
        result = evaluate_claim(claim, evidence_pool, trust_tier)
        results.append(result)
    return results
