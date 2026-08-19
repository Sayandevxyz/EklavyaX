"""
app/main.py
───────────
FastAPI application factory for the Synapse Backend (EklavyaX).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

# The ../frontend folder that ships alongside this backend. Mounted below so
# `uvicorn app.main:app` serves the whole app (API + UI) from one process/port.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG if settings.APP_ENV == "development" else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


# ── Redis (optional) ──────────────────────────────────────────────────────────

_redis_client = None


async def _init_redis() -> None:
    """Initialize Redis connection pool if REDIS_URL is configured."""
    global _redis_client
    if not settings.REDIS_URL:
        logger.info("Redis not configured (REDIS_URL not set). Skipping.")
        return

    try:
        import redis.asyncio as aioredis
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        await _redis_client.ping()
        logger.info("✅ Redis connected: %s", settings.REDIS_URL)
    except Exception as exc:
        logger.warning("⚠️  Could not connect to Redis: %s. Falling back to DB queries.", exc)
        _redis_client = None


def get_redis():
    """Return the Redis client, or None if not configured."""
    return _redis_client


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Async context manager run on startup and shutdown."""
    logger.info("🚀 EklavyaX Synapse Backend starting up...")

    # Create all database tables
    from app.db.database import Base, engine
    from app.db import models  # noqa: F401 – import to register all models

    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables ensured.")

    # Ensure optional user profile columns exist on existing databases
    from sqlalchemy import text
    columns_to_ensure = [
        ("gender", "VARCHAR(20)"),
        ("phone", "VARCHAR(30)"),
        ("roll", "VARCHAR(50)"),
        ("grade", "VARCHAR(100)"),
        ("school", "VARCHAR(150)"),
        ("target_exam", "VARCHAR(100)"),
        ("bio", "TEXT"),
    ]
    with engine.connect() as con:
        for col_name, col_type in columns_to_ensure:
            try:
                con.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                con.commit()
            except Exception:
                con.rollback()

    # Seed default factions
    from app.db.database import SessionLocal
    from app.services.game_logic import ensure_factions_exist

    db = SessionLocal()
    try:
        ensure_factions_exist(db)
        logger.info("✅ Default factions seeded.")
    except Exception as exc:
        logger.error("❌ Failed to seed factions: %s", exc)
    finally:
        db.close()

    # Initialize Redis (optional)
    await _init_redis()

    logger.info("🎮 Synapse Backend is ready. Docs: http://localhost:8000/docs")
    if settings.AI_PROVIDER.lower() == "openrouter":
        logger.info("🔑 OpenRouter configured: model=%s, key_loaded=%s (len=%d)", settings.OPENROUTER_MODEL, bool(settings.OPENROUTER_API_KEY), len(settings.OPENROUTER_API_KEY))
        print(f"[STARTUP] AI_PROVIDER = openrouter (model={settings.OPENROUTER_MODEL}, key_loaded={bool(settings.OPENROUTER_API_KEY)})")
    elif settings.AI_PROVIDER.lower() == "gemini":
        logger.info("🔑 Gemini configured: model=%s, key_loaded=%s (len=%d)", settings.GEMINI_MODEL, bool(settings.GEMINI_API_KEY), len(settings.GEMINI_API_KEY))
        print(f"[STARTUP] AI_PROVIDER = gemini (model={settings.GEMINI_MODEL}, key_loaded={bool(settings.GEMINI_API_KEY)})")
    elif settings.AI_PROVIDER.lower() == "openai":
        logger.info("🔑 OpenAI configured: model=%s, key_loaded=%s (len=%d)", settings.OPENAI_MODEL, bool(settings.OPENAI_API_KEY), len(settings.OPENAI_API_KEY))
        print(f"[STARTUP] AI_PROVIDER = openai (model={settings.OPENAI_MODEL}, key_loaded={bool(settings.OPENAI_API_KEY)})")
    else:
        logger.warning("⚠️ Unknown AI_PROVIDER: %s", settings.AI_PROVIDER)

    yield  # ← Application runs here

    # Shutdown
    if _redis_client:
        await _redis_client.aclose()
    logger.info("👋 Synapse Backend shut down gracefully.")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=(
        "**EklavyaX** – Gamified Learning Platform\n\n"
        "Powered by **Gravity AI** – the AI Explanation Microservice.\n\n"
        "Features: Streaks · Faction Wars · Peer Challenges · "
        "Bounty Board · Virtual Economy · AI Tutor"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS Middleware ───────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handlers ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions – return consistent JSON error."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ── API Routers ───────────────────────────────────────────────────────────────

from app.api.routes import auth, bounties, economy, tutor  # noqa: E402

app.include_router(auth.router)
app.include_router(bounties.router)
app.include_router(economy.router)
app.include_router(tutor.router)


# ── Root Endpoint ─────────────────────────────────────────────────────────────

@app.get("/api/status", tags=["Health"], summary="Health check")
async def root():
    """API status endpoint – confirms the server is running. (`/` serves the frontend UI.)"""
    return {
        "message": "EklavyaX Synapse Backend is running",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "healthy",
        "features": [
            "Streak Engine",
            "Virtual Economy (EduCoins)",
            "Faction Wars",
            "Peer Challenges",
            "Teacher Bounty Board",
            "Gravity AI Explanation Engine",
        ],
    }


@app.get("/health", tags=["Health"], summary="Detailed health check")
async def health_check():
    """Check connectivity to DB and Redis."""
    checks = {"api": "ok", "redis": "disabled"}

    if _redis_client:
        try:
            await _redis_client.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"

    return checks


# ── Static Frontend ───────────────────────────────────────────────────────────
# Mounted LAST so it never shadows the API routes above (Starlette matches
# routes in registration order). Serves the plain HTML/CSS/JS frontend and
# falls back to index.html for unknown paths so the app runs from one port
# with zero CORS/config hassle: `uvicorn app.main:app` → http://localhost:8000
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend directory not found at %s — API-only mode.", FRONTEND_DIR)
