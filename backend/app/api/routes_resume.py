"""Resume upload + ATS analysis route.

Flow:  PDF upload -> text extraction (pypdf) -> Resume agent tool (ATS score,
strengths/weaknesses, missing keywords / skill gap, bullet rewrites).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, get_current_user
from app.memory import long_term
from app.services.resume_parser import PdfExtractionError, extract_text_from_pdf
from app.tools.resume_review import resume_review

router = APIRouter(prefix="/resume", tags=["resume"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_EXTRACTED_CHARS = 30


@router.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    target_role: str = Form("Software Engineer"),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Analyze an uploaded PDF resume against a target role.

    Returns ATS score, strengths, weaknesses, missing keywords (skill gap), and
    quantified bullet rewrites.
    """
    filename = (file.filename or "").lower()
    if file.content_type not in ("application/pdf", "application/octet-stream") and not (
        filename.endswith(".pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF resumes are supported."
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Resume exceeds the 5 MB limit.",
        )

    try:
        text = extract_text_from_pdf(data)
    except PdfExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if len(text) < MIN_EXTRACTED_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract readable text (is this a scanned image PDF?).",
        )

    raw = resume_review.invoke({"resume_text": text, "target_role": target_role})
    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError:
        analysis = {"raw": raw}

    long_term.award_xp(user.user_id, 15)

    return {
        "target_role": target_role,
        "characters_extracted": len(text),
        "analysis": analysis,
    }
