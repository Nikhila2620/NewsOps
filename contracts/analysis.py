"""
NewsOps Revision 2 - StoryAnalysis Contract (Pydantic v2).

Represents the narrative, contextual, and practical evaluation of a story written
by the Analyst agent, strictly separating factual summary from impact and unknowns.
"""

from datetime import datetime, timezone
from typing import Any, Optional, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    AliasChoices,
)

from .enums import AnalysisStatus


class StoryAnalysis(BaseModel):
    """
    Substantive analysis produced by the Analyst agent for a Story cluster.

    Matches Member 1's MongoDB schema:
    analysis: {
        summary, why_it_matters, practical_impact, affected_users[], caveats[],
        unknowns[], submitted_by, submitted_at, status
    }
    """
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Narrative Content (Separating Facts, Impact, and Practical Use)
    summary: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Factual, concise summary of the development or tool release.",
    )
    why_it_matters: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Strategic significance and broader ecosystem context.",
    )
    practical_impact: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        validation_alias=AliasChoices("practical_impact", "daily_life_use"),
        description="Concrete daily-life developer use: how this helps in day-to-day engineering work.",
    )

    # Categorization & Boundaries
    affected_users: list[str] = Field(
        ...,
        min_length=1,
        description="Developer roles, tech stacks, or personas impacted (e.g. ['python-devs', 'mlops-engineers']).",
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Known limitations, trade-offs, constraints, or preliminary performance caveats.",
    )
    unknowns: list[str] = Field(
        default_factory=list,
        description="Explicit uncertainties, missing benchmark proofs, or unanswered questions.",
    )

    # Submission Metadata (Member 1 Alignment)
    submitted_by: str = Field(
        default="newsops-analyst",
        description="Agent or user identifier submitting the analysis.",
    )
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when analysis was generated.",
    )
    status: Union[AnalysisStatus, str] = Field(
        default=AnalysisStatus.COMPLETED,
        description="Analysis lifecycle state: completed, review_required, needs_revision, draft.",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional subjective analytical confidence score in range [0.0, 1.0].",
    )

    @field_validator("summary", "why_it_matters", "practical_impact")
    @classmethod
    def validate_text_sections(cls, v: str, info) -> str:
        trimmed = v.strip()
        if len(trimmed) < 10:
            raise ValueError(f"Field '{info.field_name}' must be at least 10 characters.")
        return trimmed

    @field_validator("affected_users")
    @classmethod
    def validate_affected_users(cls, v: list[str]) -> list[str]:
        cleaned = [u.strip() for u in v if u.strip()]
        if not cleaned:
            raise ValueError("affected_users must contain at least one non-empty persona.")
        return cleaned

    @field_validator("confidence")
    @classmethod
    def validate_confidence_score(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if not (0.0 <= v <= 1.0):
                raise ValueError("Confidence must be between 0.0 and 1.0.")
            return round(float(v), 4)
        return None

    @model_validator(mode="after")
    def ensure_utc_timestamp(self) -> "StoryAnalysis":
        if self.submitted_at and self.submitted_at.tzinfo is None:
            self.submitted_at = self.submitted_at.replace(tzinfo=timezone.utc)
        return self

    def to_mongo_dict(self) -> dict[str, Any]:
        """
        Serializes into Member 1's exact MongoDB story document analysis format:
        {
            summary, why_it_matters, practical_impact, affected_users, caveats,
            unknowns, submitted_by, submitted_at, status
        }
        """
        status_val = self.status.value if isinstance(self.status, AnalysisStatus) else str(self.status)
        return {
            "summary": self.summary,
            "why_it_matters": self.why_it_matters,
            "practical_impact": self.practical_impact,
            "affected_users": self.affected_users,
            "caveats": self.caveats,
            "unknowns": self.unknowns,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at.isoformat(),
            "status": status_val,
        }
