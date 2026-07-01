import logging
import json
import base64
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


def encode_image(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def build_vision_prompt() -> str:
    return (
        "Kamu adalah dermatolog AI senior berpengalaman 20 tahun.\n\n"
        "TUGAS: Analisis kondisi kulit wajah dari foto secara AKURAT dan JUJUR.\n\n"
        "AREA YANG DIANALISIS: Dahi, Hidung, Pipi Kiri, Pipi Kanan, Dagu.\n\n"
        "=== ATURAN KRITIS - WAJIB DIPATUHI ===\n\n"
        "ABAIKAN SEPENUHNYA:\n"
        "- Hijab, kerudung, jilbab, rambut, pakaian, aksesori\n"
        "- Makeup: foundation, blush on, lipstik, eyeshadow, eyeliner\n"
        "- Latar belakang/background foto\n\n"
        "TENTANG BAYANGAN/SHADOW:\n"
        "- Bayangan di sisi kiri/kanan hidung = efek 3D anatomi hidung, BUKAN masalah kulit\n"
        "- Bayangan di lipatan nasolabial = normal, ABAIKAN\n"
        "- Bayangan di bawah mata dari tulang wajah = normal, BUKAN lingkaran hitam\n"
        "- Bayangan di dagu/rahang dari pencahayaan = normal, ABAIKAN\n"
        "- HANYA nilai kondisi PERMUKAAN KULIT yang nyata, bukan efek cahaya\n\n"
        "TENTANG AKURASI SKOR:\n"
        "- Jika ada jerawat AKTIF banyak dan meradang: oil_level 60-85, redness 40-70, skor zona 30-55\n"
        "- Jika ada bekas jerawat/hiperpigmentasi jelas: pigmentasi 40-70\n"
        "- Jika kulit bersih tanpa masalah nyata: skor zona 75-95\n"
        "- Hidung tanpa komedo/jerawat yang TERLIHAT JELAS: pore_visibility max 45, redness max 20\n"
        "- JANGAN beri skor tinggi jika kondisi kulit jelas bermasalah\n"
        "- JANGAN beri skor rendah jika kulit jelas sehat\n\n"
        "PANDUAN JERAWAT:\n"
        "- Hitung SETIAP lesi (jerawat meradang, komedo, bekas jerawat) yang benar-benar terlihat jelas, satu per satu, per zona (dahi, hidung, pipi kiri, pipi kanan, dagu), lalu jumlahkan totalnya.\n"
        "- JANGAN membulatkan ke angka kecil hanya karena jumlahnya banyak — kalau memang terlihat puluhan titik jerawat, laporkan jumlah sebenarnya, bukan estimasi kasar yang diremehkan.\n\n"
        "KALIBRASI TINGKAT KEPARAHAN JERAWAT (acne + whitehead + blackhead + acne_scar):\n"
        "- Bersih/nyaris tanpa lesi: total 0-3\n"
        "- Ringan (beberapa titik terpisah di 1-2 zona): total 4-10\n"
        "- Sedang (cluster jerawat di beberapa zona): total 11-20\n"
        "- Berat (banyak jerawat meradang di sebagian besar zona wajah): total 21-40\n"
        "- Sangat berat (hampir seluruh wajah/dahi/pipi dipenuhi papul-pustul meradang, jelas terlihat dari jarak normal): total 40-70+ — JANGAN ragu memberi angka setinggi ini kalau memang itu yang terlihat di foto.\n"
        "- Satu zona (misal dahi atau pipi) yang PENUH jerawat meradang sendiri bisa menyumbang 10-25+ titik pada zona itu saja.\n\n"
        "- Aturan 'kalau ragu isi 0' HANYA berlaku untuk kondisi yang ambigu/tidak jelas (misal kulit tampak mulus tapi ada bayangan/pori biasa).\n"
        "  Aturan itu TIDAK BERLAKU jika lesi jerawat memang jelas dan banyak terlihat — dalam kasus itu WAJIB dihitung mendekati jumlah sebenarnya, bukan diremehkan.\n\n"
        "TENTANG BLUSH/RONA PIPI:\n"
        "- Warna pink/merah muda merata di pipi (blush on, rona alami, atau efek pencahayaan hangat) HARUS diabaikan total.\n"
        "- JANGAN tafsirkan blush/rona pipi sebagai kemerahan kulit, bekas jerawat, ATAU pigmentasi.\n"
        "- Hanya nilai kemerahan/pigmentasi jika ada bercak/lesi yang jelas berbeda dari warna kulit sekitarnya (bukan gradasi rona pipi yang merata dan simetris kiri-kanan).\n\n"
        "PANDUAN KEMERAHAN:\n"
        "- Blush on/makeup = ABAIKAN, nilai 0\n"
        "- Kemerahan dari jerawat meradang = nilai nyata 20-60\n"
        "- Kulit normal tanpa jerawat = redness 5-20\n\n"
        "=== KALKULASI ZONA HIDUNG ===\n"
        "Zona hidung harus HANYA menilai kulit permukaan hidung yang terlihat.\n"
        "Default hidung sehat (tidak ada komedo/jerawat jelas): oil 35-55, dryness 10-20, pore 25-45, redness 8-18, texture Normal/Smooth\n\n"
        "Balas HANYA JSON (tanpa markdown, tanpa penjelasan):\n"
        "{\n"
        '  "skin_type": "Normal|Oily|Dry|Combination",\n'
        '  "skin_type_confidence": 0.85,\n'
        '  "oil_level": 0-100,\n'
        '  "dryness": 0-100,\n'
        '  "pore_visibility": 0-100,\n'
        '  "skin_texture": "Smooth|Normal|Rough",\n'
        '  "acne_metrics": {"acne": 0, "whitehead": 0, "blackhead": 0, "acne_scar": 0},\n'
        '  "redness": 0-100,\n'
        '  "pigmentation": 0-100,\n'
        '  "dark_spot_count": 0,\n'
        '  "dark_circle_level": "None|Light|Medium|Heavy",\n'
        '  "fine_lines_level": "None|Mild|Moderate|Severe",\n'
        '  "skin_tone": "Fair|Light|Medium|Tan|Deep",\n'
        '  "undertone": "Cool|Warm|Neutral",\n'
        '  "zones": [\n'
        '    {"zone": "Forehead", "oil_level": 0-100, "dryness": 0-100, "pore_visibility": 0-100, "redness": 0-100, "texture": "Smooth|Normal|Rough"},\n'
        '    {"zone": "Nose", "oil_level": 0-100, "dryness": 0-100, "pore_visibility": 0-100, "redness": 0-100, "texture": "Smooth|Normal|Rough"},\n'
        '    {"zone": "Left Cheek", "oil_level": 0-100, "dryness": 0-100, "pore_visibility": 0-100, "redness": 0-100, "texture": "Smooth|Normal|Rough"},\n'
        '    {"zone": "Right Cheek", "oil_level": 0-100, "dryness": 0-100, "pore_visibility": 0-100, "redness": 0-100, "texture": "Smooth|Normal|Rough"},\n'
        '    {"zone": "Chin", "oil_level": 0-100, "dryness": 0-100, "pore_visibility": 0-100, "redness": 0-100, "texture": "Smooth|Normal|Rough"}\n'
        '  ],\n'
        '  "analysis_notes": "deskripsi kondisi kulit yang terlihat"\n'
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
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            media_type = "image/png"
        elif image_bytes[:4] == b'RIFF':
            media_type = "image/webp"

        logger.info("Mengirim foto ke Claude Vision API...")

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0,
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
    acne_active = acne_m.get("acne", 0)

    hydration_score    = 100 - (data.get("dryness", 25) * 0.8)
    texture_map        = {"Smooth": 100, "Normal": 75, "Rough": 40}
    texture_score      = texture_map.get(data.get("skin_texture", "Normal"), 75)
    pore_score         = 100 - (data.get("pore_visibility", 25) * 0.75)
    # Penalti lebih berat untuk jerawat aktif
    acne_score         = max(0, 100 - (acne_active * 5) - (acne_total * 2))
    pigmentation_score = 100 - (data.get("pigmentation", 15) * 0.85)
    redness_score      = 100 - (data.get("redness", 15) * 0.75)
    dc_map             = {"None": 100, "Light": 82, "Medium": 55, "Heavy": 25}
    dark_circle_score  = dc_map.get(data.get("dark_circle_level", "None"), 100)
    fl_map             = {"None": 100, "Mild": 80, "Moderate": 52, "Severe": 22}
    fine_lines_score   = fl_map.get(data.get("fine_lines_level", "None"), 100)
    st_map             = {"Normal": 100, "Combination": 82, "Oily": 72, "Dry": 68}
    skin_type_score    = st_map.get(data.get("skin_type", "Normal"), 82)

    score = (
        hydration_score    * 0.13 +
        texture_score      * 0.13 +
        pore_score         * 0.10 +
        acne_score         * 0.22 +
        pigmentation_score * 0.10 +
        redness_score      * 0.12 +
        dark_circle_score  * 0.08 +
        fine_lines_score   * 0.07 +
        skin_type_score    * 0.05
    )

    # ── Cap tingkat keparahan: begitu jerawat mentok di 0 (acne_score capped),
    # komponen lain (hidrasi, lingkaran hitam, dll) tidak boleh menyeret skor
    # akhir naik terlalu tinggi untuk kasus yang jelas parah secara visual.
    if acne_total >= 60 or acne_active >= 35:
        score = min(score, 22)
    elif acne_total >= 45 or acne_active >= 25:
        score = min(score, 30)
    elif acne_total >= 30 or acne_active >= 18:
        score = min(score, 38)
    elif acne_total >= 20 or acne_active >= 12:
        score = min(score, 48)
    elif acne_total >= 10 or acne_active >= 6:
        score = min(score, 62)

    return round(float(np.clip(score, 0, 100)), 1)
