"""
NewsOps Revision 2 - VerificationResult Contract (Pydantic v2).

Encapsulates the outcome of checking an atomic Claim against an Evidence pack,
computing trust badges, validating confidence, and routing edge cases to human review.
"""

from typing import Optional
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
    AliasChoices,
)

from .enums import EvidenceStatus, EvidenceType, TrustBadgeKind
from .claim import Claim
from .evidence import Evidence


class VerificationResult(BaseModel):
    """
    VerificationResult represents the evaluation of a Claim against Evidence.

    Complies with NewsOps Revision 2 Section 7.6 ('The no fake news layer')
    and Part 3 Section 4 Trust Badges.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Core Association & Outcome
    claim_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the Claim evaluated in this verification.",
    )
    status: EvidenceStatus = Field(
        ...,
        description="Result status: supported, contradicted, insufficient_evidence, not_checked.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Verification confidence score in range [0.0, 1.0].",
    )
    rationale: str = Field(
        ...,
        min_length=3,
        validation_alias=AliasChoices("rationale", "confidence_rationale"),
        description="Transparent justification of how evidence supports, contradicts, or fails to prove claim.",
    )

    # Associated Objects & Links
    claim: Optional[Claim] = Field(
        default=None,
        description="Optional embedded Claim model for self-contained verification payloads.",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="List of Evidence items used to determine this verification outcome.",
    )
    primary_evidence_url: Optional[HttpUrl] = Field(
        default=None,
        description="Direct link to primary source if verified (e.g. GitHub API release or vendor doc).",
    )

    # Trust Badging & Review Escalation
    trust_badge: Optional[TrustBadgeKind] = Field(
        default=None,
        description="Public trust badge computed from evidence provenance and status.",
    )
    review_required: bool = Field(
        default=False,
        description="Flag indicating this item requires human review before publishing.",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be within [0.0, 1.0].")
        return round(float(v), 4)

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 3:
            raise ValueError("Verification rationale must be at least 3 characters long.")
        return trimmed

    @model_validator(mode="after")
    def apply_verification_rules_and_badging(self) -> "VerificationResult":
        """
        NewsOps Revision 2 Verification Policies:
        1. If status is CONTRADICTED or INSUFFICIENT_EVIDENCE, review_required is forced to True.
        2. If confidence < 0.7, review_required is forced to True (flag low-confidence items).
        3. Community signal alone cannot substantiate status 'supported'.
        4. Auto-resolve trust_badge if not provided:
           - Primary (API-verified)
           - Vendor-reported
           - Community signal
           - Needs review
        """
        # Rule 1 & 2: Human Review Escalation
        if (
            self.status in (EvidenceStatus.CONTRADICTED, EvidenceStatus.INSUFFICIENT_EVIDENCE)
            or self.confidence < 0.70
        ):
            object.__setattr__(self, "review_required", True)

        # Rule 3: Provenance check on supported claims
        if self.status == EvidenceStatus.SUPPORTED and self.evidence:
            has_substantive = any(
                e.evidence_type in (
                    EvidenceType.PRIMARY_SOURCE,
                    EvidenceType.INDEPENDENT_REPORTING,
                    EvidenceType.SECONDARY_COMMENTARY,
                    EvidenceType.USER_PROVIDED,
                )
                for e in self.evidence
            )
            all_community = all(
                e.evidence_type == EvidenceType.COMMUNITY_SIGNAL
                for e in self.evidence
            )
            if all_community or not has_substantive:
                raise ValueError(
                    "NewsOps Revision 2 Rule: A claim cannot be marked 'supported' "
                    "solely on community_signal evidence."
                )

        # Sync primary_evidence_url if not explicitly set
        if not self.primary_evidence_url and self.evidence:
            for ev in self.evidence:
                if ev.evidence_type == EvidenceType.PRIMARY_SOURCE and ev.status == EvidenceStatus.SUPPORTED:
                    object.__setattr__(self, "primary_evidence_url", ev.evidence_url)
                    break

        # Rule 4: Trust Badge Resolution
        if not self.trust_badge:
            badge = None
            if self.status in (EvidenceStatus.CONTRADICTED, EvidenceStatus.INSUFFICIENT_EVIDENCE):
                badge = TrustBadgeKind.NEEDS_REVIEW
            elif self.status == EvidenceStatus.SUPPORTED:
                has_primary = any(
                    e.evidence_type == EvidenceType.PRIMARY_SOURCE
                    for e in self.evidence
                )
                if has_primary:
                    badge = TrustBadgeKind.PRIMARY_API_VERIFIED
                elif self.claim and self.claim.is_vendor_claim:
                    badge = TrustBadgeKind.VENDOR_REPORTED
                else:
                    badge = TrustBadgeKind.PRIMARY_API_VERIFIED
            elif (
                self.evidence
                and all(e.evidence_type == EvidenceType.COMMUNITY_SIGNAL for e in self.evidence)
            ):
                badge = TrustBadgeKind.COMMUNITY_SIGNAL
            elif self.claim and self.claim.is_vendor_claim:
                badge = TrustBadgeKind.VENDOR_REPORTED
            else:
                badge = TrustBadgeKind.NEEDS_REVIEW

            object.__setattr__(self, "trust_badge", badge)

        return self

    def to_mongo_evidence_item(self) -> dict:
        """
        Maps this result into Member 1's story.evidence item structure:
        {claim, claim_type, evidence_url, evidence_type, status, confidence_rationale}
        """
        first_ev = self.evidence[0] if self.evidence else None
        ev_url = str(self.primary_evidence_url or (first_ev.evidence_url if first_ev else ""))
        ev_type = (first_ev.evidence_type.value if first_ev else EvidenceType.SECONDARY_COMMENTARY.value)
        claim_stmt = self.claim.statement if self.claim else self.claim_id
        claim_type_val = (
            self.claim.claim_type.value
            if self.claim and isinstance(self.claim.claim_type, ClaimType)
            else (str(self.claim.claim_type) if self.claim and self.claim.claim_type else None)
        )

        return {
            "claim": claim_stmt,
            "claim_type": claim_type_val,
            "evidence_url": ev_url,
            "evidence_type": ev_type,
            "status": self.status.value,
            "confidence_rationale": self.rationale,
        }
