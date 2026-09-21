from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.security import require_role
from app.db import models
from app.services.ai_service import get_explanation

router = APIRouter(prefix="/api/study-materials", tags=["Smart Study Material"])
UPLOAD_DIR = Path(__file__).resolve().parents[4] / "frontend" / "assets" / "uploads" / "study-materials"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".txt", ".md"}


def local_insights(notes: str, chapter: str) -> dict[str, Any]:
    words = re.findall(r"[A-Za-z][A-Za-z-]{3,}", notes.lower())
    stopwords = {"this", "that", "with", "from", "into", "will", "have", "about", "chapter", "using"}
    concepts = []
    for word in words:
        if word not in stopwords and word not in concepts:
            concepts.append(word)
        if len(concepts) == 6:
            break
    formulas = re.findall(r"[^.!?\n]*(?:=|→|∫|√|²)[^.!?\n]*", notes)
    return {
        "summary": f"Study {chapter or 'this material'} in focused passes: definitions first, then worked examples, then recall practice.",
        "important_concepts": concepts or [chapter or "Core definitions", "Worked examples", "Key vocabulary"],
        "formula_sheet": [formula.strip() for formula in formulas[:8]],
        "chapter_notes": [line.strip() for line in notes.splitlines() if line.strip()][:8],
    }


@router.post("/analyze")
async def analyze_material(
    file: UploadFile | None = File(None),
    subject: str = Form("General"),
    chapter: str = Form(""),
    notes: str = Form(""),
    current_user: models.User = Depends(require_role("student")),
):
    if not file and not notes.strip():
        raise HTTPException(status_code=400, detail="Upload a PDF/PPT or paste notes first.")

    filename = None
    if file:
        extension = Path(file.filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Supported files: PDF, PPT, PPTX, TXT, or Markdown notes.")
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Study material must be smaller than 20MB.")
        filename = f"material_{secrets.token_hex(6)}{extension}"
        (UPLOAD_DIR / filename).write_bytes(content)

    insights = local_insights(notes, chapter)
    if notes.strip():
        try:
            insights["summary"] = await get_explanation(
                f"Create a concise study summary for {subject}, chapter {chapter or 'unspecified'} from these notes:\n{notes[:12000]}",
                "Simple English",
            )
        except Exception:
            pass

    return {
        "status": "analyzed",
        "filename": file.filename if file else None,
        "stored_file": f"/assets/uploads/study-materials/{filename}" if filename else None,
        "subject": subject,
        "chapter": chapter,
        **insights,
    }
