"""
tests/test_quiz_faction.py
──────────────────────────
Unit and integration tests for Part B:
- Standalone Quiz API (start, submit, next, summary)
- Streak tracking and option shuffle mapping
- Faction Wars battle score aggregation from validated rewards
- Active battle polling endpoint
- End-of-battle reward split (winner bonus + guaranteed loser participation reward)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app.core.config import settings
from app.db.database import Base
from app.db import models
from app.services import game_logic, safeguards
from app.api.routes import faction_wars, quiz
from app.schemas.quiz_sch import QuizStartRequest, QuizSubmitRequest


@pytest.fixture
def db():
    """Fresh isolated in-memory SQLite database per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def seeded_env(db):
    game_logic.ensure_factions_exist(db)
    game_logic.ensure_quiz_questions_exist(db)
    game_logic.ensure_active_battle_exists(db)

    # Create 2 users in different factions
    u1 = models.User(
        username="vidyut_student",
        email="vidyut@test.com",
        hashed_password="pw",
        role=models.UserRole.student,
        faction_id=1,  # House Vidyut
    )
    u2 = models.User(
        username="agni_student",
        email="agni@test.com",
        hashed_password="pw",
        role=models.UserRole.student,
        faction_id=2,  # House Agni
    )
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)

    w1 = models.Wallet(user_id=u1.id, balance=100, xp=0)
    w2 = models.Wallet(user_id=u2.id, balance=100, xp=0)
    db.add_all([w1, w2])
    db.commit()

    return {"user1": u1, "user2": u2}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Quiz API Lifecycle Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestQuizFlow:
    def test_start_quiz_returns_first_question_with_shuffled_options(self, db, seeded_env):
        user = seeded_env["user1"]
        req = QuizStartRequest(num_questions=5)
        resp = quiz.start_quiz(payload=req, current_user=user, db=db)

        assert resp.total_questions == 5
        assert resp.quiz_run_id is not None
        assert resp.question.question_index == 0
        assert len(resp.question.options) == 4
        assert resp.question.preview_coins > 0
        assert resp.question.preview_xp > 0

    def test_submit_quiz_answer_and_summary(self, db, seeded_env):
        user = seeded_env["user1"]
        req = QuizStartRequest(num_questions=3)
        start_resp = quiz.start_quiz(payload=req, current_user=user, db=db)

        q0 = start_resp.question
        session0 = db.get(models.QuizSession, q0.session_id)
        # Advance time so cooldown passes
        session0.question_shown_at = datetime.now(timezone.utc) - timedelta(seconds=4)
        db.commit()

        # Find the correct shuffled index
        perm = safeguards.str_to_permutation(session0.shuffled_order)
        correct_shuffled_idx = perm.index(session0.question.correct_option_index)

        # Submit correct answer
        sub_req = QuizSubmitRequest(
            session_id=session0.id,
            selected_option_index=correct_shuffled_idx,
        )
        sub_resp = quiz.submit_answer(payload=sub_req, current_user=user, db=db)

        assert sub_resp.is_correct is True
        assert sub_resp.coins_awarded > 0
        assert sub_resp.xp_awarded > 0
        assert sub_resp.streak == 1

        # Fetch Summary
        summary = quiz.get_quiz_summary(
            quiz_run_id=start_resp.quiz_run_id,
            current_user=user,
            db=db,
        )

        assert summary.total_questions == 3
        assert summary.answered == 1
        assert summary.correct == 1
        assert summary.accuracy_pct == 100.0
        assert summary.total_coins == sub_resp.coins_awarded
        assert summary.total_xp == sub_resp.xp_awarded


# ─────────────────────────────────────────────────────────────────────────────
# 2. Faction Wars Battle Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFactionWars:
    def test_active_battle_polling(self, db, seeded_env):
        user = seeded_env["user1"]
        resp = faction_wars.get_active_battle(current_user=user, db=db)

        assert resp.status == "active"
        assert resp.battle_id is not None
        assert len(resp.scores) >= 2
        assert resp.time_remaining_seconds > 0
        assert resp.poll_interval_seconds == settings.FACTION_WAR_POLL_INTERVAL_SECONDS

    def test_battle_contribution_aggregation_from_quiz(self, db, seeded_env):
        user = seeded_env["user1"]  # House Vidyut (id 1)
        req = QuizStartRequest(num_questions=1)
        start_resp = quiz.start_quiz(payload=req, current_user=user, db=db)

        session = db.get(models.QuizSession, start_resp.question.session_id)
        session.question_shown_at = datetime.now(timezone.utc) - timedelta(seconds=4)
        db.commit()

        perm = safeguards.str_to_permutation(session.shuffled_order)
        correct_idx = perm.index(session.question.correct_option_index)

        # Submit answer which will credit faction battle score
        quiz.submit_answer(
            payload=QuizSubmitRequest(
                session_id=session.id,
                selected_option_index=correct_idx,
            ),
            current_user=user,
            db=db,
        )

        # Check leaderboard
        active_battle = db.query(models.FactionBattle).first()
        lb = faction_wars.get_battle_leaderboard(
            battle_id=active_battle.id,
            current_user=user,
            db=db,
        )

        assert lb.faction_id == user.faction_id
        assert len(lb.entries) > 0
        assert lb.entries[0].user_id == user.id
        assert lb.entries[0].xp_contributed > 0

    def test_finalize_battle_reward_split(self, db, seeded_env):
        admin_user = models.User(
            username="admin_teacher",
            email="admin@test.com",
            hashed_password="pw",
            role=models.UserRole.admin,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        active_battle = db.query(models.FactionBattle).filter_by(status=models.BattleStatus.active).first()

        end_resp = faction_wars.finalize_battle(
            battle_id=active_battle.id,
            current_user=admin_user,
            db=db,
        )

        assert end_resp.status == "completed"
        assert end_resp.winner_bonus_coins == settings.FACTION_WAR_WINNER_BONUS_COINS
        assert end_resp.winner_bonus_xp == settings.FACTION_WAR_WINNER_BONUS_XP
        assert end_resp.loser_participation_coins == settings.FACTION_WAR_LOSER_PARTICIPATION_COINS
        assert end_resp.loser_participation_xp == settings.FACTION_WAR_LOSER_PARTICIPATION_XP
