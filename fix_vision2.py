code = '''import logging
import json
import base64
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


def encode_image(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def build_vision_prompt() -> str:
    return (
        "Kamu adalah dermatolog AI senior dengan spesialisasi analisis kulit wajah dari foto digital.\\n\\n"
        "Analisis HANYA area kulit wajah yang terlihat langsung: dahi, hidung, pipi kiri, pipi kanan, dagu.\\n\\n"
        "ATURAN KETAT - WAJIB DIIKUTI:\\n"
        "1. ABAIKAN SEPENUHNYA: hijab, kerudung, rambut, pakaian, latar belakang, aksesori\\n"
        "2. ABAIKAN makeup kosmetik: blush on, lipstik, eyeshadow, eyeliner\\n"
        "3. Bedakan kemerahan ALAMI vs kemerahan dari kosmetik/blush on\\n"
        "4. Hitung jerawat HANYA yang benar-benar terlihat sebagai lesi menonjol\\n"
        "5. Pigmentasi TIDAK MUNGKIN 100% kecuali seluruh wajah penuh flek hitam\\n"
        "6. Kulit sehat dan bersih = skor komponen 80-95\\n"
        "7. Nilai OBJEKTIF dan REALISTIS berdasarkan kulit yang terlihat\\n"
        "8. ZONA HIDUNG - SANGAT PENTING: Bayangan/shadow alami di sisi kiri dan kanan hidung adalah efek pencahayaan NORMAL, BUKAN masalah kulit. "
        "Jangan hitung bayangan sebagai noda, pigmentasi, kemerahan, atau masalah kulit apapun. "
        "Analisis HANYA tekstur permukaan kulit hidung, visibilitas pori, dan kondisi nyata yang terlihat langsung di area hidung. "
        "Hidung sehat tanpa jerawat atau komedo yang terlihat jelas = skor 70-90.\\n"
        "9. Bayangan di sekitar mata (periorbital shadow/eye socket shadow) adalah ANATOMI NORMAL, bukan lingkaran hitam. "
        "Lingkaran hitam hanya dinilai dari perubahan warna kulit di bawah mata, bukan dari bayangan struktural.\\n"
        "10. Bayangan di sudut hidung, lipatan nasolabial, dan dagu adalah NORMAL akibat pencahayaan - ABAIKAN.\\n\\n"
        "SKALA REFERENSI REALISTIS:\\n"
        "- Kulit sangat sehat, bersih, merata: skor komponen 80-95\\n"
        "- Kulit sehat dengan sedikit masalah minor: skor komponen 65-80\\n"
        "- Kulit dengan beberapa masalah terlihat jelas: skor komponen 45-65\\n"
        "- Kulit dengan banyak masalah nyata: skor komponen 25-45\\n\\n"
        "Balas HANYA JSON ini (tanpa markdown):\\n"
        "{\\n"
        \'  "skin_type": "Normal",\\n\'
        \'  "skin_type_confidence": 0.85,\\n\'
        \'  "oil_level": 35.0,\\n\'
        \'  "dryness": 20.0,\\n\'
        \'  "pore_visibility": 25.0,\\n\'
        \'  "skin_texture": "Smooth",\\n\'
        \'  "acne_metrics": {"acne": 0, "whitehead": 0, "blackhead": 2, "acne_scar": 0},\\n\'
        \'  "redness": 10.0,\\n\'
        \'  "pigmentation": 15.0,\\n\'
        \'  "dark_spot_count": 1,\\n\'
        \'  "dark_circle_level": "None",\\n\'
        \'  "fine_lines_level": "None",\\n\'
        \'  "skin_tone": "Medium",\\n\'
        \'  "undertone": "Warm",\\n\'
        \'  "zones": [\\n\'
        \'    {"zone": "Forehead", "oil_level": 38.0, "dryness": 18.0, "pore_visibility": 28.0, "redness": 8.0, "texture": "Smooth"},\\n\'
        \'    {"zone": "Nose", "oil_level": 45.0, "dryness": 15.0, "pore_visibility": 35.0, "redness": 10.0, "texture": "Normal"},\\n\'
        \'    {"zone": "Left Cheek", "oil_level": 30.0, "dryness": 22.0, "pore_visibility": 20.0, "redness": 12.0, "texture": "Smooth"},\\n\'
        \'    {"zone": "Right Cheek", "oil_level": 30.0, "dryness": 22.0, "pore_visibility": 20.0, "redness": 11.0, "texture": "Smooth"},\\n\'
        \'    {"zone": "Chin", "oil_level": 35.0, "dryness": 20.0, "pore_visibility": 25.0, "redness": 9.0, "texture": "Normal"}\\n\'
        \'  ],\\n\'
        \'  "analysis_notes": "catatan kondisi kulit"\\n\'
        "}"
    )


def analyze_skin_with_vision(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    try:
        import anthropic
        from backend.config.settings import settings

        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY tidak ditemukan.")
            return None

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        image_b64 = encode_image(image_bytes)

        media_type = "image/jpeg"
        if image_bytes[:8] == b\'\\x89PNG\\r\\n\\x1a\\n\':
            media_type = "image/png"
        elif image_bytes[:4] == b\'RIFF\':
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

        if "```" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1:
                response_text = response_text[start:end]

        result = json.loads(response_text)
        logger.info("Claude Vision OK. Skin type: " + str(result.get("skin_type")))
        return result

    except json.JSONDecodeError as e:
        logger.error("Claude Vision JSON error: " + str(e))
        return None
    except Exception as e:
        logger.error("Claude Vision error: " + str(e))
        return None


def calculate_overall_score_from_vision(data: Dict[str, Any]) -> float:
    acne_m = data.get("acne_metrics", {})
    acne_total = sum(acne_m.values())

    hydration_score    = 100 - (data.get("dryness", 25) * 0.8)
    texture_map        = {"Smooth": 100, "Normal": 78, "Rough": 45}
    texture_score      = texture_map.get(data.get("skin_texture", "Normal"), 78)
    pore_score         = 100 - (data.get("pore_visibility", 25) * 0.7)
    acne_score         = max(0, 100 - acne_total * 3)
    pigmentation_score = 100 - (data.get("pigmentation", 15) * 0.8)
    redness_score      = 100 - (data.get("redness", 15) * 0.7)
    dc_map             = {"None": 100, "Light": 82, "Medium": 58, "Heavy": 28}
    dark_circle_score  = dc_map.get(data.get("dark_circle_level", "None"), 100)
    fl_map             = {"None": 100, "Mild": 82, "Moderate": 55, "Severe": 25}
    fine_lines_score   = fl_map.get(data.get("fine_lines_level", "None"), 100)
    st_map             = {"Normal": 100, "Combination": 85, "Oily": 75, "Dry": 70}
    skin_type_score    = st_map.get(data.get("skin_type", "Normal"), 85)

    score = (
        hydration_score    * 0.15 +
        texture_score      * 0.12 +
        pore_score         * 0.10 +
        acne_score         * 0.18 +
        pigmentation_score * 0.10 +
        redness_score      * 0.10 +
        dark_circle_score  * 0.10 +
        fine_lines_score   * 0.10 +
        skin_type_score    * 0.05
    )

    return round(float(np.clip(score, 0, 100)), 1)
'''

with open('ai/vision_analyzer.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('vision_analyzer.py updated!')