"""
NewsOps Revision 2 - FastAPI Application Entrypoint.

Configures application lifecycle, MongoDB 7 database connectivity,
structured logging, centralized error handling, and routing.
"""

import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import settings
from .core.logging import logger
from .core.errors import (
    NewsOpsException,
    newsops_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from .db.mongodb import db_manager
from .db.indexes import create_indexes
from .db.seed import seed_initial_data
from .api.router import api_v1_router
from .api.health import router as root_health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager for startup and graceful shutdown.
    """
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' environment...")
    # 1. Connect database (MongoDB 7 with resilient mock fallback)
    await db_manager.connect()
    db = db_manager.get_database()

    # 2. Idempotent indexes
    await create_indexes(db)

    # 3. Initial seed data
    await seed_initial_data(db)

    logger.info(f"{settings.APP_NAME} initialization complete. Ready to receive requests.")
    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await db_manager.disconnect()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=f"{settings.APP_NAME} Backend",
        description="NewsOps Revision 2 Developer Intelligence Engine and Agent Coordination API",
        version="2.0.0-rev2",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Context & Tracing Middleware
    @app.middleware("http")
    async def add_context_headers(request: Request, call_next):
        task_id = request.headers.get("X-Task-ID") or f"task-{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Task-ID"] = task_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)",
            extra={"task_id": task_id},
        )
        return response

    # Centralized Error Handlers
    app.add_exception_handler(NewsOpsException, newsops_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Mount Routes
    app.include_router(root_health_router)  # /healthz at root
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)  # /api/v1/*

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "newsops.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.APP_ENV == "dev",
    )
