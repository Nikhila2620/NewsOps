"""
NewsOps Revision 2 - Task Models & MongoDB Document Schemas.

Complies with NewsOps Revision 2 Section 6 (tasks collection schema)
and Section 9 (Tasks endpoints: POST /tasks, GET /tasks/{id}, GET /tasks).
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """Authoritative task status values (NewsOps Revision 2 Section 6)."""
    QUEUED = "queued"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


class TaskCreate(BaseModel):
    """
    Request payload for POST /api/v1/tasks (NewsOps Revision 2 Section 9).
    """
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    request: str = Field(..., min_length=3, description="Task request description or query")
    since_hours: int = Field(default=24, ge=1, le=168, description="Time window in hours")
    topics: List[str] = Field(default_factory=list, description="Target topics (e.g. ['aiml', 'cloud'])")
    room_id: Optional[str] = Field(default=None, description="Optional target room key or ID")
    approval_required: bool = Field(default=True, description="Whether human review gate is required")


class Task(BaseModel):
    """
    MongoDB Task Document and Detailed API Response Model.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str = Field(
        default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}",
        alias="_id",
        description="Unique task identifier",
    )
    requester_id: str = Field(default="system", description="User ID or agent requesting the task")
    room_key: Optional[str] = Field(default=None, description="Target room key (e.g. 'aiml', 'cloud')")
    request: str = Field(..., description="Query or instructions")
    since_hours: int = Field(default=24)
    topics: List[str] = Field(default_factory=list)
    status: TaskStatus = Field(default=TaskStatus.QUEUED, description="Backend controlled status")
    stage: str = Field(default="queued", description="Current execution stage")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Task progress indicator (0.0 to 1.0)")
    error_safe: Optional[str] = Field(default=None, description="Safe error message without secrets or traces")
    approval_required: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id
        d["status"] = self.status.value
        return d


class TaskCreatedResponse(BaseModel):
    """Lightweight response for POST /api/v1/tasks."""
    task_id: str
    status: str
