"""
NewsOps Revision 2 - Sources API Endpoints.

Implements GET /sources for data source status, health, and metadata.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db.mongodb import get_db
from ..models.source import Source

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get("", response_model=List[Source], summary="List and filter data sources")
async def list_sources(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    trust_tier: Optional[int] = Query(None, ge=1, le=3, description="Filter by trust tier (1-3)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    skip: int = Query(0, ge=0, description="Offset"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    if trust_tier is not None:
        query["trust_tier"] = trust_tier

    cursor = db.sources.find(query).skip(skip).limit(limit)
    sources = []
    async for doc in cursor:
        sources.append(Source(**doc))
    return sources
