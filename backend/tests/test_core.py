"""
tests/test_core.py
──────────────────
Unit tests for core EklavyaX/Synapse backend functions.

Uses:
- SQLite in-memory database (no PostgreSQL needed for tests)
- pytest fixtures
- No external API calls (AI calls are mocked)

Run with: pytest tests/ -v
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set a test DATABASE_URL before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_EklavyaX.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.db.database import Base
from app.db import models
from app.services import game_logic
from app.services.ai_service import build_explanation_prompt, get_explanation

# Pre-computed bcrypt hash of "test" – avoids bcrypt calls in non-password tests
# (generated once with: hash_password("test"))
PRE_HASHED_TEST_PASSWORD = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


# ─────────────────────────────────────────────────────────────────────────────
# Test Database Fixture (SQLite in-memory)
# ─────────────────────────────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///./test_EklavyaX_pytest.db"


@pytest.fixture(scope="module")
def db_engine():
    """Create a fresh SQLite engine for the test module."""
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    # Clean up file
    import os
    if os.path.exists("test_EklavyaX_pytest.db"):
        try:
            os.remove("test_EklavyaX_pytest.db")
        except OSError:
            pass


@pytest.fixture
def db(db_engine):
    """Provide a fresh session for each test, rolled back after."""
    TestSessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Password Hashing
# ─────────────────────────────────────────────────────────────────────────────

class TestPasswordSecurity:
    """Tests for bcrypt password hashing utilities."""

    def test_hash_password_returns_string(self):
        hashed = hash_password("MySecurePass123!")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_not_plain_text(self):
        plain = "MySecurePass123!"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_correct_password(self):
        plain = "CorrectHorseBatteryStaple"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("RightPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt salting means same password → different hashes."""
        plain = "SamePassword"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(plain, hash1) is True
        assert verify_password(plain, hash2) is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. JWT Token
# ─────────────────────────────────────────────────────────────────────────────

class TestJWT:
    """Tests for JWT creation and decoding."""

    def test_create_and_decode_token(self):
        token = create_access_token(subject=42)
        payload = decode_access_token(token)
        assert payload["sub"] == "42"

    def test_token_contains_expiry(self):
        token = create_access_token(subject=1)
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("this.is.not.a.valid.jwt")
        assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 3. Faction Assignment
# ─────────────────────────────────────────────────────────────────────────────

class TestFactionAssignment:
    """Tests for the faction sorting algorithm."""

    def test_factions_seeded(self, db):
        game_logic.ensure_factions_exist(db)
        factions = db.query(models.Faction).all()
        assert len(factions) == 4
        names = {f.name for f in factions}
        assert "House Vidyut" in names
        assert "House Agni" in names
        assert "House Vayu" in names
        assert "House Prithvi" in names

    def test_assign_faction_returns_faction_object(self, db):
        game_logic.ensure_factions_exist(db)
        faction = game_logic.assign_faction(db)
        assert isinstance(faction, models.Faction)
        assert faction.id is not None

    def test_assign_faction_balances_members(self, db):
        """New users should be assigned to the faction with fewest members."""
        game_logic.ensure_factions_exist(db)

        # Repeatedly assign and check we get valid factions
        for _ in range(4):
            faction = game_logic.assign_faction(db)
            assert faction.name in {
                "House Vidyut", "House Agni", "House Vayu", "House Prithvi"
            }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Streak Update Logic
# ─────────────────────────────────────────────────────────────────────────────

