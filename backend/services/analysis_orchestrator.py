"""
Analysis Orchestrator — Vision API Primary + CV Fallback
Claude Vision API menganalisis foto langsung untuk akurasi maksimal.
"""

import logging
import uuid
import io
import asyncio
from typing import Dict, Any

from PIL import Image

from backend.utils.image_processing import (
    preprocess_image, check_image_quality, pil_to_cv2
)
from backend.services.face_detection import detect_face
from backend.services.skin_analyzer import calculate_overall_score
from ai.vision_analyzer import (
    analyze_skin_with_vision,
    calculate_overall_score_from_vision
)
from ai.ai_recommendation import get_ai_recommendation
from ai.recommendation_engine import generate_recommendations

import numpy as np
import cv2

logger = logging.getLogger(__name__)


def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Full analysis pipeline.
    Primary: Claude Vision API
    Fallback: Computer Vision
    """
    session_id = str(uuid.uuid4())[:16]
    logger.info(f"[{session_id}] Starting analysis pipeline")

    # ── 1. Load image ──
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Invalid image file: {e}")

    # ── 2. Quality check ──
    raw_cv2 = pil_to_cv2(pil_img)
    ok, reason = check_image_quality(raw_cv2)
    if not ok:
        raise ValueError(reason)

    # ── 3. Face detection (still needed for validation) ──
    logger.info(f"[{session_id}] Validating face...")
    preprocessed, original = preprocess_image(pil_img)
    face_result = detect_face(preprocessed)
    if not face_result.success:
        raise ValueError(face_result.error)

    # ── 4. Claude Vision API Analysis (Primary) ──
    logger.info(f"[{session_id}] Sending to Claude Vision API...")
    vision_result = None
    try:
        loop = asyncio.new_event_loop()
        vision_result = loop.run_until_complete(
            analyze_skin_with_vision(image_bytes)
        )
        loop.close()
    except Exception as e:
        logger.warning(f"[{session_id}] Vision API error: {e}")

    if vision_result:
        logger.info(f"[{session_id}] Vision API success — building result")
        result = _build_result_from_vision(vision_result, session_id)
    else:
        logger.warning(f"[{session_id}] Falling back to CV analysis")
        result = _build_result_from_cv(
            preprocessed, face_result, session_id
        )

    # ── 5. AI Recommendations ──
    logger.info(f"[{session_id}] Generating AI recommendations...")
    try:
        loop2 = asyncio.new_event_loop()
        recommendations = loop2.run_until_complete(
            get_ai_recommendation(result)
        )
        loop2.close()
        if not recommendations:
            raise ValueError("Empty")
        logger.info(f"[{session_id}] Claude AI recommendation OK")
    except Exception as e:
        logger.warning(f"[{session_id}] Recommendation fallback: {e}")
        recommendations = generate_recommendations(result)

    result["recommendations"]   = recommendations
    result["morning_routine"]   = recommendations.get("morning_routine", [])
    result["night_routine"]     = recommendations.get("night_routine", [])
    result["key_ingredients"]   = recommendations.get("key_ingredients", [])
    result["concerns"]          = recommendations.get("concerns", [])

    logger.info(f"[{session_id}] Analysis complete. Score: {result['overall_score']}")
    return result


def _build_result_from_vision(
    vision: Dict[str, Any], session_id: str
) -> Dict[str, Any]:
    """Build standardized result from Claude Vision output."""

    overall_score = calculate_overall_score_from_vision(vision)
    acne_m = vision.get("acne_metrics", {})

    return {
        "session_id":            session_id,
        "skin_type":             vision.get("skin_type", "Normal"),
        "skin_type_confidence":  round(vision.get("skin_type_confidence", 0.75), 2),
        "oil_level":             round(float(vision.get("oil_level", 40)), 1),
        "dryness":               round(float(vision.get("dryness", 30)), 1),
        "pore_visibility":       round(float(vision.get("pore_visibility", 30)), 1),
        "skin_texture":          vision.get("skin_texture", "Normal"),
        "acne_metrics": {
            "acne":       int(acne_m.get("acne", 0)),
            "whitehead":  int(acne_m.get("whitehead", 0)),
            "blackhead":  int(acne_m.get("blackhead", 0)),
            "acne_scar":  int(acne_m.get("acne_scar", 0)),
        },
        "redness":               round(float(vision.get("redness", 15)), 1),
        "pigmentation":          round(float(vision.get("pigmentation", 20)), 1),
        "dark_spot_count":       int(vision.get("dark_spot_count", 0)),
        "dark_circle_level":     vision.get("dark_circle_level", "None"),
        "fine_lines_level":      vision.get("fine_lines_level", "None"),
        "skin_tone":             vision.get("skin_tone", "Medium"),
        "undertone":             vision.get("undertone", "Neutral"),
        "overall_score":         overall_score,
        "analysis_source":       "Claude Vision AI",
        "zones": [
            {
                "zone":             z.get("zone", ""),
                "oil_level":        round(float(z.get("oil_level", 40)), 1),
                "dryness":          round(float(z.get("dryness", 30)), 1),
                "pore_visibility":  round(float(z.get("pore_visibility", 30)), 1),
                "redness":          round(float(z.get("redness", 15)), 1),
                "texture":          z.get("texture", "Normal"),
            }
            for z in vision.get("zones", [])
        ],
    }


def _build_result_from_cv(
    preprocessed, face_result, session_id: str
) -> Dict[str, Any]:
    """Fallback: Computer Vision analysis."""
    from backend.services.face_detection import extract_zone_pixels, FACE_ZONES
    from backend.services.skin_analyzer import (
        analyze_skin_type, estimate_oil_level, estimate_dryness,
        estimate_pore_visibility, estimate_redness, estimate_texture,
        estimate_pigmentation, count_dark_spots, estimate_dark_circles,
        estimate_fine_lines, estimate_skin_tone, estimate_undertone,
        detect_acne, calculate_overall_score,
    )

    landmarks = face_result.landmarks
    zone_metrics = {}
    all_pixels = []

    for zone_name, zone_indices in FACE_ZONES.items():
        pixels = extract_zone_pixels(preprocessed, landmarks, zone_indices)
        if pixels is None or len(pixels) < 10:
            zone_metrics[zone_name] = {
                "oil_level": 40.0, "dryness": 30.0,
                "pore_visibility": 30.0, "redness": 15.0,
                "texture": "Normal",
            }
            continue
        all_pixels.append(pixels)
        zone_metrics[zone_name] = {
            "oil_level":        estimate_oil_level(pixels),
            "dryness":          estimate_dryness(pixels),
            "pore_visibility":  estimate_pore_visibility(pixels),
            "redness":          estimate_redness(pixels),
            "texture":          estimate_texture(pixels),
        }

    combined = np.vstack(all_pixels) if all_pixels else preprocessed.reshape(-1, 3)

    skin_type, skin_type_confidence = analyze_skin_type(zone_metrics)
    oil_level       = float(np.mean([z["oil_level"] for z in zone_metrics.values()]))
    dryness         = float(np.mean([z["dryness"] for z in zone_metrics.values()]))
    pore_visibility = float(np.mean([z["pore_visibility"] for z in zone_metrics.values()]))
    redness         = float(np.mean([z["redness"] for z in zone_metrics.values()]))
    skin_texture    = estimate_texture(combined)
    acne_metrics    = detect_acne(preprocessed)
    acne_total      = sum(acne_metrics.values())
    pigmentation    = estimate_pigmentation(combined)
    gray            = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
    dark_spot_count = count_dark_spots(gray)
    dark_circle     = estimate_dark_circles(preprocessed, landmarks)
    fine_lines      = estimate_fine_lines(preprocessed)
    skin_tone       = estimate_skin_tone(combined)
    undertone       = estimate_undertone(combined)

    overall_score = calculate_overall_score({
        "dryness": dryness, "skin_texture": skin_texture,
        "pore_visibility": pore_visibility, "acne_total": acne_total,
        "pigmentation": pigmentation, "redness": redness,
        "dark_circle_level": dark_circle, "fine_lines_level": fine_lines,
    })

    return {
        "session_id":           session_id,
        "skin_type":            skin_type,
        "skin_type_confidence": round(skin_type_confidence, 2),
        "oil_level":            round(oil_level, 1),
        "dryness":              round(dryness, 1),
        "pore_visibility":      round(pore_visibility, 1),
        "skin_texture":         skin_texture,
        "acne_metrics":         acne_metrics,
        "redness":              round(redness, 1),
        "pigmentation":         round(pigmentation, 1),
        "dark_spot_count":      dark_spot_count,
        "dark_circle_level":    dark_circle,
        "fine_lines_level":     fine_lines,
        "skin_tone":            skin_tone,
        "undertone":            undertone,
        "overall_score":        overall_score,
        "analysis_source":      "Computer Vision (Fallback)",
        "zones": [
            {
                "zone":             zn.replace("_", " ").title(),
                "oil_level":        round(z["oil_level"], 1),
                "dryness":          round(z["dryness"], 1),
                "pore_visibility":  round(z["pore_visibility"], 1),
                "redness":          round(z["redness"], 1),
                "texture":          z["texture"],
            }
            for zn, z in zone_metrics.items()
        ],
    }