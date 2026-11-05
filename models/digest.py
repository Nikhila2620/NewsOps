"""
NewsOps Revision 2 - Digest & Approval Models (Pydantic v2).

Complies with NewsOps Revision 2 Section 6 (digests collection schema)
and Section 9 (Digests and approval endpoints: GET /digests, POST /digests/{id}/approve,
POST /digests/{id}/reject, POST /digests/{id}/publish).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DigestStatus(str, Enum):
    """Lifecycle state of a digest."""
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class DigestItem(BaseModel):
    """An individual story item positioned within a digest."""
    model_config = ConfigDict(extra="ignore")

    story_id: str = Field(..., description="Referenced story ID")
    position: int = Field(default=0, ge=0, description="Ordering index in digest")
    editor_note: Optional[str] = Field(default=None, description="Editorial annotation or comment")
    included: bool = Field(default=True, description="Whether item is selected for final publication")


class ApprovalRecord(BaseModel):
    """Audit record for human review decisions."""
    model_config = ConfigDict(extra="ignore")

    reviewer: str = Field(..., description="Chat handle or user ID of reviewer")
    decision: str = Field(..., description="Decision: 'approved', 'rejected', or 'request-changes'")
    comment: Optional[str] = Field(default=None, description="Optional reviewer remarks")
    source: str = Field(default="dashboard", description="'dashboard' or 'chat'")
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalAction(BaseModel):
    """Payload for review decision actions."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    comment: Optional[str] = Field(default=None, max_length=1000, description="Review remarks")


class Digest(BaseModel):
    """
    MongoDB Digest Document and Detailed API Model.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str = Field(default="", alias="_id", description="Unique digest ID")
    room_key: str = Field(..., description="Room key (e.g. 'aiml', 'cloud', 'security')")
    task_id: Optional[str] = Field(default=None, description="Triggering task ID")
    version: int = Field(default=1, ge=1, description="Digest revision number")
    status: DigestStatus = Field(default=DigestStatus.DRAFT, description="Approval gate status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = Field(default=None, description="Timestamp when published to room/inbox")
    items: List[DigestItem] = Field(default_factory=list, description="Curated story items")
    approvals: List[ApprovalRecord] = Field(default_factory=list, description="Historical approval audit trail")

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id
        d["status"] = self.status.value
        return d
