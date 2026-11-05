"""
NewsOps Revision 2 - Invitation Models & MongoDB Document Schemas.

Complies with NewsOps Revision 2 Section 6 (room_invites collection schema)
and Section 9 (Invitations endpoints: POST /rooms/{id}/invites, GET /invites,
POST /invites/{id}/accept, POST /invites/{id}/decline).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class InviteStatus(str, Enum):
    """Status of an invitation to join a room."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class InviteCreate(BaseModel):
    """Payload to invite a user to a room."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    invitee_handle: str = Field(..., min_length=1, description="Chat username or email to invite")
    invitee_id: Optional[str] = Field(default=None, description="Known user ID if already registered")


class RoomInvite(BaseModel):
    """
    MongoDB Room Invite Document and API Response Model.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str = Field(default="", alias="_id", description="Unique invite ID")
    room_key: str = Field(..., description="Target room key")
    inviter_id: str = Field(..., description="User ID who issued the invitation")
    invitee_id: Optional[str] = Field(default=None)
    invitee_handle: str = Field(...)
    status: InviteStatus = Field(default=InviteStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: Optional[datetime] = Field(default=None)

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id
        d["status"] = self.status.value
        return d
