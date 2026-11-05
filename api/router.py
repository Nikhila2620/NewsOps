"""
NewsOps Revision 2 - API Router.

Central router mounting all v1 routes.
"""

from fastapi import APIRouter
from .health import router as health_router
from .agent_analysis import router as agent_router
from .agent import router as agent_core_router
from .me import router as me_router
from .tasks import router as tasks_router
from .stories import router as stories_router
from .sources import router as sources_router
from .rooms import router as rooms_router
from .invites import router as invites_router
from .digests import router as digests_router
from .radar import router as radar_router
from .switch_status import router as switch_router
from .auth import router as auth_router
from .events import router as events_router
from .demo import router as demo_router
from .impact import router as impact_router

api_v1_router = APIRouter()

# Mount sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(agent_core_router)
api_v1_router.include_router(me_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(stories_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(rooms_router)
api_v1_router.include_router(invites_router)
api_v1_router.include_router(digests_router)
api_v1_router.include_router(radar_router)
api_v1_router.include_router(switch_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(demo_router)
api_v1_router.include_router(impact_router)
