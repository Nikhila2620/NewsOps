"""
NewsOps Revision 2 - Tasks API Endpoints.

Implements POST /tasks, GET /tasks/{id}, and GET /tasks as specified in Revision 2 Section 9.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.errors import NotFoundError
from ..core.logging import logger
from ..db.mongodb import get_db
from ..models.task import Task, TaskCreate, TaskCreatedResponse, TaskStatus
from ..models.user import User
from .deps import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ingestion / digest task",
)
async def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Submits an ingestion/ranking task (NewsOps Revision 2 Section 9).
    Initial status: 'queued'.
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
