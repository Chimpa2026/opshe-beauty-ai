"""
Analysis Orchestrator — Vision API Primary + CV Fallback
Synchronous version compatible dengan FastAPI.
"""

import logging
import uuid
import io
import concurrent.futures
from typing import Dict, Any

from PIL import Image

from backend.utils.image_processing import preprocess_image, check_image_quality, pil_to_cv2
from backend.services.face_detection import detect_face
from ai.vision_analyzer import analyze_skin_with_vision, calculate_overall_score_from_vision
from ai.recommendation_engine import generate_recommendations

import numpy as np
import cv2

logger = logging.getLogger(__name__)


def _run_in_thread(fn, *args, timeout=45):
    """Jalankan fungsi di thread terpisah untuk menghindari event loop conflict."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, *args)
        return future.result(timeout=timeout)


def _get_recommendation_sync(result: Dict[str, Any]) -> Dict[str, Any]:
    """Dapatkan rekomendasi Claude AI secara synchronous."""
    try:
        import anthropic
        import json
        from backend.config.settings import settings

        if not settings.ANTHROPIC_API_KEY:
            return None

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        acne = result.get("acne_metrics", {})
        zones = result.get("zones", [])
        zone_text = "\n".join([
            f"  - {z.get('zone','')}: Minyak {z.get('oil_level',0):.0f}%, Kering {z.get('dryness',0):.0f}%, Pori {z.get('pore_visibility',0):.0f}%, Kemerahan {z.get('redness',0):.0f}%, Tekstur {z.get('texture','')}"
            for z in zones
        ])

        prompt = f"""Kamu adalah dermatolog AI. Berikan rekomendasi skincare personal berdasarkan data analisis kulit berikut.

DATA ANALISIS:
- Jenis Kulit: {result.get('skin_type')} (confidence: {result.get('skin_type_confidence',0)*100:.0f}%)
- Skor: {result.get('overall_score')}/100
- Kadar Minyak: {result.get('oil_level')}%
- Kekeringan: {result.get('dryness')}%
- Visibilitas Pori: {result.get('pore_visibility')}%
- Kemerahan: {result.get('redness')}%
- Pigmentasi: {result.get('pigmentation')}%
- Tekstur: {result.get('skin_texture')}
- Jerawat: {acne.get('acne',0)}, Komedo Putih: {acne.get('whitehead',0)}, Komedo Hitam: {acne.get('blackhead',0)}, Bekas: {acne.get('acne_scar',0)}
- Lingkaran Hitam: {result.get('dark_circle_level')}
- Garis Halus: {result.get('fine_lines_level')}
- Warna Kulit: {result.get('skin_tone')} | Undertone: {result.get('undertone')}

Zona Wajah:
{zone_text}

INSTRUKSI:
- JANGAN sebut nama merek produk
- Hanya rekomendasikan jenis produk dan bahan aktif
- Bahasa Indonesia
- Pertimbangkan SEMUA parameter dan kombinasinya
- Hindari konflik bahan aktif

Balas HANYA dalam JSON (tanpa markdown):

{{"concerns":["masalah utama"],"morning_routine":[{{"step":1,"product_type":"nama produk","ingredients":["bahan"],"why":"alasan"}}],"night_routine":[{{"step":1,"product_type":"nama produk","ingredients":["bahan"],"why":"alasan","note":null}}],"weekly_treatments":[{{"product_type":"nama","ingredients":["bahan"],"why":"alasan"}}],"key_ingredients":["bahan penting"],"ingredients_by_concern":{{"kondisi":["bahan"]}},"lifestyle_tips":["tips"],"disclaimer":"Hasil analisis merupakan estimasi berbasis AI dari citra wajah dan tidak menggantikan diagnosis atau konsultasi dengan dokter kulit."}}"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        text = message.content[0].text.strip()
        if "```" in text:
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start != -1:
                text = text[start:end]

        return json.loads(text)

    except Exception as e:
        logger.error(f"Recommendation API error: {e}")
        return None


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

    # ── 3. Face detection ──
    logger.info(f"[{session_id}] Validating face...")
    preprocessed, original = preprocess_image(pil_img)
    face_result = detect_face(preprocessed)
    if not face_result.success:
        raise ValueError(face_result.error)

    # ── 4. Claude Vision API (Primary) ──
    logger.info(f"[{session_id}] Sending to Claude Vision API...")
    vision_result = None
    try:
        vision_result = _run_in_thread(analyze_skin_with_vision, image_bytes, timeout=45)
    except Exception as e:
        logger.warning(f"[{session_id}] Vision API failed: {e}")

    if vision_result:
        logger.info(f"[{session_id}] Vision API success!")
        result = _build_result_from_vision(vision_result, session_id)
    else:
        logger.warning(f"[{session_id}] Using CV fallback")
        result = _build_result_from_cv(preprocessed, face_result, session_id)

    # ── 5. AI Recommendations ──
    logger.info(f"[{session_id}] Generating AI recommendations...")
    recommendations = None
    try:
        recommendations = _run_in_thread(_get_recommendation_sync, result, timeout=45)
    except Exception as e:
        logger.warning(f"[{session_id}] Recommendation fallback: {e}")

    if not recommendations:
        recommendations = generate_recommendations(result)

    result["recommendations"] = recommendations
    result["morning_routine"] = recommendations.get("morning_routine", [])
    result["night_routine"]   = recommendations.get("night_routine", [])
    result["key_ingredients"] = recommendations.get("key_ingredients", [])
    result["concerns"]        = recommendations.get("concerns", [])

    logger.info(f"[{session_id}] Analysis complete. Score: {result['overall_score']}")
    return result


