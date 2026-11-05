"""
NewsOps Revision 2 - User & Identity Endpoints.

Implements GET /me, GET /me/profile, and PUT /me/profile as specified in Revision 2 Section 9.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import NotFoundError
from ..db.mongodb import get_db
from ..models.user import User, UserProfileUpdate
from .deps import get_current_user

router = APIRouter(prefix="/me", tags=["Identity & Profile"])


@router.get("", response_model=User, summary="Get current authenticated user")
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the current active user."""
    return current_user


@router.get("/profile", summary="Get current user preference profile")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns user personalization preferences."""
    return {
        "topics": current_user.topics,
        "blocked_topics": current_user.blocked_topics,
        "experience": current_user.experience,
        "priorities": current_user.priorities,
        "digest_frequency": current_user.digest_frequency,
        "quiet_hours": current_user.quiet_hours,
        "chat_handle": current_user.chat_handle,
    }


@router.put("/profile", response_model=User, summary="Update user personalization profile")
async def update_my_profile(
    update_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Updates topics, priorities, experience, quiet hours, and chat handle."""
    update_fields = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if not update_fields:
        return current_user

    await db.users.update_one({"_id": current_user.id}, {"$set": update_fields})
    updated_doc = await db.users.find_one({"_id": current_user.id})
    return User(**updated_doc)
