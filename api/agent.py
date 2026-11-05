"""
NewsOps Revision 2 - Agent Coordination API.

Implements /api/v1/agent/* endpoints:
- GET /agent/candidates
- GET /agent/stories/{id}/evidence
- POST /agent/activity
- GET /agent/activity
- POST /agent/digests
- POST /agent/digests/{id}/decision
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.digest import ApprovalRecord, Digest, DigestItem, DigestStatus
from ..models.story import Story
from .agent_analysis import verify_agent_token

router = APIRouter(prefix="/agent", tags=["Agent Operations"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class ActivityCreate(BaseModel):
    agent: str = Field(..., description="Agent name: scout, analyst, or editor")
    room: str = Field(..., description="Room key e.g. aiml, cloud, security")
    action: str = Field(..., description="Action description")
    story_id: Optional[str] = Field(default=None, description="Optional associated story ID")
    message: str = Field(..., description="Activity log message")


class DigestCreateAgent(BaseModel):
    room_key: str = Field(..., description="Target room key")
    story_ids: List[str] = Field(..., min_length=1, description="List of analysed story IDs")


class DigestDecision(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$", description="'approve' or 'reject'")
    by: str = Field(..., min_length=1, description="Approver chat handle or username, e.g. '@nikhila'")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/candidates",
    response_model=List[Story],
    summary="Get candidate un-analysed stories for room",
)
async def get_candidates(
    room: str = Query("aiml", description="Room slug e.g. aiml, cloud, security"),
    limit: int = Query(8, ge=1, le=50, description="Max candidate stories to return"),
    token: str = Depends(verify_agent_token),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Returns top-ranked, not-yet-analysed stories for the room (max 8 per run).
    Respects room rules (min_score, min_confidence, max_items).
    """
    room_doc = await db.rooms.find_one({"key": room})
    room_topics = [room]
    min_score = 0.0
    max_items = 8

    if room_doc:
        rules = room_doc.get("rules", {})
        min_score = rules.get("min_score", 0.0)
        max_items = rules.get("max_items", 8)
        if room_doc.get("topics"):
            room_topics = list(set([room] + room_doc["topics"]))

    eff_limit = min(limit, max_items, 8)

    query: Dict[str, Any] = {
        "$and": [
            {
                "$or": [
                    {"topics": {"$in": room_topics}},
                    {"room_key": room},
                ]
            },
            {
                "$or": [
                    {"analysis": None},
                    {"analysis": {"$exists": False}},
                ]
            },
        ]
    }

    if min_score > 0:
        query["$and"].append({"rank_score": {"$gte": min_score}})

    cursor = db.stories.find(query).sort("rank_score", -1).limit(eff_limit)

    stories = []
    async for doc in cursor:
        stories.append(Story(**doc))

    return stories


