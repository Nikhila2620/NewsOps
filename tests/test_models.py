"""
Unit tests for NewsOps MongoDB and Pydantic V2 Domain Models.
"""

import pytest
from newsops.models.digest import Digest, DigestItem, DigestStatus
from newsops.models.invite import InviteCreate, InviteStatus, RoomInvite
from newsops.models.room import Room, RoomCreate, RoomMember
from newsops.models.source import Source
from newsops.models.story import Story, StoryFeedback
from newsops.models.task import Task, TaskCreate, TaskStatus
from newsops.models.user import User, UserProfileUpdate


def test_user_model():
    user = User(_id="user-test", display_name="Developer", chat_handle="@dev")
    doc = user.to_mongo_dict()
    assert doc["_id"] == "user-test"
    assert doc["display_name"] == "Developer"


def test_story_model_validation():
    story = Story(_id="st-01", title="Important Update", rank_score=0.85)
    assert story.rank_score == 0.85

    with pytest.raises(Exception):
        Story(_id="st-bad", title="Bad Score", rank_score=1.5)


def test_task_model():
    task = Task(_id="task-01", requester_id="u1", room_key="aiml", request="Collect AI news")
    assert task.status == TaskStatus.QUEUED
    doc = task.to_mongo_dict()
    assert doc["status"] == "queued"


def test_digest_model_defaults():
    digest = Digest(_id="dig-01", room_key="cloud")
    assert digest.status == DigestStatus.DRAFT
    assert len(digest.items) == 0


def test_room_model():
    room = Room(_id="room-aiml", key="aiml", name="#aiml", approvers=["@alice"])
    assert room.key == "aiml"
    assert "@alice" in room.approvers
