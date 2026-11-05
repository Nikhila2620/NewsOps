"""
NewsOps Revision 2 - Switch Status API Endpoint.

Transparently reports how Switch agents interact with NewsOps:
Agents call NewsOps via the CLI wrapper (`scripts/newsops.py`) and REST API.
"""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..db.mongodb import get_db

router = APIRouter(prefix="/switch", tags=["Switch"])


@router.get("/status", summary="Get Switch integration status")
async def get_switch_status(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Transparently reports truth:
    Agents call NewsOps via CLI; reports timestamp of latest agent activity.
    """
    latest_activity = await db.agent_activity.find_one(sort=[("created_at", -1)])
    last_ts = latest_activity.get("created_at") if latest_activity else "never"
    last_agent = latest_activity.get("agent") if latest_activity else "none observed yet"

    return {
        "mode": "cli_agent_dispatch",
        "message": f"agents call NewsOps via CLI; last agent activity at {last_ts}",
        "last_activity_at": last_ts,
        "last_active_agent": last_agent,
        "agents": {
            "scout": "CLI candidate discovery",
            "analyst": "CLI claim extraction & verification submission",
            "editor": "CLI digest compilation & human approval check",
        },
    }
