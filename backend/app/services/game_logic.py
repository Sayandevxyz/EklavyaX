"""
app/services/game_logic.py
──────────────────────────
Core gamification algorithms for EklavyaX.

All functions accept a SQLAlchemy Session as their first argument and
operate on ORM objects. Routes should stay thin – business logic lives here.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db import models

# ── Faction configuration ─────────────────────────────────────────────────────

FACTION_DEFINITIONS = [
    {
        "name": "House Vidyut",
        "description": "Masters of logic and electricity. Swift thinkers who strike like lightning.",
        "color_hex": "#3B82F6",  # Electric blue
        "icon_url": None,
    },
    {
        "name": "House Agni",
        "description": "Fearless pioneers fuelled by passion. They burn bright and lead from the front.",
        "color_hex": "#EF4444",  # Fire red
        "icon_url": None,
    },
    {
        "name": "House Vayu",
        "description": "Fleet-footed scholars riding on the wind of curiosity and adaptability.",
        "color_hex": "#10B981",  # Wind green
        "icon_url": None,
    },
    {
        "name": "House Prithvi",
        "description": "Steadfast protectors of knowledge. Their patience and depth move mountains.",
        "color_hex": "#F59E0B",  # Earth amber
        "icon_url": None,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Faction helpers
# ─────────────────────────────────────────────────────────────────────────────

def ensure_factions_exist(db: Session) -> None:
    """
    Idempotent: create the four default factions if they don't exist yet.
    Called on application startup.
    """
    for defn in FACTION_DEFINITIONS:
        existing = db.query(models.Faction).filter_by(name=defn["name"]).first()
        if not existing:
            faction = models.Faction(**defn)
            db.add(faction)
    db.commit()


def assign_faction(db: Session) -> models.Faction:
    """
    Assign a new user to the faction with the fewest members.
    Falls back to random if all factions are equal.

    Returns:
        Faction ORM object.
    """
    # Count members per faction
    faction_counts = (
        db.query(models.Faction, func.count(models.User.id).label("cnt"))
        .outerjoin(models.User, models.User.faction_id == models.Faction.id)
        .group_by(models.Faction.id)
        .all()
    )

    if not faction_counts:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Factions not initialised. Contact an administrator.",
        )

    # Find minimum count and pick randomly among those with fewest members
    min_count = min(row.cnt for row in faction_counts)
    candidates = [row.Faction for row in faction_counts if row.cnt == min_count]
    return random.choice(candidates)


def update_faction_score(db: Session, faction_id: int, points: int) -> None:
    """Add `points` to the faction's global score."""
    faction = db.get(models.Faction, faction_id)
    if faction:
        faction.score += points
        db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Streak management
# ─────────────────────────────────────────────────────────────────────────────

def update_streak(db: Session, user_id: int) -> models.Streak:
    """
    Update the user's learning streak based on activity today.

    Rules:
    - First activity ever → streak = 1
    - Activity already recorded today → no change
    - Activity yesterday → streak += 1
    - Gap > 1 day AND streak_freezes > 0 → use a freeze, streak += 1
    - Gap > 1 day AND no freezes → reset to 1
    - Always update longest_streak and last_activity_date.

    Returns:
        Updated Streak ORM object.
    """
    streak = db.query(models.Streak).filter_by(user_id=user_id).first()
    if not streak:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Streak record not found for user {user_id}.",
        )

    today = date.today()

    if streak.last_activity_date is None:
        # First ever activity
        streak.current_streak = 1

    elif streak.last_activity_date == today:
        # Already logged today – nothing to do
        return streak

    else:
        delta = (today - streak.last_activity_date).days

        if delta == 1:
            # Consecutive day
            streak.current_streak += 1
        elif streak.streak_freezes > 0:
            # Use a freeze to bridge the gap
            streak.streak_freezes -= 1
            streak.current_streak += 1
        else:
            # Streak broken
            streak.current_streak = 1

    # Track personal best
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.last_activity_date = today
    db.commit()
    db.refresh(streak)
    return streak


# ─────────────────────────────────────────────────────────────────────────────
# Wallet / Economy
# ─────────────────────────────────────────────────────────────────────────────

def earn_coins_and_xp(
    db: Session,
    user_id: int,
    coins: int = 0,
    xp: int = 0,
    reason: str = "reward",
) -> models.Wallet:
    """
    Credit `coins` and/or `xp` to the user's wallet.
    Creates a Transaction ledger entry.
    Also increments the user's faction score by the XP earned.

    Returns:
        Updated Wallet ORM object.
    """
    wallet = db.query(models.Wallet).filter_by(user_id=user_id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet not found for user {user_id}.",
        )

    wallet.balance += coins
    wallet.xp += xp

    # Ledger entry
    tx = models.Transaction(
        user_id=user_id,
        amount=coins,
        xp_change=xp,
        reason=reason,
    )
    db.add(tx)

    # Propagate XP to faction score
    if xp > 0:
        user = db.get(models.User, user_id)
        if user and user.faction_id:
            update_faction_score(db, user.faction_id, xp)

    db.commit()
    db.refresh(wallet)
    return wallet


