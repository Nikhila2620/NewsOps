"""
NewsOps Revision 2 - Analyst Agent (Switch Agent Protocol).

Evaluates claims, examines source credibility, and submits structured
verification payloads to POST /api/v1/agent/stories/{id}/analysis.
"""

from typing import List, Optional
import httpx

from ...ai.analyst import analyst_agent
from ...core.logging import logger


class AnalystSwitchAgent:
    name = "analyst"
    description = "Verifies claims, evaluates evidence, and calculates confidence scores."
    capabilities = ["claim_verification", "evidence_evaluation", "confidence_scoring"]

    def __init__(
        self,
        api_base: str,
        agent_token: str,
        switch_client=None,
        timeout: float = 45.0,
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

    async def get_story(self, story_id: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.api_base}/stories/{story_id}", headers=self._headers())
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.warning(f"Analyst get_story warning: {e}")
        return None

    async def submit_analysis(self, story_id: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.api_base}/agent/stories/{story_id}/analysis",
                    json=payload,
                    headers=self._headers(),
                )
                if res.status_code in (200, 201):
                    return res.json()
        except Exception as e:
            logger.warning(f"Analyst submit_analysis warning: {e}")
        return {"status": "error"}

    async def analyze_story_id(self, story_id: str, switch_room_ref: str = "") -> dict:
        story = await self.get_story(story_id)
        if not story:
            return {"status": "not_found", "story_id": story_id}

        title = story.get("title", "")
        text = " ".join([str(m.get("title", "")) for m in story.get("members", [])])
        submission = analyst_agent.analyze_story(
            story_id=story_id,
            title=title,
            text=text,
            analyst_id=self.name,
        )

        res = await self.submit_analysis(story_id, submission.model_dump(mode="json"))

        summary = (
            f"🔬 **Analyst Report** | Story: `{story_id}`\n"
            f"Title: {title[:70]}\n"
            f"Claims: {len(submission.claims)} | Confidence: {submission.overall_confidence:.2f}\n"
        )
        if self.switch_client and switch_room_ref:
            await self.switch_client.post_message(switch_room_ref, summary)

        return {
            "story_id": story_id,
            "claims": len(submission.claims),
            "confidence": submission.overall_confidence,
            "api_status": res.get("status"),
            "summary": summary,
        }

    async def run(self, story_ids: List[str], switch_room_ref: str = "") -> List[dict]:
        results = []
        for sid in story_ids:
            res = await self.analyze_story_id(sid, switch_room_ref)
            results.append(res)
        return results
