"""
NewsOps Revision 2 - Reddit Connector.

Fetches technical discussions from developer subreddits.
Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET; reports availability gracefully.
"""

from datetime import datetime, timezone
from typing import List, Optional
import httpx

from ..core.logging import logger

TOPIC_SUBREDDITS = {
    "aiml": ["MachineLearning", "LocalLLaMA"],
    "cloud": ["kubernetes", "aws", "devops"],
    "security": ["netsec"],
    "devtools": ["programming"],
    "data": ["dataengineering"],
    "web_backend": ["backend"],
    "oss": ["opensource"],
}


class RedditConnector:
    source_key = "reddit"
    trust_tier = 3

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "newsops/0.1",
        timeout: float = 10.0,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.timeout = timeout
        self.is_available = bool(client_id and client_secret)
        self._token: Optional[str] = None

    async def _authenticate(self) -> Optional[str]:
        if not self.is_available:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    data={"grant_type": "client_credentials"},
                    auth=(self.client_id, self.client_secret),
                    headers={"User-Agent": self.user_agent},
                )
                res.raise_for_status()
                return res.json().get("access_token")
        except Exception as e:
            logger.warning(f"Reddit OAuth authentication failed: {e}")
            return None

    async def fetch(self, topics: List[str] = None, limit: int = 15) -> List[dict]:
        if not self.is_available:
            logger.info("Reddit connector skipped: REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not configured.")
            return []

        if not self._token:
            self._token = await self._authenticate()
            if not self._token:
                return []

        topics = topics or ["aiml"]
        subreddits = []
        for t in topics:
            subreddits.extend(TOPIC_SUBREDDITS.get(t, []))
        if not subreddits:
            subreddits = ["programming"]

        articles = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for sub in subreddits[:3]:
                    res = await client.get(
                        f"https://oauth.reddit.com/r/{sub}/hot",
                        params={"limit": 5},
                        headers={
                            "Authorization": f"Bearer {self._token}",
                            "User-Agent": self.user_agent,
                        },
                    )
                    if res.status_code == 200:
                        data = res.json()
                        for child in data.get("data", {}).get("children", []):
                            p = child.get("data", {})
                            created = datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc)
                            articles.append({
                                "title": p.get("title", ""),
                                "url": p.get("url", ""),
                                "text": (p.get("selftext") or "")[:2000],
                                "published_at": created.isoformat(),
                                "source_key": f"reddit/r/{sub}",
                                "trust_tier": self.trust_tier,
                                "topics": topics,
                                "score": p.get("score", 0),
                                "num_comments": p.get("num_comments", 0),
                            })
        except Exception as e:
            logger.warning(f"Reddit fetch warning: {e}")

        return articles[:limit]
