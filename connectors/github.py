"""
NewsOps Revision 2 - GitHub Connector.

Fetches trending and newly updated repositories using the GitHub REST API.
Extracts README install commands verbatim and annotates security risk flags.
"""

import base64
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import httpx

from ..core.logging import logger
from ..pipeline.commands import extract_commands_from_readme

GITHUB_API = "https://api.github.com"


class GitHubConnector:
    source_key = "github"
    trust_tier = 1
    is_available = True

    def __init__(self, api_token: Optional[str] = None, timeout: float = 12.0):
        self.api_token = api_token
        self.timeout = timeout

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if self.api_token:
            h["Authorization"] = f"Bearer {self.api_token}"
        return h

    async def _fetch_readme(self, full_name: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{GITHUB_API}/repos/{full_name}/readme", headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("content", "")
                    if data.get("encoding") == "base64":
                        return base64.b64decode(content).decode("utf-8", errors="ignore")
                    return content
        except Exception:
            pass
        return ""

    async def fetch(self, topics: List[str] = None, limit: int = 15) -> List[dict]:
        topics = topics or ["aiml", "devtools"]
        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        query = f"stars:>50 pushed:>{since}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(
                    f"{GITHUB_API}/search/repositories",
                    params={"q": query, "sort": "updated", "order": "desc", "per_page": min(limit, 20)},
                    headers=self._headers(),
                )
                if res.status_code in (401, 403):
                    logger.warning("GitHub rate limit reached or token invalid.")
                    return []
                res.raise_for_status()
                data = res.json()

            articles = []
            for item in data.get("items", [])[:limit]:
                full_name = item.get("full_name", "")
                readme = await self._fetch_readme(full_name)
                commands = extract_commands_from_readme(readme)

                articles.append({
                    "title": f"{full_name}: {item.get('description') or 'Open source repository'}",
                    "url": item.get("html_url"),
                    "text": item.get("description") or "",
                    "readme_text": readme[:4000],
                    "published_at": item.get("pushed_at") or item.get("created_at"),
                    "source_key": self.source_key,
                    "trust_tier": self.trust_tier,
                    "topics": topics,
                    "stars": item.get("stargazers_count", 0),
                    "license": (item.get("license") or {}).get("spdx_id", ""),
                    "extracted_commands": [c["command"] for c in commands],
                    "risk_flags": [f for c in commands for f in c["risk_flags"]],
                    "verified_verbatim": all(c["verified_verbatim"] for c in commands),
                })
            return articles
        except Exception as e:
            logger.warning(f"GitHub connector warning: {e}")
            return []
