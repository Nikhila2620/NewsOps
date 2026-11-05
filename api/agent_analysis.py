"""
NewsOps Revision 2 - Agent Story Analysis Endpoint.

Implements POST /api/v1/agent/stories/{id}/analysis as defined in Revision 2
Sections 7.8, 9, and 14.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Path, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..config.settings import settings
from ..core.errors import UnauthorizedError, ValidationContractError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..contracts.submission import AnalysisSubmission

router = APIRouter(prefix="/agent/stories", tags=["Agent Operations"])


def verify_agent_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Validates the shared service token sent by Switch template agents.
    Specification lines 657 & 801: Authorization: Bearer <AGENT_API_TOKEN>
    """
    if not authorization:
        raise UnauthorizedError("Missing Authorization header for agent endpoint.")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Authorization header must be in format 'Bearer <token>'.")

    token = parts[1]
    if token != settings.AGENT_API_TOKEN:
        raise UnauthorizedError("Invalid agent service token.")

    return token


@router.post(
    "/{id}/analysis",
    status_code=status.HTTP_200_OK,
    summary="Submit Agent Story Analysis & Claim Verifications",
    response_description="Confirmation of persisted analysis and review routing",
)
async def submit_story_analysis(
    submission: AnalysisSubmission,
    id: str = Path(..., description="Unique story ID matching the analyzed cluster"),
    token: str = Depends(verify_agent_token),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Receives schema-validated analysis and claim verification results from the Analyst agent.
    
    Revision 2 Rules:
    - Rejects malformed or unsourced outputs.
    - Updates Member 1's MongoDB stories collection.
    - Sets review_flag if confidence < 0.70 or claims are contradicted/insufficient.
    """
    # URL path ID and body story_id consistency
    if submission.story_id and submission.story_id != id:
        raise ValidationContractError(
            f"Path story ID '{id}' does not match payload story_id '{submission.story_id}'."
        )

    # Convert submission to Member 1's stories document update schema
    story_update = submission.to_story_update()

    # Persist or upsert into MongoDB 'stories' collection
    result = await db.stories.update_one(
        {"_id": id},
        {
            "$set": {
                "analysis": story_update["analysis"],
                "evidence": story_update["evidence"],
                "review_flag": story_update["review_flag"],
                "last_updated_at": story_update["last_updated_at"],
            },
            "$setOnInsert": {
                "_id": id,
                "title": submission.analysis.summary[:80],
                "topics": ["general"],
                "first_seen_at": story_update["last_updated_at"],
                "rank_score": round(submission.overall_confidence, 2),
                "reason_codes": ["agent_analyzed"],
                "members": [],
                "entities": [],
                "tool_ids": [],
            },
        },
        upsert=True,
    )

    logger.info(
        f"Persisted analysis for story '{id}' (review_required={submission.review_required}, "
        f"confidence={submission.overall_confidence})",
        extra={"story_id": id, "stage": "agent_analysis"},
    )

    return {
        "status": "accepted",
        "story_id": id,
        "review_required": submission.review_required,
        "overall_confidence": submission.overall_confidence,
        "evidence_items_count": len(story_update["evidence"]),
        "submitted_by": submission.agent_id,
        "updated_existing": result.matched_count > 0,
    }
