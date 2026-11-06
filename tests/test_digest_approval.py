"""
Integration tests for Digest Approval Gate and Publication Workflow.

CRITICAL NON-NEGOTIABLE SPEC RULE:
POST /digests/{id}/publish MUST return 403 unless the digest status is 'approved'.
"""

import pytest
import uuid
import asyncio
from httpx import ASGITransport, AsyncClient

from newsops.db.mongodb import db_manager
from newsops.main import create_app
from newsops.models.digest import Digest, DigestStatus
from newsops.db.seed import seed_initial_data


@pytest.fixture(autouse=True)
async def ensure_db():
    await db_manager.connect(force_mock=True)
    await seed_initial_data(db_manager.get_database())
    yield
    await db_manager.disconnect()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_publish_unapproved_returns_403(client):
    async with client as c:
        db = db_manager.get_database()
        digest_id = f"dig-{uuid.uuid4().hex[:8]}"

        # Insert draft digest
        digest = Digest(_id=digest_id, room_key="aiml", status=DigestStatus.DRAFT)
        await db.digests.insert_one(digest.to_mongo_dict())

        # Attempt to publish draft -> MUST be 403
        res = await c.post(f"/api/v1/digests/{digest_id}/publish")
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"
        assert "must be in 'approved' status" in res.text


@pytest.mark.anyio
async def test_approve_then_publish_succeeds(client):
    async with client as c:
        db = db_manager.get_database()
        digest_id = f"dig-{uuid.uuid4().hex[:8]}"

        # Insert draft digest
        digest = Digest(_id=digest_id, room_key="aiml", status=DigestStatus.DRAFT)
        await db.digests.insert_one(digest.to_mongo_dict())

        # Step 1: Approve digest (default demo user Alice can approve aiml)
        appr_res = await c.post(f"/api/v1/digests/{digest_id}/approve", json={"comment": "Looks good!"})
        assert appr_res.status_code == 200
        assert appr_res.json()["status"] == "approved"

        # Step 2: Publish approved digest
        pub_res = await c.post(f"/api/v1/digests/{digest_id}/publish")
        assert pub_res.status_code == 200
        data = pub_res.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None


@pytest.mark.anyio
async def test_reject_blocks_publish(client):
    async with client as c:
        db = db_manager.get_database()
        digest_id = f"dig-{uuid.uuid4().hex[:8]}"

        digest = Digest(_id=digest_id, room_key="security", status=DigestStatus.DRAFT)
        await db.digests.insert_one(digest.to_mongo_dict())

        # Reject
        rej_res = await c.post(f"/api/v1/digests/{digest_id}/reject", json={"comment": "Inaccurate claim"})
        assert rej_res.status_code == 200
        assert rej_res.json()["status"] == "rejected"

        # Attempt to publish -> 403
        pub_res = await c.post(f"/api/v1/digests/{digest_id}/publish")
        assert pub_res.status_code == 403


@pytest.mark.anyio
async def test_persona_approval_authorization_gates(client):
    """
    Verifies that:
    - Sam Rivera cannot approve #aiml (returns 403)
    - Sam Rivera CAN approve #cloud (returns 200, reviewer='sam_cloud')
    - Alice Chen cannot approve #cloud (returns 403)
    - Alice Chen CAN approve #aiml (returns 200, reviewer='alice_aiml')
    """
    async with client as c:
        db = db_manager.get_database()

        aiml_dig_id = f"dig-aiml-{uuid.uuid4().hex[:6]}"
        cloud_dig_id = f"dig-cloud-{uuid.uuid4().hex[:6]}"

        await db.digests.insert_one(Digest(_id=aiml_dig_id, room_key="aiml", status=DigestStatus.REVIEW_REQUIRED).to_mongo_dict())
        await db.digests.insert_one(Digest(_id=cloud_dig_id, room_key="cloud", status=DigestStatus.REVIEW_REQUIRED).to_mongo_dict())

        sam_headers = {"Authorization": "Bearer demo-token-sam"}
        alice_headers = {"Authorization": "Bearer demo-token-alice"}

        # 1. Sam tries to approve AIML digest -> 403 Forbidden
        res_sam_aiml = await c.post(f"/api/v1/digests/{aiml_dig_id}/approve", headers=sam_headers)
        assert res_sam_aiml.status_code == 403, f"Expected 403 for Sam approving aiml, got {res_sam_aiml.status_code}"

        # 2. Sam approves Cloud digest -> 200 OK
        res_sam_cloud = await c.post(f"/api/v1/digests/{cloud_dig_id}/approve", headers=sam_headers)
        assert res_sam_cloud.status_code == 200, f"Expected 200 for Sam approving cloud, got {res_sam_cloud.status_code}"
        data_cloud = res_sam_cloud.json()
        assert data_cloud["status"] == "approved"
        assert len(data_cloud["approvals"]) > 0
        assert data_cloud["approvals"][-1]["reviewer"] == "sam_cloud"

        # 3. Alice tries to approve Cloud digest -> 403 Forbidden
        # Reset cloud digest to review_required
        cloud_dig_2 = f"dig-cloud-{uuid.uuid4().hex[:6]}"
        await db.digests.insert_one(Digest(_id=cloud_dig_2, room_key="cloud", status=DigestStatus.REVIEW_REQUIRED).to_mongo_dict())
        res_alice_cloud = await c.post(f"/api/v1/digests/{cloud_dig_2}/approve", headers=alice_headers)
        assert res_alice_cloud.status_code == 403, f"Expected 403 for Alice approving cloud, got {res_alice_cloud.status_code}"

        # 4. Alice approves AIML digest -> 200 OK
        res_alice_aiml = await c.post(f"/api/v1/digests/{aiml_dig_id}/approve", headers=alice_headers)
        assert res_alice_aiml.status_code == 200, f"Expected 200 for Alice approving aiml, got {res_alice_aiml.status_code}"
        data_aiml = res_alice_aiml.json()
        assert data_aiml["status"] == "approved"
        assert data_aiml["approvals"][-1]["reviewer"] == "alice_aiml"


@pytest.mark.anyio
async def test_seeded_initial_digests_exist(client):
    """Verifies that seed data populates initial digests for #aiml, #cloud, and #security."""
    async with client as c:
        res = await c.get("/api/v1/digests")
        assert res.status_code == 200
        digests = res.json()
        room_keys = {d["room_key"] for d in digests}
        assert "aiml" in room_keys
        assert "cloud" in room_keys
        assert "security" in room_keys


@pytest.mark.anyio
async def test_task_pipeline_execution(client):
    """Verifies that POST /tasks runs in background and transitions status."""
    async with client as c:
        res = await c.post("/api/v1/tasks", json={
            "request": "Collect cloud infrastructure releases",
            "room_id": "cloud",
            "approval_required": True,
        })
        assert res.status_code == 201
        task_id = res.json()["task_id"]

        # Allow background task to execute
        await asyncio.sleep(0.5)

        get_res = await c.get(f"/api/v1/tasks/{task_id}")
        assert get_res.status_code == 200
        task_data = get_res.json()
        assert task_data["status"] in ("collecting", "processing", "review_required", "published")
        assert task_data["progress"] > 0.0
