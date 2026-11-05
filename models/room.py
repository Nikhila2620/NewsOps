"""
NewsOps Revision 2 - Room Models & MongoDB Document Schemas.

Complies with NewsOps Revision 2 Section 6 (rooms collection schema)
and Section 9 (Rooms endpoints: GET/POST /rooms, GET /rooms/{id}, GET /rooms/{id}/members).
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RoomRules(BaseModel):
    """Interest and scoring rules for a room."""
    model_config = ConfigDict(extra="ignore")

    min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum rank score threshold")
    priorities: List[str] = Field(default_factory=list, description="Priority focus topics/tags")
    blocked: List[str] = Field(default_factory=list, description="Blocked tags to filter out")


class RoomMember(BaseModel):
    """Member entry in a room."""
    model_config = ConfigDict(extra="ignore")

    user_id: str = Field(..., description="Referenced user ID")
    role: str = Field(default="member", description="Role: 'admin', 'approver', or 'member'")


class RoomCreate(BaseModel):
    """Payload to create or register a room."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    key: str = Field(..., min_length=2, max_length=50, description="Unique room key (e.g. 'aiml', 'cloud')")
    name: str = Field(..., min_length=2, max_length=100, description="Display name")
    topics: List[str] = Field(default_factory=list, description="Topics covered by this room")
    chat_platform: str = Field(default="mattermost", description="Chat platform adapter name")
    chat_channel_id: Optional[str] = Field(default="", description="Mapped chat channel identifier")
    switch_room_ref: Optional[str] = Field(default="", description="Opaque Switch room reference")
    rules: Optional[RoomRules] = Field(default=None)


class Room(BaseModel):
    """
    MongoDB Room Document and API Model.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str = Field(default="", alias="_id", description="Unique room ID")
    key: str = Field(..., description="Unique room slug/key (e.g. 'aiml')")
    name: str = Field(..., description="Room title")
    topics: List[str] = Field(default_factory=list)
    rules: RoomRules = Field(default_factory=RoomRules)
    approvers: List[str] = Field(default_factory=list, description="Chat handles or user IDs who may approve digests")
    members: List[RoomMember] = Field(default_factory=list, description="Room participants")
    chat_platform: str = Field(default="mattermost")
    chat_channel_id: str = Field(default="")
    switch_room_ref: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id or f"room-{self.key}"
        return d
