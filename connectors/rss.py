"""
NewsOps Revision 2 - RSS/Atom Feed Connector.

Parses developer news feeds (dev.to, engineering blogs) via standard XML parsing.
"""

import re
from typing import List
from xml.etree import ElementTree as ET
import httpx

from ..core.logging import logger

DEFAULT_FEEDS = [
    {"url": "https://dev.to/feed", "source_key": "dev_to", "trust_tier": 2, "topics": ["web_backend", "devtools"]},
]


class RSSConnector:
    source_key = "rss"
    trust_tier = 2
    is_available = True

    def __init__(self, feeds: List[dict] = None, timeout: float = 10.0):
        self.feeds = feeds or DEFAULT_FEEDS
        self.timeout = timeout

    async def fetch(self, topics: List[str] = None, limit: int = 20) -> List[dict]:
        topics = topics or ["oss", "devtools"]
        all_articles = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for feed in self.feeds:
                try:
                    res = await client.get(feed["url"], follow_redirects=True)
                    if res.status_code != 200:
                        continue
                    root = ET.fromstring(res.text)
                    channel = root.find("channel")
                    if channel is None:
                        continue

                    for item in channel.findall("item")[:limit]:
                        title = (item.findtext("title") or "").strip()
                        url = (item.findtext("link") or "").strip()
                        desc = (item.findtext("description") or "").strip()
                        desc_clean = re.sub(r"<[^>]+>", "", desc)

                        if title and url:
                            all_articles.append({
                                "title": title,
                                "url": url,
                                "text": desc_clean[:2000],
                                "published_at": item.findtext("pubDate") or "",
                                "source_key": feed["source_key"],
                                "trust_tier": feed["trust_tier"],
                                "topics": feed.get("topics", topics),
                            })
                except Exception as e:
                    logger.warning(f"RSS parse warning for {feed['url']}: {e}")

        return all_articles[:limit]
