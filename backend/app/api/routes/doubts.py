from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/doubts", tags=["Doubts & Attachments"])

UPLOAD_DIR = Path(__file__).resolve().parents[4] / "frontend" / "assets" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class AskDoubtRequest(BaseModel):
    title: str
    subject: str = "Physics"
    description: str
    teacher_id: Optional[int] = None
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_type: Optional[str] = None  # 'image' or 'pdf'


class ReplyDoubtRequest(BaseModel):
    message: str
    attachment_url: Optional[str] = None


@router.get("/teachers", summary="Get list of available teachers for doubt assignment")
def get_teachers_list(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns all teachers with names and avatars so students can direct their doubt to a specific teacher."""
    teachers = (
        db.query(models.User)
        .filter(models.User.role.in_([models.UserRole.teacher, models.UserRole.admin]))
        .all()
    )

    return {
        "teachers": [
            {
                "id": t.id,
                "name": t.username,
                "email": t.email,
                "avatar_url": t.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={t.username}",
            }
            for t in teachers
        ]
    }


@router.post("/upload", summary="Upload a doubt photo or PDF attachment")
async def upload_doubt_attachment(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Accepts JPG, PNG, WebP image or PDF document.
    Saves to the server's uploads folder and returns access URL.
    """
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
    orig_ext = Path(file.filename).suffix.lower()

    if orig_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{orig_ext}'. Please upload an image (JPG, PNG) or PDF document.",
        )

    # 10MB limit
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum 10MB limit.",
        )

    file_type = "pdf" if orig_ext == ".pdf" else "image"
    safe_filename = f"doubt_{secrets.token_hex(6)}{orig_ext}"
    dest_path = UPLOAD_DIR / safe_filename

    with open(dest_path, "wb") as f:
        f.write(content)

    file_url = f"/assets/uploads/{safe_filename}"

    return {
        "status": "uploaded",
        "file_url": file_url,
        "filename": file.filename,
        "attachment_type": file_type,
    }


@router.post("/ask", summary="Student asks doubt directed to a chosen teacher with photo/pdf")
def ask_doubt(
    payload: AskDoubtRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Creates a new doubt thread and sends a direct alert to the chosen teacher."""
    thread = models.ChatThread(
        student_id=current_user.id,
        teacher_id=payload.teacher_id,
        title=payload.title,
        topic=payload.subject,
        status="open",
        attachment_url=payload.attachment_url,
        attachment_name=payload.attachment_name,
        attachment_type=payload.attachment_type,
    )
    db.add(thread)
    db.flush()

    # Initial message
    first_msg = models.ChatMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        message=payload.description,
        attachment_url=payload.attachment_url,
        is_teacher_reply=False,
    )
    db.add(first_msg)

    # Notify teacher if assigned
    if payload.teacher_id:
        teacher = db.query(models.User).filter_by(id=payload.teacher_id).first()
        if teacher:
            notif = models.Notification(
                user_id=teacher.id,
                title=f"❓ New Doubt from {current_user.username}",
                message=f"Student {current_user.username} ne aapse '{payload.title}' par doubt poocha hai.",
                notif_type="doubt_assigned",
                action_url="../teacher/doubts.html",
            )
            db.add(notif)

    db.commit()

    return {
        "status": "posted",
        "doubt_id": thread.id,
        "title": thread.title,
        "assigned_teacher_id": payload.teacher_id,
    }


@router.get("/list", summary="List doubts for current student or teacher")
def list_doubts(
    status_filter: Optional[str] = None,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Students view their doubts; Teachers view doubts assigned to them or all open questions.
    """
    query = db.query(models.ChatThread)

    if current_user.role == models.UserRole.student:
        query = query.filter_by(student_id=current_user.id)
    elif current_user.role == models.UserRole.teacher:
        # Teachers see doubts assigned to them or unassigned in their specialization subject
        teacher_subj = current_user.specialization_subject or ""
        base_cond = (models.ChatThread.teacher_id == current_user.id)
        if teacher_subj:
            base_cond = base_cond | (models.ChatThread.topic.ilike(f"%{teacher_subj}%"))
        else:
            base_cond = base_cond | (models.ChatThread.teacher_id == None)
        query = query.filter(base_cond)

    if status_filter:
        query = query.filter_by(status=status_filter)
    if subject and subject != "all":
        query = query.filter(models.ChatThread.topic.ilike(f"%{subject}%"))

    doubts = query.order_by(models.ChatThread.updated_at.desc()).all()

    results = []
    for d in doubts:
        assigned_teacher_name = d.teacher.username if d.teacher else "Unassigned / Any Teacher"
        msg_count = len(d.messages)
        last_msg = d.messages[-1].message if d.messages else ""

        results.append({
            "id": d.id,
            "title": d.title,
            "subject": d.topic,
            "status": d.status,
            "student_name": d.student.username,
            "student_grade": d.student.grade or "Class 12",
            "assigned_teacher_name": assigned_teacher_name,
            "assigned_teacher_id": d.teacher_id,
            "attachment_url": d.attachment_url,
            "attachment_name": d.attachment_name,
            "attachment_type": d.attachment_type,
            "message_count": msg_count,
            "last_message": last_msg[:120],
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
        })

    return {"doubts": results}


@router.get("/{doubt_id}", summary="Get complete doubt thread and conversation")
def get_doubt_detail(
    doubt_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve doubt details, attachments, and message history."""
    thread = db.query(models.ChatThread).filter_by(id=doubt_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doubt not found")

    messages = (
        db.query(models.ChatMessage)
        .filter_by(thread_id=doubt_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    return {
        "id": thread.id,
        "title": thread.title,
        "subject": thread.topic,
        "status": thread.status,
        "student_id": thread.student_id,
        "student_name": thread.student.username,
        "assigned_teacher_name": thread.teacher.username if thread.teacher else "Any Teacher",
        "attachment_url": thread.attachment_url,
        "attachment_name": thread.attachment_name,
        "attachment_type": thread.attachment_type,
        "created_at": thread.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_name": m.sender.username,
                "sender_role": m.sender.role.value if hasattr(m.sender.role, "value") else str(m.sender.role),
                "is_teacher_reply": m.is_teacher_reply,
                "message": m.message,
                "attachment_url": m.attachment_url,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/{doubt_id}/reply", summary="Post a reply to the doubt")
def reply_doubt(
    doubt_id: int,
    payload: ReplyDoubtRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Add a response message to the doubt thread."""
    thread = db.query(models.ChatThread).filter_by(id=doubt_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doubt not found")

    is_teacher = current_user.role in [models.UserRole.teacher, models.UserRole.admin]

    msg = models.ChatMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        message=payload.message,
        attachment_url=payload.attachment_url,
        is_teacher_reply=is_teacher,
    )
    db.add(msg)
    thread.updated_at = datetime.now(timezone.utc)

    # If teacher replies, notify the student
    if is_teacher and thread.student_id != current_user.id:
        notif = models.Notification(
            user_id=thread.student_id,
            title="👨‍🏫 Teacher Answered Your Doubt!",
            message=f"Teacher {current_user.username} ne aapke doubt '{thread.title}' ka solution bheja hai.",
            notif_type="doubt_solution",
            action_url="../student/doubts.html",
        )
        db.add(notif)

    db.commit()

    return {"status": "replied", "message_id": msg.id}
