"""
NewsOps Revision 2 - Radar & Community Voting API Endpoints.

Implements GET /radar, POST /radar/items, GET /radar/items/{id}, POST /radar/items/{id}/votes.
Votes are unique per (item_id, user_id): re-voting replaces or updates the vote.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.user import User
from .deps import get_current_user

router = APIRouter(prefix="/radar", tags=["Radar"])


class RadarItemCreate(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    room_key: str = Field(..., description="Target room key")
    title: str = Field(..., min_length=3, description="Tool or technology title")
    url: str = Field(..., description="Link to repo, release, or announcement")
    description: Optional[str] = Field(default=None, description="Short summary")
    topics: List[str] = Field(default_factory=list, description="Associated topics")


class RadarItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore", str_strip_whitespace=True)

    id: str = Field(default="", alias="_id")
    room_key: str
    title: str
    url: str
    description: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    vote_count: int = Field(default=0, ge=0)
    submitted_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id
        return d


@router.get("", response_model=List[RadarItem], summary="List radar items")
async def list_radar(
    room: Optional[str] = Query(None, description="Filter by room key"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = {}
    if room:
        query["room_key"] = room

    cursor = db.radar_items.find(query).sort("vote_count", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(RadarItem(**doc))
    return items


@router.post(
    "/items",
    response_model=RadarItem,
    status_code=status.HTTP_201_CREATED,
    summary="Submit item to radar",
)
async def create_radar_item(
    payload: RadarItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    item = RadarItem(
        _id=f"radar-{uuid.uuid4().hex[:10]}",
        room_key=payload.room_key,
        title=payload.title,
        url=payload.url,
        description=payload.description,
        topics=payload.topics,
        vote_count=1,
        submitted_by=current_user.id,
    )
    await db.radar_items.insert_one(item.to_mongo_dict())

    # Initial submitter vote recorded
    await db.radar_votes.insert_one({
        "item_id": item.id,
        "user_id": current_user.id,
        "voted_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"Radar item '{item.id}' submitted by '{current_user.id}'")
    return item


@router.get("/items/{id}", response_model=RadarItem, summary="Get radar item by ID")
async def get_radar_item(id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.radar_items.find_one({"_id": id})
    if not doc:
        raise NotFoundError("RadarItem", id)
    return RadarItem(**doc)


@router.post("/items/{id}/votes", summary="Upvote radar item (unique per user)")
async def vote_radar_item(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    item_doc = await db.radar_items.find_one({"_id": id})
    if not item_doc:
        raise NotFoundError("RadarItem", id)

    now = datetime.now(timezone.utc).isoformat()
    existing_vote = await db.radar_votes.find_one({"item_id": id, "user_id": current_user.id})

    if not existing_vote:
        # New vote: insert record and increment vote count
        await db.radar_votes.insert_one({
            "item_id": id,
            "user_id": current_user.id,
            "voted_at": now,
        })
        await db.radar_items.update_one({"_id": id}, {"$inc": {"vote_count": 1}})
    else:
        # Update timestamp for existing vote
        await db.radar_votes.update_one(
            {"_id": existing_vote["_id"]},
            {"$set": {"voted_at": now}}
        )

    updated = await db.radar_items.find_one({"_id": id})
    return {
        "status": "voted",
        "item_id": id,
        "vote_count": updated.get("vote_count", 1),
        "is_new_vote": existing_vote is None,
    }
