"""
NewsOps Revision 2 - Story Models & MongoDB Document Schemas.

Complies with NewsOps Revision 2 Section 6 (stories collection schema)
and Section 9 (Stories endpoints: GET /stories, GET /stories/{id}, POST /stories/{id}/feedback).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from ..contracts.enums import TrustBadgeKind
from ..contracts.analysis import StoryAnalysis
from ..contracts.evidence import Evidence


class ClusterMember(BaseModel):
    """Article member within a deduplicated story cluster."""
    model_config = ConfigDict(extra="ignore")

    article_id: str = Field(default="", description="Unique article ID")
    url: str = Field(..., description="Canonical article or source URL")
    title: str = Field(..., description="Article headline")
    publisher: str = Field(..., description="Source publication or domain")
    trust_tier: int = Field(default=2, ge=1, le=3, description="1=primary, 2=vendor/secondary, 3=community")


class StoryFeedback(BaseModel):
    """Feedback submitted on a story by users."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    type: str = Field(..., pattern="^(relevant|irrelevant|correction)$", description="Feedback classification")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Optional user commentary")


class Story(BaseModel):
    """
    MongoDB Story Document and API representation.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        str_strip_whitespace=True,
    )

    id: str = Field(default="", alias="_id", description="Unique story ID (UUID or slug)")
    title: str = Field(..., min_length=3, description="Story headline")
    summary: Optional[str] = Field(default=None, description="Short executive summary")
    source_domain: Optional[str] = Field(default=None, description="Primary publisher domain")
    source_url: Optional[str] = Field(default=None, description="Canonical source URL")
    published_at: Optional[datetime] = Field(default=None, description="Publication timestamp")
    room_key: Optional[str] = Field(default=None, description="Associated primary room key")
    topics: List[str] = Field(default_factory=list, description="Associated topic taxonomy tags")
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rank_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Calculated relevance & ranking score")
    confidence: Optional[float] = Field(default=None, description="Analysis confidence score")
    impact: Optional[str] = Field(default=None, description="Ecosystem impact assessment")
    reason_codes: List[str] = Field(default_factory=list, description="Explainable ranking justification codes")
    members: List[ClusterMember] = Field(default_factory=list, description="Articles clustered into this story")
    entities: List[str] = Field(default_factory=list, description="Extracted packages/repos for dependency matching")
    tool_ids: List[str] = Field(default_factory=list, description="Associated tool IDs")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Evidence items linked to story claims")
    claims: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted factual claims")
    analysis: Optional[StoryAnalysis] = Field(default=None, description="Analyst agent narrative analysis")
    review_flag: bool = Field(default=False, description="Flag indicating human review is required")
    badge: Optional[Union[TrustBadgeKind, str]] = Field(default=None, description="Primary trust badge displayed in UI")
    trust_badge: Optional[str] = Field(default=None, description="String representation of trust badge")
    install_command: Optional[str] = Field(default=None, description="Verbatim install command extracted from README")
    install_commit: Optional[str] = Field(default=None, description="Git commit SHA from which install command was extracted")
    commit_sha: Optional[str] = Field(default=None, description="Commit SHA alias")
    risk_flags: List[str] = Field(default_factory=list, description="Security risk flags detected in install commands")
    seeded: bool = Field(default=False, description="Whether story was generated via seed/offline fixture")

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id
        return d


class StoryListResponse(BaseModel):
    """Paginated list of stories."""
    items: List[Story]
    total: int
    limit: int
    skip: int
