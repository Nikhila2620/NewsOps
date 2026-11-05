"""
NewsOps Revision 2 - Hacker News Connector.

Fetches tech stories using the Algolia HN Search API (hn.algolia.com).
No external credentials required.
"""

from datetime import datetime, timedelta, timezone
from typing import List
import httpx

from ..core.logging import logger

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

TOPIC_QUERIES = {
    "aiml": "AI machine learning LLM",
    "cloud": "kubernetes docker cloud AWS",
    "security": "CVE vulnerability exploit",
    "devtools": "developer tools IDE",
    "data": "database PostgreSQL",
    "web_backend": "FastAPI backend API",
    "oss": "open source release",
}


class HackerNewsConnector:
    source_key = "hackernews"
    trust_tier = 3
    is_available = True

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def fetch(self, topics: List[str] = None, limit: int = 20) -> List[dict]:
        topics = topics or ["aiml", "cloud", "security"]
        query_parts = [TOPIC_QUERIES.get(t, t) for t in topics]
        query = " OR ".join(query_parts) if query_parts else "programming"

        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": min(limit, 50),
            "numericFilters": f"created_at_i>{int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp())}",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(HN_SEARCH_URL, params=params)
                res.raise_for_status()
                data = res.json()

            articles = []
            for hit in data.get("hits", []):
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                articles.append({
                    "title": hit.get("title", ""),
                    "url": url,
                    "text": hit.get("story_text") or "",
                    "published_at": hit.get("created_at", ""),
                    "source_key": self.source_key,
                    "trust_tier": self.trust_tier,
                    "topics": topics,
                    "score": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "author": hit.get("author", ""),
                })
            return articles
        except Exception as e:
            logger.warning(f"HackerNews connector warning: {e}")
            return []
