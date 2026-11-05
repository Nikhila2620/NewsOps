"""
NewsOps Revision 2 - Centralized Error Handling.

Standardizes all error responses to the exact contract specified in Revision 2 Section 9:
{ "error": { "code": "...", "message": "safe message", "task_id": "..." } }
"""

import uuid
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import logger

HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class NewsOpsException(Exception):
    """Base application exception for NewsOps."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        task_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.task_id = task_id


class NotFoundError(NewsOpsException):
    def __init__(self, resource: str, item_id: str, task_id: Optional[str] = None):
        super().__init__(
            message=f"{resource} '{item_id}' not found.",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            task_id=task_id,
        )


class UnauthorizedError(NewsOpsException):
    def __init__(self, message: str = "Invalid or missing authentication credentials.", task_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            task_id=task_id,
        )


class ForbiddenError(NewsOpsException):
    def __init__(self, message: str = "Action prohibited without proper approval or role.", task_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            task_id=task_id,
        )


class ConflictError(NewsOpsException):
    def __init__(self, message: str, task_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            task_id=task_id,
        )


class ValidationContractError(NewsOpsException):
    def __init__(self, message: str, task_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=HTTP_422,
            task_id=task_id,
        )


class DatabaseUnavailableError(NewsOpsException):
    def __init__(self, message: str = "Database service is temporarily unreachable.", task_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            task_id=task_id,
        )


def format_error_response(
    code: str,
    message: str,
    status_code: int,
    task_id: Optional[str] = None,
) -> JSONResponse:
    """Produces the standardized NewsOps error JSON body."""
    error_body = {
        "error": {
            "code": code,
            "message": message,
            "task_id": task_id,
        }
    }
    return JSONResponse(status_code=status_code, content=error_body)


async def newsops_exception_handler(request: Request, exc: NewsOpsException) -> JSONResponse:
    """Handles all internal domain exceptions."""
    logger.warning(
        f"Domain error [{exc.code}] on {request.method} {request.url.path}: {exc.message}",
        extra={"task_id": exc.task_id},
    )
    return format_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        task_id=exc.task_id,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Formats Pydantic validation errors into clean, safe API error responses."""
    details = exc.errors()
    summary_messages = []
    for err in details:
        loc = " -> ".join(str(l) for l in err.get("loc", []) if l != "body")
        msg = err.get("msg", "Invalid value")
        summary_messages.append(f"{loc}: {msg}" if loc else msg)

    safe_message = "; ".join(summary_messages) or "Request validation failed."
    task_id = request.headers.get("X-Task-ID")

    logger.warning(
        f"Validation failed on {request.method} {request.url.path}: {safe_message}",
        extra={"task_id": task_id},
    )
    return format_error_response(
        code="VALIDATION_ERROR",
        message=safe_message,
        status_code=HTTP_422,
        task_id=task_id,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard HTTP exceptions (404, 401, 403, etc.)."""
    task_id = request.headers.get("X-Task-ID")
    code = "HTTP_ERROR"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"

    return format_error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
        task_id=task_id,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unanticipated crashes. Logs stack trace internally but returns safe response."""
    safe_task_id = request.headers.get("X-Task-ID") or f"err-{uuid.uuid4().hex[:8]}"
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=exc,
        extra={"task_id": safe_task_id},
    )
    return format_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please reference the task_id.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        task_id=safe_task_id,
    )
