"""
Analysis Orchestrator
Coordinates the full pipeline: preprocess → detect → analyze → recommend → store.
"""

import logging
import uuid
import io
from typing import Dict, Any

from PIL import Image

from backend.utils.image_processing import (
    preprocess_image, check_image_quality, pil_to_cv2
)
from backend.services.face_detection import detect_face, extract_zone_pixels, FACE_ZONES
from backend.services.skin_analyzer import (
    analyze_skin_type,
    estimate_oil_level,
    estimate_dryness,
    estimate_pore_visibility,
    estimate_redness,
    estimate_texture,
    estimate_pigmentation,
    count_dark_spots,
    estimate_dark_circles,
    estimate_fine_lines,
    estimate_skin_tone,
    estimate_undertone,
    detect_acne,
    calculate_overall_score,
)
from ai.recommendation_engine import generate_recommendations

import numpy as np
import cv2

logger = logging.getLogger(__name__)

ZONE_NAMES = list(FACE_ZONES.keys())  # forehead, nose, left_cheek, right_cheek, chin


def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Full analysis pipeline from raw image bytes.

    Returns:
        Complete analysis result dict or raises ValueError on failure.
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

    # ── 3. Preprocess ──
    logger.info(f"[{session_id}] Preprocessing image")
    preprocessed, original = preprocess_image(pil_img)

    # ── 4. Face detection ──
    logger.info(f"[{session_id}] Running face detection")
    face_result = detect_face(preprocessed)
    if not face_result.success:
        raise ValueError(face_result.error)

    landmarks = face_result.landmarks

    # ── 5. Per-zone metrics ──
    logger.info(f"[{session_id}] Computing zone metrics")
    zone_metrics = {}
    all_face_pixels = []

    for zone_name, zone_indices in FACE_ZONES.items():
        pixels = extract_zone_pixels(preprocessed, landmarks, zone_indices)
        if pixels is None or len(pixels) < 10:
            zone_metrics[zone_name] = {
                "oil_level": 40.0, "dryness": 30.0,
                "pore_visibility": 30.0, "redness": 15.0,
                "texture": "Normal",
            }
            continue

        all_face_pixels.append(pixels)
        zone_metrics[zone_name] = {
            "oil_level": estimate_oil_level(pixels),
            "dryness": estimate_dryness(pixels),
            "pore_visibility": estimate_pore_visibility(pixels),
            "redness": estimate_redness(pixels),
            "texture": estimate_texture(pixels),
        }

    # Aggregate all-face pixels
    if all_face_pixels:
        combined_pixels = np.vstack(all_face_pixels)
    else:
        combined_pixels = preprocessed.reshape(-1, 3)

    # ── 6. Global metrics ──
    logger.info(f"[{session_id}] Computing global metrics")

    skin_type, skin_type_confidence = analyze_skin_type(zone_metrics)
    oil_level      = float(np.mean([z["oil_level"] for z in zone_metrics.values()]))
    dryness        = float(np.mean([z["dryness"] for z in zone_metrics.values()]))
    pore_visibility= float(np.mean([z["pore_visibility"] for z in zone_metrics.values()]))
    redness        = float(np.mean([z["redness"] for z in zone_metrics.values()]))
    skin_texture   = estimate_texture(combined_pixels)

    # Acne
    acne_metrics = detect_acne(preprocessed)
    acne_total = sum(acne_metrics.values())

    # Other
    pigmentation   = estimate_pigmentation(combined_pixels)
    gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
    dark_spot_count= count_dark_spots(gray)
    dark_circle    = estimate_dark_circles(preprocessed, landmarks)
    fine_lines     = estimate_fine_lines(preprocessed)
    skin_tone      = estimate_skin_tone(combined_pixels)
    undertone      = estimate_undertone(combined_pixels)

    # ── 7. Overall score ──
    metrics_for_score = {
        "dryness": dryness,
        "skin_texture": skin_texture,
        "pore_visibility": pore_visibility,
        "acne_total": acne_total,
        "pigmentation": pigmentation,
        "redness": redness,
        "dark_circle_level": dark_circle,
        "fine_lines_level": fine_lines,
    }
    overall_score = calculate_overall_score(metrics_for_score)

    # ── 8. Build result ──
    result = {
        "session_id": session_id,
        "skin_type": skin_type,
        "skin_type_confidence": round(skin_type_confidence, 2),
        "oil_level": round(oil_level, 1),
        "dryness": round(dryness, 1),
        "pore_visibility": round(pore_visibility, 1),
        "skin_texture": skin_texture,
        "acne_metrics": acne_metrics,
        "redness": round(redness, 1),
        "pigmentation": round(pigmentation, 1),
        "dark_spot_count": dark_spot_count,
        "dark_circle_level": dark_circle,
        "fine_lines_level": fine_lines,
        "skin_tone": skin_tone,
        "undertone": undertone,
        "overall_score": overall_score,
        "zones": [
            {
                "zone": zone_name.replace("_", " ").title(),
                "oil_level": round(z["oil_level"], 1),
                "dryness": round(z["dryness"], 1),
                "pore_visibility": round(z["pore_visibility"], 1),
                "redness": round(z["redness"], 1),
                "texture": z["texture"],
            }
            for zone_name, z in zone_metrics.items()
        ],
    }

    # ── 9. Recommendations ──
    logger.info(f"[{session_id}] Generating recommendations")
    recommendations = generate_recommendations(result)
    result["recommendations"] = recommendations
    result["morning_routine"] = recommendations["morning_routine"]
    result["night_routine"] = recommendations["night_routine"]
    result["key_ingredients"] = recommendations["key_ingredients"]
    result["concerns"] = recommendations["concerns"]

    logger.info(f"[{session_id}] Analysis complete. Score: {overall_score}")
    return result
