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
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class ChallengeStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    completed = "completed"
    cancelled = "cancelled"


class Faction(Base):
    __tablename__ = "factions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    color_hex: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    icon_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    users: Mapped[List["User"]] = relationship("User", back_populates="faction")

    def __repr__(self) -> str:
        return f"<Faction id={self.id} name={self.name!r} score={self.score}>"


class User(Base):
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
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    office_hours: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    specialization_subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    dob: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    parent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parent_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    attendance_rate: Mapped[Optional[float]] = mapped_column(Float, default=92.0, nullable=True)
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


class Streak(Base):
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    streak_freezes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="streak")

    def __repr__(self) -> str:
        return (
            f"<Streak user_id={self.user_id} "
            f"current={self.current_streak} longest={self.longest_streak}>"
        )


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="wallet")

    def __repr__(self) -> str:
        return f"<Wallet user_id={self.user_id} balance={self.balance} xp={self.xp}>"


class Transaction(Base):
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

    user: Mapped["User"] = relationship("User", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} user_id={self.user_id} amount={self.amount} reason={self.reason!r}>"


class Bounty(Base):
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

    teacher: Mapped["User"] = relationship("User", back_populates="bounties_created")
    submissions: Mapped[List["BountySubmission"]] = relationship(
        "BountySubmission", back_populates="bounty", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Bounty id={self.id} title={self.title!r} active={self.is_active}>"


class BountySubmission(Base):
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
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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


class Challenge(Base):
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


class ChallengeResult(Base):
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

    challenge: Mapped["Challenge"] = relationship("Challenge", back_populates="results")
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return (
            f"<ChallengeResult id={self.id} "
            f"challenge={self.challenge_id} student={self.student_id} correct={self.correct}>"
        )


class AIExplanationLog(Base):
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

    user: Mapped["User"] = relationship("User", back_populates="ai_logs")

    def __repr__(self) -> str:
        return (
            f"<AIExplanationLog id={self.id} "
            f"user_id={self.user_id} cost={self.cost_coins} refunded={self.refunded}>"
        )


class ReasonCode(str, enum.Enum):
    granted = "granted"
    cooldown_violation = "cooldown_violation"
    cap_exceeded = "cap_exceeded"
    pattern_flagged = "pattern_flagged"
    invalid_answer = "invalid_answer"


class RewardAuditLog(Base):
    __tablename__ = "reward_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reward_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason_code: Mapped[ReasonCode] = mapped_column(
        Enum(ReasonCode, name="reasoncode"), nullable=False
    )
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return (
            f"<RewardAuditLog id={self.id} user={self.user_id} "
            f"reason={self.reason_code} coins={self.reward_coins} xp={self.reward_xp}>"
        )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(500), nullable=False)
    option_b: Mapped[str] = mapped_column(String(500), nullable=False)
    option_c: Mapped[str] = mapped_column(String(500), nullable=False)
    option_d: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_option_index: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    preview_coins: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    preview_xp: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def get_canonical_options(self) -> list[str]:
        return [self.option_a, self.option_b, self.option_c, self.option_d]

    def __repr__(self) -> str:
        return f"<QuizQuestion id={self.id} topic={self.topic!r}>"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    __table_args__ = (
        UniqueConstraint("quiz_run_id", "question_id", name="uq_run_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quiz_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    shuffled_order: Mapped[str] = mapped_column(String(20), nullable=False)
    question_shown_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    selected_option_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    question: Mapped["QuizQuestion"] = relationship("QuizQuestion", foreign_keys=[question_id])

    def __repr__(self) -> str:
        return (
            f"<QuizSession id={self.id} run={self.quiz_run_id} "
            f"user={self.user_id} q={self.question_id}>"
        )


class UserResponseMetric(Base):
    __tablename__ = "user_response_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<UserResponseMetric user={self.user_id} "
            f"time={self.response_time_ms}ms correct={self.is_correct}>"
        )


class BattleStatus(str, enum.Enum):
    scheduled = "scheduled"
    active = "active"
    completed = "completed"


class FactionBattle(Base):
    __tablename__ = "faction_battles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="Faction Wars", nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[BattleStatus] = mapped_column(
        Enum(BattleStatus, name="battlestatus"),
        default=BattleStatus.scheduled,
        nullable=False,
    )
    winning_faction_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("factions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    scores: Mapped[List["FactionBattleScore"]] = relationship(
        "FactionBattleScore", back_populates="battle", cascade="all, delete-orphan"
    )
    contributions: Mapped[List["FactionBattleContribution"]] = relationship(
        "FactionBattleContribution", back_populates="battle", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FactionBattle id={self.id} status={self.status} title={self.title!r}>"


class FactionBattleScore(Base):
    __tablename__ = "faction_battle_scores"

    __table_args__ = (
        UniqueConstraint("battle_id", "faction_id", name="uq_battle_faction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    battle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("faction_battles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    faction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("factions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contributor_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    battle: Mapped["FactionBattle"] = relationship("FactionBattle", back_populates="scores")
    faction: Mapped["Faction"] = relationship("Faction", foreign_keys=[faction_id])

    def __repr__(self) -> str:
        return (
            f"<FactionBattleScore battle={self.battle_id} "
            f"faction={self.faction_id} xp={self.total_xp}>"
        )


class FactionBattleContribution(Base):
    __tablename__ = "faction_battle_contributions"

    __table_args__ = (
        UniqueConstraint("battle_id", "user_id", name="uq_battle_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    battle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("faction_battles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    faction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("factions.id", ondelete="CASCADE"), nullable=False
    )
    xp_contributed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    battle: Mapped["FactionBattle"] = relationship("FactionBattle", back_populates="contributions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return (
            f"<FactionBattleContribution battle={self.battle_id} "
            f"user={self.user_id} xp={self.xp_contributed}>"
        )


# ─── Feature Models ──────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notif_type: Mapped[str] = mapped_column(String(50), default="info", nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="🏆", nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=25, nullable=False)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    achievement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    achievement: Mapped["Achievement"] = relationship("Achievement", foreign_keys=[achievement_id])
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    source_question_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    repetition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, default=lambda: datetime.now(timezone.utc).date(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class StudyGroup(Base):
    __tablename__ = "study_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    join_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
    members: Mapped[List["StudyGroupMember"]] = relationship("StudyGroupMember", back_populates="group", cascade="all, delete-orphan")
    notes: Mapped[List["GroupNote"]] = relationship("GroupNote", back_populates="group", cascade="all, delete-orphan")


class StudyGroupMember(Base):
    __tablename__ = "study_group_members"

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    group: Mapped["StudyGroup"] = relationship("StudyGroup", back_populates="members")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class GroupNote(Base):
    __tablename__ = "group_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    group: Mapped["StudyGroup"] = relationship("StudyGroup", back_populates="notes")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    attachment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'image' or 'pdf'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    teacher: Mapped[Optional["User"]] = relationship("User", foreign_keys=[teacher_id])
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_teacher_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])



class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    referrer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referee_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    referral_code: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    bonus_coins: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    bonus_xp: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    referrer: Mapped["User"] = relationship("User", foreign_keys=[referrer_id])
    referee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[referee_id])


class StudyPlanTask(Base):
    __tablename__ = "study_plan_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_exam: Mapped[str] = mapped_column(String(100), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    topic: Mapped[str] = mapped_column(String(150), nullable=False)
    subtasks: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    xp_reward: Mapped[int] = mapped_column(Integer, default=25, nullable=False)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reporter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reported_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "question", "chat_message", "user", "note"
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # "pending", "reviewed", "dismissed"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id])
    reported_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reported_user_id])


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certificate_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_name: Mapped[str] = mapped_column(String(150), nullable=False)
    score_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, default=lambda: datetime.now(timezone.utc).date(), nullable=False)
    verification_url: Mapped[str] = mapped_column(String(255), nullable=False)
    qr_data: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class LiveBattleRoom(Base):
    __tablename__ = "live_battle_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    host_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(100), default="General Science", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="waiting", nullable=False)  # "waiting", "active", "completed"
    questions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    host: Mapped["User"] = relationship("User", foreign_keys=[host_id])


