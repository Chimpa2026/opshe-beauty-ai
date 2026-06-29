"""
Image Preprocessing Utilities
Face alignment, brightness/contrast normalization, white balance, noise reduction.
"""

import logging
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def pil_to_cv2(img: Image.Image) -> np.ndarray:
    """Convert PIL Image (RGB) to OpenCV (BGR)."""
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def cv2_to_pil(img: np.ndarray) -> Image.Image:
    """Convert OpenCV (BGR) to PIL Image (RGB)."""
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def correct_brightness(img: np.ndarray) -> np.ndarray:
    """Auto brightness correction using CLAHE on L channel."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def correct_white_balance(img: np.ndarray) -> np.ndarray:
    """Simple gray-world white balance correction."""
    result = img.copy().astype(np.float32)
    mean_b = np.mean(result[:, :, 0])
    mean_g = np.mean(result[:, :, 1])
    mean_r = np.mean(result[:, :, 2])
    mean_gray = (mean_b + mean_g + mean_r) / 3

    result[:, :, 0] = np.clip(result[:, :, 0] * (mean_gray / (mean_b + 1e-6)), 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] * (mean_gray / (mean_g + 1e-6)), 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] * (mean_gray / (mean_r + 1e-6)), 0, 255)
    return result.astype(np.uint8)


def reduce_noise(img: np.ndarray) -> np.ndarray:
    """Apply bilateral filter for noise reduction while preserving edges."""
    return cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)


def normalize_contrast(img: np.ndarray) -> np.ndarray:
    """Normalize contrast using histogram equalization per channel."""
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


def align_face(
    img: np.ndarray,
    left_eye: Tuple[float, float],
    right_eye: Tuple[float, float],
    output_size: Tuple[int, int] = (224, 224),
) -> np.ndarray:
    """
    Rotate and scale image so eyes are horizontally aligned.

    Args:
        img: BGR image
        left_eye: (x, y) of left eye center
        right_eye: (x, y) of right eye center
        output_size: target output size (w, h)

    Returns:
        Aligned and resized image
    """
    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]
    angle = np.degrees(np.arctan2(dy, dx))

    center = (
        int((left_eye[0] + right_eye[0]) / 2),
        int((left_eye[1] + right_eye[1]) / 2),
    )

    M = cv2.getRotationMatrix2D(center, angle, scale=1.0)
    rotated = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
    return cv2.resize(rotated, output_size)


def extract_face_roi(
    img: np.ndarray,
    landmarks: list,
    padding: float = 0.15,
) -> Optional[np.ndarray]:
    """
    Extract face region of interest with padding.

    Args:
        img: BGR image
        landmarks: list of (x, y) normalized landmark coordinates (0–1)
        padding: fractional padding around bounding box

    Returns:
        Cropped face region or None
    """
    h, w = img.shape[:2]
    xs = [lm[0] * w for lm in landmarks]
    ys = [lm[1] * h for lm in landmarks]

    x_min = max(0, int(min(xs) - padding * w))
    y_min = max(0, int(min(ys) - padding * h))
    x_max = min(w, int(max(xs) + padding * w))
    y_max = min(h, int(max(ys) + padding * h))

    return img[y_min:y_max, x_min:x_max]


def preprocess_image(pil_img: Image.Image) -> Tuple[np.ndarray, np.ndarray]:
    """
    Full preprocessing pipeline.

    Returns:
        (preprocessed_cv2_bgr, original_cv2_bgr)
    """
    original = pil_to_cv2(pil_img)
    img = original.copy()

    img = correct_white_balance(img)
    img = correct_brightness(img)
    img = reduce_noise(img)

    return img, original


def check_image_quality(img: np.ndarray) -> Tuple[bool, str]:
    """
    Check if image has sufficient quality for analysis.

    Returns:
        (is_ok, reason_if_not_ok)
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Blur detection via Laplacian variance
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < 15:
        return False, "Image is too blurry. Please capture a clearer photo."

    # Brightness check
    mean_brightness = np.mean(gray)
    if mean_brightness < 40:
        return False, "Image is too dark. Please improve lighting conditions."
    if mean_brightness > 230:
        return False, "Image is overexposed. Please reduce brightness or lighting."

    return True, ""
