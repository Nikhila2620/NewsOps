"""
NewsOps Revision 2 - Evidence Contract (Pydantic v2).

Represents a verifiable piece of evidence supporting or refuting an atomic claim,
adhering strictly to NewsOps Revision 2 provenance rules and Member 1 database alignment.
"""

from datetime import datetime, timezone
from typing import Any, Optional, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
    AliasChoices,
)

from .enums import EvidenceStatus, EvidenceType, ClaimType


class Evidence(BaseModel):
    """
    Evidence model representing factual artifacts verified against external sources.

    Complies with NewsOps Revision 2 Section 6 (stories.evidence schema) and Section 7.6.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Required Fields
    evidence_url: HttpUrl = Field(
        ...,
        validation_alias=AliasChoices("evidence_url", "url"),
        description="Authoritative, accessible HTTP/HTTPS URL of the evidence artifact.",
    )
    evidence_type: EvidenceType = Field(
        ...,
        validation_alias=AliasChoices("evidence_type", "type"),
        description="Provenance classification tier (primary_source, independent_reporting, etc.).",
    )
    source_reference: str = Field(
        ...,
        min_length=1,
        max_length=500,
        validation_alias=AliasChoices("source_reference", "source_ref", "source"),
        description="Factual source reference (e.g. 'GitHub API v3 release tag v2.4.0', 'OSV Advisory GHSA-xxxx').",
    )

    # Status & Confidence
    status: EvidenceStatus = Field(
        default=EvidenceStatus.NOT_CHECKED,
        description="Evaluation status: supported, contradicted, insufficient_evidence, not_checked.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score in [0.0, 1.0]. Validated against status and provenance tier.",
    )
    confidence_rationale: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("confidence_rationale", "rationale"),
        description="Detailed explanation of the confidence level and status determination.",
    )

    # Optional / Associated Claim Metadata (aligned with Member 1's story.evidence document)
    claim: Optional[str] = Field(
        default=None,
        description="The atomic claim or assertion statement evaluated by this evidence.",
    )
    claim_type: Optional[Union[ClaimType, str]] = Field(
        default=None,
        description="Category of the claim (e.g. version, benchmark, capability, license).",
    )
    claim_id: Optional[str] = Field(
        default=None,
        description="Unique identifier of the associated Claim model, if linked.",
    )
    excerpt: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Untrusted quotation or data snippet extracted from the evidence source.",
    )
    retrieved_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this evidence artifact was fetched or checked.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific metadata (e.g. commit SHA, stars count, package name).",
    )

    @field_validator("source_reference")
    @classmethod
    def validate_source_reference(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("source_reference cannot be empty or purely whitespace.")
        return trimmed

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be strictly between 0.0 and 1.0 inclusive.")
        return round(float(v), 4)

    @model_validator(mode="after")
    def validate_status_and_tier_consistency(self) -> "Evidence":
        """
        Enforce NewsOps Revision 2 provenance constraints:
        1. Community signal (Reddit, HN) is discovery only, cannot independently mark a claim as 'supported'.
        2. Insufficient evidence must have confidence <= 0.5.
        3. Contradicted claims require a non-empty rationale explaining the discrepancy.
        """
        # Rule 1: Community signal cannot prove a claim
        if self.evidence_type == EvidenceType.COMMUNITY_SIGNAL and self.status == EvidenceStatus.SUPPORTED:
            raise ValueError(
                "NewsOps Revision 2 Rule: 'community_signal' is for discovery only and "
                "cannot independently yield status 'supported'."
            )

        # Rule 2: Insufficient evidence confidence ceiling
        if self.status == EvidenceStatus.INSUFFICIENT_EVIDENCE and self.confidence > 0.5:
            # Normalize confidence for insufficient evidence to reflect uncertainty
            self.confidence = 0.5

        # Rule 3: Contradiction rationale requirement
        if self.status == EvidenceStatus.CONTRADICTED:
            if not self.confidence_rationale or not self.confidence_rationale.strip():
                raise ValueError(
                    "Contradicted evidence must include a non-empty 'confidence_rationale' explaining the conflict."
                )

        return self

    def to_mongo_dict(self) -> dict[str, Any]:
        """
        Serializes into Member 1's exact MongoDB story document evidence format:
        {claim, claim_type, evidence_url, evidence_type, status, confidence_rationale}
        """
        claim_type_val = (
            self.claim_type.value
            if isinstance(self.claim_type, ClaimType)
            else (str(self.claim_type) if self.claim_type else None)
        )
        return {
            "claim": self.claim,
            "claim_type": claim_type_val,
            "evidence_url": str(self.evidence_url),
            "evidence_type": self.evidence_type.value,
            "status": self.status.value,
            "confidence_rationale": self.confidence_rationale,
        }
