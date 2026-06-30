"""
Claude Vision Skin Analyzer — Synchronous version
Compatible dengan FastAPI event loop.
"""

import logging
import json
import base64
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def encode_image(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def build_vision_prompt() -> str:
    return """Kamu adalah dermatolog AI senior dengan spesialisasi analisis kulit wajah dari foto digital.

Analisis HANYA area kulit wajah yang terlihat langsung: dahi, hidung, pipi kiri, pipi kanan, dan dagu.

ATURAN KETAT — WAJIB DIIKUTI:
1. ABAIKAN SEPENUHNYA: hijab, kerudung, jilbab, rambut, pakaian, latar belakang, aksesori
2. ABAIKAN makeup kosmetik: blush on di pipi, lipstik, eyeshadow, eyeliner — ini BUKAN kondisi kulit
3. Bedakan kemerahan ALAMI (jerawat meradang, rosacea) vs kemerahan dari BLUSH ON/kosmetik
4. Hitung jerawat HANYA yang benar-benar terlihat sebagai lesi menonjol atau meradang
5. Pigmentasi TIDAK MUNGKIN 100% kecuali seluruh wajah penuh flek hitam — nilai realistis
6. Bintik gelap maksimal sesuai yang benar-benar terlihat jelas
7. Jika kulit terlihat sehat dan bersih → berikan skor tinggi (70-90)
8. Nilai OBJEKTIF berdasarkan kulit yang terlihat, bukan asumsi

SKALA REFERENSI REALISTIS:
- Kulit sangat sehat, bersih, merata → Skor komponen 80-95
- Kulit sehat, sedikit masalah minor → Skor komponen 65-80
- Kulit dengan beberapa masalah terlihat jelas → Skor komponen 45-65
- Kulit dengan banyak masalah jelas → Skor komponen 25-45

Balas HANYA dalam format JSON (tanpa markdown):

{
  "skin_type": "Normal",
  "skin_type_confidence": 0.85,
  "oil_level": 35.0,
  "dryness": 20.0,
  "pore_visibility": 25.0,
  "skin_texture": "Smooth",
  "acne_metrics": {
    "acne": 0,
    "whitehead": 0,
    "blackhead": 2,
    "acne_scar": 0
  },
  "redness": 10.0,
  "pigmentation": 15.0,
  "dark_spot_count": 1,
  "dark_circle_level": "None",
  "fine_lines_level": "None",
  "skin_tone": "Medium",
  "undertone": "Warm",
  "zones": [
    {"zone": "Forehead", "oil_level": 38.0, "dryness": 18.0, "pore_visibility": 28.0, "redness": 8.0, "texture": "Smooth"},
    {"zone": "Nose", "oil_level": 45.0, "dryness": 15.0, "pore_visibility": 35.0, "redness": 10.0, "texture": "Normal"},
    {"zone": "Left Cheek", "oil_level": 30.0, "dryness": 22.0, "pore_visibility": 20.0, "redness": 12.0, "texture": "Smooth"},
    {"zone": "Right Cheek", "oil_level": 30.0, "dryness": 22.0, "pore_visibility": 20.0, "redness": 11.0, "texture": "Smooth"},
    {"zone": "Chin", "oil_level": 35.0, "dryness": 20.0, "pore_visibility": 25.0, "redness": 9.0, "texture": "Normal"}
  ],
  "analysis_notes": "catatan singkat kondisi kulit"
}"""


def analyze_skin_with_vision(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    Analisis kulit menggunakan Claude Vision API — Synchronous.
    Return None jika gagal (fallback ke CV).
    """
    try:
        import anthropic
        from backend.config.settings import settings

        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY tidak ditemukan.")
            return None

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        image_b64 = encode_image(image_bytes)

        # Detect media type
        media_type = "image/jpeg"
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            media_type = "image/png"
        elif image_bytes[:4] == b'RIFF':
            media_type = "image/webp"

        logger.info("Mengirim foto ke Claude Vision API...")

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": build_vision_prompt()
                        }
                    ],
                }
            ],
        )

        response_text = message.content[0].text.strip()

        # Bersihkan markdown jika ada
        if "```" in response_text:
            start = response_text.find("{")
            end   = response_text.rfind("}") + 1
            if start != -1 and end > start:
                response_text = response_text[start:end]

        result = json.loads(response_text)
        logger.info(f"Claude Vision OK. Skin type: {result.get('skin_type')}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Claude Vision JSON error: {e}")
        return None
    except Exception as e:
        logger.error(f"Claude Vision error: {e}")
        return None


def calculate_overall_score_from_vision(data: Dict[str, Any]) -> float:
    """Hitung overall score dari hasil vision analysis."""
    import numpy as np

    acne_m     = data.get("acne_metrics", {})
    acne_total = sum(acne_m.values())

    hydration_score    = 100 - (data.get("dryness", 25) * 0.8)
    texture_score      = {"Smooth": 100, "Normal": 78, "Rough": 45}.get(data.get("skin_texture", "Normal"), 78)
    pore_score         = 100 - (data.get("pore_visibility", 25) * 0.7)
    acne_score         = max(0, 100 - acne_total * 3)
    pigmentation_score = 100 - (data.get("pigmentation", 15) * 0.8)
    redness_score      = 100 - (data.get("redness", 15) * 0.7)
    dark_circle_score  = {"None": 100, "Light": 82, "Medium": 58, "Heavy": 28}.get(data.get("dark_circle_level", "None"), 100)
    fine_lines_score   = {"None": 100, "Mild": 82, "Moderate": 55, "Severe": 25}.get(data.get("fine_lin