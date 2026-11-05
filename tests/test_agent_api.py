"""
NewsOps Revision 2 - Agent API & CLI Integration Tests.

Verifies:
- 401 Unauthorized without token / with invalid token
- Idempotent analysis resubmissions
- 403 Publish gate on unapproved digests
- Approver check (non-approver 403, approver 200)
- Room candidates respect limit (max 8)
- Community-signal alone rejected from proving supported (422)
- Activity logging and transparent GET
"""

import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from newsops.main import app
from newsops.config.settings import settings
from newsops.db.mongodb import db_manager
from newsops.db.seed import seed_initial_data


@pytest.fixture(autouse=True)
async def ensure_db():
    await db_manager.connect(force_mock=True)
    await seed_initial_data(db_manager.db)
    yield
    await db_manager.disconnect()


@pytest.mark.anyio
async def test_agent_endpoints_unauthorized_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # candidates without token
        resp = await client.get("/api/v1/agent/candidates?room=aiml")
        assert resp.status_code == 401

        # candidates with wrong token
        resp_wrong = await client.get(
            "/api/v1/agent/candidates?room=aiml",
            headers={"Authorization": "Bearer wrong-token-1234"},
        )
        assert resp_wrong.status_code == 401

        # activity POST without token
        resp_act = await client.post(
            "/api/v1/agent/activity",
            json={"agent": "scout", "room": "aiml", "action": "test", "message": "msg"},
        )
        assert resp_act.status_code == 401


@pytest.mark.anyio
async def test_agent_activity_transparent_read():
    token_headers = {"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Post activity with token
        post_resp = await client.post(
            "/api/v1/agent/activity",
            json={"agent": "scout", "room": "aiml", "action": "scan", "message": "Scout running"},
            headers=token_headers,
        )
        assert post_resp.status_code == 201

        # Read activity WITHOUT token (public/transparent read-only)
        get_resp = await client.get("/api/v1/agent/activity?room=aiml")
        assert get_resp.status_code == 200
        activities = get_resp.json()
        assert len(activities) >= 1
        assert activities[0]["agent"] == "scout"


@pytest.mark.anyio
async def test_agent_candidates_limit_and_room_rules():
    token_headers = {"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/agent/candidates?room=aiml&limit=20", headers=token_headers)
        assert resp.status_code == 200
        candidates = resp.json()
        # Max limit is capped at 8 per specification
        assert len(candidates) <= 8


@pytest.mark.anyio
async def test_agent_story_evidence_and_404():
    token_headers = {"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid story evidence
        resp = await client.get("/api/v1/agent/stories/story-aiml-001/evidence", headers=token_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["story_id"] == "story-aiml-001"
        assert "evidence" in data
        assert data["install_command"] == "pip install vllm>=0.6.4"

        # Missing story 404
        resp_404 = await client.get("/api/v1/agent/stories/nonexistent-999/evidence", headers=token_headers)
        assert resp_404.status_code == 404


@pytest.mark.anyio
async def test_idempotent_analysis_resubmit():
    token_headers = {"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"}
    fixtures_path = Path(__file__).resolve().parent.parent / "fixtures" / "example_analysis_submission.json"
    with open(fixtures_path, "r", encoding="utf-8") as f:
        submission = json.load(f)

    # Point submission to seeded story-aiml-001
    submission["story_id"] = "story-aiml-001"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First submission
        r1 = await client.post("/api/v1/agent/stories/story-aiml-001/analysis", json=submission, headers=token_headers)
        assert r1.status_code == 200

        # Idempotent re-submission
        r2 = await client.post("/api/v1/agent/stories/story-aiml-001/analysis", json=submission, headers=token_headers)
        assert r2.status_code == 200


@pytest.mark.anyio
async def test_community_only_supported_rejected():
    token_headers = {"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"}
    fixtures_path = Path(__file__).resolve().parent.parent / "fixtures" / "example_analysis_submission.json"
    with open(fixtures_path, "r", encoding="utf-8") as f:
        bad_submission = json.load(f)

    bad_submission["story_id"] = "story-aiml-001"
    # Change evidence to community_signal but claim status supported -> must be rejected
    for res in bad_submission["verification_results"]:
        for ev in res["evidence"]:
            ev["evidence_type"] = "community_signal"
            ev["status"] = "supported"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/agent/stories/story-aiml-001/analysis", json=bad_submission, headers=token_headers)
        # Rejection via Pydantic contract validation
        assert resp.status_code == 422


@pytest.mark.anyio
async def test_publish_gate_and_approver_check():
    token_headers = {"Authorization": f"Bearer {settings.AGENT_API_TOKEN}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create draft digest
        dig_resp = await client.post(
            "/api/v1/agent/digests",
            json={"room_key": "aiml", "story_ids": ["story-aiml-001"]},
            headers=token_headers,
        )
        assert dig_resp.status_code == 201
        digest = dig_resp.json()
        digest_id = digest["_id"]
        assert digest["status"] == "draft"

        # Non-negotiable 403 Publish Gate: Cannot publish unapproved draft
        pub_resp = await client.post(f"/api/v1/digests/{digest_id}/publish", headers=token_headers)
        assert pub_resp.status_code == 403

        # Approver check: Unauthorized person gets 403
        dec_unauth = await client.post(
            f"/api/v1/agent/digests/{digest_id}/decision",
            json={"decision": "approve", "by": "@intruder"},
            headers=token_headers,
        )
        assert dec_unauth.status_code == 403

        # Authorized approver from room rules (e.g. lead_reviewer)
        dec_auth = await client.post(
            f"/api/v1/agent/digests/{digest_id}/decision",
            json={"decision": "approve", "by": "lead_reviewer"},
            headers=token_headers,
        )
        assert dec_auth.status_code == 200
        assert dec_auth.json()["status"] == "approved"

        # Now publishing succeeds
        pub_ok = await client.post(f"/api/v1/digests/{digest_id}/publish", headers=token_headers)
        assert pub_ok.status_code == 200
        assert pub_ok.json()["status"] == "published"


@pytest.mark.anyio
async def test_switch_status_honesty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/switch/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents call NewsOps via CLI" in data["message"]
        assert "last_activity_at" in data
        assert "connected" not in data  # removed misleading connection flags