def _build_result_from_vision(vision: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Build result dari Claude Vision output."""
    overall_score = calculate_overall_score_from_vision(vision)
    acne_m = vision.get("acne_metrics", {})

    return {
        "session_id":           session_id,
        "skin_type":            vision.get("skin_type", "Normal"),
        "skin_type_confidence": round(float(vision.get("skin_type_confidence", 0.75)), 2),
        "oil_level":            round(float(vision.get("oil_level", 40)), 1),
        "dryness":              round(float(vision.get("dryness", 30)), 1),
        "pore_visibility":      round(float(vision.get("pore_visibility", 30)), 1),
        "skin_texture":         vision.get("skin_texture", "Normal"),
        "acne_metrics": {
            "acne":      int(acne_m.get("acne", 0)),
            "whitehead": int(acne_m.get("whitehead", 0)),
            "blackhead": int(acne_m.get("blackhead", 0)),
            "acne_scar": int(acne_m.get("acne_scar", 0)),
        },
        "redness":           round(float(vision.get("redness", 15)), 1),
        "pigmentation":      round(float(vision.get("pigmentation", 20)), 1),
        "dark_spot_count":   int(vision.get("dark_spot_count", 0)),
        "dark_circle_level": vision.get("dark_circle_level", "None"),
        "fine_lines_level":  vision.get("fine_lines_level", "None"),
        "skin_tone":         vision.get("skin_tone", "Medium"),
        "undertone":         vision.get("undertone", "Neutral"),
        "overall_score":     overall_score,
        "analysis_source":   "Claude Vision AI",
        "zones": [
            {
                "zone":            z.get("zone", ""),
                "oil_level":       round(float(z.get("oil_level", 40)), 1),
                "dryness":         round(float(z.get("dryness", 30)), 1),
                "pore_visibility": round(float(z.get("pore_visibility", 30)), 1),
                "redness":         round(float(z.get("redness", 15)), 1),
                "texture":         z.get("texture", "Normal"),
            }
            for z in vision.get("zones", [])
        ],
    }


def _build_result_from_cv(preprocessed, face_result, session_id: str) -> Dict[str, Any]:
    """Fallback: Computer Vision analysis."""
    from backend.services.face_detection import extract_zone_pixels, FACE_ZONES
    from backend.services.skin_analyzer import (
        analyze_skin_type, estimate_oil_level, estimate_dryness,
        estimate_pore_visibility, estimate_redness, estimate_texture,
        estimate_pigmentation, count_dark_spots, estimate_dark_circles,
        estimate_fine_lines, estimate_skin_tone, estimate_undertone,
        detect_acne, calculate_overall_score,
    )

    landmarks    = face_result.landmarks
    zone_metrics = {}
    all_pixels   = []

    for zone_name, zone_indices in FACE_ZONES.items():
        pixels = extract_zone_pixels(preprocessed, landmarks, zone_indices)
        if pixels is None or len(pixels) < 10:
            zone_metrics[zone_name] = {"oil_level": 40.0, "dryness": 30.0, "pore_visibility": 30.0, "redness": 15.0, "texture": "Normal"}
            continue
        all_pixels.append(pixels)
        zone_metrics[zone_name] = {
            "oil_level":       estimate_oil_level(pixels),
            "dryness":         estimate_dryness(pixels),
            "pore_visibility": estimate_pore_visibility(pixels),
            "redness":         estimate_redness(pixels),
            "texture":         estimate_texture(pixels),
        }

    combined        = np.vstack(all_pixels) if all_pixels else preprocessed.reshape(-1, 3)
    skin_type, conf = analyze_skin_type(zone_metrics)
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
    overall_score   = calculate_overall_score({
        "dryness": dryness, "skin_texture": skin_texture,
        "pore_visibility": pore_visibility, "acne_total": acne_total,
        "pigmentation": pigmentation, "redness": redness,
        "dark_circle_level": dark_circle, "fine_lines_level": fine_lines,
    })

    return {
        "session_id": session_id, "skin_type": skin_type,
        "skin_type_confidence": round(conf, 2),
        "oil_level": round(oil_level, 1), "dryness": round(dryness, 1),
        "pore_visibility": round(pore_visibility, 1), "skin_texture": skin_texture,
        "acne_metrics": acne_metrics, "redness": round(redness, 1),
        "pigmentation": round(pigmentation, 1), "dark_spot_count": dark_spot_count,
        "dark_circle_level": dark_circle, "fine_lines_level": fine_lines,
        "skin_tone": skin_tone, "undertone": undertone,
        "overall_score": overall_score, "analysis_source": "Computer Vision (Fallback)",
        "zones": [
            {
                "zone": zn.replace("_", " ").title(),
                "oil_level": round(z["oil_level"], 1),
                "dryness": round(z["dryness"], 1),
                "pore_visibility": round(z["pore_visibility"], 1),
                "redness": round(z["redness"], 1),
                "texture": z["texture"],
            }
            for zn, z in zone_metrics.items()
        ],
    }