"""
Claude Vision Skin Analyzer
Mengirim foto langsung ke Claude API untuk analisis kulit yang akurat.
"""

import logging
import json
import base64
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def encode_image(image_bytes: bytes) -> str:
    """Encode image bytes ke base64."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def build_vision_prompt() -> str:
    return """Kamu adalah dermatolog AI dengan keahlian analisis kulit wajah dari foto.

Analisis foto wajah ini dengan SANGAT TELITI dan AKURAT.

PENTING:
- Jika ada tanda-tanda makeup/kosmetik (foundation, blush, lipstik), ABAIKAN dan fokus pada kondisi kulit yang terlihat di balik makeup
- Bedakan kemerahan ALAMI (rosacea, iritasi, jerawat meradang) vs kemerahan dari KOSMETIK
- Jangan over-detect jerawat — hanya hitung yang benar-benar terlihat jelas sebagai lesi jerawat
- Pigmentasi 100% TIDAK MUNGKIN kecuali wajah penuh bintik gelap
- Nilai secara OBJEKTIF dan REALISTIS

Analisis area berikut: Dahi, Hidung, Pipi Kiri, Pipi Kanan, Dagu.

Parameter yang harus dianalisis:
1. Jenis Kulit: Oily/Dry/Combination/Normal + confidence (0-1)
2. Kadar Minyak: 0-100%
3. Kekeringan: 0-100%
4. Visibilitas Pori: 0-100%
5. Tekstur: Smooth/Normal/Rough
6. Jerawat aktif: jumlah (hitung yang BENAR-BENAR terlihat)
7. Komedo putih: jumlah
8. Komedo hitam: jumlah
9. Bekas jerawat: jumlah
10. Kemerahan ALAMI (bukan makeup): 0-100%
11. Pigmentasi/ketidakrataan warna: 0-100% (realistis!)
12. Bintik gelap: jumlah
13. Lingkaran hitam: None/Light/Medium/Heavy
14. Garis halus: None/Mild/Moderate/Severe
15. Warna kulit: Fair/Light/Medium/Tan/Deep
16. Undertone: Cool/Warm/Neutral

Balas HANYA dalam format JSON berikut (tanpa markdown, tanpa penjelasan):

{
  "skin_type": "Normal",
  "skin_type_confidence": 0.85,
  "oil_level": 45.0,
  "dryness": 25.0,
  "pore_visibility": 35.0,
  "skin_texture": "Normal",
  "acne_metrics": {
    "acne": 2,
    "whitehead": 1,
    "blackhead": 3,
    "acne_scar": 0
  },
  "redness": 15.0,
  "pigmentation": 20.0,
  "dark_spot_count": 2,
  "dark_circle_level": "None",
  "fine_lines_level": "None",
  "skin_tone": "Medium",
  "undertone": "Warm",
  "zones": [
    {
      "zone": "Forehead",
      "oil_level": 50.0,
      "dryness": 20.0,
      "pore_visibility": 40.0,
      "redness": 10.0,
      "texture": "Normal"
    },
    {
      "zone": "Nose",
      "oil_level": 60.0,
      "dryness": 15.0,
      "pore_visibility": 55.0,
      "redness": 12.0,
      "texture": "Normal"
    },
    {
      "zone": "Left Cheek",
      "oil_level": 40.0,
      "dryness": 28.0,
      "pore_visibility": 30.0,
      "redness": 18.0,
      "texture": "Normal"
    },
    {
      "zone": "Right Cheek",
      "oil_level": 38.0,
      "dryness": 30.0,
      "pore_visibility": 28.0,
      "redness": 16.0,
      "texture": "Normal"
    },
    {
      "zone": "Chin",
      "oil_level": 45.0,
      "dryness": 22.0,
      "pore_visibility": 35.0,
      "redness": 14.0,
      "texture": "Normal"
    }
  ],
  "analysis_notes": "catatan singkat tentang kondisi kulit yang terlihat"
}"""


async def analyze_skin_with_vision(
    image_bytes: bytes,
) -> Optional[Dict[str, Any]]:
    """
    Analisis kulit menggunakan Claude Vision API.
    Return None jika gagal (akan fallback ke CV analysis).
    """
    try:
        import anthropic
        from backend.config.settings import settings

        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY tidak ditemukan.")
            return None

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Encode image
        image_b64 = encode_image(image_bytes)

        # Detect media type
        media_type = "image/jpeg"
        if image_bytes[:4] == b'\x89PNG':
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
            lines = response_text.split("\n")
            cleaned = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if not in_block or in_block:
                    cleaned.append(line)
            response_text = "\n".join(cleaned)

        result = json.loads(response_text)
        logger.info("Claude Vision API berhasil menganalisis kulit.")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Claude Vision response bukan JSON valid: {e}")
        return None
    except Exception as e:
        logger.error(f"Claude Vision API error: {e}")
        return None


def calculate_overall_score_from_vision(data: Dict[str, Any]) -> float:
    """Hitung overall score dari hasil vision analysis."""
    import numpy as np

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

    acne_m     = data.get("acne_metrics", {})
    acne_total = sum(acne_m.values())

    hydration_score    = 100 - data.get("dryness", 30)
    texture_score      = {"Smooth": 100, "Normal": 70, "Rough": 35}.get(data.get("skin_texture", "Normal"), 70)
    pore_score         = 100 - data.get("pore_visibility", 30)
    acne_score         = max(0, 100 - acne_total * 4)
    pigmentation_score = 100 - data.get("pigmentation", 20)
    redness_score      = 100 - data.get("redness", 15)
    dark_circle_score  = {"None": 100, "Light": 78, "Medium": 48, "Heavy": 18}.get(data.get("dark_circle_level", "None"), 100)
    fine_lines_score   = {"None": 100, "Mild": 78, "Moderate": 48, "Severe": 20}.get(data.get("fine_lines_level", "None"), 100)

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