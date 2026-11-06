"""
NewsOps Revision 2 - Digests & Human Approval API Endpoints.

Implements GET /digests, GET /digests/{id}, POST /digests/{id}/approve,
POST /digests/{id}/reject, POST /digests/{id}/request-changes, POST /digests/{id}/publish.

CRITICAL RULES:
1. POST /digests/{id}/approve, /reject, /request-changes MUST verify that the user
   is an authorized approver for the room (room.approvers or user.approver_rooms).
   Returns HTTP 403 Forbidden if not authorized.
2. POST /digests/{id}/publish MUST return HTTP 403 unless the digest status is 'approved'.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel as _BaseModel

from ..core.errors import NotFoundError, NewsOpsException
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.digest import ApprovalAction, ApprovalRecord, Digest, DigestStatus
from ..models.user import User
from .deps import get_current_user

router = APIRouter(prefix="/digests", tags=["Digests"])


async def _assert_can_approve(room_key: str, current_user: User, db: AsyncIOMotorDatabase) -> None:
    """Verifies that current_user has approval rights for the specified room."""
    room = await db.rooms.find_one({"key": room_key})
    room_approvers = room.get("approvers", []) if room else []
    
    normalized_approvers = {a.lstrip("@").lower() for a in room_approvers}
    user_handle = current_user.chat_handle.lstrip("@").lower()
    user_approver_rooms = [r.lower() for r in getattr(current_user, "approver_rooms", [])]

    is_authorized = (
        user_handle in normalized_approvers
        or current_user.id in room_approvers
        or room_key.lower() in user_approver_rooms
        or (user_handle == "lead_reviewer" and "lead_reviewer" in normalized_approvers)
    )

    if not is_authorized:
        logger.warning(
            f"Approval action blocked: user '{current_user.chat_handle}' is not authorized "
            f"for room '#{room_key}'. Authorized approvers: {room_approvers}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.chat_handle}' is not authorized to approve digests for #{room_key}.",
        )


@router.get("", response_model=List[Digest], summary="List and filter digests")
async def list_digests(
    room_key: Optional[str] = Query(None, description="Filter by room key"),
    status: Optional[DigestStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = {}
    if room_key:
        query["room_key"] = room_key
    if status:
        query["status"] = status.value

    cursor = db.digests.find(query).sort("created_at", -1).skip(skip).limit(limit)
    digests = []
    async for doc in cursor:
        digests.append(Digest(**doc))
    return digests


@router.get("/{id}", response_model=Digest, summary="Get digest by ID")
async def get_digest(id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.digests.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Digest", id)
    return Digest(**doc)


@router.post("/{id}/approve", response_model=Digest, summary="Approve digest for publication")
async def approve_digest(
    id: str,
    action: Optional[ApprovalAction] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.digests.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Digest", id)

    # Enforce approver permission
    await _assert_can_approve(doc["room_key"], current_user, db)

    record = ApprovalRecord(
        reviewer=current_user.chat_handle or current_user.id,
        decision="approved",
        comment=action.comment if action else None,
        source="dashboard",
        at=datetime.now(timezone.utc),
    )

    await db.digests.update_one(
        {"_id": id},
        {
            "$set": {"status": DigestStatus.APPROVED.value},
            "$push": {"approvals": record.model_dump(mode="json")},
        },
    )

    updated = await db.digests.find_one({"_id": id})
    logger.info(f"Digest '{id}' approved by '{current_user.chat_handle}'")
    return Digest(**updated)


@router.post("/{id}/reject", response_model=Digest, summary="Reject digest")
async def reject_digest(
    id: str,
    action: Optional[ApprovalAction] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.digests.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Digest", id)

    # Enforce approver permission
    await _assert_can_approve(doc["room_key"], current_user, db)

    record = ApprovalRecord(
        reviewer=current_user.chat_handle or current_user.id,
        decision="rejected",
        comment=action.comment if action else None,
        source="dashboard",
        at=datetime.now(timezone.utc),
    )

    await db.digests.update_one(
        {"_id": id},
        {
            "$set": {"status": DigestStatus.REJECTED.value},
            "$push": {"approvals": record.model_dump(mode="json")},
        },
    )

    updated = await db.digests.find_one({"_id": id})
    return Digest(**updated)


@router.post("/{id}/request-changes", response_model=Digest, summary="Request changes on digest")
async def request_changes(
    id: str,
    action: Optional[ApprovalAction] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.digests.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Digest", id)

    # Enforce approver permission
    await _assert_can_approve(doc["room_key"], current_user, db)

    record = ApprovalRecord(
        reviewer=current_user.chat_handle or current_user.id,
        decision="request-changes",
        comment=action.comment if action else None,
        source="dashboard",
        at=datetime.now(timezone.utc),
    )

    await db.digests.update_one(
        {"_id": id},
        {
            "$set": {"status": DigestStatus.REVIEW_REQUIRED.value},
            "$push": {"approvals": record.model_dump(mode="json")},
        },
    )

    updated = await db.digests.find_one({"_id": id})
    return Digest(**updated)


@router.post("/{id}/publish", response_model=Digest, summary="Publish approved digest")
async def publish_digest(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    CRITICAL NON-NEGOTIABLE RULE:
    MUST return HTTP 403 Forbidden unless the digest is in 'approved' status.
    """
    doc = await db.digests.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Digest", id)

    current_status = doc.get("status")
    if current_status != DigestStatus.APPROVED.value and current_status != DigestStatus.APPROVED:
        logger.warning(f"Publish attempt blocked: digest '{id}' is in '{current_status}' status, not 'approved'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Digest publication blocked. Digest must be in 'approved' status before publishing. Current status: '{current_status}'",
        )

    now = datetime.now(timezone.utc)
    await db.digests.update_one(
        {"_id": id},
        {
            "$set": {
                "status": DigestStatus.PUBLISHED.value,
                "published_at": now.isoformat(),
            }
        },
    )

    updated = await db.digests.find_one({"_id": id})
    logger.info(f"Digest '{id}' successfully published at {now.isoformat()}")
    return Digest(**updated)


class ItemDecision(_BaseModel):
    included: bool  # True = keep, False = remove


@router.patch(
    "/{id}/items/{story_id}",
    response_model=Digest,
    summary="Keep or remove a flagged digest item (reviewer decision)",
)
async def patch_digest_item(
    id: str,
    story_id: str,
    decision: ItemDecision,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.digests.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Digest", id)

    # Reviewer must have room authorization
    await _assert_can_approve(doc["room_key"], current_user, db)

    digest = Digest(**doc)
    matched = False
    for item in digest.items:
        if item.story_id == story_id:
            item.included = decision.included
            matched = True
            break

    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story '{story_id}' not found in digest '{id}'.",
        )

    updated_items = [i.model_dump() for i in digest.items]
    await db.digests.update_one({"_id": id}, {"$set": {"items": updated_items}})
    updated_doc = await db.digests.find_one({"_id": id})
    logger.info(
        f"Digest item '{story_id}' in '{id}' set included={decision.included} "
        f"by '{current_user.chat_handle}'"
    )
    return Digest(**updated_doc)
