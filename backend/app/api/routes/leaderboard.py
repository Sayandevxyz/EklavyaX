from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_optional_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


def get_educoin_badge_tier(coins: int) -> Dict[str, Any]:
    """Calculates user's prestige badge tier based on EduCoins."""
    if coins >= 750:
        return {
            "tier_score": 4,
            "badge_name": "Heroic",
            "badge_icon": "👑",
            "badge_color": "#f43f5e",
            "badge_bg": "rgba(244, 63, 94, 0.2)",
        }
    elif coins >= 500:
        return {
            "tier_score": 3,
            "badge_name": "Diamond",
            "badge_icon": "💎",
            "badge_color": "#38bdf8",
            "badge_bg": "rgba(56, 189, 248, 0.2)",
        }
    elif coins >= 200:
        return {
            "tier_score": 2,
            "badge_name": "Gold",
            "badge_icon": "🥇",
            "badge_color": "#f59e0b",
            "badge_bg": "rgba(245, 158, 11, 0.2)",
        }
    elif coins >= 100:
        return {
            "tier_score": 1,
            "badge_name": "Silver",
            "badge_icon": "🥈",
            "badge_color": "#94a3b8",
            "badge_bg": "rgba(148, 163, 184, 0.2)",
        }
    else:
        return {
            "tier_score": 0,
            "badge_name": "Bronze",
            "badge_icon": "🥉",
            "badge_color": "#cd7f32",
            "badge_bg": "rgba(205, 127, 50, 0.2)",
        }


@router.get("/global", summary="Get global leaderboard")
def get_global_leaderboard(
    period: str = Query("all_time", regex="^(all_time|weekly|monthly)$"),
    sort_by: str = Query("coins", regex="^(coins|xp|streak|badge)$"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user),
) -> Dict[str, Any]:
    """
    Returns the global leaderboard of students ranked by Badge Tier (EduCoins prestige),
    Coins, XP, or Streak.
    """
    query = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.avatar_url,
            models.Faction.name.label("faction_name"),
            models.Faction.color_hex.label("faction_color"),
            models.Wallet.xp,
            models.Wallet.balance.label("coins"),
            models.Streak.current_streak.label("streak"),
        )
        .outerjoin(models.Faction, models.User.faction_id == models.Faction.id)
        .outerjoin(models.Wallet, models.User.id == models.Wallet.user_id)
        .outerjoin(models.Streak, models.User.id == models.Streak.user_id)
        .filter(models.User.role == models.UserRole.student)
    )

    rows = query.all()

    # Calculate badge tiers and sort
    annotated = []
    for r in rows:
        c_coins = r.coins or 0
        b_info = get_educoin_badge_tier(c_coins)
        annotated.append({
            "user_id": r.id,
            "username": r.username,
            "avatar_url": r.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={r.username}",
            "faction_name": r.faction_name or "Neutral",
            "faction_color": r.faction_color or "#888888",
            "xp": r.xp or 0,
            "coins": c_coins,
            "streak": r.streak or 0,
            "badge_tier": b_info["badge_name"],
            "badge_icon": b_info["badge_icon"],
            "badge_color": b_info["badge_color"],
            "badge_bg": b_info["badge_bg"],
            "tier_score": b_info["tier_score"],
        })

    # Sort: Those with more coins and higher performance (XP) rank at the top!
    if sort_by == "streak":
        annotated.sort(key=lambda x: (x["streak"], x["coins"], x["xp"]), reverse=True)
    elif sort_by == "xp":
        annotated.sort(key=lambda x: (x["xp"], x["coins"], x["tier_score"]), reverse=True)
    else:
        # Default or 'coins': Highest coins first, then XP (performance), then tier
        annotated.sort(key=lambda x: (x["coins"], x["xp"], x["tier_score"]), reverse=True)

    leaderboard = []
    my_rank_info = None

    for rank, item in enumerate(annotated[:limit], start=1):
        item["rank"] = rank
        leaderboard.append(item)
        if current_user and item["user_id"] == current_user.id:
            my_rank_info = item

    return {
        "period": period,
        "sort_by": sort_by,
        "total_ranked": len(leaderboard),
        "rankings": leaderboard,
        "my_rank": my_rank_info,
    }



@router.get("/factions", summary="Get faction rankings and top contributors")
def get_faction_leaderboard(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns ranking of all factions based on total scores, along with member counts
    and top contributor per faction.
    """
    factions = db.query(models.Faction).order_by(desc(models.Faction.score)).all()
    results = []

    for rank, faction in enumerate(factions, start=1):
        member_count = (
            db.query(func.count(models.User.id))
            .filter(models.User.faction_id == faction.id)
            .scalar()
            or 0
        )

        top_member = (
            db.query(models.User.username, models.Wallet.xp)
            .join(models.Wallet, models.User.id == models.Wallet.user_id)
            .filter(models.User.faction_id == faction.id)
            .order_by(desc(models.Wallet.xp))
            .first()
        )

        results.append({
            "rank": rank,
            "id": faction.id,
            "name": faction.name,
            "score": faction.score,
            "color_hex": faction.color_hex or "#4A90E2",
            "member_count": member_count,
            "top_contributor": top_member[0] if top_member else "None",
            "top_contributor_xp": top_member[1] if top_member else 0,
        })

    return {"factions": results}


@router.get("/me", summary="Get current user's ranking metrics")
def get_my_ranking(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns current user's global and faction rank positions."""
    wallet = db.query(models.Wallet).filter_by(user_id=current_user.id).first()
    my_xp = wallet.xp if wallet else 0

    higher_xp_count = (
        db.query(func.count(models.Wallet.id))
        .join(models.User, models.Wallet.user_id == models.User.id)
        .filter(models.User.role == models.UserRole.student, models.Wallet.xp > my_xp)
        .scalar()
        or 0
    )
    global_rank = higher_xp_count + 1

    total_students = (
        db.query(func.count(models.User.id))
        .filter(models.User.role == models.UserRole.student)
        .scalar()
        or 1
    )
    percentile = max(0.0, min(100.0, round(100.0 - (global_rank / total_students * 100.0), 1)))

    return {
        "global_rank": global_rank,
        "total_students": total_students,
        "percentile": percentile,
        "xp": my_xp,
        "coins": wallet.balance if wallet else 0,
        "streak": current_user.streak.current_streak if current_user.streak else 0,
    }
