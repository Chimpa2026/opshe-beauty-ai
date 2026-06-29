import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
import numpy as np
import cv2

logger = logging.getLogger(__name__)

@dataclass
class FaceDetectionResult:
    success: bool
    error: Optional[str] = None
    landmarks: Optional[List[Tuple[float, float]]] = None
    left_eye: Optional[Tuple[float, float]] = None
    right_eye: Optional[Tuple[float, float]] = None
    zones: Optional[Dict[str, List[int]]] = None
    face_bbox: Optional[Tuple[int, int, int, int]] = None

FACE_ZONES = {
    "forehead":    [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152],
    "nose":        [1,2,5,4,6,195,197,168,8,9],
    "left_cheek":  [234,93,132,58,172,136,150,149,176,148,152,377,400,378,379,365,397,288,361,323],
    "right_cheek": [454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93],
    "chin":        [152,377,400,378,379,365,397,288,361,323,172,136,150,149,176,148],
}

def detect_face(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    # Coba deteksi dengan parameter ketat dulu
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=8, minSize=(100,100))
    # Kalau tidak ketemu, coba lebih longgar
    if len(faces) == 0:
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80,80))
    if len(faces) == 0:
        return FaceDetectionResult(success=False, error="No face detected. Please ensure your face is clearly visible.")
    # Ambil wajah terbesar saja
    faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
    x, y, fw, fh = faces[0]
    h, w = img_bgr.shape[:2]
    left_eye = (x + fw*0.3, y + fh*0.35)
    right_eye = (x + fw*0.7, y + fh*0.35)
    norm_landmarks = []
    for row in np.linspace(y, y+fh, 20):
        for col in np.linspace(x, x+fw, 25):
            norm_landmarks.append((col/w, row/h))
    return FaceDetectionResult(success=True, landmarks=norm_landmarks, left_eye=left_eye, right_eye=right_eye, zones=FACE_ZONES, face_bbox=(x,y,fw,fh))

def extract_zone_pixels(img_bgr, landmarks, zone_indices):
    h, w = img_bgr.shape[:2]
    valid_indices = [i for i in zone_indices if i < len(landmarks)]
    if len(valid_indices) < 3:
        return img_bgr[h//4:3*h//4, w//4:3*w//4].reshape(-1,3)
    pts = np.array([(int(landmarks[i][0]*w), int(landmarks[i][1]*h)) for i in valid_indices], dtype=np.int32)
    mask = np.zeros((h,w), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    pixels = img_bgr[mask==255]
    return pixels if len(pixels) > 0 else img_bgr[h//4:3*h//4, w//4:3*w//4].reshape(-1,3)
