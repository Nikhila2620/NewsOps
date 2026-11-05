"""
NewsOps Revision 2 - Health Check Endpoint.

Implements GET /healthz and GET /api/v1/healthz as specified in Revision 2 Section 9.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..config.settings import settings
from ..db.mongodb import get_db, db_manager

router = APIRouter(tags=["Health"])


@router.get("/healthz", summary="Liveness & Readiness probe")
async def health_check():
    """
    Returns service health, database connection state, and runtime environment.
    """
    db_health = await db_manager.ping()
    is_healthy = db_health.get("status") == "connected"

    return {
        "status": "ok" if is_healthy else "degraded",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_health,
        "version": "2.0.0-rev2",
    }
