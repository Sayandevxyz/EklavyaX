from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

_is_sqlite = db_url.startswith("sqlite")

try:
    if _is_sqlite:
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    else:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
        # Test connection
        with engine.connect() as conn:
            pass
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(
        "⚠️ PostgreSQL connection error: %s. Falling back to SQLite.", e
    )
    db_url = "sqlite:///./eklavyax.db"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass



def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and ensure it is closed after the request.

    Usage::

        @router.get("/users")
        def list_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
