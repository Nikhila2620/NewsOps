"""
NewsOps Revision 2 - Room Invitations API Endpoints.

Implements POST /rooms/{room_key}/invites, GET /invites, POST /invites/{id}/accept, POST /invites/{id}/decline.
"""

import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.invite import InviteCreate, InviteStatus, RoomInvite
from ..models.room import RoomMember
from ..models.user import User
from .deps import get_current_user

router = APIRouter(tags=["Invites"])


@router.post(
    "/rooms/{room_key}/invites",
    response_model=RoomInvite,
    status_code=status.HTTP_201_CREATED,
    summary="Create room invitation",
)
async def create_invite(
    room_key: str,
    payload: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    room = await db.rooms.find_one({"key": room_key}) or await db.rooms.find_one({"_id": room_key})
    if not room:
        raise NotFoundError("Room", room_key)

    invite = RoomInvite(
        _id=f"inv-{uuid.uuid4().hex[:12]}",
        room_key=room_key,
        inviter_id=current_user.id,
        invitee_handle=payload.invitee_handle,
        invitee_id=payload.invitee_id,
        status=InviteStatus.PENDING,
    )
    await db.room_invites.insert_one(invite.to_mongo_dict())
    logger.info(f"Invite created for '{payload.invitee_handle}' to '{room_key}'")
    return invite


@router.get("/invites", response_model=List[RoomInvite], summary="List invitations for current user")
async def list_invites(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.room_invites.find({
        "$or": [
            {"invitee_handle": current_user.chat_handle},
            {"invitee_id": current_user.id},
        ]
    })
    invites = []
    async for doc in cursor:
        invites.append(RoomInvite(**doc))
    return invites


@router.post("/invites/{id}/accept", summary="Accept invitation")
async def accept_invite(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    invite_doc = await db.room_invites.find_one({"_id": id})
    if not invite_doc:
        raise NotFoundError("RoomInvite", id)

    now = datetime.now(timezone.utc).isoformat()
    await db.room_invites.update_one(
        {"_id": id},
        {"$set": {"status": InviteStatus.ACCEPTED.value, "responded_at": now}}
    )

    # Add member to room
    room_key = invite_doc.get("room_key")
    if room_key:
        member = RoomMember(user_id=current_user.id, role="member").model_dump()
        await db.rooms.update_one(
            {"$or": [{"key": room_key}, {"_id": room_key}]},
            {"$push": {"members": member}}
        )

    return {"status": "accepted", "invite_id": id, "room_key": room_key}


@router.post("/invites/{id}/decline", summary="Decline invitation")
async def decline_invite(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    invite_doc = await db.room_invites.find_one({"_id": id})
    if not invite_doc:
        raise NotFoundError("RoomInvite", id)

    now = datetime.now(timezone.utc).isoformat()
    await db.room_invites.update_one(
        {"_id": id},
        {"$set": {"status": InviteStatus.DECLINED.value, "responded_at": now}}
    )
    return {"status": "declined", "invite_id": id}