class TeacherQuiz(Base):
    __tablename__ = "teacher_quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    teacher: Mapped["User"] = relationship("User", foreign_keys=[teacher_id])
    questions: Mapped[List["TeacherQuizQuestion"]] = relationship("TeacherQuizQuestion", back_populates="quiz", cascade="all, delete-orphan")


class TeacherQuizQuestion(Base):
    __tablename__ = "teacher_quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teacher_quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(500), nullable=False)
    option_b: Mapped[str] = mapped_column(String(500), nullable=False)
    option_c: Mapped[str] = mapped_column(String(500), nullable=False)
    option_d: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_option_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    quiz: Mapped["TeacherQuiz"] = relationship("TeacherQuiz", back_populates="questions")


class ParentAccessKey(Base):
    __tablename__ = "parent_access_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    parent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parent_email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])


class SchoolClass(Base):
    __tablename__ = "school_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)  # e.g., 'Class 10'
    grade_level: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    stream: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Science, Commerce, Arts


class SchoolSection(Base):
    __tablename__ = "school_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., '10-A'
    class_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True)
    class_teacher_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    room_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class SchoolSubject(Base):
    __tablename__ = "school_subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)  # e.g., 'MATH101'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    classes: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., '10-A, 10-B'
    teacher_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class TimetablePeriod(Base):
    __tablename__ = "timetable_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)  # MON, TUE, WED, THU, FRI
    period_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    start_time: Mapped[str] = mapped_column(String(20), default="09:00 AM", nullable=False)
    end_time: Mapped[str] = mapped_column(String(20), default="10:00 AM", nullable=False)
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_section: Mapped[str] = mapped_column(String(50), default="10-A", nullable=False)
    teacher_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    room_no: Mapped[Optional[str]] = mapped_column(String(20), default="Room 101", nullable=True)


