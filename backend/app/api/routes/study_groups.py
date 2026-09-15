from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/study-groups", tags=["Study Groups"])


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject: str = "General"


class GroupJoin(BaseModel):
    join_code: str


class NoteCreate(BaseModel):
    title: str
    content: str


@router.get("/my", summary="List user's study groups")
def get_my_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all study groups the current user has created or joined."""
    memberships = (
        db.query(models.StudyGroupMember)
        .filter_by(user_id=current_user.id)
        .all()
    )

    groups = []
    for m in memberships:
        g = m.group
        member_count = db.query(models.StudyGroupMember).filter_by(group_id=g.id).count()
        notes_count = db.query(models.GroupNote).filter_by(group_id=g.id).count()

        groups.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "subject": g.subject,
            "join_code": g.join_code,
            "my_role": m.role,
            "creator_name": g.creator.username,
            "member_count": member_count,
            "notes_count": notes_count,
            "created_at": g.created_at.isoformat(),
        })

    return {"groups": groups}


@router.post("/create", summary="Create a new study group")
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new peer study group and generate a shareable join code."""
    join_code = f"GRP-{secrets.token_hex(3).upper()}"

    group = models.StudyGroup(
        name=payload.name,
        description=payload.description,
        subject=payload.subject,
        join_code=join_code,
        creator_id=current_user.id,
    )
    db.add(group)
    db.flush()

    member = models.StudyGroupMember(
        group_id=group.id,
        user_id=current_user.id,
        role="creator",
    )
    db.add(member)

    # Initial welcome note
    welcome_note = models.GroupNote(
        group_id=group.id,
        user_id=current_user.id,
        title="🌟 Group Notes Guidelines",
        content=(
            f"# Welcome to {group.name}!\n\n"
            "Yahan aap sabhi members milkar revision notes, important formulas, aur quiz strategies share kar sakte hain.\n"
            "- Apne doston ko invite karne ke liye yeh code share karein: **" + join_code + "**"
        ),
    )
    db.add(welcome_note)
    db.commit()

    return {
        "status": "created",
        "group_id": group.id,
        "name": group.name,
        "join_code": group.join_code,
    }


@router.post("/join", summary="Join a study group via code")
def join_group(
    payload: GroupJoin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Join an existing study group using its join code."""
    group = (
        db.query(models.StudyGroup)
        .filter_by(join_code=payload.join_code.strip().upper())
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study group code invalid hai. Kripya check karke dobara dalein.",
        )

    existing = (
        db.query(models.StudyGroupMember)
        .filter_by(group_id=group.id, user_id=current_user.id)
        .first()
    )
    if existing:
        return {"status": "already_joined", "group_id": group.id, "name": group.name}

    member = models.StudyGroupMember(
        group_id=group.id,
        user_id=current_user.id,
        role="member",
    )
    db.add(member)
    db.commit()

    return {"status": "joined", "group_id": group.id, "name": group.name}


@router.get("/{group_id}/notes", summary="Fetch all shared notes in a group")
def get_group_notes(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List notes within a group."""
    member = (
        db.query(models.StudyGroupMember)
        .filter_by(group_id=group_id, user_id=current_user.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Aap is group ke sadasya nahi hain.")

    notes = (
        db.query(models.GroupNote)
        .filter_by(group_id=group_id)
        .order_by(models.GroupNote.updated_at.desc())
        .all()
    )

    return {
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "author": n.user.username,
                "updated_at": n.updated_at.isoformat(),
            }
            for n in notes
        ]
    }


@router.post("/{group_id}/notes", summary="Add a shared note to a study group")
def add_group_note(
    group_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new note in the group."""
    member = (
        db.query(models.StudyGroupMember)
        .filter_by(group_id=group_id, user_id=current_user.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Aap is group ke sadasya nahi hain.")

    note = models.GroupNote(
        group_id=group_id,
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
    )
    db.add(note)
    db.commit()

    return {"status": "created", "note_id": note.id, "title": note.title}
