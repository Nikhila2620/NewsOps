"""
NewsOps Revision 2 - Stories API Endpoints.

Implements GET /stories, GET /stories/{id}, and POST /stories/{id}/feedback
as specified in Revision 2 Section 9.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.story import Story, StoryFeedback, StoryListResponse
from ..models.user import User
from .deps import get_current_user

router = APIRouter(prefix="/stories", tags=["Stories"])


@router.get("", response_model=StoryListResponse, summary="List ranked story clusters")
async def list_stories(
    topic: Optional[str] = Query(None, description="Filter by topic (e.g. 'aiml', 'cloud', 'security')"),
    q: Optional[str] = Query(None, description="Search query matching story title or summary"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum rank score"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Returns ranked story clusters with trust badges and pagination (NewsOps Revision 2 Section 9).
    """
    filter_query = {}
    if topic:
        filter_query["topics"] = topic
    if min_score is not None:
        filter_query["rank_score"] = {"$gte": min_score}
    if q:
        filter_query["title"] = {"$regex": q, "$options": "i"}

    total = await db.stories.count_documents(filter_query)
    cursor = db.stories.find(filter_query).sort("rank_score", -1).skip(skip).limit(limit)

    stories = []
    async for doc in cursor:
        stories.append(Story(**doc))

    return StoryListResponse(
        items=stories,
        total=total,
        limit=limit,
        skip=skip,
    )


@router.get("/{id}", response_model=Story, summary="Get full story details and provenance")
async def get_story(id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Returns full story details: sources, claims/evidence, analysis, tools, reason codes.
    """
    doc = await db.stories.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Story", id, task_id=id)
    return Story(**doc)


@router.post(
    "/{id}/feedback",
    status_code=status.HTTP_200_OK,
    summary="Submit user relevance or correction feedback",
)
async def submit_story_feedback(
    id: str,
    feedback: StoryFeedback,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Records human feedback on a story (relevant, irrelevant, correction).
    """
    story = await db.stories.find_one({"_id": id})
    if not story:
        raise NotFoundError("Story", id, task_id=id)

    feedback_doc = {
        "story_id": id,
        "user_id": current_user.id,
        "type": feedback.type,
        "comment": feedback.comment,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.story_feedback.insert_one(feedback_doc)

    logger.info(
        f"Recorded feedback '{feedback.type}' for story '{id}' from user '{current_user.id}'",
        extra={"story_id": id, "stage": "feedback"},
    )

    return {
        "status": "accepted",
        "story_id": id,
        "feedback_type": feedback.type,
    }
