"""
NewsOps Revision 2 - Switch Agent Protocol Client.

Implements HTTP operations and event dispatching according to the Switch Agent Protocol.
Handles connection state, credentials check, and clean error reporting.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import httpx

from ..core.logging import logger


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class AgentRegistration:
    agent_id: str
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)


class SwitchProtocolClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.agent_id = agent_id or ""
        self.token = token or ""
        self.timeout = timeout
        self.state = ConnectionState.DISCONNECTED
        self.connection_id: Optional[str] = None
        self._handlers: Dict[str, List[Callable]] = {}
        self.is_configured = bool(self.base_url and self.agent_id and self.token)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Agent-ID": self.agent_id,
        }

    def on(self, event_type: str, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    async def connect(self) -> bool:
        if not self.is_configured:
            logger.info("SwitchProtocolClient: Credentials not configured. Operating in stub/standby mode.")
            self.state = ConnectionState.DISCONNECTED
            return False

        self.state = ConnectionState.CONNECTING
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.base_url}/health", headers=self._headers())
                res.raise_for_status()

            self.state = ConnectionState.CONNECTED
            self.connection_id = f"conn-{self.agent_id}-{int(datetime.now(timezone.utc).timestamp())}"
            logger.info(f"Connected to Switch platform (conn: {self.connection_id})")
            return True
        except Exception as e:
            self.state = ConnectionState.ERROR
            logger.warning(f"Switch connection attempt failed: {e}")
            return False

    async def disconnect(self):
        self.state = ConnectionState.DISCONNECTED
        self.connection_id = None

    async def register_agent(self, registration: AgentRegistration) -> dict:
        if not self.is_configured:
            return {"status": "pending_credentials", "agent_id": registration.agent_id}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/agents/register",
                    json={
                        "agent_id": registration.agent_id,
                        "name": registration.name,
                        "description": registration.description,
                        "capabilities": registration.capabilities,
                    },
                    headers=self._headers(),
                )
                res.raise_for_status()
                return res.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def post_message(self, room_ref: str, text: str, metadata: dict = None) -> dict:
        if not self.is_configured:
            logger.info(f"Switch post_message (stub): [Room: {room_ref}] {text[:80]}...")
            return {"status": "pending_credentials", "room_ref": room_ref}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/rooms/{room_ref}/messages",
                    json={"room_ref": room_ref, "text": text, "metadata": metadata or {}},
                    headers=self._headers(),
                )
                res.raise_for_status()
                return res.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def status(self) -> dict:
        return {
            "connected": self.state == ConnectionState.CONNECTED,
            "state": self.state.value,
            "agent_id": self.agent_id,
            "connection_id": self.connection_id,
            "is_configured": self.is_configured,
        }
