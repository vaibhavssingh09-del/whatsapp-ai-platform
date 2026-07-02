"""
Application entrypoint.

Design decision: DB connect/disconnect and index creation happen in an
`asynccontextmanager` lifespan (FastAPI's recommended pattern over the
deprecated `@app.on_event`), so the Mongo client's lifetime is explicitly
tied to the app process's lifetime rather than lazily created on first use
(which would make the first request after a cold start unpredictably slow
and would make startup failures show up as a confusing runtime 500 instead
of a clear boot-time crash).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, broadcasts, conversations, dashboard, media, tenants, webhook
from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.logging import configure_logging, get_logger
from app.middleware.logging_middleware import RequestLoggingMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    logger.info("app_startup_complete")
    yield
    await close_mongo_connection()
    logger.info("app_shutdown_complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Returned shape matches HTTPException's {"detail": ...} so frontend
        # error handling doesn't need two different branches for "bad input"
        # vs "business logic error" — see frontend/src/api/client.js.
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.warning("value_error", error=str(exc))
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    api_prefix = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(tenants.router, prefix=api_prefix)
    app.include_router(webhook.router, prefix=api_prefix)
    app.include_router(conversations.router, prefix=api_prefix)
    app.include_router(media.router, prefix=api_prefix)
    app.include_router(broadcasts.router, prefix=api_prefix)
    app.include_router(dashboard.router, prefix=api_prefix)

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app


app = create_app()
