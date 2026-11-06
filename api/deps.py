"""
NewsOps Revision 2 - API Dependencies & Authentication Helpers.

Implements identity resolution for the MVP (Section 9):
Resolves user identity from:
1. Authorization header: Bearer <token> (e.g. demo-token-alice, demo-token-sam, mock-alice, mock-sam)
2. Query param: access_token
3. X-User-ID or X-Chat-Handle headers
4. Default fallback: seeded demo user ('user-001' / Alice Chen)
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import NotFoundError
from ..db.mongodb import get_db
from ..models.user import User

# Demo persona definitions matching auth.py and frontend mocks
DEMO_USERS_BY_TOKEN = {
    "demo-token-alice": {
        "_id": "user-001",
        "display_name": "Alice Chen",
        "chat_handle": "alice_aiml",
        "approver_rooms": ["aiml", "security"],
        "topics": ["aiml", "oss"],
    },
    "mock-alice": {
        "_id": "user-001",
        "display_name": "Alice Chen",
        "chat_handle": "alice_aiml",
        "approver_rooms": ["aiml", "security"],
        "topics": ["aiml", "oss"],
    },
    "demo-token-sam": {
        "_id": "user-sam-001",
        "display_name": "Sam Rivera",
        "chat_handle": "sam_cloud",
        "approver_rooms": ["cloud"],
        "topics": ["cloud"],
    },
    "mock-sam": {
        "_id": "user-sam-001",
        "display_name": "Sam Rivera",
        "chat_handle": "sam_cloud",
        "approver_rooms": ["cloud"],
        "topics": ["cloud"],
    },
}


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_chat_handle: Optional[str] = Header(None, alias="X-Chat-Handle"),
    access_token: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> User:
    """
    Resolves current user context.
    Checks Bearer token, query access_token, headers, or falls back to demo Alice.
    """
    # 1. Check Bearer token or access_token param
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif access_token:
        token = access_token.strip()

    target_id = None
    target_handle = None

    if token and token in DEMO_USERS_BY_TOKEN:
        target_info = DEMO_USERS_BY_TOKEN[token]
        target_id = target_info["_id"]
        target_handle = target_info["chat_handle"]
    elif x_user_id:
        target_id = x_user_id
    elif x_chat_handle:
        target_handle = x_chat_handle.lstrip("@")

    # 2. Query MongoDB
    query = {}
    if target_id:
        query = {"_id": target_id}
    elif target_handle:
        query = {"$or": [{"chat_handle": target_handle}, {"chat_handle": f"@{target_handle}"}]}
    else:
        # Default demo user (Alice)
        query = {"_id": "user-001"}

    doc = await db.users.find_one(query)

    # If Sam requested but not in DB yet, seed Sam automatically
    if not doc and target_id == "user-sam-001":
        sam_data = {
            "_id": "user-sam-001",
            "display_name": "Sam Rivera",
            "chat_handle": "sam_cloud",
            "github_login": "sam-dev",
            "topics": ["cloud"],
            "blocked_topics": [],
            "experience": "senior",
            "priorities": ["kubernetes"],
            "approver_rooms": ["cloud"],
            "digest_frequency": "daily",
            "quiet_hours": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(sam_data)
        await db.rooms.update_one({"key": "cloud"}, {"$addToSet": {"approvers": "sam_cloud"}})
        doc = sam_data

    # Fallback search if not found
    if not doc:
        doc = await db.users.find_one({"chat_handle": "lead_reviewer"})
    if not doc:
        doc = await db.users.find_one({"_id": "user-001"})
    if not doc:
        doc = await db.users.find_one({})

    if not doc:
        raise NotFoundError("User", target_id or target_handle or "default")

    # Ensure approver_rooms is populated for demo personas if omitted in legacy doc
    user_dict = dict(doc)
    if not user_dict.get("approver_rooms"):
        if user_dict.get("_id") == "user-001" or user_dict.get("chat_handle") in ("alice_aiml", "@alice_aiml"):
            user_dict["approver_rooms"] = ["aiml", "security"]
        elif user_dict.get("_id") == "user-sam-001" or user_dict.get("chat_handle") in ("sam_cloud", "@sam_cloud"):
            user_dict["approver_rooms"] = ["cloud"]

    return User(**user_dict)
