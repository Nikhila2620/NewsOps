"""
NewsOps Revision 2 - Initial Seed Data.

Populates initial database state idempotently on startup:
- Default rooms (#aiml, #cloud, #security) with interest rules and approvers
- Demo developer personas and profiles
- Ingestion sources with trust tiers
"""

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..core.logging import logger


INITIAL_ROOMS = [
    {
        "_id": "room-aiml-001",
        "key": "aiml",
        "name": "AI/ML Intelligence",
        "topics": ["aiml"],
        "rules": {
            "min_score": 0.60,
            "priorities": ["llm", "agents", "rag", "eval"],
            "blocked": [],
        },
        "approvers": ["lead_reviewer", "alice_aiml"],
        "members": [{"user_id": "user-001", "role": "admin"}],
        "chat_platform": "mattermost",
        "chat_channel_id": "channel-aiml",
        "switch_room_ref": "switch:room:aiml",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "room-cloud-002",
        "key": "cloud",
        "name": "Cloud & Platform Eng",
        "topics": ["cloud", "devtools"],
        "rules": {
            "min_score": 0.55,
            "priorities": ["kubernetes", "terraform", "observability"],
            "blocked": [],
        },
        "approvers": ["lead_reviewer", "bob_cloud"],
        "members": [{"user_id": "user-002", "role": "admin"}],
        "chat_platform": "mattermost",
        "chat_channel_id": "channel-cloud",
        "switch_room_ref": "switch:room:cloud",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "room-sec-003",
        "key": "security",
        "name": "Security & Supply Chain",
        "topics": ["security"],
        "rules": {
            "min_score": 0.70,
            "priorities": ["cve", "advisories", "secrets", "supply_chain"],
            "blocked": [],
        },
        "approvers": ["lead_reviewer"],
        "members": [{"user_id": "user-003", "role": "admin"}],
        "chat_platform": "mattermost",
        "chat_channel_id": "channel-security",
        "switch_room_ref": "switch:room:security",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]

INITIAL_USERS = [
    {
        "_id": "user-001",
        "display_name": "Alice Chen",
        "chat_handle": "alice_aiml",
        "github_login": "alice-dev",
        "topics": ["aiml", "oss"],
        "blocked_topics": [],
        "experience": "senior",
        "priorities": ["agents", "rag"],
        "digest_frequency": "daily",
        "quiet_hours": "22:00-08:00",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "user-002",
        "display_name": "Bob Martinez",
        "chat_handle": "bob_cloud",
        "github_login": "bob-ops",
        "topics": ["cloud", "devtools"],
        "blocked_topics": [],
        "experience": "lead",
        "priorities": ["kubernetes", "security"],
        "digest_frequency": "daily",
        "quiet_hours": "23:00-07:00",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "user-003",
        "display_name": "Chief Editor",
        "chat_handle": "lead_reviewer",
        "github_login": "lead-reviewer",
        "topics": ["aiml", "cloud", "security"],
        "blocked_topics": [],
        "experience": "principal",
        "priorities": ["quality", "provenance"],
        "digest_frequency": "realtime",
        "quiet_hours": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]

INITIAL_SOURCES = [
    {
        "_id": "source-gh-001",
        "name": "GitHub Trending & Releases",
        "type": "api",
        "domain": "api.github.com",
        "terms_url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
        "trust_tier": 1,
        "enabled": True,
        "health": "ok",
        "last_ok_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "source-hn-002",
        "name": "Hacker News (Algolia API)",
        "type": "api",
        "domain": "hn.algolia.com",
        "terms_url": "https://www.ycombinator.com/legal/",
        "trust_tier": 3,
        "enabled": True,
        "health": "ok",
        "last_ok_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "source-osv-003",
        "name": "OSV Vulnerability Database",
        "type": "api",
        "domain": "api.osv.dev",
        "terms_url": "https://osv.dev/about",
        "trust_tier": 1,
        "enabled": True,
        "health": "ok",
        "last_ok_at": datetime.now(timezone.utc).isoformat(),
    },
]


async def seed_initial_data(db: AsyncIOMotorDatabase) -> None:
    """Inserts initial seed records idempotently using upserts."""
    logger.info("Checking and seeding initial NewsOps data...")

    # Seed rooms
    for room in INITIAL_ROOMS:
        await db.rooms.update_one({"key": room["key"]}, {"$setOnInsert": room}, upsert=True)

    # Seed users
    for user in INITIAL_USERS:
        await db.users.update_one({"_id": user["_id"]}, {"$setOnInsert": user}, upsert=True)

    # Seed sources
    for source in INITIAL_SOURCES:
        await db.sources.update_one({"_id": source["_id"]}, {"$setOnInsert": source}, upsert=True)

    logger.info("Seed data verification completed.")
