from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/chat-threads", tags=["In-App Chat Threads"])


class ThreadCreate(BaseModel):
    title: str
    topic: str = "General"
    initial_message: str


class MessageCreate(BaseModel):
    message: str


class StatusUpdate(BaseModel):
    status: str  # "open" or "resolved"


@router.get("", summary="List discussion threads for current user")
def get_threads(
    topic: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve chat threads. Teachers view all open doubts; students view their own threads."""
    query = db.query(models.ChatThread)

    if current_user.role == models.UserRole.student:
        query = query.filter_by(student_id=current_user.id)

    if topic:
        query = query.filter_by(topic=topic)
    if status_filter:
        query = query.filter_by(status=status_filter)

    threads = query.order_by(models.ChatThread.updated_at.desc()).all()

    results = []
    for t in threads:
        msg_count = len(t.messages)
        last_msg = t.messages[-1].message if t.messages else ""
        results.append({
            "id": t.id,
            "title": t.title,
            "topic": t.topic,
            "status": t.status,
            "student_name": t.student.username,
            "student_avatar": t.student.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={t.student.username}",
            "message_count": msg_count,
            "last_message": last_msg[:100] + ("..." if len(last_msg) > 100 else ""),
            "updated_at": t.updated_at.isoformat(),
        })

    return {"threads": results}


@router.post("", summary="Start a new chat doubt thread")
def create_thread(
    payload: ThreadCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Open a new threaded doubt discussion."""
    thread = models.ChatThread(
        student_id=current_user.id,
        title=payload.title,
        topic=payload.topic,
        status="open",
    )
    db.add(thread)
    db.flush()

    first_message = models.ChatMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        message=payload.initial_message,
        is_teacher_reply=(current_user.role in [models.UserRole.teacher, models.UserRole.admin]),
    )
    db.add(first_message)
    db.commit()

    return {
        "status": "created",
        "thread_id": thread.id,
        "title": thread.title,
    }


@router.get("/{thread_id}", summary="Get thread conversation messages")
def get_thread_details(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """View all messages in a specific thread."""
    thread = db.query(models.ChatThread).filter_by(id=thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    messages = (
        db.query(models.ChatMessage)
        .filter_by(thread_id=thread_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    return {
        "id": thread.id,
        "title": thread.title,
        "topic": thread.topic,
        "status": thread.status,
        "student_id": thread.student_id,
        "student_name": thread.student.username,
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_name": m.sender.username,
                "sender_role": m.sender.role.value if hasattr(m.sender.role, "value") else str(m.sender.role),
                "is_teacher_reply": m.is_teacher_reply,
                "message": m.message,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/{thread_id}/messages", summary="Send a reply message in a thread")
def send_message(
    thread_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Send a reply to an ongoing thread."""
    thread = db.query(models.ChatThread).filter_by(id=thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    is_teacher = current_user.role in [models.UserRole.teacher, models.UserRole.admin]
    msg = models.ChatMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        message=payload.message,
        is_teacher_reply=is_teacher,
    )
    db.add(msg)
    thread.updated_at = datetime.now(timezone.utc)

    # Notify student if teacher replied
    if is_teacher and thread.student_id != current_user.id:
        notif = models.Notification(
            user_id=thread.student_id,
            title="💬 Teacher Answered Your Doubt!",
            message=f"Teacher {current_user.username} ne aapke thread '{thread.title}' par jawab diya hai.",
            notif_type="chat_reply",
            action_url="../student/chat_threads.html",
        )
        db.add(notif)

    db.commit()

    return {
        "status": "sent",
        "message_id": msg.id,
        "created_at": msg.created_at.isoformat(),
    }


@router.patch("/{thread_id}/status", summary="Resolve or reopen a thread")
def update_thread_status(
    thread_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Toggle thread status between open and resolved."""
    thread = db.query(models.ChatThread).filter_by(id=thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    thread.status = payload.status
    thread.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "updated", "new_status": thread.status}
