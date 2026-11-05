"""
NewsOps Revision 2 - Scout Agent.

Discovers relevant news, collects candidate stories from sources,
and triggers ingestion/ranking tasks.
"""

from typing import List, Optional
import httpx

from ...core.logging import logger


class ScoutAgent:
    name = "scout"
    description = "Discovers and collects relevant news stories and releases."
    capabilities = ["news_discovery", "source_collection", "trend_identification"]

    def __init__(
        self,
        api_base: str,
        agent_token: str,
        switch_client=None,
        timeout: float = 30.0,
    ):
        self.api_base = api_base.rstrip("/")
        self.agent_token = agent_token
        self.switch_client = switch_client
        self.timeout = timeout

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.agent_token}",
            "Content-Type": "application/json",
        }

    async def discover_candidates(self, room_key: str, topics: List[str] = None, limit: int = 20) -> List[dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {"limit": limit}
                if topics:
                    params["topic"] = topics[0]
                res = await client.get(f"{self.api_base}/stories", params=params, headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    return data.get("items", [])
        except Exception as e:
            logger.warning(f"Scout discover_candidates warning: {e}")
        return []

    async def create_ingest_task(self, room_key: str, topics: List[str], request: str = "Scout discovery run") -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.api_base}/tasks",
                    json={
                        "room_id": room_key,
                        "request": request,
                        "topics": topics,
                        "since_hours": 24,
                        "approval_required": True,
                    },
                    headers=self._headers(),
                )
                if res.status_code in (200, 201):
                    return res.json()
        except Exception as e:
            logger.warning(f"Scout task creation warning: {e}")
        return {"status": "error"}

    async def run(self, room_key: str, topics: List[str] = None, switch_room_ref: str = "") -> dict:
        topics = topics or ["aiml", "cloud", "security"]
        candidates = await self.discover_candidates(room_key, topics)
        task = await self.create_ingest_task(room_key, topics)

        summary = (
            f"🔍 **Scout Report** | Room: #{room_key}\n"
            f"Discovered {len(candidates)} candidate stories.\n"
            f"Task: `{task.get('task_id', 'N/A')}`\n"
        )
        if self.switch_client and switch_room_ref:
            await self.switch_client.post_message(switch_room_ref, summary)

        return {
            "room_key": room_key,
            "candidates_found": len(candidates),
            "task_id": task.get("task_id"),
            "top_story_ids": [c.get("_id") or c.get("id") for c in candidates[:5]],
            "summary": summary,
        }
