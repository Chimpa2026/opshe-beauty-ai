"""
AI Recommendation Engine — Claude API Primary + Rule Engine Fallback
"""

import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)


def build_prompt(analysis: Dict[str, Any]) -> str:
    """Buat prompt lengkap dari hasil analisis kulit."""
    acne = analysis.get("acne_metrics", {})
    zones = analysis.get("zones", [])

    zone_text = ""
    for z in zones:
        zone_text += f"\n  - {z.get('zone','')}: Minyak {z.get('oil_level',0):.0f}%, Kering {z.get('dryness',0):.0f}%, Pori {z.get('pore_visibility',0):.0f}%, Kemerahan {z.get('redness',0):.0f}%, Tekstur {z.get('texture','')}"

    prompt = f"""Kamu adalah dermatolog AI ahli skincare. Berdasarkan hasil analisis kulit berikut, berikan rekomendasi rutinitas skincare yang sangat personal dan akurat.

## DATA ANALISIS KULIT

**Skor Keseluruhan:** {analysis.get('overall_score', 0)}/100
**Jenis Kulit:** {analysis.get('skin_type', 'Normal')} (confidence: {analysis.get('skin_type_confidence', 0)*100:.0f}%)
**Warna Kulit:** {analysis.get('skin_tone', '-')}
**Undertone:** {analysis.get('undertone', '-')}

**Metrik Utama:**
- Kadar Minyak: {analysis.get('oil_level', 0):.1f}%
- Kekeringan: {analysis.get('dryness', 0):.1f}%
- Visibilitas Pori: {analysis.get('pore_visibility', 0):.1f}%
- Kemerahan: {analysis.get('redness', 0):.1f}%
- Pigmentasi: {analysis.get('pigmentation', 0):.1f}%
- Bintik Gelap: {analysis.get('dark_spot_count', 0)} titik
- Tekstur: {analysis.get('skin_texture', '-')}
- Lingkaran Hitam: {analysis.get('dark_circle_level', '-')}
- Garis Halus: {analysis.get('fine_lines_level', '-')}

**Jerawat & Noda:**
- Jerawat aktif: {acne.get('acne', 0)}
- Komedo putih: {acne.get('whitehead', 0)}
- Komedo hitam: {acne.get('blackhead', 0)}
- Bekas jerawat: {acne.get('acne_scar', 0)}

**Analisis Per Zona:**{zone_text}

## INSTRUKSI

Berikan rekomendasi rutinitas skincare LENGKAP berdasarkan SEMUA data di atas. Pertimbangkan:
1. Kombinasi kondisi (bukan hanya satu masalah)
2. Tingkat keparahan setiap parameter
3. Konflik antar bahan aktif (jangan rekomendasikan yang konflik)
4. Urutan aplikasi yang benar
5. Frekuensi penggunaan

PENTING:
- JANGAN sebut nama merek produk apapun
- Hanya rekomendasikan JENIS produk dan BAHAN AKTIF
- Gunakan Bahasa Indonesia
- Sertakan alasan ilmiah singkat untuk setiap rekomendasi

Balas HANYA dalam format JSON berikut (tanpa markdown, tanpa penjelasan di luar JSON):

{{
  "concerns": ["daftar masalah utama dalam bahasa Indonesia"],
  "morning_routine": [
    {{
      "step": 1,
      "product_type": "nama jenis produk",
      "ingredients": ["bahan aktif 1", "bahan aktif 2"],
      "why": "alasan singkat dalam bahasa Indonesia"
    }}
  ],
  "night_routine": [
    {{
      "step": 1,
      "product_type": "nama jenis produk",
      "ingredients": ["bahan aktif 1", "bahan aktif 2"],
      "why": "alasan singkat dalam bahasa Indonesia",
      "note": "catatan penting jika ada, null jika tidak ada"
    }}
  ],
  "weekly_treatments": [
    {{
      "product_type": "nama jenis produk",
      "ingredients": ["bahan aktif"],
      "why": "alasan"
    }}
  ],
  "key_ingredients": ["daftar bahan aktif terpenting"],
  "ingredients_by_concern": {{
    "nama_kondisi": ["bahan aktif yang sesuai"]
  }},
  "lifestyle_tips": ["tips gaya hidup dalam bahasa Indonesia"],
  "disclaimer": "Hasil analisis merupakan estimasi berbasis AI dari citra wajah dan tidak menggantikan diagnosis atau konsultasi dengan dokter kulit."
}}"""

    return prompt


async def get_ai_recommendation(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dapatkan rekomendasi dari Claude API.
    Return None jika gagal (akan fallback ke rule engine).
    """
    try:
        import anthropic
        from backend.config.settings import settings

        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY tidak ditemukan, menggunakan rule engine.")
            return None

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        prompt = build_prompt(analysis)

        logger.info("Menghubungi Claude API untuk rekomendasi...")

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text.strip()

        # Bersihkan jika ada markdown code block
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        result = json.loads(response_text)
        logger.info("Claude API berhasil memberikan rekomendasi.")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Claude API response bukan JSON valid: {e}")
        return None
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return None