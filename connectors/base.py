"""
NewsOps Revision 2 - Source Connector Base Protocol.

All connectors implement the SourceConnector protocol (NewsOps Spec §7.1).
"""

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class SourceConnector(Protocol):
    source_key: str
    trust_tier: int
    is_available: bool

    async def fetch(self, topics: List[str] = None, limit: int = 20) -> List[dict]:
        ...


class ConnectorUnavailableError(Exception):
    def __init__(self, connector: str, reason: str):
        self.connector = connector
        self.reason = reason
        super().__init__(f"Connector '{connector}' unavailable: {reason}")
