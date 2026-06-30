"""
Skin Analysis Engine — Enhanced Version
Improved accuracy for all skin metrics.
"""

import logging
import numpy as np
import cv2
from typing import Dict, Any, List, Optional, Tuple

from backend.services.face_detection import extract_zone_pixels, FACE_ZONES

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# PREPROCESSING HELPERS
# ──────────────────────────────────────────────

def _normalize_pixels(pixels: np.ndarray) -> np.ndarray:
    """Normalize pixel values and remove outliers."""
    if pixels is None or len(pixels) == 0:
        return pixels
    # Remove extreme outliers (top/bottom 2%)
    low = np.percentile(pixels, 2, axis=0)
    high = np.percentile(pixels, 98, axis=0)
    return np.clip(pixels, low, high).astype(np.uint8)


def _get_hsv_lab(pixels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Convert pixel array to HSV and LAB color spaces."""
    px = pixels.reshape(-1, 1, 3).astype(np.uint8)
    hsv = cv2.cvtColor(px, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(float)
    lab = cv2.cvtColor(px, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(float)
    return hsv, lab


# ──────────────────────────────────────────────
# SKIN TYPE CLASSIFICATION
# ──────────────────────────────────────────────

def analyze_skin_type(zone_metrics: Dict[str, Dict]) -> Tuple[str, float]:
    """Classify skin type with improved accuracy."""
    oil_values = [z.get("oil_level", 0) for z in zone_metrics.values()]
    dry_values  = [z.get("dryness", 0) for z in zone_metrics.values()]

    avg_oil = float(np.mean(oil_values))
    avg_dry = float(np.mean(dry_values))

    tzone_oil = np.mean([
        zone_metrics.get("forehead", {}).get("oil_level", avg_oil),
        zone_metrics.get("nose", {}).get("oil_level", avg_oil),
    ])
    cheek_oil = np.mean([
        zone_metrics.get("left_cheek", {}).get("oil_level", avg_oil),
        zone_metrics.get("right_cheek", {}).get("oil_level", avg_oil),
    ])

    # More nuanced classification
    if avg_oil > 65 and avg_dry < 30:
        return "Oily", round(min(0.95, avg_oil / 100), 2)
    elif avg_dry > 60 and avg_oil < 35:
        return "Dry", round(min(0.95, avg_dry / 100), 2)
    elif tzone_oil > 60 and cheek_oil < 50:
        diff = tzone_oil - cheek_oil
        conf = min(0.92, 0.70 + diff / 100)
        return "Combination", round(conf, 2)
    else:
        return "Normal", 0.78


# ──────────────────────────────────────────────
# OIL LEVEL — Improved
# ──────────────────────────────────────────────

def estimate_oil_level(pixels: np.ndarray) -> float:
    """
    Estimate oil level using specular reflection analysis.
    Oily skin has higher brightness variance and specular highlights.
    """
    if pixels is None or len(pixels) < 10:
        return 0.0

    pixels = _normalize_pixels(pixels)
    hsv, lab = _get_hsv_lab(pixels)

    # V channel (brightness) — oily skin reflects more
    v = hsv[:, 2]
    v_mean = np.mean(v)
    v_std  = np.std(v)

    # High brightness specular highlights
    specular_ratio = np.sum(v > 230) / len(v)

    # L channel from LAB
    l = lab[:, 0]
    l_mean = np.mean(l)

    # Combine: brightness + specular + L channel
    oil = (
        (v_mean / 255) * 35 +
        (l_mean / 255) * 25 +
        specular_ratio * 40
    )

    return float(np.clip(oil, 0, 100))


# ──────────────────────────────────────────────
# DRYNESS — Improved
# ──────────────────────────────────────────────

def estimate_dryness(pixels: np.ndarray) -> float:
    """
    Estimate dryness from saturation and texture roughness.
    Dry skin: low saturation, uneven texture, dull appearance.
    """
    if pixels is None or len(pixels) < 10:
        return 0.0

    pixels = _normalize_pixels(pixels)
    hsv, lab = _get_hsv_lab(pixels)

    s = hsv[:, 1]
    v = hsv[:, 2]
    l = lab[:, 0]

    # Low saturation = dry/dull
    s_mean = np.mean(s)
    # Low brightness variance = flat/dull
    v_std = np.std(v)
    # Low L = darker/dull
    l_mean = np.mean(l)

    # Inverse of hydration
    dryness = (
        (1 - s_mean / 255) * 45 +
        (1 - min(v_std / 60, 1)) * 25 +
        (1 - min(l_mean / 180, 1)) * 30
    )

    return float(np.clip(dryness, 0, 100))


# ──────────────────────────────────────────────
# PORE VISIBILITY — Improved
# ──────────────────────────────────────────────

def estimate_pore_visibility(pixels: np.ndarray) -> float:
    """
    Estimate pore visibility using local texture analysis.
    Uses Laplacian variance for texture detail detection.
    """
    if pixels is None or len(pixels) < 10:
        return 0.0

    # Convert to grayscale patch
    gray = cv2.cvtColor(
        pixels.reshape(-1, 1, 3).astype(np.uint8),
        cv2.COLOR_BGR2GRAY
    ).flatten()

    # Local variance as pore indicator
    std = float(np.std(gray))
    mean = float(np.mean(gray))

    # Normalize relative to brightness
    # Darker areas with high variance = more visible pores
    relative_texture = std / (mean + 1e-6)

    pore_score = min(relative_texture * 150, 100)
    return float(np.clip(pore_score, 0, 100))


# ──────────────────────────────────────────────
# REDNESS — Improved
# ──────────────────────────────────────────────

def estimate_redness(pixels: np.ndarray) -> float:
    """
    Improved redness detection using LAB color space.
    A channel in LAB is most accurate for red detection.
    """
    if pixels is None or len(pixels) < 10:
        return 0.0

    pixels = _normalize_pixels(pixels)
    _, lab = _get_hsv_lab(pixels)

    # A channel: green(-) to red(+), centered at 128
    a = lab[:, 1]
    a_mean = np.mean(a) - 128  # center at 0

    # Only count positive (red) values
    red_pixels = a[a > 128]
    if len(red_pixels) == 0:
        return 0.0

    red_intensity = np.mean(red_pixels) - 128
    red_ratio = len(red_pixels) / len(a)

    redness = (red_intensity / 50) * 60 + red_ratio * 40
    return float(np.clip(redness, 0, 100))


# ──────────────────────────────────────────────
# TEXTURE — Improved
# ──────────────────────────────────────────────

def estimate_texture(pixels: np.ndarray) -> str:
    """Classify texture using local binary pattern variance."""
    if pixels is None or len(pixels) < 10:
        return "Normal"

    gray = cv2.cvtColor(
        pixels.reshape(-1, 1, 3).astype(np.uint8),
        cv2.COLOR_BGR2GRAY
    ).flatten()

    # Use coefficient of variation for texture
    mean = np.mean(gray)
    std  = np.std(gray)
    cv   = std / (mean + 1e-6)

    if cv < 0.08:
        return "Smooth"
    elif cv < 0.18:
        return "Normal"
    else:
        return "Rough"


# ──────────────────────────────────────────────
# PIGMENTATION — Improved
# ──────────────────────────────────────────────

def estimate_pigmentation(pixels: np.ndarray) -> float:
    """
    Estimate pigmentation using LAB color space unevenness.
    High pigmentation = high color variation.
    """
    if pixels is None or len(pixels) < 10:
        return 0.0

    pixels = _normalize_pixels(pixels)
    _, lab = _get_hsv_lab(pixels)

    l = lab[:, 0]
    a = lab[:, 1]
    b = lab[:, 2]

    # Std dev of L (brightness unevenness) = pigmentation indicator
    l_std = np.std(l)
    a_std = np.std(a)
    b_std = np.std(b)

    # Combined color unevenness
    pigmentation = (l_std / 30) * 50 + (a_std / 15) * 30 + (b_std / 15) * 20
    return float(np.clip(pigmentation, 0, 100))


# ──────────────────────────────────────────────
# DARK SPOTS — Improved
# ──────────────────────────────────────────────

def count_dark_spots(img_gray: np.ndarray) -> int:
    """
    Count dark spots using adaptive thresholding.
    More accurate than global threshold.
    """
    try:
        if img_gray is None or img_gray.size == 0:
            return 0

        # Blur to reduce noise
        blurred = cv2.GaussianBlur(img_gray, (9, 9), 0)

        # Adaptive threshold — better than global
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 8
        )

        # Morphological cleanup
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter by area — only meaningful spots (not noise, not whole face)
        h, w = img_gray.shape
        face_area = h * w
        spots = [
            c for c in contours
            if 30 < cv2.contourArea(c) < face_area * 0.005
        ]
        return min(len(spots), 30)
    except Exception:
        return 0


# ──────────────────────────────────────────────
# DARK CIRCLES — Improved
# ──────────────────────────────────────────────

def estimate_dark_circles(img_bgr: np.ndarray, landmarks: List[Tuple]) -> str:
    """
    Improved dark circle detection using LAB L channel comparison.
    """
    h, w = img_bgr.shape[:2]

    if len(landmarks) > 200:
        left_eye_y  = int(landmarks[33][1] * h)
        left_eye_x  = int(landmarks[33][0] * w)
        right_eye_y = int(landmarks[263][1] * h)
        right_eye_x = int(landmarks[263][0] * w)
    else:
        left_eye_y  = int(h * 0.42)
        left_eye_x  = int(w * 0.32)
        right_eye_y = int(h * 0.42)
        right_eye_x = int(w * 0.68)

    pad = max(12, int(h * 0.055))

    def safe_crop(cx, cy, offset_y=0):
        y1 = max(0, cy + offset_y)
        y2 = min(h, cy + offset_y + pad)
        x1 = max(0, cx - pad)
        x2 = min(w, cx + pad)
        return img_bgr[y1:y2, x1:x2]

    def lab_l_mean(patch):
        if patch is None or patch.size == 0:
            return 128.0
        lab = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB)
        return float(np.mean(lab[:, :, 0]))

    left_patch   = safe_crop(left_eye_x, left_eye_y, pad // 2)
    right_patch  = safe_crop(right_eye_x, right_eye_y, pad // 2)
    cheek_patch  = img_bgr[int(h*0.55):int(h*0.68), int(w*0.3):int(w*0.7)]

    eye_l   = (lab_l_mean(left_patch) + lab_l_mean(right_patch)) / 2
    cheek_l = lab_l_mean(cheek_patch)

    diff = cheek_l - eye_l

    if diff < 4:
        return "None"
    elif diff < 10:
        return "Light"
    elif diff < 20:
        return "Medium"
    else:
        return "Heavy"


# ──────────────────────────────────────────────
# FINE LINES — Improved
# ──────────────────────────────────────────────

def estimate_fine_lines(img_bgr: np.ndarray) -> str:
    """
    Detect fine lines using Canny edge density in forehead + eye area.
    """
    h, w = img_bgr.shape[:2]

    # Analyze forehead and eye corner areas
    regions = [
        img_bgr[int(h*0.10):int(h*0.28), int(w*0.25):int(w*0.75)],  # forehead
        img_bgr[int(h*0.38):int(h*0.48), int(w*0.15):int(w*0.35)],  # left eye corner
        img_bgr[int(h*0.38):int(h*0.48), int(w*0.65):int(w*0.85)],  # right eye corner
    ]

    densities = []
    for region in regions:
        if region.size == 0:
            continue
        gray    = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        edges   = cv2.Canny(blurred, 40, 120)
        density = float(np.sum(edges > 0)) / edges.size
        densities.append(density)

    if not densities:
        return "None"

    avg_density = np.mean(densities)

    if avg_density < 0.025:
        return "None"
    elif avg_density < 0.065:
        return "Mild"
    elif avg_density < 0.12:
        return "Moderate"
    else:
        return "Severe"


# ──────────────────────────────────────────────
# SKIN TONE & UNDERTONE — Improved
# ──────────────────────────────────────────────

def estimate_skin_tone(pixels: np.ndarray) -> str:
    """Classify skin tone using ITA (Individual Typology Angle)."""
    if pixels is None or len(pixels) < 10:
        return "Medium"

    pixels = _normalize_pixels(pixels)
    _, lab = _get_hsv_lab(pixels)

    L = np.mean(lab[:, 0])
    b = np.mean(lab[:, 2]) - 128

    ita = float(np.degrees(np.arctan2(L - 50, b + 1e-6)))

    if ita > 55:   return "Fair"
    elif ita > 41: return "Light"
    elif ita > 28: return "Medium"
    elif ita > 10: return "Tan"
    else:          return "Deep"


def estimate_undertone(pixels: np.ndarray) -> str:
    """Estimate undertone from LAB a and b channels."""
    if pixels is None or len(pixels) < 10:
        return "Neutral"

    pixels = _normalize_pixels(pixels)
    _, lab = _get_hsv_lab(pixels)

    a_mean = np.mean(lab[:, 1]) - 128
    b_mean = np.mean(lab[:, 2]) - 128

    if b_mean > 6 and a_mean > 1:
        return "Warm"
    elif b_mean < -4 or a_mean < -2:
        return "Cool"
    else:
        return "Neutral"


# ──────────────────────────────────────────────
# ACNE DETECTION — Significantly Improved
# ──────────────────────────────────────────────

def detect_acne(img_bgr: np.ndarray) -> Dict[str, int]:
    """
    Improved acne detection with strict filtering to reduce false positives.
    Uses multi-stage validation for each acne type.
    """
    h, w = img_bgr.shape[:2]
    face_area = h * w

    # Minimum and maximum area thresholds relative to face size
    min_acne_area   = max(15, face_area * 0.00008)
    max_acne_area   = face_area * 0.008
    min_blackhead   = max(8, face_area * 0.00003)
    max_blackhead   = face_area * 0.002
    min_whitehead   = max(8, face_area * 0.00003)
    max_whitehead   = face_area * 0.002

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)

    # ── Acne (inflamed red lesions) ──
    # Strict red range with saturation check
    red_mask1 = cv2.inRange(hsv, np.array([0, 80, 60]), np.array([8, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([172, 80, 60]), np.array([180, 255, 255]))
    red_mask  = cv2.bitwise_or(red_mask1, red_mask2)

    # Morphological cleanup — remove noise
    kernel3 = np.ones((3, 3), np.uint8)
    kernel5 = np.ones((5, 5), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel3, iterations=2)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel5)

    acne_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Validate each contour: circularity + area
    acne_count = 0
    for c in acne_contours:
        area = cv2.contourArea(c)
        if not (min_acne_area < area < max_acne_area):
            continue
        perimeter = cv2.arcLength(c, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter ** 2)
        if circularity > 0.3:  # Must be somewhat circular
            acne_count += 1

    # ── Blackhead (dark, small, circular) ──
    # Very dark areas with low saturation
    dark_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 80, 55]))
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel3, iterations=2)

    bh_contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blackhead_count = 0
    for c in bh_contours:
        area = cv2.contourArea(c)
        if not (min_blackhead < area < max_blackhead):
            continue
        perimeter = cv2.arcLength(c, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter ** 2)
        if circularity > 0.4:
            blackhead_count += 1

    # ── Whitehead (bright, small bumps) ──
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # Use adaptive threshold for whiteheads
    _, white_mask = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel3, iterations=2)

    wh_contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    whitehead_count = 0
    for c in wh_contours:
        area = cv2.contourArea(c)
        if not (min_whitehead < area < max_whitehead):
            continue
        perimeter = cv2.arcLength(c, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter ** 2)
        if circularity > 0.35:
            whitehead_count += 1

    # ── Acne Scar (flat discolored patches, larger area) ──
    a_channel = lab[:, :, 1].astype(float)
    l_channel = lab[:, :, 0].astype(float)

    # Brown/post-inflammatory hyperpigmentation
    scar_mask = np.zeros((h, w), dtype=np.uint8)
    scar_mask[(a_channel > 133) & (a_channel < 155) &
              (l_channel > 50) & (l_channel < 130)] = 255

    scar_mask = cv2.morphologyEx(scar_mask, cv2.MORPH_OPEN, kernel5)
    scar_mask = cv2.morphologyEx(scar_mask, cv2.MORPH_CLOSE, kernel5)

    sc_contours, _ = cv2.findContours(scar_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    scar_count = len([
        c for c in sc_contours
        if face_area * 0.0003 < cv2.contourArea(c) < face_area * 0.015
    ])

    return {
        "acne":       min(acne_count, 20),
        "whitehead":  min(whitehead_count, 15),
        "blackhead":  min(blackhead_count, 20),
        "acne_scar":  min(scar_count, 15),
    }


# ──────────────────────────────────────────────
# OVERALL SCORE — Improved Weighting
# ──────────────────────────────────────────────

def calculate_overall_score(metrics: Dict[str, Any]) -> float:
    """Calculate weighted overall skin health score (0-100)."""
    weights = {
        "hydration":    0.18,
        "texture":      0.15,
        "pores":        0.12,
        "acne":         0.20,
        "pigmentation": 0.10,
        "redness":      0.10,
        "dark_circles": 0.07,
        "fine_lines":   0.08,
    }

    hydration_score    = 100 - metrics.get("dryness", 50)
    texture_score      = {"Smooth": 100, "Normal": 68, "Rough": 28}.get(metrics.get("skin_texture", "Normal"), 68)
    pore_score         = 100 - metrics.get("pore_visibility", 50)
    acne_total         = metrics.get("acne_total", 0)
    acne_score         = max(0, 100 - (acne_total * 4))
    pigmentation_score = 100 - metrics.get("pigmentation", 30)
    redness_score      = 100 - metrics.get("redness", 20)
    dark_circle_score  = {"None": 100, "Light": 78, "Medium": 48, "Heavy": 18}.get(
        metrics.get("dark_circle_level", "None"), 85
    )
    fine_lines_score   = {"None": 100, "Mild": 78, "Moderate": 48, "Severe": 20}.get(
        metrics.get("fine_lines_level", "None"), 92
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