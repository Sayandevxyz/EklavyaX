from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class NotificationCreate(BaseModel):
    title: str
    message: str
    notif_type: str = "info"  # "streak_reminder", "bounty_deadline", "war_result", "duel_invite", "achievement"
    action_url: Optional[str] = None


@router.get("", summary="List current user notifications")
def get_notifications(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch notifications for the logged-in user with unread count."""
    notifs = (
        db.query(models.Notification)
        .filter_by(user_id=current_user.id)
        .order_by(desc(models.Notification.created_at))
        .limit(limit)
        .all()
    )

    unread_count = (
        db.query(models.Notification)
        .filter_by(user_id=current_user.id, is_read=False)
        .count()
    )

    return {
        "unread_count": unread_count,
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "notif_type": n.notif_type,
                "is_read": n.is_read,
                "action_url": n.action_url,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
    }


@router.post("/{notification_id}/read", summary="Mark a single notification as read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark a specific notification as read."""
    notif = db.query(models.Notification).filter_by(id=notification_id, user_id=current_user.id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"status": "ok", "message": "Notification marked as read"}


@router.post("/read-all", summary="Mark all notifications as read")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark all unread notifications of the user as read."""
    db.query(models.Notification).filter_by(user_id=current_user.id, is_read=False).update(
        {"is_read": True}
    )
    db.commit()
    return {"status": "ok", "message": "All notifications marked as read"}


@router.post("/trigger-reminders", summary="Check and trigger automatic streak and deadline reminders")
def trigger_reminders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Check if user hasn't studied today or has active bounties expiring,
    and create proactive notification cards.
    """
    notifications_created = 0
    today = datetime.now(timezone.utc).date()

    # Streak reminder
    streak = current_user.streak
    if streak and streak.last_activity_date != today:
        existing = (
            db.query(models.Notification)
            .filter_by(user_id=current_user.id, notif_type="streak_reminder")
            .filter(models.Notification.created_at >= datetime.combine(today, datetime.min.time()))
            .first()
        )
        if not existing:
            notif = models.Notification(
                user_id=current_user.id,
                title="🔥 Streak Danger Alert!",
                message=f"Aapka {streak.current_streak} din ka streak khatam hone wala hai! Aaj ka ek 5-minute quiz solve karein aur streak bachayein.",
                notif_type="streak_reminder",
                action_url="../student/quiz.html",
            )
            db.add(notif)
            notifications_created += 1

    # Active Bounty reminder
    active_bounties = db.query(models.Bounty).filter_by(is_active=True).limit(2).all()
    for b in active_bounties:
        existing_bounty_notif = (
            db.query(models.Notification)
            .filter_by(user_id=current_user.id, notif_type="bounty_deadline")
            .filter(models.Notification.created_at >= datetime.combine(today, datetime.min.time()))
            .first()
        )
        if not existing_bounty_notif:
            notif = models.Notification(
                user_id=current_user.id,
                title=f"⚡ New Bounty: {b.title}",
                message=f"Topic: {b.topic} | Reward: +{b.reward_coins} EduCoins! Solve karne se pehle deadline check karein.",
                notif_type="bounty_deadline",
                action_url="../student/assignments.html",
            )
            db.add(notif)
            notifications_created += 1
            break

    db.commit()
    return {"status": "ok", "new_notifications": notifications_created}
