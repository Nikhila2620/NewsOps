"""
NewsOps Revision 2 - Tasks API Endpoints.

Implements POST /tasks, GET /tasks/{id}, and GET /tasks as specified in Revision 2 Section 9.
Executes ingestion/digest creation pipeline in background so tasks do not remain queued forever.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.task import Task, TaskCreate, TaskCreatedResponse, TaskStatus
from ..models.user import User
from .deps import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def run_task_pipeline(task_id: str, db: AsyncIOMotorDatabase) -> None:
    """
    Executes the ingestion and digest pipeline for a created task.
    Transitions task through COLLECTING -> PROCESSING -> REVIEW_REQUIRED/PUBLISHED.
    """
    try:
        # 1. Collecting stage
        await db.tasks.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "status": TaskStatus.COLLECTING.value,
                    "stage": "collecting",
                    "progress": 0.25,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        task_doc = await db.tasks.find_one({"_id": task_id})
        if not task_doc:
            return

        room_key = task_doc.get("room_key")
        topics = task_doc.get("topics", [])
        approval_required = task_doc.get("approval_required", True)

        # 2. Processing stage
        await db.tasks.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "status": TaskStatus.PROCESSING.value,
                    "stage": "processing",
                    "progress": 0.70,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        # Find matching stories in DB
        query = {}
        if room_key:
            query["room_key"] = room_key
        elif topics:
            query["topics"] = {"$in": topics}

        cursor = db.stories.find(query).sort("rank_score", -1).limit(8)
        stories = []
        async for s in cursor:
            stories.append(s)

        if not stories:
            cursor = db.stories.find({}).sort("rank_score", -1).limit(4)
            async for s in cursor:
                stories.append(s)

        # 3. Create digest if room is targeted and approval required
        if room_key and approval_required:
            digest_id = f"digest-{room_key}-{task_id[-6:]}"
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
                "task_id": task_id,
                "version": 1,
                "status": "review_required",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "items": digest_items,
                "approvals": [],
            }
            await db.digests.update_one({"_id": digest_id}, {"$set": digest_doc}, upsert=True)

            await db.tasks.update_one(
                {"_id": task_id},
                {
                    "$set": {
                        "status": TaskStatus.REVIEW_REQUIRED.value,
                        "stage": "review_required",
                        "progress": 1.0,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            logger.info(f"Task '{task_id}' created draft digest '{digest_id}' and is awaiting review")
        else:
            await db.tasks.update_one(
                {"_id": task_id},
                {
                    "$set": {
                        "status": TaskStatus.PUBLISHED.value,
                        "stage": "completed",
                        "progress": 1.0,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            logger.info(f"Task '{task_id}' completed successfully")

    except Exception as exc:
        logger.error(f"Task '{task_id}' failed: {exc}", exc_info=True)
        await db.tasks.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "status": TaskStatus.FAILED.value,
                    "stage": "failed",
                    "error_safe": f"Processing error: {str(exc)[:100]}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )


@router.post(
    "",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ingestion / digest task",
)
async def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Submits an ingestion/ranking task (NewsOps Revision 2 Section 9).
    Dispatches background pipeline execution.
    Returns {task_id, status}.
    """
    task = Task(
        requester_id=current_user.id,
        room_key=payload.room_id,
        request=payload.request,
        since_hours=payload.since_hours,
        topics=payload.topics or current_user.topics,
        status=TaskStatus.QUEUED,
        stage="queued",
        progress=0.0,
        approval_required=payload.approval_required,
    )

    await db.tasks.insert_one(task.to_mongo_dict())

    # Dispatch pipeline runner in background
    background_tasks.add_task(run_task_pipeline, task.id, db)

    logger.info(
        f"Created task '{task.id}' for request '{payload.request}' (topics: {task.topics})",
        extra={"task_id": task.id, "stage": "task_created"},
    )

    return TaskCreatedResponse(task_id=task.id, status=task.status.value)


@router.get("/{id}", response_model=Task, summary="Get task execution status and progress")
async def get_task(id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Returns stage, status, progress, and safe error details for a task."""
    doc = await db.tasks.find_one({"_id": id})
    if not doc:
        raise NotFoundError("Task", id, task_id=id)
    return Task(**doc)


@router.get("", response_model=List[Task], summary="List and filter tasks")
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    room_key: Optional[str] = Query(None, description="Filter by room key"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Lists tasks with filtering and pagination."""
    query = {}
    if status:
        query["status"] = status.value
    if room_key:
        query["room_key"] = room_key

    cursor = db.tasks.find(query).sort("created_at", -1).skip(skip).limit(limit)
    tasks = []
    async for doc in cursor:
        tasks.append(Task(**doc))
    return tasks