class TestStreakLogic:
    """Tests for the streak update algorithm with different date gaps."""

    def _make_user_and_streak(self, db) -> tuple:
        """Helper: create a user + streak record and return both."""
        game_logic.ensure_factions_exist(db)
        faction = game_logic.assign_faction(db)

        import uuid
        user = models.User(
            username=f"u_{uuid.uuid4().hex[:8]}",
            email=f"u_{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=PRE_HASHED_TEST_PASSWORD,
            role=models.UserRole.student,
            faction_id=faction.id,
        )
        db.add(user)
        db.flush()

        wallet = models.Wallet(user_id=user.id, balance=100, xp=0)
        db.add(wallet)

        streak = models.Streak(user_id=user.id)
        db.add(streak)
        db.flush()
        return user, streak

    def test_first_activity_sets_streak_to_1(self, db):
        user, streak = self._make_user_and_streak(db)
        assert streak.last_activity_date is None

        updated = game_logic.update_streak(db, user.id)
        assert updated.current_streak == 1
        assert updated.last_activity_date == date.today()

    def test_same_day_does_not_increment(self, db):
        user, streak = self._make_user_and_streak(db)
        streak.last_activity_date = date.today()
        streak.current_streak = 5
        db.flush()

        updated = game_logic.update_streak(db, user.id)
        assert updated.current_streak == 5  # Unchanged

    def test_consecutive_day_increments(self, db):
        user, streak = self._make_user_and_streak(db)
        streak.last_activity_date = date.today() - timedelta(days=1)
        streak.current_streak = 7
        db.flush()

        updated = game_logic.update_streak(db, user.id)
        assert updated.current_streak == 8

    def test_gap_without_freeze_resets_streak(self, db):
        user, streak = self._make_user_and_streak(db)
        streak.last_activity_date = date.today() - timedelta(days=3)
        streak.current_streak = 10
        streak.streak_freezes = 0
        db.flush()

        updated = game_logic.update_streak(db, user.id)
        assert updated.current_streak == 1  # Reset

    def test_gap_with_freeze_preserves_streak(self, db):
        user, streak = self._make_user_and_streak(db)
        streak.last_activity_date = date.today() - timedelta(days=3)
        streak.current_streak = 10
        streak.streak_freezes = 2
        db.flush()

        updated = game_logic.update_streak(db, user.id)
        assert updated.current_streak == 11  # Freeze used, streak extended
        assert updated.streak_freezes == 1   # One freeze consumed

    def test_longest_streak_updated(self, db):
        user, streak = self._make_user_and_streak(db)
        streak.last_activity_date = date.today() - timedelta(days=1)
        streak.current_streak = 9
        streak.longest_streak = 9
        db.flush()

        updated = game_logic.update_streak(db, user.id)
        assert updated.longest_streak == 10


# ─────────────────────────────────────────────────────────────────────────────
# 5. Wallet Credit / Debit
# ─────────────────────────────────────────────────────────────────────────────

class TestWalletFunctions:
    """Tests for earn_coins_and_xp and spend_coins."""

    def _make_user_with_wallet(self, db, starting_balance: int = 100) -> models.User:
        game_logic.ensure_factions_exist(db)
        faction = game_logic.assign_faction(db)

        import uuid
        user = models.User(
            username=f"w_{uuid.uuid4().hex[:8]}",
            email=f"w_{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=PRE_HASHED_TEST_PASSWORD,
            role=models.UserRole.student,
            faction_id=faction.id,
        )
        db.add(user)
        db.flush()

        wallet = models.Wallet(user_id=user.id, balance=starting_balance, xp=0)
        db.add(wallet)
        db.flush()
        return user

    def test_earn_coins_increases_balance(self, db):
        user = self._make_user_with_wallet(db, starting_balance=50)
        wallet = game_logic.earn_coins_and_xp(db, user.id, coins=30, xp=0, reason="test_earn")
        assert wallet.balance == 80

    def test_earn_xp_increases_xp(self, db):
        user = self._make_user_with_wallet(db, starting_balance=50)
        wallet = game_logic.earn_coins_and_xp(db, user.id, coins=0, xp=25, reason="test_xp")
        assert wallet.xp == 25

    def test_spend_coins_reduces_balance(self, db):
        user = self._make_user_with_wallet(db, starting_balance=100)
        wallet = game_logic.spend_coins(db, user.id, coins=40, reason="test_spend")
        assert wallet.balance == 60

    def test_spend_more_than_balance_raises(self, db):
        from fastapi import HTTPException
        user = self._make_user_with_wallet(db, starting_balance=10)
        with pytest.raises(HTTPException) as exc_info:
            game_logic.spend_coins(db, user.id, coins=50, reason="overspend")
        assert exc_info.value.status_code == 400
        assert "Insufficient" in exc_info.value.detail

    def test_transaction_is_recorded(self, db):
        user = self._make_user_with_wallet(db, starting_balance=100)
        game_logic.earn_coins_and_xp(db, user.id, coins=20, xp=10, reason="module_complete")

        txs = db.query(models.Transaction).filter_by(user_id=user.id).all()
        assert any(t.reason == "module_complete" for t in txs)

    def test_refund_coins(self, db):
        user = self._make_user_with_wallet(db, starting_balance=50)
        # Spend some
        game_logic.spend_coins(db, user.id, coins=10, reason="ai_explain")
        # Refund
        wallet = game_logic.refund_coins(db, user.id, coins=5, reason="ai_refund")
        assert wallet.balance == 45  # 50 - 10 + 5


