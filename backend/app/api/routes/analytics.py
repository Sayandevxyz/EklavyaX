from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/analytics", tags=["Teacher Analytics"])


def require_teacher(current_user: models.User):
    if current_user.role not in [models.UserRole.teacher, models.UserRole.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yeh analytics sirf teachers aur admins ke liye upalabdh hai.",
        )


@router.get("/overview", summary="Teacher class overview metrics")
def get_teacher_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Summary metrics: total students, active today, average accuracy, total questions attempted."""
    require_teacher(current_user)

    total_students = (
        db.query(func.count(models.User.id))
        .filter_by(role=models.UserRole.student)
        .scalar()
        or 0
    )

    today = datetime.now(timezone.utc).date()
    active_today = (
        db.query(func.count(models.Streak.id))
        .filter(models.Streak.last_activity_date == today)
        .scalar()
        or 0
    )

    total_attempts = db.query(func.count(models.QuizSession.id)).scalar() or 0
    correct_attempts = (
        db.query(func.count(models.QuizSession.id))
        .filter_by(is_correct=True)
        .scalar()
        or 0
    )

    avg_accuracy = (
        round((correct_attempts / total_attempts * 100), 1)
        if total_attempts > 0
        else 0.0
    )

    bounties_active = db.query(func.count(models.Bounty.id)).filter_by(is_active=True).scalar() or 0

    return {
        "total_students": total_students,
        "active_today": active_today,
        "total_questions_solved": total_attempts,
        "average_accuracy_percent": avg_accuracy,
        "active_bounties": bounties_active,
    }


@router.get("/weak-topics", summary="Weak topics heatmap across all students")
def get_weak_topics_heatmap(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns aggregated error rates per topic.
    Topics with higher failure rates are flagged as 'High Concern'.
    """
    require_teacher(current_user)

    stats = (
        db.query(
            models.QuizQuestion.topic,
            func.count(models.QuizSession.id).label("total"),
            func.sum(
                func.case((models.QuizSession.is_correct == False, 1), else_=0)
            ).label("incorrect"),
        )
        .join(models.QuizQuestion, models.QuizSession.question_id == models.QuizQuestion.id)
        .group_by(models.QuizQuestion.topic)
        .having(func.count(models.QuizSession.id) > 0)
        .all()
    )

    heatmap = []
    for row in stats:
        tot = row.total or 0
        inc = row.incorrect or 0
        error_rate = round((inc / tot * 100), 1) if tot > 0 else 0.0

        if error_rate >= 50:
            severity = "Critical"
            color = "#ef4444"
        elif error_rate >= 30:
            severity = "Moderate"
            color = "#f59e0b"
        else:
            severity = "Good"
            color = "#10b981"

        heatmap.append({
            "topic": row.topic,
            "total_attempts": tot,
            "incorrect_count": inc,
            "error_rate_percent": error_rate,
            "severity": severity,
            "color": color,
        })

    heatmap.sort(key=lambda x: x["error_rate_percent"], reverse=True)
    return {"heatmap": heatmap}


@router.get("/engagement", summary="Student engagement and streak trends")
def get_engagement_trends(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Engagement distributions and at-risk students."""
    require_teacher(current_user)

    # Streak distribution
    streak_buckets = {
        "0 days (Inactive)": 0,
        "1-3 days": 0,
        "4-7 days": 0,
        "8-14 days": 0,
        "15+ days (Champions)": 0,
    }

    streaks = db.query(models.Streak.current_streak).all()
    for (st,) in streaks:
        if st == 0:
            streak_buckets["0 days (Inactive)"] += 1
        elif 1 <= st <= 3:
            streak_buckets["1-3 days"] += 1
        elif 4 <= st <= 7:
            streak_buckets["4-7 days"] += 1
        elif 8 <= st <= 14:
            streak_buckets["8-14 days"] += 1
        else:
            streak_buckets["15+ days (Champions)"] += 1

    # At-risk students (Streak 0 or low accuracy)
    at_risk = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.email,
            models.Streak.current_streak,
            models.Wallet.xp,
        )
        .outerjoin(models.Streak, models.User.id == models.Streak.user_id)
        .outerjoin(models.Wallet, models.User.id == models.Wallet.user_id)
        .filter(models.User.role == models.UserRole.student)
        .filter((models.Streak.current_streak == 0) | (models.Streak.current_streak == None))
        .limit(10)
        .all()
    )

    at_risk_list = [
        {
            "id": r.id,
            "username": r.username,
            "email": r.email,
            "streak": r.current_streak or 0,
            "xp": r.xp or 0,
            "issue": "Streak inactive (>48 hrs)",
        }
        for r in at_risk
    ]

    return {
        "streak_distribution": streak_buckets,
        "at_risk_students": at_risk_list,
    }
