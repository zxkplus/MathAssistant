"""Database engine, session factory, and Base for SQLAlchemy ORM."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from math_assistant.server.config import ServerConfig


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Created on first call to init_db()
_engine = None
SessionLocal = None


def init_db(config: ServerConfig):
    """Initialize the database engine and session factory.

    Must be called once before any database operations.
    Creates all tables if they don't exist.

    Args:
        config: ServerConfig with database URL.
    """
    global _engine, SessionLocal

    connect_args = {}
    if config.database.url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        config.database.url,
        connect_args=connect_args,
        echo=False,
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
    )

    # Import all models so they register with Base
    import math_assistant.server.models  # noqa: F401

    Base.metadata.create_all(bind=_engine)


def get_db():
    """FastAPI dependency: yields a database session.

    Usage:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            ...
    """
    if SessionLocal is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
