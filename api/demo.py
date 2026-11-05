"""
NewsOps - Demo Reset Endpoint.

Implements POST /demo/reset — wipes all runtime state so the frontend
demo can be replayed from a clean slate without restarting the server.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.logging import logger
from ..db.mongodb import get_db
from ..db.seed import seed_initial_data
from .events import _room_queues, _room_seq, _room_step

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.post("/reset", summary="Reset all demo runtime state")
async def reset_demo(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Clears digests, tasks, and in-memory event state, then re-seeds
    rooms and users so the demo pipeline can run from scratch.
    """
    # Clear in-memory event bus
    _room_queues.clear()
    _room_seq.clear()
    _room_step.clear()

    # Drop volatile collections
    await db.digests.delete_many({})
    await db.tasks.delete_many({})

    # Re-seed stable data
    await seed_initial_data(db)

    logger.info("Demo reset: event bus cleared, digests and tasks dropped, seed data restored.")
    return {"reset": True, "message": "Demo state reset. Ready for a new run."}
