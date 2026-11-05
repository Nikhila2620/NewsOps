"""
Unit tests for NewsOps Source Connectors.
"""

import pytest
from newsops.connectors.base import SourceConnector
from newsops.connectors.github import GitHubConnector
from newsops.connectors.hackernews import HackerNewsConnector
from newsops.connectors.reddit import RedditConnector
from newsops.connectors.rss import RSSConnector


def test_connector_protocol_conformance():
    hn = HackerNewsConnector()
    assert isinstance(hn, SourceConnector)
    assert hn.source_key == "hackernews"
    assert hn.trust_tier == 3
    assert hn.is_available is True

    gh = GitHubConnector()
    assert isinstance(gh, SourceConnector)
    assert gh.source_key == "github"
    assert gh.trust_tier == 1

    rss = RSSConnector()
    assert isinstance(rss, SourceConnector)
    assert rss.source_key == "rss"


def test_reddit_uncredentialed_behavior():
    reddit = RedditConnector(client_id=None, client_secret=None)
    assert reddit.is_available is False


@pytest.mark.anyio
async def test_reddit_fetch_without_credentials_returns_empty():
    reddit = RedditConnector()
    items = await reddit.fetch(["aiml"])
    assert items == []
