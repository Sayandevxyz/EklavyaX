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


PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
REACT_FRONTEND_DIR = PROJECT_DIR / "frontend-react" / "dist"
FRONTEND_DIR = REACT_FRONTEND_DIR if REACT_FRONTEND_DIR.is_dir() else PROJECT_DIR / "frontend"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG if settings.APP_ENV == "development" else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


class SPAStaticFiles(StaticFiles):
    """Serve the React entry point for client-side routes."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response




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
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

        await _redis_client.ping()

        logger.info("✅ Redis connected: %s", settings.REDIS_URL)

    except Exception as exc:
        logger.warning(
            "⚠️ Could not connect to Redis: %s. Falling back to DB queries.",
            exc,
        )
        _redis_client = None


def get_redis():
    """Return the Redis client, or None if not configured."""
    return _redis_client




@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Async context manager run on startup and shutdown."""

    logger.info("🚀 EklavyaX GRAVITY Backend starting up...")

  
    from app.db.database import Base, engine
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    logger.info("✅ Database tables ensured.")

   
    from sqlalchemy import text

    columns_to_ensure = [
        ("gender", "VARCHAR(20)"),
        ("phone", "VARCHAR(30)"),
        ("roll", "VARCHAR(50)"),
        ("grade", "VARCHAR(100)"),
        ("school", "VARCHAR(150)"),
        ("target_exam", "VARCHAR(100)"),
        ("bio", "TEXT"),
        ("department", "VARCHAR(100)"),
        ("office_hours", "VARCHAR(100)"),
        ("specialization_subject", "VARCHAR(100)"),
        ("section", "VARCHAR(20)"),
        ("dob", "VARCHAR(30)"),
        ("parent_name", "VARCHAR(100)"),
        ("parent_phone", "VARCHAR(30)"),
        ("parent_id", "INTEGER"),
        ("attendance_rate", "FLOAT"),
    ]

    with engine.connect() as con:
        for col_name, col_type in columns_to_ensure:
            try:
                con.execute(
                    text(
                        f"ALTER TABLE users ADD COLUMN "
                        f"{col_name} {col_type}"
                    )
                )
                con.commit()
            except Exception:
                con.rollback()

        try:
            con.execute(text("ALTER TABLE quiz_questions ADD COLUMN explanation TEXT"))
            con.commit()
        except Exception:
            con.rollback()

    
    from app.db.database import SessionLocal
    from app.services.game_logic import (
        ensure_active_battle_exists,
        ensure_factions_exist,
        ensure_quiz_questions_exist,
    )

    def ensure_default_accounts_exist(db_sess):
        from app.core.security import hash_password
        # 1. Teacher (Physics)
        if not db_sess.query(models.User).filter_by(email="teacher@eklavya.edu").first():
            db_sess.add(models.User(
                username="teacher_physics",
                email="teacher@eklavya.edu",
                hashed_password=hash_password("Teacher@123"),
                role=models.UserRole.teacher,
                school="Eklavya Central Academy",
                department="Science & Technology",
                specialization_subject="Physics",
                office_hours="Mon-Fri 02:00 PM - 04:00 PM",
            ))
        # 2. Student (Class 10)
        if not db_sess.query(models.User).filter_by(email="student@eklavya.edu").first():
            st = models.User(
                username="sayan_mondal",
                email="student@eklavya.edu",
                hashed_password=hash_password("Student@123"),
                role=models.UserRole.student,
                school="Eklavya Central Academy",
                grade="Class 10",
                section="A",
                roll="EK-101",
                parent_name="Bikash Mondal",
                parent_phone="+91 9876543200",
                attendance_rate=95.0,
            )
            db_sess.add(st)
            db_sess.flush()
            db_sess.add(models.Wallet(user_id=st.id, balance=250, xp=480))
            db_sess.add(models.Streak(user_id=st.id, current_streak=5, longest_streak=7))
        db_sess.commit()

    db = SessionLocal()

    try:
        ensure_factions_exist(db)
        ensure_quiz_questions_exist(db)
        ensure_active_battle_exists(db)
        ensure_default_accounts_exist(db)
        logger.info("✅ Default factions, quiz questions, active battle, and core accounts seeded.")

    except Exception as exc:
        logger.error("❌ Failed to seed initial data: %s", exc)

    finally:
        db.close()

   
    await _init_redis()

    logger.info(
        "🎮 GRAVITY Backend is ready. Docs: http://localhost:8000/docs"
    )

   
    if settings.AI_PROVIDER.lower() == "groq":

        logger.info(
            "🔑 Groq configured: model=%s, key_loaded=%s (len=%d)",
            settings.GROQ_MODEL,
            bool(settings.GROQ_API_KEY),
            len(settings.GROQ_API_KEY),
        )

        print(
            f"[STARTUP] AI_PROVIDER = groq "
            f"(model={settings.GROQ_MODEL}, "
            f"key_loaded={bool(settings.GROQ_API_KEY)})"
        )

    elif settings.AI_PROVIDER.lower() == "openrouter":

        logger.info(
            "🔑 OpenRouter configured: model=%s, key_loaded=%s (len=%d)",
            settings.OPENROUTER_MODEL,
            bool(settings.OPENROUTER_API_KEY),
            len(settings.OPENROUTER_API_KEY),
        )

        print(
            f"[STARTUP] AI_PROVIDER = openrouter "
            f"(model={settings.OPENROUTER_MODEL}, "
            f"key_loaded={bool(settings.OPENROUTER_API_KEY)})"
        )

    elif settings.AI_PROVIDER.lower() == "gemini":

        logger.info(
            "🔑 Gemini configured: model=%s, key_loaded=%s (len=%d)",
            settings.GEMINI_MODEL,
            bool(settings.GEMINI_API_KEY),
            len(settings.GEMINI_API_KEY),
        )

        print(
            f"[STARTUP] AI_PROVIDER = gemini "
            f"(model={settings.GEMINI_MODEL}, "
            f"key_loaded={bool(settings.GEMINI_API_KEY)})"
        )

    elif settings.AI_PROVIDER.lower() == "openai":

        logger.info(
            "🔑 OpenAI configured: model=%s, key_loaded=%s (len=%d)",
            settings.OPENAI_MODEL,
            bool(settings.OPENAI_API_KEY),
            len(settings.OPENAI_API_KEY),
        )

        print(
            f"[STARTUP] AI_PROVIDER = openai "
            f"(model={settings.OPENAI_MODEL}, "
            f"key_loaded={bool(settings.OPENAI_API_KEY)})"
        )

    else:
        logger.warning(
            "⚠️ Unknown AI_PROVIDER: %s",
            settings.AI_PROVIDER,
        )

  
    yield

   
    if _redis_client:
        await _redis_client.aclose()

    logger.info("👋 GRAVITY Backend shut down gracefully.")




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




