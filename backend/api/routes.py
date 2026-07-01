"""
API Routes
POST /analyze  - Analyze uploaded/captured skin image
GET  /history  - Retrieve past analysis results
GET  /health   - Service health check
"""

import logging
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.database.db import get_db, AnalysisResult
from backend.services.analysis_orchestrator import analyze_image
from ai.vision_analyzer import BlurryPhotoError

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/jpg"
}
MAX_BYTES = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


# ──────────────────────────────────────────────
# FRONTEND ROUTES
# ──────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})


# ──────────────────────────────────────────────
# API ROUTES
# ──────────────────────────────────────────────

@router.post("/analyze")
async def analyze_skin(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Analyze skin from uploaded image.

    - Validates file type and size
    - Runs full analysis pipeline
    - Stores result in database
    - Returns comprehensive skin analysis + recommendations
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Use JPEG, PNG, or WebP.",
        )

    # Read and validate size
    image_bytes = await file.read()
    if len(image_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum size is {settings.MAX_IMAGE_SIZE_MB}MB.",
        )
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty image file.")

    # Run analysis
    try:
        result = analyze_image(image_bytes)
    except BlurryPhotoError as e:
        # Foto ditolak karena buram — kirim notif terstruktur yang dibaca frontend
        return JSONResponse(status_code=422, content={"rejected": True, **e.notice})
    except ValueError as e:
        # Penolakan lain (mis. wajah tidak terdeteksi) — bungkus format sama
        # supaya frontend bisa munculkan modal notif yang konsisten, bukan alert polos.
        return JSONResponse(status_code=422, content={
            "rejected": True,
            "title": "Foto Tidak Bisa Dianalisis",
            "message": str(e),
            "action_label": "Coba Lagi",
        })
    except Exception as e:
        logger.exception(f"Unexpected error during analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis error. Please try again.")

    # Persist to database
    try:
        acne_m = result.get("acne_metrics", {})
        db_record = AnalysisResult(
            session_id=result["session_id"],
            skin_type=result["skin_type"],
            skin_type_confidence=result["skin_type_confidence"],
            oil_level=result["oil_level"],
            dryness=result["dryness"],
            pore_visibility=result["pore_visibility"],
            skin_texture=result["skin_texture"],
            acne_count=acne_m.get("acne", 0),
            whitehead_count=acne_m.get("whitehead", 0),
            blackhead_count=acne_m.get("blackhead", 0),
            acne_scar_count=acne_m.get("acne_scar", 0),
            redness=result["redness"],
            pigmentation=result["pigmentation"],
            dark_spot_count=result["dark_spot_count"],
            dark_circle_level=result["dark_circle_level"],
            fine_lines_level=result["fine_lines_level"],
            skin_tone=result["skin_tone"],
            undertone=result["undertone"],
            overall_score=result["overall_score"],
            full_result=result,
            recommendations=result.get("recommendations"),
        )
        db.add(db_record)
        db.commit()
        logger.info(f"Saved analysis {result['session_id']} to database.")
    except Exception as e:
        logger.warning(f"Could not save to DB: {e}")
        db.rollback()

    return JSONResponse(content=result)


@router.get("/history")
async def get_history(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Retrieve past analysis results (most recent first).
    """
    records = (
        db.query(AnalysisResult)
        .order_by(AnalysisResult.created_at.desc())
        .limit(min(limit, 50))
        .all()
    )

    history = [
        {
            "id": r.id,
            "session_id": r.session_id,
            "created_at": r.created_at.isoformat(),
            "skin_type": r.skin_type,
            "overall_score": r.overall_score,
            "skin_tone": r.skin_tone,
        }
        for r in records
    ]

    return JSONResponse(content={"history": history, "count": len(history)})


@router.get("/health")
async def health():
    return {"status": "ok", "service": "OPSHE Beauty AI", "version": "1.0.0"}
