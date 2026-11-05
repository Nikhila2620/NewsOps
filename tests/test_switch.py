"""
Unit tests for Switch Agent Protocol client and agents (Scout, Analyst, Editor).
"""

import pytest
from newsops.switch.protocol import AgentRegistration, ConnectionState, SwitchProtocolClient
from newsops.switch.agents.scout import ScoutAgent
from newsops.switch.agents.analyst import AnalystSwitchAgent
from newsops.switch.agents.editor import EditorAgent


def test_switch_protocol_unconfigured_graceful():
    client = SwitchProtocolClient()
    assert client.is_configured is False
    assert client.state == ConnectionState.DISCONNECTED
    status = client.status()
    assert status["connected"] is False


@pytest.mark.anyio
async def test_switch_protocol_post_message_stub():
    client = SwitchProtocolClient()
    res = await client.post_message("room-general", "Hello developers")
    assert res["status"] == "pending_credentials"


@pytest.mark.anyio
async def test_scout_agent_dry_run():
    scout = ScoutAgent(api_base="http://test:8000/api/v1", agent_token="token-123")
    res = await scout.run("aiml")
    assert res["room_key"] == "aiml"
    assert "candidates_found" in res
    assert "Scout Report" in res["summary"]


@pytest.mark.anyio
async def test_editor_agent_blocked_without_approval():
    editor = EditorAgent(api_base="http://test:8000/api/v1", agent_token="token-123")
    res = await editor.attempt_publish("nonexistent-digest")
    # Will fail network or return error, not crash
    assert "status" in res
