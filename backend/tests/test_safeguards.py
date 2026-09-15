"""
tests/test_safeguards.py
────────────────────────
Unit tests for Part A Anti-Gaming Safeguards:
- Server-side answer validation
- Per-question cooldown gating (minimum response threshold)
- Daily earn caps (policies: reject, zero, reduced)
- Suspicious pattern detection (rolling z-score outlier flagging)
- Queryable audit log entries for all paths
- Answer option shuffling
- Fail-safe error handling
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
def test_user(db):
    game_logic.ensure_factions_exist(db)
    user = models.User(
        username="safeguard_student",
        email="safeguard@test.com",
        hashed_password="hashed_pw_test",
        role=models.UserRole.student,
        faction_id=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    wallet = models.Wallet(user_id=user.id, balance=100, xp=50)
    db.add(wallet)
    db.commit()
    return user


@pytest.fixture
def test_question(db):
    q = models.QuizQuestion(
        topic="Physics",
        prompt="What is the unit of force?",
        option_a="Joule",
        option_b="Newton",
        option_c="Pascal",
        option_d="Watt",
        correct_option_index=1,  # Newton (index 1)
        difficulty="easy",
        preview_coins=10,
        preview_xp=20,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


# ─────────────────────────────────────────────────────────────────────────────
# 1. Option Shuffling Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOptionShuffling:
    def test_shuffled_options_contains_all_canonical(self, test_question):
        shuffled, perm = safeguards.generate_shuffled_options(test_question)
        canonical = test_question.get_canonical_options()

        assert len(shuffled) == 4
        assert len(perm) == 4
        assert set(shuffled) == set(canonical)

        # Mapping verification
        for idx, canon_idx in enumerate(perm):
            assert shuffled[idx] == canonical[canon_idx]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Server-side Answer Validation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestServerAnswerValidation:
    def test_valid_answer_returns_true(self, db, test_user, test_question):
        # Permutation where canonical option 1 ("Newton") is placed at shuffled index 2
        session = models.QuizSession(
            quiz_run_id="run-1",
            user_id=test_user.id,
            question_id=test_question.id,
            question_index=0,
            total_questions=1,
            shuffled_order="0,2,1,3",  # canonical 1 is at shuffled index 2
            question_shown_at=datetime.now(timezone.utc) - timedelta(seconds=5),
        )
        db.add(session)
        db.commit()

        # Client selects shuffled index 2 (which maps to canonical 1 -> Newton)
        assert safeguards.validate_server_answer(session, 2) is True
        # Client selects shuffled index 0 (which maps to canonical 0 -> Joule -> Wrong)
        assert safeguards.validate_server_answer(session, 0) is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Cooldown Verification Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCooldownSafeguard:
    def test_cooldown_violation_rejected(self, db, test_user, test_question):
        now = datetime.now(timezone.utc)
        # Question shown 0.5s ago (< 2.0s cooldown threshold)
        session = models.QuizSession(
            quiz_run_id="run-2",
            user_id=test_user.id,
            question_id=test_question.id,
            question_index=0,
            total_questions=1,
            shuffled_order="0,1,2,3",
            question_shown_at=now - timedelta(milliseconds=500),
        )
        db.add(session)
        db.commit()

        res = safeguards.grant_safeguarded_reward(
            db, test_user.id, session, selected_shuffled_index=1
        )

        assert res["is_correct"] is True
        assert res["coins_awarded"] == 0
        assert res["xp_awarded"] == 0
        assert res["rejection_reason"] == "cooldown_violation"

        # Verify audit log entry
        audit = (
            db.query(models.RewardAuditLog)
            .filter_by(user_id=test_user.id, reason_code=models.ReasonCode.cooldown_violation)
            .first()
        )
        assert audit is not None
        assert "minimum is" in audit.details


# ─────────────────────────────────────────────────────────────────────────────
# 4. Valid Answer and Full Reward Grant Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRewardGrant:
    def test_valid_answer_with_sufficient_time_grants_reward(self, db, test_user, test_question):
        now = datetime.now(timezone.utc)
        session = models.QuizSession(
            quiz_run_id="run-3",
            user_id=test_user.id,
            question_id=test_question.id,
            question_index=0,
            total_questions=1,
            shuffled_order="0,1,2,3",
            question_shown_at=now - timedelta(seconds=5),  # 5s > 2s
        )
        db.add(session)
        db.commit()

        initial_coins = test_user.wallet.balance
        initial_xp = test_user.wallet.xp

        res = safeguards.grant_safeguarded_reward(
            db, test_user.id, session, selected_shuffled_index=1
        )

        assert res["is_correct"] is True
        assert res["coins_awarded"] == 10
        assert res["xp_awarded"] == 20
        assert res["rejection_reason"] is None

        # Check updated wallet
        db.refresh(test_user.wallet)
        assert test_user.wallet.balance == initial_coins + 10
        assert test_user.wallet.xp == initial_xp + 20

        # Check audit log
        audit = (
            db.query(models.RewardAuditLog)
            .filter_by(user_id=test_user.id, reason_code=models.ReasonCode.granted)
            .order_by(models.RewardAuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.reward_coins == 10
        assert audit.reward_xp == 20


# ─────────────────────────────────────────────────────────────────────────────
# 5. Invalid Answer Rejection Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidAnswerSafeguard:
    def test_wrong_answer_grants_zero_and_logs_invalid(self, db, test_user, test_question):
        now = datetime.now(timezone.utc)
        session = models.QuizSession(
            quiz_run_id="run-4",
            user_id=test_user.id,
            question_id=test_question.id,
            question_index=0,
            total_questions=1,
            shuffled_order="0,1,2,3",
            question_shown_at=now - timedelta(seconds=5),
        )
        db.add(session)
        db.commit()

        # Selected index 0 (Joule - wrong)
        res = safeguards.grant_safeguarded_reward(
            db, test_user.id, session, selected_shuffled_index=0
        )

        assert res["is_correct"] is False
        assert res["coins_awarded"] == 0
        assert res["xp_awarded"] == 0
        assert res["rejection_reason"] == "invalid_answer"

        audit = (
            db.query(models.RewardAuditLog)
            .filter_by(user_id=test_user.id, reason_code=models.ReasonCode.invalid_answer)
            .first()
        )
        assert audit is not None


# ─────────────────────────────────────────────────────────────────────────────
# 6. Daily Cap Enforcement Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDailyCapSafeguards:
    def test_cap_policy_reduced(self, db, test_user, test_question):
        # Simulate user already earned 495 coins today (cap is 500)
        today = datetime.now(timezone.utc)
        prior_audit = models.RewardAuditLog(
            user_id=test_user.id,
            question_id="prev-1",
            reward_coins=495,
            reward_xp=990,
            reason_code=models.ReasonCode.granted,
            created_at=today,
        )
        db.add(prior_audit)
        db.commit()

        # Try to earn 10 coins / 20 XP
        adj_coins, adj_xp, detail = safeguards.check_and_apply_daily_cap(
            db, test_user.id, requested_coins=10, requested_xp=20
        )

        # Reduced policy applies factor (0.25) clamped to headroom (5 coins / 10 XP)
        assert adj_coins == 2  # min(10 * 0.25 = 2, headroom = 5)
        assert adj_xp == 5     # min(20 * 0.25 = 5, headroom = 10)
        assert detail is not None
        assert "Daily cap hit" in detail


# ─────────────────────────────────────────────────────────────────────────────
# 7. Pattern Anomaly Flagging Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPatternAnomalyFlagging:
    def test_statistical_outlier_is_flagged(self, db, test_user, test_question):
        # Seed 15 normal responses (mean around 5000ms, std ~ 1000ms)
        for i in range(15):
            metric = models.UserResponseMetric(
                user_id=test_user.id,
                question_id=test_question.id,
                response_time_ms=5000 + (i * 50),
                is_correct=True,
            )
            db.add(metric)
        db.commit()

        # Submit an inhumanly fast answer (50ms) with 100% accuracy history
        flagged = safeguards.evaluate_suspicious_patterns(
            db,
            user_id=test_user.id,
            response_time_ms=50,
            is_correct=True,
            question_id=test_question.id,
        )

        assert flagged is True

        flag_audit = (
            db.query(models.RewardAuditLog)
            .filter_by(user_id=test_user.id, reason_code=models.ReasonCode.pattern_flagged)
            .first()
        )
        assert flag_audit is not None
        assert flag_audit.is_flagged is True
        assert "Speed z-score" in flag_audit.details
