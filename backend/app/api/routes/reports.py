from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/reports", tags=["Content Moderation & Reports"])


class ReportCreate(BaseModel):
    target_type: str  # "question", "chat_message", "user", "note"
    target_id: str
    reason: str
    description: Optional[str] = None
    reported_user_id: Optional[int] = None


class ResolveReport(BaseModel):
    action: str  # "dismissed", "action_taken"


@router.post("", summary="Submit a moderation report against content")
def submit_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Flag inappropriate or incorrect content."""
    report = models.Report(
        reporter_id=current_user.id,
        reported_user_id=payload.reported_user_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        description=payload.description,
        status="pending",
    )
    db.add(report)
    db.commit()

    return {
        "status": "reported",
        "report_id": report.id,
        "message": "Aapki report submit kar di gayi hai. Moderators ise jald review karenge.",
    }


@router.get("", summary="Teacher / Admin moderation queue")
def list_reports(
    status_filter: Optional[str] = "pending",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """View flagged reports list (Teachers/Admins only)."""
    if current_user.role not in [models.UserRole.teacher, models.UserRole.admin]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    query = db.query(models.Report)
    if status_filter:
        query = query.filter_by(status=status_filter)

    reports = query.order_by(models.Report.created_at.desc()).all()

    return {
        "reports": [
            {
                "id": r.id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "description": r.description,
                "status": r.status,
                "reporter_name": r.reporter.username,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ]
    }


@router.post("/{report_id}/resolve", summary="Resolve a moderation report")
def resolve_report(
    report_id: int,
    payload: ResolveReport,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Moderator marks report as reviewed or dismissed."""
    if current_user.role not in [models.UserRole.teacher, models.UserRole.admin]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    report = db.query(models.Report).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.status = payload.action
    db.commit()

    return {"status": "ok", "report_id": report.id, "new_status": report.status}
