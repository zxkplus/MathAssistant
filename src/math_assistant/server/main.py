"""FastAPI application factory and entry point for the MathAssistant backend."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from math_assistant.server.config import ServerConfig
from math_assistant.server.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize DB on startup, cleanup on shutdown."""
    config: ServerConfig = app.state.config
    init_db(config)
    yield


def create_app(config: ServerConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: ServerConfig instance. If None, loads from default location.

    Returns:
        Configured FastAPI application ready to serve.
    """
    if config is None:
        config = ServerConfig.load()

    app = FastAPI(
        title="MathAssistant Backend",
        description="User management, question tagging, and learning analytics API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.config = config

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers (imported here to avoid circular imports)
    from math_assistant.server.routers import (
        analytics_router,
        auth_router,
        knowledge_points_router,
        questions_router,
    )

    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(
        knowledge_points_router, prefix="/api/knowledge-points", tags=["Knowledge Points"]
    )
    app.include_router(questions_router, prefix="/api/questions", tags=["Questions"])
    app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])

    return app


def main():
    """Entry point: start the uvicorn server."""
    import uvicorn

    config = ServerConfig.load()
    uvicorn.run(
        "math_assistant.server.main:create_app",
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        factory=True,
    )


if __name__ == "__main__":
    main()
