"""
NewsOps Revision 2 - Editor Agent.

Curates verified digests and triggers publication only after human approval.
Respects the 403 publish gate when unapproved.
"""

from typing import Optional
import httpx

from ...core.logging import logger


class EditorAgent:
    name = "editor"
    description = "Prepares and publishes verified digests subject to human approval."
    capabilities = ["digest_creation", "editorial_summary", "publication"]

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

    async def get_digest(self, digest_id: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.api_base}/digests/{digest_id}", headers=self._headers())
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.warning(f"Editor get_digest warning: {e}")
        return None

    async def attempt_publish(self, digest_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.api_base}/digests/{digest_id}/publish", headers=self._headers())
                if res.status_code == 403:
                    return {"status": "blocked", "reason": "approval_required", "code": 403}
                if res.status_code == 200:
                    return {"status": "published", **res.json()}
                return {"status": "error", "code": res.status_code}
        except Exception as e:
            logger.warning(f"Editor attempt_publish warning: {e}")
            return {"status": "error", "error": str(e)}

    async def run(self, digest_id: str, switch_room_ref: str = "") -> dict:
        digest = await self.get_digest(digest_id)
        if not digest:
            return {"status": "not_found", "digest_id": digest_id}

        result = await self.attempt_publish(digest_id)
        current_status = digest.get("status")

        if result.get("status") == "published":
            summary = f"📰 **Editor**: Digest `{digest_id}` published successfully to #{digest.get('room_key')}."
        elif result.get("status") == "blocked":
            summary = (
                f"📰 **Editor**: Digest `{digest_id}` requires approval before publishing. "
                f"Current status: `{current_status}`."
            )
        else:
            summary = f"📰 **Editor**: Digest `{digest_id}` publish result: {result.get('status')}."

        if self.switch_client and switch_room_ref:
            await self.switch_client.post_message(switch_room_ref, summary)

        return {
            "digest_id": digest_id,
            "digest_status": current_status,
            "publish_result": result,
            "summary": summary,
        }