try:
    configured_origins = settings.get_cors_origins()
except Exception:
    configured_origins = []

# Make sure configured_origins is always a list
if isinstance(configured_origins, str):
    configured_origins = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]

cors_origins = list(configured_origins)

allowed_frontends = [
    "https://eklavyax.vercel.app",
    "https://eklavya-x.vercel.app",
]

for origin in allowed_frontends:
    if origin not in cors_origins:
        cors_origins.append(origin)


for local_origin in [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]:
    if local_origin not in cors_origins:
        cors_origins.append(local_origin)

logger.info("🌐 CORS allowed origins: %s", cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all for unhandled exceptions – return consistent JSON error."""

    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": (
                "An internal server error occurred. "
                "Please try again later."
            )
        },
    )




from app.api.routes import (  # noqa: E402
    auth,
    bounties,
    economy,
    faction_wars,
    quiz,
    tutor,
    leaderboard,
    notifications,
    analytics,
    study_groups,
    achievements,
    flashcards,
    chat_threads,
    referrals,
    study_planner,
    live_quiz,
    reports,
    certificates,
    doubts,
    pedagogy,
)

app.include_router(auth.router)
app.include_router(bounties.router)
app.include_router(economy.router)
app.include_router(faction_wars.router)
app.include_router(quiz.router)
app.include_router(tutor.router)
app.include_router(leaderboard.router)
app.include_router(notifications.router)
app.include_router(analytics.router)
app.include_router(study_groups.router)
app.include_router(achievements.router)
app.include_router(flashcards.router)
app.include_router(chat_threads.router)
app.include_router(referrals.router)
app.include_router(study_planner.router)
app.include_router(live_quiz.router)
app.include_router(reports.router)
app.include_router(certificates.router)
app.include_router(doubts.router)
app.include_router(pedagogy.router)




@app.get(
    "/api/status",
    tags=["Health"],
    summary="Health check",
)
async def root():
    """API status endpoint – confirms the server is running."""

    return {
        "message": "EklavyaX GRAVITY Backend is running",
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


@app.get(
    "/health",
    tags=["Health"],
    summary="Detailed health check",
)
async def health_check():
    """Check connectivity to DB and Redis."""

    checks = {
        "api": "ok",
        "redis": "disabled",
    }

    if _redis_client:
        try:
            await _redis_client.ping()
            checks["redis"] = "ok"

        except Exception:
            checks["redis"] = "error"

    return checks




if FRONTEND_DIR.is_dir():

    app.mount(
        "/",
        SPAStaticFiles(
            directory=str(FRONTEND_DIR),
            html=True,
        ),
        name="frontend",
    )

else:

    logger.warning(
        "Frontend directory not found at %s — API-only mode.",
        FRONTEND_DIR,
    )
