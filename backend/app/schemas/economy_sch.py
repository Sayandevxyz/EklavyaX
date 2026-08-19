"""
app/schemas/economy_sch.py
──────────────────────────
Pydantic schemas for the virtual economy, challenges, and leaderboard.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Wallet ────────────────────────────────────────────────────────────────────

class WalletResponse(BaseModel):
    user_id: int
    balance: int
    xp: int

    model_config = {"from_attributes": True}


# ── Transaction ───────────────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: int
    xp_change: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Internal earn/spend ───────────────────────────────────────────────────────

class EarnRequest(BaseModel):
    """Internal: add coins/XP to wallet."""
    coins: int = Field(0, ge=0)
    xp: int = Field(0, ge=0)
    reason: str = Field(..., max_length=100)


class SpendRequest(BaseModel):
    """Internal: deduct coins from wallet."""
    coins: int = Field(..., gt=0)
    reason: str = Field(..., max_length=100)


# ── Challenges ────────────────────────────────────────────────────────────────

class ChallengeStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    completed = "completed"
    cancelled = "cancelled"


class ChallengeCreate(BaseModel):
    """Create a new peer challenge. opponent_id=None means open challenge."""
    opponent_id: Optional[int] = Field(None, description="Target opponent. Omit for open challenge.")
    topic: str = Field(..., min_length=2, max_length=100, description="Topic/subject of the challenge")
    wager_coins: int = Field(0, ge=0, description="EduCoins wagered (must not exceed wallet balance)")


class ChallengeResponse(BaseModel):
    id: int
    challenger_id: int
    opponent_id: Optional[int] = None
    topic: str
    wager_coins: int
    status: ChallengeStatus
    winner_id: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChallengeSubmitResult(BaseModel):
    """Submit outcome of a challenge round."""
    winner_id: int = Field(..., description="User ID of the winner")


# ── Leaderboard ───────────────────────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    xp: int
    faction_name: Optional[str] = None


class FactionLeaderboardEntry(BaseModel):
    rank: int
    faction_id: int
    faction_name: str
    score: int
    member_count: int


class ClassLeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]


class FactionLeaderboardResponse(BaseModel):
    entries: List[FactionLeaderboardEntry]
