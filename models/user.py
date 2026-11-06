"""
NewsOps Revision 2 - User & Profile Models (Pydantic v2).

Complies with NewsOps Revision 2 Section 6 (users collection schema)
and Section 9 (Identity and profile API).
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpdate(BaseModel):
    """Payload for updating user preferences."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    topics: Optional[List[str]] = Field(default=None, description="Preferred topics (e.g. ['aiml', 'cloud'])")
    blocked_topics: Optional[List[str]] = Field(default=None, description="Topics to suppress")
    experience: Optional[str] = Field(default=None, description="Experience level (junior, mid, senior, lead, principal)")
    priorities: Optional[List[str]] = Field(default=None, description="High-priority keywords/tags")
    digest_frequency: Optional[str] = Field(default=None, description="realtime, daily, or weekly")
    quiet_hours: Optional[str] = Field(default=None, description="Quiet hours window (e.g. '22:00-08:00')")
    chat_handle: Optional[str] = Field(default=None, description="Chat platform handle for room mention routing")


class User(BaseModel):
    """
    MongoDB User Document and API Model.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str = Field(default="", alias="_id", description="Unique user ID")
    display_name: str = Field(..., min_length=1, description="Display name")
    chat_handle: str = Field(..., min_length=1, description="Chat username/handle for room routing")
    github_login: Optional[str] = Field(default=None, description="GitHub username")
    topics: List[str] = Field(default_factory=list, description="Followed topic tags")
    blocked_topics: List[str] = Field(default_factory=list, description="Blocked topic tags")
    experience: str = Field(default="mid", description="Experience level")
    priorities: List[str] = Field(default_factory=list, description="Priority focus tags")
    approver_rooms: List[str] = Field(default_factory=list, description="Rooms where user has approval authority")
    digest_frequency: str = Field(default="daily", description="realtime, daily, or weekly")
    quiet_hours: str = Field(default="", description="Quiet hours window")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id
        return d