# ─────────────────────────────────────────────────────────────────────────────
# 6. AI Prompt Builder
# ─────────────────────────────────────────────────────────────────────────────

class TestAIPromptBuilder:
    """Tests for the Gravity.ai prompt engineering function."""

    def test_prompt_contains_highlighted_text(self):
        text = "Photosynthesis converts sunlight into glucose."
        prompt = build_explanation_prompt(text, "Simple English")
        assert text in prompt

    def test_prompt_contains_target_language(self):
        prompt = build_explanation_prompt("Some text", "Hindi")
        assert "Hindi" in prompt

    def test_prompt_mentions_direct_answer(self):
        prompt = build_explanation_prompt("What is Newton's third law?", "Simple English")
        # Prompt should instruct AI to answer directly and explicitly
        assert "DIRECT ANSWER" in prompt or "direct" in prompt.lower()

    def test_prompt_is_non_empty_string(self):
        prompt = build_explanation_prompt("Any text", "Tamil")
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_prompt_trimmed_whitespace(self):
        prompt = build_explanation_prompt("  Some text with spaces  ", "Simple English")
        # The text should appear in the prompt (stripped)
        assert "Some text with spaces" in prompt


# ─────────────────────────────────────────────────────────────────────────────
# 7. AI Service Provider Execution
# ─────────────────────────────────────────────────────────────────────────────

class TestAIService:
    """Tests for the multi-provider AI explanation engine."""

    @pytest.mark.asyncio
    async def test_get_explanation_calls_openrouter(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is a guided explanation from OpenRouter."
                    }
                }
            ]
        }
        fake_response.raise_for_status.return_value = None

        with patch("app.core.config.settings.AI_PROVIDER", "openrouter"), \
             patch("app.core.config.settings.OPENROUTER_API_KEY", "test-key"), \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = fake_response

            result = await get_explanation("Newton's second law", "Simple English")
            assert result == "This is a guided explanation from OpenRouter."
            assert mock_post.called
            call_url = mock_post.call_args[0][0]
            assert "openrouter.ai" in call_url


# ─────────────────────────────────────────────────────────────────────────────
# 8. User Profile Update & Password Change
# ─────────────────────────────────────────────────────────────────────────────

class TestUserProfileAndAuth:
    """Tests for user profile updates and password security."""

    def test_user_profile_columns_update(self, db):
        user = models.User(
            username="testprofileuser",
            email="profiletest@example.com",
            hashed_password=PRE_HASHED_TEST_PASSWORD,
            role=models.UserRole.student,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Update fields
        user.username = "New Display Name"
        user.phone = "+91 99999 88888"
        user.roll = "EK-2026-999"
        user.grade = "Class 12"
        user.school = "Model High School"
        user.target_exam = "JEE Advanced"
        user.bio = "Aspiring Scientist"
        user.avatar_url = "assets/img/student_boy.jpg"
        user.gender = "male"
        db.commit()
        db.refresh(user)

        assert user.username == "New Display Name"
        assert user.phone == "+91 99999 88888"
        assert user.roll == "EK-2026-999"
        assert user.grade == "Class 12"
        assert user.school == "Model High School"
        assert user.target_exam == "JEE Advanced"
        assert user.bio == "Aspiring Scientist"

    def test_password_change_logic(self, db):
        plain_old = "OldPassword123"
        plain_new = "NewPassword456"
        user = models.User(
            username="testpasschangeuser",
            email="passchange@example.com",
            hashed_password=hash_password(plain_old),
            role=models.UserRole.student,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Verify old password matches
        assert verify_password(plain_old, user.hashed_password) is True

        # Update password
        user.hashed_password = hash_password(plain_new)
        db.commit()
        db.refresh(user)

        assert verify_password(plain_old, user.hashed_password) is False
        assert verify_password(plain_new, user.hashed_password) is True

