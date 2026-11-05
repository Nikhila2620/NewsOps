"""
NewsOps Revision 2 - MongoDB 7 Database Connection & Lifecycle Management.

Supports async Motor client connections to MongoDB 7 with connection pooling,
graceful offline/testing fallback (via mongomock-motor), and health pinging.
"""

from typing import Optional, Any, Dict
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import mongomock_motor

from ..config.settings import settings
from ..core.logging import logger


class DatabaseManager:
    """
    Manages MongoDB async client lifecycle, connections, and health status.
    """
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.is_connected: bool = False
        self.is_mock: bool = False

    async def connect(self, force_mock: bool = False) -> None:
        """
        Initializes MongoDB connection. If live database is unreachable or force_mock is True,
        falls back to mongomock-motor to ensure resilience and demo reliability.
        """
        if force_mock:
            logger.info("Initializing in-memory mock database client for tests/offline mode.")
            self.client = mongomock_motor.AsyncMongoMockClient()
            self.db = self.client[settings.MONGODB_DB]
            self.is_connected = True
            self.is_mock = True
            return

        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI} (db: {settings.MONGODB_DB})...")
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                uuidRepresentation="standard",
            )
            # Test connection with ping
            await self.client.admin.command("ping")
            self.db = self.client[settings.MONGODB_DB]
            self.is_connected = True
            self.is_mock = False
            logger.info("Successfully connected to live MongoDB 7 instance.")
        except Exception as exc:
            logger.warning(
                f"Could not connect to live MongoDB at {settings.MONGODB_URI} ({exc}). "
                "Activating in-memory mock client to guarantee offline operation and demo resilience."
            )
            self.client = mongomock_motor.AsyncMongoMockClient()
            self.db = self.client[settings.MONGODB_DB]
            self.is_connected = True
            self.is_mock = True

    async def disconnect(self) -> None:
        """Closes active database connections."""
        if self.client:
            logger.info("Closing MongoDB connection.")
            self.client.close()
            self.is_connected = False
            self.client = None
            self.db = None

    async def ping(self) -> Dict[str, Any]:
        """Checks connection health."""
        if not self.is_connected or self.client is None:
            return {"status": "disconnected", "database": settings.MONGODB_DB, "is_mock": False}

        try:
            if not self.is_mock:
                await self.client.admin.command("ping")
            return {
                "status": "connected",
                "database": settings.MONGODB_DB,
                "is_mock": self.is_mock,
                "engine": "mongomock-motor" if self.is_mock else "mongodb-7",
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "error": str(exc),
                "database": settings.MONGODB_DB,
                "is_mock": self.is_mock,
            }

    def get_database(self) -> AsyncIOMotorDatabase:
        """Returns the current active database instance."""
        if self.db is None:
            raise RuntimeError("Database is not connected. Call connect() before accessing database.")
        return self.db


db_manager = DatabaseManager()


def get_db() -> AsyncIOMotorDatabase:
    """Dependency injection helper for FastAPI routes."""
    return db_manager.get_database()
