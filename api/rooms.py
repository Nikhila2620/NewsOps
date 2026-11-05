"""
NewsOps Revision 2 - Rooms API Endpoints.

Implements GET/POST /rooms, GET /rooms/{key}, GET /rooms/{key}/members, GET /rooms/{key}/agents.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import ConflictError, NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.room import Room, RoomCreate, RoomMember, RoomRules
from ..models.user import User
from .deps import get_current_user

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=List[Room], summary="List all rooms")
async def list_rooms(
    limit: int = 50,
    skip: int = 0,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db.rooms.find({}).skip(skip).limit(limit)
    rooms = []
    async for doc in cursor:
        rooms.append(Room(**doc))
    return rooms


@router.post(
    "",
    response_model=Room,
    status_code=status.HTTP_201_CREATED,
    summary="Create or register a room",
)
async def create_room(
    payload: RoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    existing = await db.rooms.find_one({"key": payload.key})
    if existing:
        raise ConflictError(f"Room with key '{payload.key}' already exists.")

    room_id = f"room-{payload.key}"
    rules = payload.rules or RoomRules()
    members = [RoomMember(user_id=current_user.id, role="admin")]
    approvers = [current_user.chat_handle]

    room = Room(
        _id=room_id,
        key=payload.key,
        name=payload.name,
        topics=payload.topics,
        rules=rules,
        approvers=approvers,
        members=members,
        chat_platform=payload.chat_platform,
        chat_channel_id=payload.chat_channel_id or "",
        switch_room_ref=payload.switch_room_ref or "",
    )

    await db.rooms.insert_one(room.to_mongo_dict())
    logger.info(f"Room '{payload.key}' created by user '{current_user.id}'")
    return room


@router.get("/{key}", response_model=Room, summary="Get room details by key")
async def get_room(key: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.rooms.find_one({"key": key})
    if not doc:
        # Fallback query by _id
        doc = await db.rooms.find_one({"_id": key})
    if not doc:
        raise NotFoundError("Room", key)
    return Room(**doc)


@router.get("/{key}/members", response_model=List[RoomMember], summary="List room members")
async def get_room_members(key: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.rooms.find_one({"key": key}) or await db.rooms.find_one({"_id": key})
    if not doc:
        raise NotFoundError("Room", key)
    room = Room(**doc)
    return room.members


@router.get("/{key}/agents", summary="List agents configured for room")
async def get_room_agents(key: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.rooms.find_one({"key": key}) or await db.rooms.find_one({"_id": key})
    if not doc:
        raise NotFoundError("Room", key)
    room = Room(**doc)
    return {
        "room_key": room.key,
        "agents": ["scout", "analyst", "editor"],
        "switch_room_ref": room.switch_room_ref,
        "approvers": room.approvers,
    }