def spend_coins(
    db: Session,
    user_id: int,
    coins: int,
    reason: str = "purchase",
) -> models.Wallet:
    """
    Deduct `coins` from the wallet.

    Raises:
        HTTPException 400 if balance is insufficient.

    Returns:
        Updated Wallet ORM object.
    """
    wallet = db.query(models.Wallet).filter_by(user_id=user_id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet not found for user {user_id}.",
        )

    if wallet.balance < coins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient EduCoins. "
                f"Required: {coins}, Available: {wallet.balance}."
            ),
        )

    wallet.balance -= coins

    tx = models.Transaction(
        user_id=user_id,
        amount=-coins,
        xp_change=0,
        reason=reason,
    )
    db.add(tx)
    db.commit()
    db.refresh(wallet)
    return wallet


def refund_coins(
    db: Session,
    user_id: int,
    coins: int,
    reason: str = "refund",
) -> models.Wallet:
    """
    Add coins back to wallet (used for the "Good Student" refund mechanic).

    Returns:
        Updated Wallet ORM object.
    """
    return earn_coins_and_xp(db, user_id, coins=coins, xp=0, reason=reason)


# ─────────────────────────────────────────────────────────────────────────────
# Challenges
# ─────────────────────────────────────────────────────────────────────────────

def process_challenge_winner(
    db: Session,
    challenge_id: int,
    winner_id: int,
) -> Tuple[models.Challenge, models.Wallet]:
    """
    Finalise a completed challenge:
    1. Transfer the full wager pot (both wagers summed) to the winner.
    2. Award bonus XP to the winner.
    3. Mark the challenge as completed with a timestamp.

    Returns:
        (updated Challenge, winner's updated Wallet)
    """
    challenge = db.get(models.Challenge, challenge_id)
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge {challenge_id} not found.",
        )

    if challenge.status != models.ChallengeStatus.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge is not in an accepted state.",
        )

    if winner_id not in {challenge.challenger_id, challenge.opponent_id}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="winner_id must be one of the two participants.",
        )

    # Total pot = both sides wagered the same amount
    pot = challenge.wager_coins * 2

    # Award pot + XP to winner
    xp_reward = 25 + (pot // 10)  # Base 25 XP + 1 XP per 10 coins in pot
    winner_wallet = earn_coins_and_xp(
        db,
        winner_id,
        coins=pot,
        xp=xp_reward,
        reason="challenge_wager_win",
    )

    # Finalize challenge
    challenge.winner_id = winner_id
    challenge.status = models.ChallengeStatus.completed
    challenge.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(challenge)

    return challenge, winner_wallet


# ─────────────────────────────────────────────────────────────────────────────
# Leaderboards
# ─────────────────────────────────────────────────────────────────────────────

def get_class_leaderboard(
    db: Session, limit: int = 10
) -> List[dict]:
    """
    Return top `limit` students ordered by XP descending.

    Returns:
        List of dicts with user_id, username, xp, faction_name.
    """
    rows = (
        db.query(
            models.User.id,
            models.User.username,
            models.Wallet.xp,
            models.Faction.name.label("faction_name"),
        )
        .join(models.Wallet, models.Wallet.user_id == models.User.id)
        .outerjoin(models.Faction, models.Faction.id == models.User.faction_id)
        .filter(models.User.role == models.UserRole.student)
        .order_by(desc(models.Wallet.xp))
        .limit(limit)
        .all()
    )

    return [
        {
            "rank": idx + 1,
            "user_id": row.id,
            "username": row.username,
            "xp": row.xp,
            "faction_name": row.faction_name,
        }
        for idx, row in enumerate(rows)
    ]


def get_faction_leaderboard(db: Session) -> List[dict]:
    """
    Return all factions ordered by score descending, with member counts.

    Returns:
        List of dicts with faction data.
    """
    rows = (
        db.query(
            models.Faction.id,
            models.Faction.name,
            models.Faction.score,
            func.count(models.User.id).label("member_count"),
        )
        .outerjoin(models.User, models.User.faction_id == models.Faction.id)
        .group_by(models.Faction.id)
        .order_by(desc(models.Faction.score))
        .all()
    )

    return [
        {
            "rank": idx + 1,
            "faction_id": row.id,
            "faction_name": row.name,
            "score": row.score,
            "member_count": row.member_count,
        }
        for idx, row in enumerate(rows)
    ]
