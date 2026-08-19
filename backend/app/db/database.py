"""
app/db/database.py
──────────────────
SQLAlchemy engine, session factory, declarative base, and
the FastAPI `get_db` dependency.
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# ── Engine ───────────────────────────────────────────────────────────────────
# Normalize postgres:// -> postgresql:// for compatibility with hosted providers (Supabase, Neon, Render, etc.)
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

_is_sqlite = db_url.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=settings.APP_ENV == "development",
    )
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,        # Reconnect on stale connections
        pool_size=10,              # Connection pool size
        max_overflow=20,           # Extra connections when pool exhausted
        echo=settings.APP_ENV == "development",  # SQL logging in dev only
    )

# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # Keep attributes accessible after commit
)


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ── FastAPI DB dependency ─────────────────────────────────────────────────────
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
