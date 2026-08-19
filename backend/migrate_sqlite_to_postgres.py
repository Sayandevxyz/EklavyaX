"""
migrate_sqlite_to_postgres.py
─────────────────────────────
Utility to migrate all existing data from local SQLite database (eklavyax.db)
into a PostgreSQL database.

Usage:
    cd backend
    python migrate_sqlite_to_postgres.py
"""

import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from app.db.database import Base
from app.db import models

SQLITE_PATH = BASE_DIR / "eklavyax.db"
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"
PG_URL = settings.DATABASE_URL
if PG_URL.startswith("postgres://"):
    PG_URL = PG_URL.replace("postgres://", "postgresql://", 1)


def migrate():
    print("=" * 60)
    print(">> EklavyaX: SQLite to PostgreSQL Migration")
    print("=" * 60)
    print(f"Source (SQLite)    : {SQLITE_URL}")
    print(f"Target (PostgreSQL): {PG_URL}")
    print("-" * 60)

    if not SQLITE_PATH.exists():
        print(f"[INFO] SQLite database file not found at {SQLITE_PATH}.")
        print("Initializing PostgreSQL schema directly...")
        pg_engine = create_engine(PG_URL)
        Base.metadata.create_all(bind=pg_engine)
        print("[SUCCESS] PostgreSQL tables created successfully!")
        return

    # Engines and sessions
    sqlite_engine = create_engine(SQLITE_URL)
    pg_engine = create_engine(PG_URL)

    # 1. Cleanly recreate tables in PostgreSQL to match current schema
    print("[INFO] Recreating clean tables in PostgreSQL...")
    Base.metadata.drop_all(bind=pg_engine)
    Base.metadata.create_all(bind=pg_engine)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    sqlite_db = SqliteSession()
    pg_db = PgSession()

    try:
        tables = [
            (models.Faction, "factions"),
            (models.User, "users"),
            (models.Streak, "streaks"),
            (models.Wallet, "wallets"),
            (models.Transaction, "transactions"),
            (models.Bounty, "bounties"),
            (models.BountySubmission, "bounty_submissions"),
            (models.Challenge, "challenges"),
            (models.ChallengeResult, "challenge_results"),
            (models.AIExplanationLog, "ai_explanation_logs"),
        ]

        for model_cls, table_name in tables:
            rows = sqlite_db.execute(select(model_cls)).scalars().all()
            print(f"[INFO] Migrating {len(rows)} records from '{table_name}'...")
            for row in rows:
                sqlite_db.expunge(row)
                pg_db.merge(row)
            pg_db.commit()

        # Update Postgres sequence values for auto-incrementing primary keys
        print("[INFO] Updating PostgreSQL auto-increment sequences...")
        with pg_engine.connect() as conn:
            for _, table_name in tables:
                try:
                    conn.execute(
                        text(
                            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1));"
                        )
                    )
                    conn.commit()
                except Exception as seq_err:
                    pass

        print("=" * 60)
        print("[SUCCESS] Migration to PostgreSQL completed successfully!")
        print("=" * 60)

    except Exception as exc:
        pg_db.rollback()
        print(f"[ERROR] Error during migration: {exc}")
        raise exc
    finally:
        sqlite_db.close()
        pg_db.close()


if __name__ == "__main__":
    migrate()
