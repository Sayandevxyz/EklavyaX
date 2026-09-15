from __future__ import annotations

import io
import secrets
from datetime import date, datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api/certificates", tags=["Progress Certificates"])


class ClaimCertificateRequest(BaseModel):
    course_name: str
    score_percent: float = 95.0


def generate_certificate_pdf(cert: models.Certificate, student_name: str) -> io.BytesIO:
    """Generates an elegant, high-resolution landscape PDF certificate using ReportLab."""
    buffer = io.BytesIO()
    # Landscape orientation: 11 x 8.5 inches
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    # 1. Background color
    c.setFillColor(colors.HexColor("#081C14"))
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # 2. Outer decorative golden border
    c.setStrokeColor(colors.HexColor("#F4AE25"))
    c.setLineWidth(5)
    c.rect(20, 20, width - 40, height - 40, fill=False, stroke=True)

    # 3. Inner subtle emerald border
    c.setStrokeColor(colors.HexColor("#10B981"))
    c.setLineWidth(1.5)
    c.rect(28, 28, width - 56, height - 56, fill=False, stroke=True)

    # 4. Corner accents
    corner_size = 20
    c.setFillColor(colors.HexColor("#F4AE25"))
    # Top-left, top-right, bottom-left, bottom-right accents
    for x, y in [(30, height - 30), (width - 30, height - 30), (30, 30), (width - 30, 30)]:
        c.circle(x, y, 4, fill=True, stroke=False)

    # 5. Header / Brand Title
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.HexColor("#F4AE25"))
    c.drawCentredString(width / 2.0, height - 85, "E K L A V Y A X   A C A D E M Y")

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#9CA3AF"))
    c.drawCentredString(width / 2.0, height - 105, "GRAVITY GAMIFIED LEARNING PLATFORM • OFFICIAL VERIFICATION")

    # 6. Certificate Title
    c.setFont("Times-BoldItalic", 34)
    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.drawCentredString(width / 2.0, height - 165, "Certificate of Academic Excellence")

    # 7. Subtitle
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#D1D5DB"))
    c.drawCentredString(width / 2.0, height - 200, "This is proudly presented to:")

    # 8. Student Name
    c.setFont("Helvetica-Bold", 32)
    c.setFillColor(colors.HexColor("#FBBF24"))
    c.drawCentredString(width / 2.0, height - 250, student_name.upper())

    # Decorative line under name
    c.setStrokeColor(colors.HexColor("#F4AE25"))
    c.setLineWidth(2)
    c.line(width / 2.0 - 150, height - 262, width / 2.0 + 150, height - 262)

    # 9. Course Description
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#E5E7EB"))
    cert_text = (
        f"for outstanding mastery and exceptional dedication in successfully completing the course"
    )
    c.drawCentredString(width / 2.0, height - 295, cert_text)

    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#34D399"))
    c.drawCentredString(width / 2.0, height - 330, cert.course_name)

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor("#9CA3AF"))
    c.drawCentredString(width / 2.0, height - 355, f"Graduated with a Score of {cert.score_percent}%")

    # 10. Footer info: Issue Date, Verification Hash, Signatures
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#F4AE25"))
    c.drawString(60, 110, "ISSUE DATE")
    c.drawString(width - 240, 110, "ACADEMIC DIRECTOR")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#D1D5DB"))
    c.drawString(60, 92, cert.issue_date.strftime("%B %d, %Y"))
    c.drawString(width - 240, 92, "Prof. Dronacharya • EklavyaX")

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawCentredString(width / 2.0, 50, f"Certificate ID: {cert.certificate_id}  •  Verify at: {cert.verification_url}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


@router.get("/my", summary="List student's claimed certificates")
def get_my_certificates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all certificates earned by the student."""
    certs = (
        db.query(models.Certificate)
        .filter_by(user_id=current_user.id)
        .order_by(models.Certificate.issue_date.desc())
        .all()
    )

    return {
        "certificates": [
            {
                "id": c.id,
                "certificate_id": c.certificate_id,
                "course_name": c.course_name,
                "score_percent": c.score_percent,
                "issue_date": c.issue_date.isoformat(),
                "verification_url": c.verification_url,
                "download_url": f"/api/certificates/{c.certificate_id}/download-pdf",
            }
            for c in certs
        ]
    }


@router.post("/claim", summary="Claim or award a course certificate")
def claim_certificate(
    payload: ClaimCertificateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Issues a verifiable certificate for student achievement."""
    # Check if already issued for this course
    existing = (
        db.query(models.Certificate)
        .filter_by(user_id=current_user.id, course_name=payload.course_name)
        .first()
    )
    if existing:
        return {
            "status": "already_claimed",
            "certificate_id": existing.certificate_id,
            "download_url": f"/api/certificates/{existing.certificate_id}/download-pdf",
        }

    cert_id = f"EK-CERT-{secrets.token_hex(4).upper()}"
    today = datetime.now(timezone.utc).date()
    ver_url = f"https://eklavyax.app/verify/{cert_id}"

    cert = models.Certificate(
        certificate_id=cert_id,
        user_id=current_user.id,
        course_name=payload.course_name,
        score_percent=payload.score_percent,
        issue_date=today,
        verification_url=ver_url,
        qr_data=ver_url,
    )
    db.add(cert)

    # Award bonus XP for earning a certificate
    if current_user.wallet:
        current_user.wallet.xp += 100

    notif = models.Notification(
        user_id=current_user.id,
        title="🎓 New Certificate Earned!",
        message=f"Badhai ho! Aapne '{payload.course_name}' course ka official certificate haasil kar liya hai.",
        notif_type="achievement",
        action_url="../student/certificates.html",
    )
    db.add(notif)

    db.commit()

    return {
        "status": "issued",
        "certificate_id": cert_id,
        "course_name": payload.course_name,
        "download_url": f"/api/certificates/{cert_id}/download-pdf",
    }


@router.get("/{cert_id}/download-pdf", summary="Download official certificate PDF")
def download_certificate_pdf(
    cert_id: str,
    db: Session = Depends(get_db),
):
    """Streams the official high-resolution PDF certificate."""
    cert = db.query(models.Certificate).filter_by(certificate_id=cert_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    pdf_buffer = generate_certificate_pdf(cert, cert.user.username)
    filename = f"EklavyaX_Certificate_{cert.certificate_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
