"""
NewsOps Revision 2 - MongoDB Index Management.

Creates all unique and performance indexes specified in Revision 2 Section 6:
- articles: unique canonical_url, content_hash, published_at desc
- stories: (topics, rank_score desc), last_updated_at, entities
- tools: unique sparse repo_url, (topics, stars_delta_7d desc)
- rooms: unique key
- agent_activity: (room_key, created_at desc)
- radar_votes: unique (item_id, user_id)
- dependency_manifests: (room_key, uploaded_at desc)
- impact_findings: unique (manifest_id, package, advisory_id, finding_type)
- inbox_items: (user_id, created_at desc)
"""

import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..core.logging import logger


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Creates required indexes across collections idempotently on application startup."""
    try:
        logger.info("Ensuring MongoDB indexes match NewsOps Revision 2 specification...")

        # 1. articles
        await db.articles.create_index([("canonical_url", pymongo.ASCENDING)], unique=True)
        await db.articles.create_index([("content_hash", pymongo.ASCENDING)])
        await db.articles.create_index([("published_at", pymongo.DESCENDING)])

        # 2. stories
        await db.stories.create_index([("topics", pymongo.ASCENDING), ("rank_score", pymongo.DESCENDING)])
        await db.stories.create_index([("last_updated_at", pymongo.DESCENDING)])
        await db.stories.create_index([("entities", pymongo.ASCENDING)])

        # 3. tools
        await db.tools.create_index([("repo_url", pymongo.ASCENDING)], unique=True, sparse=True)
        await db.tools.create_index([("topics", pymongo.ASCENDING), ("stars_delta_7d", pymongo.DESCENDING)])

        # 4. rooms
        await db.rooms.create_index([("key", pymongo.ASCENDING)], unique=True)

        # 5. agent_activity
        await db.agent_activity.create_index([("room_key", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])

        # 6. radar_votes: strict uniqueness on (item_id, user_id)
        await db.radar_votes.create_index(
            [("item_id", pymongo.ASCENDING), ("user_id", pymongo.ASCENDING)],
            unique=True,
        )

        # 7. dependency_manifests
        await db.dependency_manifests.create_index(
            [("room_key", pymongo.ASCENDING), ("uploaded_at", pymongo.DESCENDING)]
        )

        # 8. impact_findings: strict uniqueness to prevent rescan duplicates
        await db.impact_findings.create_index(
            [
                ("manifest_id", pymongo.ASCENDING),
                ("package", pymongo.ASCENDING),
                ("advisory_id", pymongo.ASCENDING),
                ("finding_type", pymongo.ASCENDING),
            ],
            unique=True,
        )

        # 9. inbox_items
        await db.inbox_items.create_index([("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])

        logger.info("MongoDB indexes verified successfully.")
    except Exception as exc:
        logger.warning(f"Index creation encountered a warning (safe in mock or existing environments): {exc}")
