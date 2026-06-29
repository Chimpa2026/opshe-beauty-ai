"""
Skin Analysis Engine
Analyzes skin metrics from preprocessed image and face landmarks.
All analysis is performed using computer vision techniques.
"""

import logging
import numpy as np
import cv2
from typing import Dict, Any, List, Optional, Tuple

from backend.services.face_detection import extract_zone_pixels, FACE_ZONES

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# SKIN TYPE CLASSIFICATION
# ──────────────────────────────────────────────

def analyze_skin_type(
    zone_metrics: Dict[str, Dict],
) -> Tuple[str, float]:
    """
    Classify skin type based on per-zone oil and dryness scores.

    Returns:
        (skin_type, confidence_0_to_1)
    """
    oil_values = [z.get("oil_level", 0) for z in zone_metrics.values()]
    dry_values = [z.get("dryness", 0) for z in zone_metrics.values()]

    avg_oil = float(np.mean(oil_values))
    avg_dry = float(np.mean(dry_values))

    # T-zone (forehead + nose) vs cheeks
    tzone_oil = np.mean([
        zone_metrics.get("forehead", {}).get("oil_level", avg_oil),
        zone_metrics.get("nose", {}).get("oil_level", avg_oil),
    ])
    cheek_oil = np.mean([
        zone_metrics.get("left_cheek", {}).get("oil_level", avg_oil),
        zone_metrics.get("right_cheek", {}).get("oil_level", avg_oil),
    ])

    if avg_oil > 60 and avg_dry < 25:
        return "Oily", min(0.95, avg_oil / 100)
    elif avg_dry > 55 and avg_oil < 30:
        return "Dry", min(0.95, avg_dry / 100)
    elif tzone_oil > 55 and cheek_oil < 45:
        return "Combination", 0.80
    else:
        return "Normal", 0.75


# ──────────────────────────────────────────────
# ZONE METRIC EXTRACTION
# ──────────────────────────────────────────────