class SchoolExam(Base):
    __tablename__ = "school_exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)  # Mid-Term Exam 2026
    exam_type: Mapped[str] = mapped_column(String(50), default="Unit Test", nullable=False)
    class_name: Mapped[str] = mapped_column(String(50), default="Class 10", nullable=False)
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    exam_date: Mapped[str] = mapped_column(String(30), nullable=False)
    start_time: Mapped[str] = mapped_column(String(20), default="10:00 AM", nullable=False)
    end_time: Mapped[str] = mapped_column(String(20), default="01:00 PM", nullable=False)
    max_marks: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    passing_marks: Mapped[int] = mapped_column(Integer, default=40, nullable=False)


class ExamResult(Base):
    __tablename__ = "exam_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey("school_exams.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    marks_obtained: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str] = mapped_column(String(10), default="A", nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date_str: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(20), default="present", nullable=False)  # present, absent, leave
    class_section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class SchoolAnnouncement(Base):
    __tablename__ = "school_announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(50), default="Entire School", nullable=False)  # Entire School, Teachers, Students, Parents, Class 10
    priority: Mapped[str] = mapped_column(String(20), default="Normal", nullable=False)  # Normal, Important, Urgent
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author_name: Mapped[str] = mapped_column(String(100), default="School Principal", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ParentTeacherMessage(Base):
    __tablename__ = "parent_teacher_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_from_parent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ResourceLibraryItem(Base):
    __tablename__ = "resource_library_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="Notes", nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), default="pdf", nullable=False)
    size_str: Mapped[str] = mapped_column(String(20), default="1.5 MB", nullable=False)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class TeacherQuizSubmission(Base):
    __tablename__ = "teacher_quiz_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("teacher_quizzes.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_marks: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    accuracy_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string of answers and evaluations
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


# ── Advanced Pedagogical Models ────────────────────────────────────────────────

class TopicMasteryRecord(Base):
    __tablename__ = "topic_mastery_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    concept_name: Mapped[str] = mapped_column(String(150), default="General", nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_seconds_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    doubts_posted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class RevisionRadarSchedule(Base):
    __tablename__ = "revision_radar_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(150), nullable=False)
    studied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    day1_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    day1_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    day7_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    day7_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    day30_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    day30_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retention_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class WeakAreaFlag(Base):
    __tablename__ = "weak_area_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(150), nullable=False)
    initial_score_pct: Mapped[float] = mapped_column(Float, nullable=False)
    retry_score_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bonus_coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class PYQQuestion(Base):
    __tablename__ = "pyq_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # JEE Main, JEE Advanced, NEET, CBSE Class 12
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chapter: Mapped[str] = mapped_column(String(150), nullable=False)
    topic: Mapped[str] = mapped_column(String(150), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(500), nullable=False)
    option_b: Mapped[str] = mapped_column(String(500), nullable=False)
    option_c: Mapped[str] = mapped_column(String(500), nullable=False)
    option_d: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_option_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    time_limit_sec: Mapped[int] = mapped_column(Integer, default=120, nullable=False)


class PYQAttempt(Base):
    __tablename__ = "pyq_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    accuracy_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_taken_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class QuestionBookmark(Base):
    __tablename__ = "question_bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="daily", nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(150), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    correct_option_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class PrerequisiteNode(Base):
    __tablename__ = "prerequisite_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    prerequisite_topic: Mapped[str] = mapped_column(String(150), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    explanation_warning: Mapped[str] = mapped_column(Text, nullable=False)

