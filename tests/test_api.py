"""
NewsOps Revision 2 - Pytest API Integration Tests.

Tests:
1. GET /healthz and GET /api/v1/healthz
2. Error response structure: { "error": { "code": ..., "message": ..., "task_id": ... } }
3. POST /api/v1/agent/stories/{id}/analysis:
   - 401 Unauthorized without bearer token
   - 401 Unauthorized with wrong token
   - 422 Unprocessable Entity for unsourced / malformed output
   - 200 OK for valid submission, updating story document and persisting evidence
"""

import pytest
from httpx import AsyncClient, ASGITransport
from newsops.main import app
from newsops.config.settings import settings
from newsops.db.mongodb import db_manager


@pytest.fixture(autouse=True)
async def ensure_db():
    """Ensures database is initialized before tests."""
    await db_manager.connect(force_mock=True)
    yield
    await db_manager.disconnect()


@pytest.mark.anyio
async def test_root_healthz_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "NewsOps"
        assert "database" in data
        assert data["database"]["status"] == "connected"


@pytest.mark.anyio
async def test_api_v1_healthz_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.anyio
async def test_centralized_error_format_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/nonexistent-route")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "message" in data["error"]
        assert "task_id" in data["error"]


@pytest.mark.anyio
async def test_agent_analysis_missing_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/agent/stories/story-test-001/analysis",
            json={"analysis": {"summary": "test"}},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.anyio
async def test_agent_analysis_invalid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/agent/stories/story-test-001/analysis",
            headers={"Authorization": "Bearer wrong-token"},
            json={"analysis": {"summary": "test"}},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.anyio
async def test_agent_analysis_valid_submission():
    payload = {
        "story_id": "story-fastapi-v0115",
        "analysis": {
            "summary": "FastAPI version 0.115 introduced internal router optimizations and bugfixes.",
            "why_it_matters": "Improves request dispatching latency for complex route trees.",
            "practical_impact": "Developers will experience lower routing latency on high-throughput microservices.",
            "affected_users": ["fastapi-devs", "backend-engineers"],
            "caveats": [],
            "unknowns": [],
        },
        "claims": [
            {
                "claim_id": "claim-fastapi-01",
                "statement": "FastAPI 0.115 optimizes internal router dispatching.",
                "claim_type": "capability",
            }
        ],
        "verification_results": [
            {
                "claim_id": "claim-fastapi-01",
                "status": "supported",
                "confidence": 0.98,
                "rationale": "Verified against GitHub release notes.",
                "evidence": [
                    {
                        "evidence_url": "https://github.com/fastapi/fastapi/releases/tag/0.115.0",
                        "evidence_type": "primary_source",
                        "source_reference": "GitHub API release tag",
                        "status": "supported",
                        "confidence": 0.98,
                    }
                ],
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/agent/stories/story-fastapi-v0115/analysis",
            headers={"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"},
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["story_id"] == "story-fastapi-v0115"
        assert data["review_required"] is False
        assert data["overall_confidence"] == 0.98
        assert data["evidence_items_count"] == 1

        # Verify that Member 1's stories collection now contains the persisted story
        db = db_manager.get_database()
        story = await db.stories.find_one({"_id": "story-fastapi-v0115"})
        assert story is not None
        assert story["analysis"]["summary"].startswith("FastAPI version 0.115")
        assert story["review_flag"] is False
        assert len(story["evidence"]) == 1
        assert story["evidence"][0]["status"] == "supported"


@pytest.mark.anyio
async def test_agent_analysis_rejects_unsourced_claims():
    # If claims are provided without evidence or verification results, it must be rejected (422)
    payload = {
        "story_id": "story-unverified",
        "analysis": {
            "summary": "Unsubstantiated assertion about a secret LLM breakthrough.",
            "why_it_matters": "Potentially disruptive if true.",
            "practical_impact": "Wait for peer evaluation.",
            "affected_users": ["ai-engineers"],
        },
        "claims": [
            {
                "claim_id": "claim-unverified-01",
                "statement": "Secret model beats GPT-4 by 200%.",
                "claim_type": "benchmark",
            }
        ],
        "verification_results": [],
        "evidence": [],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/agent/stories/story-unverified/analysis",
            headers={"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"},
            json=payload,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "unsourced output" in data["error"]["message"]
