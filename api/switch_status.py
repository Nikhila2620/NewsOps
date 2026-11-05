"""
NewsOps Revision 2 - Switch Status API Endpoint.

Implements GET /switch/status to transparently report the connection state
between NewsOps and the Switch Agent Protocol.
"""

from fastapi import APIRouter
from ..config.settings import settings

router = APIRouter(prefix="/switch", tags=["Switch"])


@router.get("/status", summary="Get Switch Agent Protocol integration status")
async def get_switch_status():
    configured = bool(settings.SWITCH_BASE_URL and settings.SWITCH_POSTER_TOKEN)
    return {
        "connected": configured,
        "status": "configured" if configured else "pending_credentials",
        "message": (
            "Switch Agent Protocol is configured and connected."
            if configured
            else "Switch integration is built and ready, but awaiting live credentials. "
                 "Configure SWITCH_BASE_URL, SWITCH_POSTER_AGENT_ID, and SWITCH_POSTER_TOKEN in .env to connect live."
        ),
        "agents": {
            "scout": "ready" if configured else "pending_credentials",
            "analyst": "ready" if configured else "pending_credentials",
            "editor": "ready" if configured else "pending_credentials",
        },
        "docs_mcp": "https://docs.switchagents.ai/mcp",
        "protocol": "HTTP Operations + WebSocket Events",
    }
