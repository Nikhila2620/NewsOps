"""
NewsOps Revision 2 - AnalysisSubmission Contract (Pydantic v2).

The authoritative payload model accepted by:
POST /api/v1/agent/stories/{id}/analysis

Implements schema validation, rejection of unsourced or malformed claims,
confidence aggregation, and seamless mapping to Member 1's MongoDB stories collection.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    AliasChoices,
)

from .enums import EvidenceStatus, EvidenceType
from .evidence import Evidence
from .claim import Claim
from .analysis import StoryAnalysis
from .verification import VerificationResult


class AnalysisSubmission(BaseModel):
    """
    Submission payload for POST /api/v1/agent/stories/{id}/analysis.

    Complies with NewsOps Revision 2 Section 7.8 and Section 9 (Agent-facing API).
    Enforces that all analyst findings are sourced, valid, and properly flagged.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Context & Target Story
    story_id: Optional[str] = Field(
        default=None,
        description="ID of the story being analyzed. Validated against URL path parameter {id}.",
    )

    # Narrative Analysis (Required)
    analysis: StoryAnalysis = Field(
        ...,
        description="The structured StoryAnalysis containing summary, impact, and developer context.",
    )

    # Claims, Evidence, and Verification Results
    claims: list[Claim] = Field(
        default_factory=list,
        description="Atomic factual claims extracted by the Analyst agent.",
    )
    verification_results: list[VerificationResult] = Field(
        default_factory=list,
        description="Evaluations linking extracted claims to evidence artifacts.",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Direct evidence items provided with this submission.",
    )

    # Confidence & Gate Routing
    overall_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("overall_confidence", "confidence_score", "confidence"),
        description="Aggregated confidence score in range [0.0, 1.0]. Auto-computed if omitted.",
    )
    review_required: bool = Field(
        default=False,
        validation_alias=AliasChoices("review_required", "review_flag"),
        description="True if human gatekeeper approval is required before story publication.",
    )

    # Submission Provenance
    agent_id: str = Field(
        default="newsops-analyst",
        validation_alias=AliasChoices("agent_id", "submitted_by"),
        description="Identifier of the Analyst agent submitting this analysis.",
    )
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of submission.",
    )

    @field_validator("overall_confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Overall confidence must be within [0.0, 1.0].")
        return round(float(v), 4)

    @model_validator(mode="after")
    def validate_submission_integrity(self) -> "AnalysisSubmission":
        """
        NewsOps Revision 2 Submission Rules:
        1. Reject unsourced output: If claims are extracted, there must be evidence or verification results.
        2. Escalation gate: If any verification result requires review, or confidence < 0.70,
           or any claim is contradicted / insufficient_evidence, review_required must be True.
        3. Aggregated confidence: If overall_confidence was left at default 1.0 and verification
           results exist, compute the composite confidence from verification results.
        """
        # Rule 1: Sourcing check
        total_evidence_count = len(self.evidence) + sum(len(vr.evidence) for vr in self.verification_results)
        if self.claims and total_evidence_count == 0 and not self.verification_results:
            raise ValueError(
                "NewsOps Revision 2 Rule: Submission rejected because claims were provided "
                "without supporting evidence or verification results (unsourced output)."
            )

        # Rule 2: Compute composite confidence if results exist
        if self.verification_results:
            conf_scores = [vr.confidence for vr in self.verification_results]
            avg_conf = sum(conf_scores) / len(conf_scores)
            if self.overall_confidence == 1.0 and avg_conf < 1.0:
                object.__setattr__(self, "overall_confidence", round(avg_conf, 4))

        # Rule 3: Human review escalation
        any_review_needed = any(vr.review_required for vr in self.verification_results)
        any_contradicted_or_insufficient = any(
            vr.status in (EvidenceStatus.CONTRADICTED, EvidenceStatus.INSUFFICIENT_EVIDENCE)
            for vr in self.verification_results
        ) or any(
            e.status in (EvidenceStatus.CONTRADICTED, EvidenceStatus.INSUFFICIENT_EVIDENCE)
            for e in self.evidence
        )
        low_confidence = self.overall_confidence < 0.70

        if any_review_needed or any_contradicted_or_insufficient or low_confidence:
            object.__setattr__(self, "review_required", True)

        # Keep agent_id and analysis.submitted_by in sync
        if self.agent_id and self.analysis.submitted_by == "newsops-analyst":
            object.__setattr__(self.analysis, "submitted_by", self.agent_id)

        return self

    def collect_all_evidence(self) -> list[Evidence]:
        """
        Collects all unique Evidence items from both top-level evidence and verification_results.
        """
        seen_urls = set()
        collected = []

        # 1. Top-level evidence
        for ev in self.evidence:
            url_str = str(ev.evidence_url)
            if url_str not in seen_urls:
                seen_urls.add(url_str)
                collected.append(ev)

        # 2. Verification results evidence
        for vr in self.verification_results:
            for ev in vr.evidence:
                url_str = str(ev.evidence_url)
                if url_str not in seen_urls:
                    seen_urls.add(url_str)
                    collected.append(ev)

        return collected

    def to_story_update(self) -> dict[str, Any]:
        """
        Generates the exact update payload for Member 1's MongoDB 'stories' collection.

        Stories document schema in MongoDB (NewsOps Revision 2 Section 6):
        {
            "analysis": {
                "summary": ...,
                "why_it_matters": ...,
                "practical_impact": ...,
                "affected_users": [...],
                "caveats": [...],
                "unknowns": [...],
                "submitted_by": ...,
                "submitted_at": ...,
                "status": ...
            },
            "evidence": [
                {
                    "claim": ...,
                    "claim_type": ...,
                    "evidence_url": ...,
                    "evidence_type": ...,
                    "status": ...,
                    "confidence_rationale": ...
                }
            ],
            "review_flag": bool,
            "last_updated_at": ISO-8601 UTC string
        }
        """
        mongo_evidence_list: list[dict[str, Any]] = []

        # From verification results (preferred rich pairing)
        for vr in self.verification_results:
            mongo_evidence_list.append(vr.to_mongo_evidence_item())

        # Plus any additional top-level evidence not already added
        existing_urls = {item["evidence_url"] for item in mongo_evidence_list}
        for ev in self.evidence:
            ev_dict = ev.to_mongo_dict()
            if ev_dict["evidence_url"] not in existing_urls:
                mongo_evidence_list.append(ev_dict)
                existing_urls.add(ev_dict["evidence_url"])

        return {
            "analysis": self.analysis.to_mongo_dict(),
            "evidence": mongo_evidence_list,
            "review_flag": self.review_required,
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
        }