def _bgr_to_hsv_stats(pixels: np.ndarray) -> Dict[str, float]:
    """Compute HSV channel statistics from BGR pixel array."""
    if pixels is None or len(pixels) == 0:
        return {"h_mean": 0, "s_mean": 0, "v_mean": 0}
    pixels_reshaped = pixels.reshape(-1, 1, 3).astype(np.uint8)
    hsv = cv2.cvtColor(pixels_reshaped, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    return {
        "h_mean": float(np.mean(hsv[:, 0])),
        "s_mean": float(np.mean(hsv[:, 1])),
        "v_mean": float(np.mean(hsv[:, 2])),
        "s_std": float(np.std(hsv[:, 1])),
        "v_std": float(np.std(hsv[:, 2])),
    }


def estimate_oil_level(pixels: np.ndarray) -> float:
    """
    Estimate oil level from pixel brightness and saturation variance.
    Oily skin reflects more light → higher brightness, lower saturation uniformity.
    """
    if pixels is None or len(pixels) == 0:
        return 0.0
    stats = _bgr_to_hsv_stats(pixels)
    # Normalize V (0–255) to 0–100 with bias toward reflection
    oil = (stats["v_mean"] / 255) * 70 + (stats["s_std"] / 128) * 30
    return float(np.clip(oil, 0, 100))


def estimate_dryness(pixels: np.ndarray) -> float:
    """
    Estimate dryness from saturation (low S = pale/ashy → dry).
    """
    if pixels is None or len(pixels) == 0:
        return 0.0
    stats = _bgr_to_hsv_stats(pixels)
    # Low saturation and low brightness → dry/dull
    dry = 100 - ((stats["s_mean"] / 255) * 60 + (stats["v_mean"] / 255) * 40)
    return float(np.clip(dry, 0, 100))


def estimate_pore_visibility(pixels: np.ndarray, img_gray_patch: Optional[np.ndarray] = None) -> float:
    """
    Estimate pore visibility using local standard deviation (texture).
    Higher local variance → more visible pores.
    """
    if pixels is None or len(pixels) == 0:
        return 0.0
    gray = cv2.cvtColor(pixels.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    std = float(np.std(gray))
    # Map std (typically 0–80) to 0–100
    return float(np.clip((std / 60) * 100, 0, 100))


def estimate_redness(pixels: np.ndarray) -> float:
    """
    Estimate redness by comparing red channel dominance.
    """
    if pixels is None or len(pixels) == 0:
        return 0.0
    b = pixels[:, 0].astype(float)
    g = pixels[:, 1].astype(float)
    r = pixels[:, 2].astype(float)
    redness = np.mean((r - (b + g) / 2) / (np.mean(r) + 1e-6)) * 100
    return float(np.clip(redness, 0, 100))


def estimate_texture(pixels: np.ndarray) -> str:
    """Classify texture as Smooth / Normal / Rough based on local variance."""
    if pixels is None or len(pixels) == 0:
        return "Normal"
    gray = cv2.cvtColor(pixels.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    variance = float(np.var(gray))
    if variance < 200:
        return "Smooth"
    elif variance < 600:
        return "Normal"
    else:
        return "Rough"


# ──────────────────────────────────────────────
# PIGMENTATION / DARK SPOTS
# ──────────────────────────────────────────────

def estimate_pigmentation(pixels: np.ndarray) -> float:
    """
    Estimate pigmentation from saturation variation and brown hue concentration.
    """
    if pixels is None or len(pixels) == 0:
        return 0.0
    stats = _bgr_to_hsv_stats(pixels)
    # Higher saturation variation and warm hue → more pigmentation
    pigmentation = (stats["s_std"] / 50) * 60 + (stats.get("h_mean", 0) / 30) * 40
    return float(np.clip(pigmentation, 0, 100))


def count_dark_spots(img_gray: np.ndarray) -> int:
    """
    Count dark spots using blob detection.
    """
    try:
        blurred = cv2.GaussianBlur(img_gray, (7, 7), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Filter by area: only meaningful spots
        spots = [c for c in contours if 10 < cv2.contourArea(c) < 500]
        return min(len(spots), 50)  # Cap at 50
    except Exception:
        return 0


# ──────────────────────────────────────────────
# DARK CIRCLES
# ──────────────────────────────────────────────

def estimate_dark_circles(
    img_bgr: np.ndarray,
    landmarks: List[Tuple[float, float]],
) -> str:
    """
    Estimate dark circle level by comparing under-eye region to cheek brightness.
    """
    h, w = img_bgr.shape[:2]

    # Approximate under-eye landmarks (indices 33 area)
    # Use relative positions if landmarks are limited
    if len(landmarks) > 200:
        # Left under-eye (around index 33, 7)
        left_eye_y = int(landmarks[33][1] * h)
        left_eye_x = int(landmarks[33][0] * w)
        right_eye_y = int(landmarks[263][1] * h)
        right_eye_x = int(landmarks[263][0] * w)
    else:
        # Fallback: approximate positions
        left_eye_y = int(h * 0.42)
        left_eye_x = int(w * 0.35)
        right_eye_y = int(h * 0.42)
        right_eye_x = int(w * 0.65)

    pad = max(10, int(h * 0.05))

    def safe_crop(cx, cy):
        y1, y2 = max(0, cy), min(h, cy + pad)
        x1, x2 = max(0, cx - pad), min(w, cx + pad)
        return img_bgr[y1:y2, x1:x2]

    left_patch = safe_crop(left_eye_x, left_eye_y + pad // 2)
    right_patch = safe_crop(right_eye_x, right_eye_y + pad // 2)
    # Cheek reference
    cheek_patch = img_bgr[int(h * 0.55):int(h * 0.65), int(w * 0.35):int(w * 0.65)]

    def brightness(patch):
        if patch.size == 0:
            return 128.0
        gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    eye_brightness = (brightness(left_patch) + brightness(right_patch)) / 2
    cheek_brightness = brightness(cheek_patch)

    diff = cheek_brightness - eye_brightness

    if diff < 5:
        return "None"
    elif diff < 15:
        return "Light"
    elif diff < 30:
        return "Medium"
    else:
        return "Heavy"


# ──────────────────────────────────────────────
# FINE LINES
# ──────────────────────────────────────────────

def estimate_fine_lines(img_bgr: np.ndarray) -> str:
    """
    Detect fine lines using Canny edge density in forehead region.
    """
    h, w = img_bgr.shape[:2]
    forehead = img_bgr[int(h * 0.1):int(h * 0.3), int(w * 0.25):int(w * 0.75)]

    if forehead.size == 0:
        return "None"

    gray = cv2.cvtColor(forehead, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 30, 100)
    edge_density = float(np.sum(edges > 0)) / edges.size

    if edge_density < 0.02:
        return "None"
    elif edge_density < 0.06:
        return "Mild"
    elif edge_density < 0.12:
        return "Moderate"
    else:
        return "Severe"


# ──────────────────────────────────────────────
# SKIN TONE & UNDERTONE
# ──────────────────────────────────────────────

def estimate_skin_tone(pixels: np.ndarray) -> str:
    """Classify ITA (Individual Typology Angle) into skin tone categories."""
    if pixels is None or len(pixels) == 0:
        return "Medium"

    lab = cv2.cvtColor(
        pixels.reshape(-1, 1, 3).astype(np.uint8),
        cv2.COLOR_BGR2LAB,
    ).reshape(-1, 3)

    L = float(np.mean(lab[:, 0]))
    b = float(np.mean(lab[:, 2])) - 128  # OpenCV shifts b by 128

    ita = float(np.degrees(np.arctan((L - 50) / (b + 1e-6))))

    if ita > 55:
        return "Fair"
    elif ita > 41:
        return "Light"
    elif ita > 28:
        return "Medium"
    elif ita > 10:
        return "Tan"
    else:
        return "Deep"


def estimate_undertone(pixels: np.ndarray) -> str:
    """
    Estimate undertone from Lab color space.
    Cool: more blue, Warm: more yellow/red, Neutral: balanced.
    """
    if pixels is None or len(pixels) == 0:
        return "Neutral"

    lab = cv2.cvtColor(
        pixels.reshape(-1, 1, 3).astype(np.uint8),
        cv2.COLOR_BGR2LAB,
    ).reshape(-1, 3)

    a_mean = float(np.mean(lab[:, 1])) - 128  # green↔red
    b_mean = float(np.mean(lab[:, 2])) - 128  # blue↔yellow

    if b_mean > 5 and a_mean > 0:
        return "Warm"
    elif b_mean < -3:
        return "Cool"
    else:
        return "Neutral"


# ──────────────────────────────────────────────
# ACNE DETECTION
# ──────────────────────────────────────────────

def detect_acne(img_bgr: np.ndarray) -> Dict[str, int]:
    """
    Detect acne, whitehead, blackhead, and acne scars using color + morphology.
    """
    h, w = img_bgr.shape[:2]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)

    # ── Acne (inflamed, red lesions) ──
    red_mask1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    acne_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    acne_count = len([c for c in acne_contours if 20 < cv2.contourArea(c) < 800])

    # ── Whitehead (white, bright bumps) ──
    _, white_mask = cv2.threshold(
        cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY), 210, 255, cv2.THRESH_BINARY
    )
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    wh_contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    whitehead_count = len([c for c in wh_contours if 5 < cv2.contourArea(c) < 200])

    # ── Blackhead (dark, low-brightness spots) ──
    dark_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 60, 60]))
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    bh_contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blackhead_count = len([c for c in bh_contours if 3 < cv2.contourArea(c) < 100])

    # ── Acne Scars (flat, discolored patches) ──
    l_channel = lab[:, :, 0]
    scar_mask = cv2.inRange(l_channel, 60, 140)
    a_channel = lab[:, :, 1]
    brown_mask = cv2.inRange(a_channel, 130, 160)
    scar_combined = cv2.bitwise_and(scar_mask, brown_mask)
    sc_contours, _ = cv2.findContours(scar_combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    scar_count = len([c for c in sc_contours if 50 < cv2.contourArea(c) < 2000])

    return {
        "acne": min(acne_count, 30),
        "whitehead": min(whitehead_count, 30),
        "blackhead": min(blackhead_count, 30),
        "acne_scar": min(scar_count, 20),
    }


# ──────────────────────────────────────────────
# OVERALL SCORE
# ──────────────────────────────────────────────

def calculate_overall_score(metrics: Dict[str, Any]) -> float:
    """
    Calculate weighted overall skin health score (0–100).
    Higher = healthier skin.
    """
    weights = {
        "hydration":    0.20,
        "texture":      0.15,
        "pores":        0.12,
        "acne":         0.18,
        "pigmentation": 0.10,
        "redness":      0.10,
        "dark_circles": 0.07,
        "fine_lines":   0.08,
    }

    # Invert where higher means worse
    hydration_score   = 100 - metrics.get("dryness", 50)
    texture_score     = {"Smooth": 100, "Normal": 70, "Rough": 30}.get(metrics.get("skin_texture", "Normal"), 70)
    pore_score        = 100 - metrics.get("pore_visibility", 50)
    acne_score        = max(0, 100 - (metrics.get("acne_total", 0) * 5))
    pigmentation_score= 100 - metrics.get("pigmentation", 30)
    redness_score     = 100 - metrics.get("redness", 20)
    dark_circle_score = {"None": 100, "Light": 75, "Medium": 45, "Heavy": 15}.get(
        metrics.get("dark_circle_level", "None"), 80
    )
    fine_lines_score  = {"None": 100, "Mild": 75, "Moderate": 45, "Severe": 20}.get(
        metrics.get("fine_lines_level", "None"), 90
    )

    score = (
        hydration_score    * weights["hydration"] +
        texture_score      * weights["texture"] +
        pore_score         * weights["pores"] +
        acne_score         * weights["acne"] +
        pigmentation_score * weights["pigmentation"] +
        redness_score      * weights["redness"] +
        dark_circle_score  * weights["dark_circles"] +
        fine_lines_score   * weights["fine_lines"]
    )

    return round(float(np.clip(score, 0, 100)), 1)
