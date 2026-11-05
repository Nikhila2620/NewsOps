"""
NewsOps Revision 2 - API Dependencies & Authentication Helpers.

Implements identity resolution for the MVP (Section 9):
Reads X-User-ID or X-Chat-Handle header, defaulting to seeded demo user.
"""

from typing import Optional
from fastapi import Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import NotFoundError, UnauthorizedError
from ..db.mongodb import get_db
from ..models.user import User


async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_chat_handle: Optional[str] = Header(None, alias="X-Chat-Handle"),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> User:
    """
    Resolves current user context.
    If headers omitted, falls back to the default seeded demo user ('user-001').
    """
    query = {}
    if x_user_id:
        query = {"_id": x_user_id}
    elif x_chat_handle:
        query = {"chat_handle": x_chat_handle}
    else:
        # Default demo user
        query = {"_id": "user-001"}

    doc = await db.users.find_one(query)
    if not doc:
        # Try finding lead_reviewer or any first user
        doc = await db.users.find_one({"chat_handle": "lead_reviewer"})
        if not doc:
            doc = await db.users.find_one({})

    if not doc:
        raise NotFoundError("User", x_user_id or x_chat_handle or "default")

    return User(**doc)
