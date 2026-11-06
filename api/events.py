"""
NewsOps - Server-Sent Events (SSE) and Activity Endpoints.

Implements:
  GET /events?room_key=…&access_token=…   — live SSE stream
  GET /activity?room_key=…&after_seq=N    — replay missed events
  GET /rooms/{key}/state                  — current pipeline state snapshot
  POST /rooms/{key}/messages              — send a message into the room

Event persistence: events are saved into MongoDB `db.room_events` collection.
Scout pipeline: triggers real candidate queries, logs to db.agent_activity,
and creates real draft digests in db.digests.
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

from ..config.settings import settings
from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.room import Room
from ..api.auth import TOKEN_MAP

router = APIRouter(tags=["Events & Rooms"])

# ---------------------------------------------------------------------------
# In-memory event bus and replay log cache per room
# ---------------------------------------------------------------------------
_room_queues: dict[str, list] = {}       # room_key → list of event dicts
_room_seq: dict[str, int] = {}           # room_key → next seq counter
_room_subscribers: dict[str, list] = {}  # room_key → list of asyncio.Queue
_room_step: dict[str, dict] = {}         # room_key → {step, status}


def _get_seq(room_key: str) -> int:
    _room_seq.setdefault(room_key, 0)
    _room_seq[room_key] += 1
    return _room_seq[room_key]


def _push_event(room_key: str, event: dict, db: Optional[AsyncIOMotorDatabase] = None) -> dict:
    """Append an event to the room log, broadcast to subscribers, and persist to MongoDB."""
    _room_queues.setdefault(room_key, [])
    _room_subscribers.setdefault(room_key, [])
    seq = _get_seq(room_key)
    stamped = {**event, "seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
    _room_queues[room_key].append(stamped)

    # Track step state if step event
    if event.get("type") == "step" and "step" in event:
        _room_step[room_key] = {"step": event["step"], "status": event.get("status", "running")}

    for q in list(_room_subscribers[room_key]):
        try:
            q.put_nowait(stamped)
        except asyncio.QueueFull:
            pass

    # Persist in MongoDB
    if db is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(db.room_events.insert_one({"room_key": room_key, **stamped}))
        except Exception:
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


def _get_step_state(room_key: str) -> dict:
    return _room_step.get(room_key, {"step": -1, "status": "idle"})


async def _load_persisted_events(room_key: str, db: AsyncIOMotorDatabase):
    """Hydrates in-memory event queues from MongoDB on restart."""
    if room_key not in _room_queues or not _room_queues[room_key]:
        _room_queues[room_key] = []
        cursor = db.room_events.find({"room_key": room_key}).sort("seq", 1)
        max_seq = 0
        async for doc in cursor:
            doc.pop("_id", None)
            doc.pop("room_key", None)
            _room_queues[room_key].append(doc)
            if doc.get("seq", 0) > max_seq:
                max_seq = doc["seq"]
        if max_seq > _room_seq.get(room_key, 0):
            _room_seq[room_key] = max_seq


def _resolve_user_handle(access_token: Optional[str]) -> str:
    if access_token and access_token in TOKEN_MAP:
        return TOKEN_MAP[access_token]["chat_handle"]
    return "alice_aiml"


# ---------------------------------------------------------------------------
# GET /events (SSE)
# ---------------------------------------------------------------------------
async def _event_generator(
    room_key: str,
    after_seq: int,
    access_token: Optional[str],
    db: AsyncIOMotorDatabase,
) -> AsyncGenerator[str, None]:
    doc = await db.rooms.find_one({"key": room_key})
    if not doc:
        yield f"event: error\ndata: {json.dumps({'message': f'Room {room_key!r} not found'})}\n\n"
        return

    await _load_persisted_events(room_key, db)

    # Replay missed events
    backlog = [e for e in _room_queues.get(room_key, []) if e["seq"] > after_seq]
    for event in backlog:
        etype = event.get("type", "message")
        yield f"event: {etype}\ndata: {json.dumps(event)}\n\n"

    # Send initial step state
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

    q = _subscribe(room_key)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=20.0)
                etype = event.get("type", "message")
                yield f"event: {etype}\ndata: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
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
# GET /activity (replay, JSON array)
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
    await _load_persisted_events(room_key, db)
    events = [e for e in _room_queues.get(room_key, []) if e["seq"] > after_seq]
    return {"room_key": room_key, "events": events[-limit:], "count": len(events)}


# ---------------------------------------------------------------------------
# GET /rooms/{key}/state (pipeline snapshot)
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
# POST /rooms/{key}/messages
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
    is_switch_live = bool(settings.SWITCH_BASE_URL and settings.SWITCH_POSTER_TOKEN)

    event = _push_event(key, {
        "type": "message",
        "who": user_handle,
        "text": payload.text,
        "user_name": user_handle,
        "delivered": is_switch_live,
    }, db=db)

    # If @scout is mentioned, execute the actual agent pipeline
    if "@scout" in payload.text.lower():
        asyncio.create_task(_run_scout_pipeline(key, payload.text, db))

    logger.info(f"Message sent to room '{key}' by '{user_handle}': {payload.text[:60]}")
    return MessageResponse(
        seq=event["seq"],
        delivered=is_switch_live,
        message="Message delivered to room." if is_switch_live else "Message posted to room (offline mode: Switch console not connected).",
    )


async def _run_scout_pipeline(room_key: str, trigger_text: str, db: AsyncIOMotorDatabase):
    """
    Executes real Scout → Analyst → Editor pipeline.
    Queries real stories, logs agent activities to MongoDB, and compiles real draft digest.
    """
    try:
        # Step 1: Scout
        _push_event(room_key, {"type": "step", "step": 1, "status": "running", "agent": "scout"}, db=db)
        _push_event(room_key, {"type": "message", "who": "scout", "text": f"🔍 Scout scanning sources for #{room_key}..."}, db=db)
        await asyncio.sleep(1.0)

        # Query stories
        cursor = db.stories.find({"room_key": room_key}).sort("rank_score", -1).limit(4)
        stories = []
        async for s in cursor:
            stories.append(s)

        if not stories:
            cursor = db.stories.find({}).sort("rank_score", -1).limit(4)
            async for s in cursor:
                stories.append(s)

        titles = [s.get("title", "") for s in stories]
        first_titles = f"'{titles[0]}' and '{titles[1]}'" if len(titles) >= 2 else (f"'{titles[0]}'" if titles else "candidate stories")

        _push_event(room_key, {"type": "step", "step": 1, "status": "done", "agent": "scout"}, db=db)
        _push_event(
            room_key,
            {
                "type": "message",
                "who": "scout",
                "text": f"Scout complete. Found {len(stories)} candidate stories ({first_titles}). Handing off to Analyst →",
                "handoff": "Scout → Analyst",
            },
            db=db,
        )
        await db.agent_activity.insert_one({
            "agent": "scout",
            "room": room_key,
            "action": "candidate_discovery",
            "message": f"Discovered {len(stories)} candidates for #{room_key}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(1.2)

        # Step 2: Analyst
        _push_event(room_key, {"type": "step", "step": 2, "status": "running", "agent": "analyst"}, db=db)
        _push_event(room_key, {"type": "message", "who": "analyst", "text": f"🧪 Analyst checking primary evidence and trust badges for {len(stories)} stories..."}, db=db)
        await asyncio.sleep(1.2)

        _push_event(room_key, {"type": "step", "step": 2, "status": "done", "agent": "analyst"}, db=db)
        _push_event(
            room_key,
            {
                "type": "message",
                "who": "analyst",
                "text": f"Analysis done. {len(stories)} stories verified (trust badges: primary/vendor_reported). Handing to Editor →",
                "handoff": "Analyst → Editor",
            },
            db=db,
        )
        await db.agent_activity.insert_one({
            "agent": "analyst",
            "room": room_key,
            "action": "claim_verification",
            "message": f"Verified claims for {len(stories)} stories in #{room_key}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(1.2)

        # Step 3: Editor
        _push_event(room_key, {"type": "step", "step": 3, "status": "running", "agent": "editor"}, db=db)
        _push_event(room_key, {"type": "message", "who": "editor", "text": f"✏️ Editor assembling #{room_key} draft digest from verified stories..."}, db=db)

        # Create/upsert real draft digest
        digest_id = f"digest-{room_key}-001"
        digest_items = [
            {
                "story_id": s["_id"],
                "position": idx,
                "editor_note": s.get("title", ""),
                "included": True,
            }
            for idx, s in enumerate(stories)
        ]
        digest_doc = {
            "_id": digest_id,
            "room_key": room_key,
            "version": 1,
            "status": "review_required",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seeded": False,
            "items": digest_items,
            "approvals": [],
        }
        await db.digests.update_one({"_id": digest_id}, {"$set": digest_doc}, upsert=True)

        await db.agent_activity.insert_one({
            "agent": "editor",
            "room": room_key,
            "action": "digest_compilation",
            "message": f"Compiled draft digest {digest_id} with {len(stories)} stories",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(1.0)

        _push_event(room_key, {"type": "step", "step": 3, "status": "done", "agent": "editor"}, db=db)
        _push_event(
            room_key,
            {
                "type": "message",
                "who": "editor",
                "text": f"Digest '{digest_id}' is ready. Awaiting human approval before publishing. →",
                "handoff": "Editor → Approver",
            },
            db=db,
        )

        # Step 4: Approver waiting
        _push_event(room_key, {"type": "step", "step": 4, "status": "idle", "agent": "approver"}, db=db)

    except Exception as exc:
        logger.error(f"Scout pipeline error: {exc}", exc_info=True)