@router.get(
    "/stories/{id}/evidence",
    summary="Get source items and verbatim install command evidence for a story",
)
async def get_story_evidence(
    id: str,
    token: str = Depends(verify_agent_token),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Returns source items, repo facts, install command with commit SHA and risk flags.
    Returns 404 if story missing.
    """
    doc = await db.stories.find_one({"_id": id})
    if not doc:
        doc = await db.stories.find_one({"id": id})
    if not doc:
        raise NotFoundError("Story", id)

    source_url = doc.get("source_url")
    if not source_url and doc.get("members"):
        source_url = doc["members"][0].get("url")

    commit_sha = doc.get("install_commit") or doc.get("commit_sha")

    return {
        "story_id": doc.get("_id") or doc.get("id"),
        "title": doc.get("title", ""),
        "room_key": doc.get("room_key") or (doc.get("topics", [None])[0] if doc.get("topics") else None),
        "sources": doc.get("members", []),
        "evidence": doc.get("evidence", []),
        "install_command": doc.get("install_command"),
        "source_url": source_url,
        "commit_sha": commit_sha,
        "risk_flags": doc.get("risk_flags", []),
    }


@router.post(
    "/activity",
    status_code=status.HTTP_201_CREATED,
    summary="Record agent activity",
)
async def post_activity(
    activity: ActivityCreate,
    token: str = Depends(verify_agent_token),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Records agent actions in agent_activity collection.
    Source of the dashboard activity feed.
    """
    now = datetime.now(timezone.utc)
    activity_doc = {
        "_id": f"act-{uuid.uuid4().hex[:12]}",
        "agent": activity.agent,
        "room": activity.room,
        "action": activity.action,
        "story_id": activity.story_id,
        "message": activity.message,
        "created_at": now.isoformat(),
    }
    await db.agent_activity.insert_one(activity_doc)
    return {"status": "created", "activity_id": activity_doc["_id"], "created_at": activity_doc["created_at"]}


@router.get(
    "/activity",
    summary="List recent agent activities (read-only, transparent)",
)
async def get_activity(
    room: Optional[str] = Query(None, description="Optional room filter"),
    limit: int = Query(50, ge=1, le=200, description="Max activities to return"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Read-only list of agent activities (no token required).
    Sorted created_at desc.
    """
    query = {}
    if room:
        query["room"] = room

    cursor = db.agent_activity.find(query).sort("created_at", -1).limit(limit)
    activities = []
    async for doc in cursor:
        doc["id"] = doc.get("_id")
        activities.append(doc)
    return activities


@router.post(
    "/digests",
    status_code=status.HTTP_201_CREATED,
    response_model=Digest,
    summary="Editor builds draft digest from analysed stories",
)
async def create_agent_digest(
    payload: DigestCreateAgent,
    token: str = Depends(verify_agent_token),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Editor builds a draft digest from analysed stories, capped by room max_items.
    """
    room_doc = await db.rooms.find_one({"key": payload.room_key})
    max_items = 8
    if room_doc:
        max_items = room_doc.get("rules", {}).get("max_items", 8)

    selected_ids = payload.story_ids[:max_items]

    items = [
        DigestItem(story_id=sid, position=idx, included=True)
        for idx, sid in enumerate(selected_ids)
    ]

    digest_id = f"digest-{payload.room_key}-{uuid.uuid4().hex[:8]}"
    digest = Digest(
        id=digest_id,
        room_key=payload.room_key,
        status=DigestStatus.DRAFT,
        items=items,
        approvals=[],
    )

    await db.digests.insert_one(digest.to_mongo_dict())
    logger.info(f"Draft digest '{digest_id}' created by Editor for room '{payload.room_key}' with {len(items)} items")
    return digest


@router.post(
    "/digests/{id}/decision",
    response_model=Digest,
    summary="Submit approval or rejection decision on a digest",
)
async def record_digest_decision(
    id: str,
    payload: DigestDecision,
    token: str = Depends(verify_agent_token),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Records review decision from chat or agent.
    Accepted ONLY if 'by' is in room approvers; else returns 403 Forbidden.
    """
    doc = await db.digests.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Digest", id)

    room_key = doc.get("room_key", "")
    room_doc = await db.rooms.find_one({"key": room_key})

    approvers = room_doc.get("approvers", []) if room_doc else []
    clean_by = payload.by.lstrip("@").strip().lower()
    clean_approvers = [a.lstrip("@").strip().lower() for a in approvers]

    if clean_by not in clean_approvers:
        logger.warning(f"Digest decision rejected: '{payload.by}' not in approvers {approvers} for room '{room_key}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{payload.by}' is not authorized to approve digests for room '{room_key}'. Authorized approvers: {approvers}",
        )

    new_status = DigestStatus.APPROVED if payload.decision == "approve" else DigestStatus.REJECTED
    record = ApprovalRecord(
        reviewer=payload.by,
        decision=new_status.value,
        comment=f"Decision recorded via Agent API by {payload.by}",
        source="chat",
        at=datetime.now(timezone.utc),
    )

    await db.digests.update_one(
        {"_id": id},
        {
            "$set": {"status": new_status.value},
            "$push": {"approvals": record.model_dump()},
        },
    )

    updated_doc = await db.digests.find_one({"_id": id})
    logger.info(f"Digest '{id}' set to '{new_status.value}' by '{payload.by}'")
    return Digest(**updated_doc)
