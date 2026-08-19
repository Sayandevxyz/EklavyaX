"""
app/db/models.py
────────────────
SQLAlchemy 2.0-style ORM models for EklavyaX.

All models use Mapped[] + mapped_column() for full type-safety.
Relationships use back_populates for bidirectional navigation.
"""
from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class ChallengeStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    completed = "completed"
    cancelled = "cancelled"


# ─────────────────────────────────────────────────────────────────────────────
# Faction
# ─────────────────────────────────────────────────────────────────────────────

class Faction(Base):
    """
    One of four permanent houses a user is sorted into on registration.
    Faction score aggregates XP from all its members.
    """
    __tablename__ = "factions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    color_hex: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # e.g. "#FF6B35"
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    icon_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="faction")

    def __repr__(self) -> str:
        return f"<Faction id={self.id} name={self.name!r} score={self.score}>"


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    """Core user model. Handles all three roles: student, teacher, admin."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), default=UserRole.student, nullable=False
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    roll: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    school: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    target_exam: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    faction_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("factions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    faction: Mapped[Optional["Faction"]] = relationship("Faction", back_populates="users")
    streak: Mapped[Optional["Streak"]] = relationship(
        "Streak", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    wallet: Mapped[Optional["Wallet"]] = relationship(
        "Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    bounties_created: Mapped[List["Bounty"]] = relationship(
        "Bounty", back_populates="teacher", cascade="all, delete-orphan"
    )
    bounty_submissions: Mapped[List["BountySubmission"]] = relationship(
        "BountySubmission",
        back_populates="student",
        foreign_keys="BountySubmission.student_id",
        cascade="all, delete-orphan",
    )
    ai_logs: Mapped[List["AIExplanationLog"]] = relationship(
        "AIExplanationLog", back_populates="user", cascade="all, delete-orphan"
    )
    challenges_as_challenger: Mapped[List["Challenge"]] = relationship(
        "Challenge",
        back_populates="challenger",
        foreign_keys="Challenge.challenger_id",
    )
    challenges_as_opponent: Mapped[List["Challenge"]] = relationship(
        "Challenge",
        back_populates="opponent",
        foreign_keys="Challenge.opponent_id",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"


# ─────────────────────────────────────────────────────────────────────────────
# Streak
# ─────────────────────────────────────────────────────────────────────────────

class Streak(Base):
    """
    Daily learning streak tracker.
    Maintains current streak, longest streak, and freeze token count.
    """
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    streak_freezes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="streak")

    def __repr__(self) -> str:
        return (
            f"<Streak user_id={self.user_id} "
            f"current={self.current_streak} longest={self.longest_streak}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Wallet
# ─────────────────────────────────────────────────────────────────────────────

class Wallet(Base):
    """
    Virtual economy wallet.
    balance = EduCoins (spendable currency)
    xp      = Experience Points (non-spendable, drives leaderboard)
    """
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="wallet")

    def __repr__(self) -> str:
        return f"<Wallet user_id={self.user_id} balance={self.balance} xp={self.xp}>"


# ─────────────────────────────────────────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────────────────────────────────────────

class Transaction(Base):
    """
    Immutable ledger of all coin movements.
    amount > 0 = credit, amount < 0 = debit.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_change: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} user_id={self.user_id} amount={self.amount} reason={self.reason!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# Bounty
# ─────────────────────────────────────────────────────────────────────────────

class Bounty(Base):
    """
    Teacher-posted time-limited challenge on a specific topic.
    Students earn reward_coins upon teacher approval.
    """
    __tablename__ = "bounties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reward_coins: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    teacher: Mapped["User"] = relationship("User", back_populates="bounties_created")
    submissions: Mapped[List["BountySubmission"]] = relationship(
        "BountySubmission", back_populates="bounty", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Bounty id={self.id} title={self.title!r} active={self.is_active}>"


# ─────────────────────────────────────────────────────────────────────────────
# BountySubmission
# ─────────────────────────────────────────────────────────────────────────────

class BountySubmission(Base):
    """Student's claim that they completed a bounty. Requires teacher approval."""

    __tablename__ = "bounty_submissions"
    __table_args__ = (
        UniqueConstraint("bounty_id", "student_id", name="uq_bounty_student"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bounty_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bounties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # 0-100 percentage

    # Relationships
    bounty: Mapped["Bounty"] = relationship("Bounty", back_populates="submissions")
    student: Mapped["User"] = relationship(
        "User",
        back_populates="bounty_submissions",
        foreign_keys=[student_id],
    )

    def __repr__(self) -> str:
        return (
            f"<BountySubmission id={self.id} "
            f"bounty_id={self.bounty_id} student_id={self.student_id} "
            f"approved={self.is_approved}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Challenge
# ─────────────────────────────────────────────────────────────────────────────

class Challenge(Base):
    """
    1v1 peer challenge with optional EduCoin wager.
    Supports both targeted (opponent_id set) and open challenges.
    """
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    challenger_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opponent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    wager_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ChallengeStatus] = mapped_column(
        Enum(ChallengeStatus, name="challengestatus"),
        default=ChallengeStatus.pending,
        nullable=False,
    )
    winner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    challenger: Mapped["User"] = relationship(
        "User",
        back_populates="challenges_as_challenger",
        foreign_keys=[challenger_id],
    )
    opponent: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="challenges_as_opponent",
        foreign_keys=[opponent_id],
    )
    winner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[winner_id],
    )
    results: Mapped[List["ChallengeResult"]] = relationship(
        "ChallengeResult", back_populates="challenge", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Challenge id={self.id} "
            f"challenger={self.challenger_id} vs opponent={self.opponent_id} "
            f"status={self.status}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ChallengeResult
# ─────────────────────────────────────────────────────────────────────────────

class ChallengeResult(Base):
    """Per-question performance record for a challenge."""

    __tablename__ = "challenge_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(String(100), nullable=False)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_taken_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    challenge: Mapped["Challenge"] = relationship("Challenge", back_populates="results")
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return (
            f"<ChallengeResult id={self.id} "
            f"challenge={self.challenge_id} student={self.student_id} correct={self.correct}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# AIExplanationLog
# ─────────────────────────────────────────────────────────────────────────────

class AIExplanationLog(Base):
    """
    Immutable log of every Synapse.ai explain call.
    Used to track coin expenditure and power the "Good Student" refund mechanic.
    """
    __tablename__ = "ai_explanation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    highlighted_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_language: Mapped[str] = mapped_column(String(50), default="Simple English", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    cost_coins: Mapped[int] = mapped_column(Integer, nullable=False)
    refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="ai_logs")

    def __repr__(self) -> str:
        return (
            f"<AIExplanationLog id={self.id} "
            f"user_id={self.user_id} cost={self.cost_coins} refunded={self.refunded}>"
        )
