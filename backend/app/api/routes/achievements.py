from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/achievements", tags=["Achievements"])

DEFAULT_ACHIEVEMENTS = [
    {
        "code": "first_blood",
        "title": "First Step",
        "description": "Pehla quiz safaltapoorvak complete kiya",
        "icon": "🌱",
        "category": "quiz",
        "xp_reward": 50,
        "coins_reward": 25,
    },
    {
        "code": "streak_3",
        "title": "Consistency Spark",
        "description": "3 din ka niyamit study streak banaya",
        "icon": "⚡",
        "category": "streak",
        "xp_reward": 60,
        "coins_reward": 30,
    },
    {
        "code": "streak_7",
        "title": "7-Day Streak Warrior",
        "description": "Lagatar 7 din padhai ki bina rukaawat",
        "icon": "🔥",
        "category": "streak",
        "xp_reward": 150,
        "coins_reward": 75,
    },
    {
        "code": "perfect_score",
        "title": "Perfectionist",
        "description": "Kisi bhi quiz mein 100% correct score haasil kiya",
        "icon": "🎯",
        "category": "quiz",
        "xp_reward": 100,
        "coins_reward": 50,
    },
    {
        "code": "speed_demon",
        "title": "Lightning Mind",
        "description": "5 seconds se kam time mein question ka sahi jawab diya",
        "icon": "⚡",
        "category": "speed",
        "xp_reward": 80,
        "coins_reward": 40,
    },
    {
        "code": "faction_hero",
        "title": "Faction Warrior",
        "description": "Apni Faction ke liye 200+ XP contribute kiya",
        "icon": "🛡️",
        "category": "faction",
        "xp_reward": 120,
        "coins_reward": 60,
    },
    {
        "code": "coin_collector",
        "title": "EduCoin Tycoon",
        "description": "Wallet mein 300+ EduCoins ikattha kiye",
        "icon": "💰",
        "category": "economy",
        "xp_reward": 100,
        "coins_reward": 50,
    },
]


def ensure_achievements_exist(db: Session):
    for a_data in DEFAULT_ACHIEVEMENTS:
        existing = db.query(models.Achievement).filter_by(code=a_data["code"]).first()
        if not existing:
            ach = models.Achievement(**a_data)
            db.add(ach)
    db.commit()


@router.get("", summary="List all badges with user unlock status")
def get_achievements(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all available achievements and whether current user has unlocked them."""
    ensure_achievements_exist(db)

    all_achievements = db.query(models.Achievement).all()
    unlocked_records = (
        db.query(models.UserAchievement)
        .filter_by(user_id=current_user.id)
        .all()
    )
    unlocked_map = {u.achievement_id: u.unlocked_at for u in unlocked_records}

    results = []
    for a in all_achievements:
        is_unlocked = a.id in unlocked_map
        results.append({
            "id": a.id,
            "code": a.code,
            "title": a.title,
            "description": a.description,
            "icon": a.icon,
            "category": a.category,
            "xp_reward": a.xp_reward,
            "coins_reward": a.coins_reward,
            "unlocked": is_unlocked,
            "unlocked_at": unlocked_map[a.id].isoformat() if is_unlocked else None,
        })

    total_unlocked = len(unlocked_records)
    return {
        "total_achievements": len(all_achievements),
        "unlocked_count": total_unlocked,
        "achievements": results,
    }


@router.post("/check", summary="Evaluate and unlock newly earned achievements")
def check_and_unlock_achievements(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Inspect user milestones and grant any newly qualified badges."""
    ensure_achievements_exist(db)

    unlocked_ids = {
        u.achievement_id
        for u in db.query(models.UserAchievement).filter_by(user_id=current_user.id).all()
    }

    newly_unlocked = []

    def grant(code: str):
        ach = db.query(models.Achievement).filter_by(code=code).first()
        if ach and ach.id not in unlocked_ids:
            ua = models.UserAchievement(user_id=current_user.id, achievement_id=ach.id)
            db.add(ua)
            # Award coins & XP
            if current_user.wallet:
                current_user.wallet.balance += ach.coins_reward
                current_user.wallet.xp += ach.xp_reward

            # Add in-app notification
            notif = models.Notification(
                user_id=current_user.id,
                title=f"🏆 Badge Unlocked: {ach.title}!",
                message=f"{ach.description} | +{ach.xp_reward} XP & +{ach.coins_reward} EduCoins awarded!",
                notif_type="achievement",
                action_url="../student/student_dashboard.html#achievements",
            )
            db.add(notif)
            newly_unlocked.append(ach.title)
            unlocked_ids.add(ach.id)

    # 1. First step (any quiz session)
    any_quiz = db.query(models.QuizSession).filter_by(user_id=current_user.id).first()
    if any_quiz:
        grant("first_blood")

    # 2. Streak checks
    streak = current_user.streak
    if streak:
        if streak.current_streak >= 3 or streak.longest_streak >= 3:
            grant("streak_3")
        if streak.current_streak >= 7 or streak.longest_streak >= 7:
            grant("streak_7")

    # 3. Wallet coins check
    if current_user.wallet and current_user.wallet.balance >= 300:
        grant("coin_collector")

    # 4. Perfect score check
    correct_run = (
        db.query(models.QuizSession.quiz_run_id)
        .filter_by(user_id=current_user.id, is_correct=True)
        .first()
    )
    if correct_run:
        grant("perfect_score")

    db.commit()

    return {
        "status": "ok",
        "new_unlocks_count": len(newly_unlocked),
        "newly_unlocked": newly_unlocked,
    }
