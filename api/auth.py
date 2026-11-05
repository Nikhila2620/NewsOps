"""
NewsOps - Auth API Endpoints.

Implements POST /auth/demo-login for persona switch between demo users.
The frontend calls this to get a session token for Alice or Sam.
"""

from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from ..core.logging import logger
from ..db.mongodb import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])

# Demo personas as defined in the frontend spec:
# Alice — approver for #aiml and #security
# Sam — approver for #cloud only
DEMO_PERSONAS = {
    "alice": {
        "user_id": "user-001",
        "chat_handle": "alice_aiml",
        "display_name": "Alice Chen",
        "approver_rooms": ["aiml", "security"],
        "token": "demo-token-alice",
    },
    "sam": {
        "user_id": "user-sam-001",
        "chat_handle": "sam_cloud",
        "display_name": "Sam Rivera",
        "approver_rooms": ["cloud"],
        "token": "demo-token-sam",
    },
}

# Simple in-memory token → persona map (demo only)
TOKEN_MAP = {v["token"]: v for v in DEMO_PERSONAS.values()}


class DemoLoginRequest(BaseModel):
    persona: Literal["alice", "sam"]


class DemoLoginResponse(BaseModel):
    token: str
    user_id: str
    chat_handle: str
    display_name: str
    approver_rooms: list[str]


@router.post(
    "/demo-login",
    response_model=DemoLoginResponse,
    summary="Switch demo persona (Alice or Sam)",
)
async def demo_login(
    payload: DemoLoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Issues a demo bearer token for the requested persona.
    Alice can approve #aiml and #security; Sam can approve #cloud only.
    """
    persona = DEMO_PERSONAS.get(payload.persona)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown persona '{payload.persona}'. Must be 'alice' or 'sam'.",
        )

    # Ensure Sam exists in db (Alice is seeded as user-001)
    if payload.persona == "sam":
        sam_doc = await db.users.find_one({"_id": "user-sam-001"})
        if not sam_doc:
            await db.users.insert_one({
                "_id": "user-sam-001",
                "display_name": "Sam Rivera",
                "chat_handle": "sam_cloud",
                "github_login": "sam-dev",
                "topics": ["cloud"],
                "blocked_topics": [],
                "experience": "senior",
                "priorities": ["kubernetes"],
                "digest_frequency": "daily",
                "quiet_hours": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            # Add Sam as approver for cloud room
            await db.rooms.update_one(
                {"key": "cloud"},
                {"$addToSet": {"approvers": "sam_cloud"}},
            )
            logger.info("Seeded Sam Rivera (sam_cloud) on first demo-login")

    logger.info(f"Demo login: persona='{payload.persona}' handle='{persona['chat_handle']}'")
    return DemoLoginResponse(**persona)
