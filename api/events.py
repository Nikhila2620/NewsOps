"""
NewsOps - Server-Sent Events (SSE) and Activity Endpoints.

Implements:
  GET /events?room_key=…&access_token=…   — live SSE stream
  GET /activity?room_key=…&after_seq=N    — replay missed events
  GET /rooms/{key}/state                  — current pipeline state snapshot
  POST /rooms/{key}/messages              — send a message into the room
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.room import Room
from ..api.auth import TOKEN_MAP

router = APIRouter(tags=["Events & Rooms"])

# ---------------------------------------------------------------------------
# In-memory event bus (per room).  A real deployment would use Redis Pub/Sub.
# For the demo/hackathon this is sufficient — the process is single-worker.
# ---------------------------------------------------------------------------
_room_queues: dict[str, list] = {}   # room_key → list of event dicts (append-only log)
_room_seq: dict[str, int] = {}       # room_key → next seq counter
_room_subscribers: dict[str, list] = {}  # room_key → list of asyncio.Queue


def _get_seq(room_key: str) -> int:
    _room_seq.setdefault(room_key, 0)
    _room_seq[room_key] += 1
    return _room_seq[room_key]


def _push_event(room_key: str, event: dict) -> dict:
    """Append an event to the room log and broadcast to subscribers."""
    _room_queues.setdefault(room_key, [])
    _room_subscribers.setdefault(room_key, [])
    seq = _get_seq(room_key)
    stamped = {**event, "seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
    _room_queues[room_key].append(stamped)
    for q in list(_room_subscribers[room_key]):
        try:
            q.put_nowait(stamped)
        except asyncio.QueueFull:
            pass
    return stamped


def _subscribe(room_key: str) -> asyncio.Queue:
    _room_subscribers.setdefault(room_key, [])
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _room_subscribers[room_key].append(q)
    return q


def _unsubscribe(room_key: str, q: asyncio.Queue):
    try:
        _room_subscribers.get(room_key, []).remove(q)
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Pipeline step state per room (step -1..4, status idle/running/done/rejected)
# ---------------------------------------------------------------------------
_room_step: dict[str, dict] = {}  # room_key → {step, status}

_STEP_AGENTS = {-1: "idle", 0: "scout", 1: "scout", 2: "analyst", 3: "editor", 4: "approver"}


def _get_step_state(room_key: str) -> dict:
    return _room_step.get(room_key, {"step": -1, "status": "idle"})


# ---------------------------------------------------------------------------
# Helper: resolve user from bearer token (demo) or default
# ---------------------------------------------------------------------------
def _resolve_user_handle(access_token: Optional[str]) -> str:
    if access_token and access_token in TOKEN_MAP:
        return TOKEN_MAP[access_token]["chat_handle"]
    return "alice_aiml"  # default demo user


# ---------------------------------------------------------------------------
# GET /events   (SSE)
# ---------------------------------------------------------------------------
async def _event_generator(
    room_key: str,
    after_seq: int,
    access_token: Optional[str],
    db: AsyncIOMotorDatabase,
) -> AsyncGenerator[str, None]:
    # Verify room exists
    doc = await db.rooms.find_one({"key": room_key})
    if not doc:
        yield f"event: error\ndata: {json.dumps({'message': f'Room {room_key!r} not found'})}\n\n"
        return

    # Replay missed events
    backlog = [e for e in _room_queues.get(room_key, []) if e["seq"] > after_seq]
    for event in backlog:
        etype = event.get("type", "message")
        yield f"event: {etype}\ndata: {json.dumps(event)}\n\n"

    # Send initial step state as a step event
    step_state = _get_step_state(room_key)
    init_event = {
        "type": "step",
        "seq": 0,
        "step": step_state["step"],
        "status": step_state["status"],
        "ts": datetime.now(timezone.utc).isoformat(),
        "system": True,
    }
    yield f"event: step\ndata: {json.dumps(init_event)}\n\n"

    # Subscribe and stream live events
    q = _subscribe(room_key)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=20.0)
                etype = event.get("type", "message")
                yield f"event: {etype}\ndata: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat keep-alive
                yield f": heartbeat {int(time.time())}\n\n"
    finally:
        _unsubscribe(room_key, q)


@router.get(
    "/events",
    summary="SSE stream of room events (messages, steps, digests, stories)",
)
async def stream_events(
    room_key: str = Query(..., description="Room key, e.g. 'aiml'"),
    after_seq: int = Query(0, alias="after_seq"),
    access_token: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return StreamingResponse(
        _event_generator(room_key, after_seq, access_token, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# GET /activity  (replay, JSON array)
# ---------------------------------------------------------------------------
@router.get(
    "/activity",
    summary="Replay room events since a sequence number",
)
async def get_activity(
    room_key: str = Query(...),
    after_seq: int = Query(0, alias="after_seq"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.rooms.find_one({"key": room_key})
    if not doc:
        raise NotFoundError("Room", room_key)
    events = [e for e in _room_queues.get(room_key, []) if e["seq"] > after_seq]
    return {"room_key": room_key, "events": events[-limit:], "count": len(events)}


# ---------------------------------------------------------------------------
# GET /rooms/{key}/state  (pipeline snapshot)
# ---------------------------------------------------------------------------
@router.get(
    "/rooms/{key}/state",
    summary="Get current pipeline state for a room",
)
async def get_room_state(
    key: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.rooms.find_one({"key": key}) or await db.rooms.find_one({"_id": key})
    if not doc:
        raise NotFoundError("Room", key)

    room = Room(**doc)
    step_state = _get_step_state(key)

    # Fetch latest digest for this room
    digest_doc = await db.digests.find_one(
        {"room_key": key},
        sort=[("created_at", -1)],
    )
    digest_info = None
    if digest_doc:
        digest_info = {
            "id": digest_doc.get("_id"),
            "status": digest_doc.get("status"),
            "item_count": len(digest_doc.get("items", [])),
        }

    return {
        "room_key": key,
        "room_name": room.name,
        "step": step_state["step"],
        "status": step_state["status"],
        "agents": ["scout", "analyst", "editor"],
        "approvers": room.approvers,
        "chat_channel_id": room.chat_channel_id,
        "digest": digest_info,
        "last_seq": _room_seq.get(key, 0),
    }


# ---------------------------------------------------------------------------
# POST /rooms/{key}/messages  (send a message, broadcasts as SSE event)
# ---------------------------------------------------------------------------
class MessageRequest(BaseModel):
    text: str
    access_token: Optional[str] = None


class MessageResponse(BaseModel):
    seq: int
    delivered: bool
    message: str


@router.post(
    "/rooms/{key}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to a room (triggers agent pipeline if @scout mentioned)",
)
async def send_room_message(
    key: str,
    payload: MessageRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.rooms.find_one({"key": key}) or await db.rooms.find_one({"_id": key})
    if not doc:
        raise NotFoundError("Room", key)

    user_handle = _resolve_user_handle(payload.access_token)

    event = _push_event(key, {
        "type": "message",
        "who": user_handle,
        "text": payload.text,
        "user_name": user_handle,
        "delivered": True,
    })

    # If @scout is mentioned, simulate the agent pipeline start
    if "@scout" in payload.text.lower():
        asyncio.get_event_loop().call_later(0.5, _simulate_pipeline, key, payload.text)

    logger.info(f"Message sent to room '{key}' by '{user_handle}': {payload.text[:60]}")
    return MessageResponse(
        seq=event["seq"],
        delivered=True,
        message="Message delivered to room.",
    )


def _simulate_pipeline(room_key: str, trigger_text: str):
    """
    Simulate Scout → Analyst → Editor pipeline steps for demo mode.
    Fires step events with delays using call_later chaining.
    """
    loop = asyncio.get_event_loop()

    def push_step(step: int, agent: str, delay: float, extra: dict = {}):
        loop.call_later(delay, lambda: _push_event(room_key, {
            "type": "step", "step": step, "status": "running",
            "agent": agent, **extra,
        }))

    def push_message(who: str, text: str, delay: float, handoff: str = None):
        ev = {"type": "message", "who": who, "text": text}
        if handoff:
            ev["handoff"] = handoff
        loop.call_later(delay, lambda: _push_event(room_key, ev))

    def push_done(step: int, agent: str, delay: float):
        loop.call_later(delay, lambda: _push_event(room_key, {
            "type": "step", "step": step, "status": "done", "agent": agent,
        }))

    # Scout (step 1)
    push_step(1, "scout", 0.5)
    push_message("scout", f"🔍 Scanning sources for '{trigger_text}'...", 1.0)
    push_done(1, "scout", 3.0)
    push_message("scout", "Scout complete. 3 candidates found. Handing off to Analyst →", 3.2,
                 handoff="Scout → Analyst")
    # Analyst (step 2)
    push_step(2, "analyst", 3.5)
    push_message("analyst", "🧪 Verifying claims and checking evidence...", 4.0)
    push_done(2, "analyst", 7.0)
    push_message("analyst", "Analysis done. 2 stories verified (confidence ≥ 0.80). Handing to Editor →", 7.2,
                 handoff="Analyst → Editor")
    # Editor (step 3)
    push_step(3, "editor", 7.5)
    push_message("editor", "✏️ Assembling digest...", 8.0)
    push_done(3, "editor", 10.0)
    push_message("editor", "Digest ready. Awaiting human approval before publishing. →", 10.2,
                 handoff="Editor → Approver")
    # Approver (step 4 — waiting)
    loop.call_later(10.5, lambda: _push_event(room_key, {
        "type": "step", "step": 4, "status": "idle", "agent": "approver",
    }))
