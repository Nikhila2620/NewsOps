"""
Integration tests for Digest Approval Gate and Publication Workflow.

CRITICAL NON-NEGOTIABLE SPEC RULE:
POST /digests/{id}/publish MUST return 403 unless the digest status is 'approved'.
"""

import pytest
import uuid
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

        # Step 1: Approve digest
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
