"""
AI Recommendation Engine
Maps skin conditions to product types and active ingredients.
NO brand names are ever mentioned.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# INGREDIENT KNOWLEDGE BASE
# ──────────────────────────────────────────────

INGREDIENT_KB = {
    "oily": {
        "ingredients": ["Niacinamide", "Zinc PCA", "Salicylic Acid", "Green Tea Extract",
                         "BHA", "Clay", "Witch Hazel Extract"],
        "avoid": ["Heavy mineral oil", "Petroleum jelly", "Coconut oil"],
    },
    "dry": {
        "ingredients": ["Ceramide", "Squalane", "Hyaluronic Acid", "Glycerin",
                         "Panthenol", "Shea Butter", "Beta Glucan", "Urea (5%)"],
        "avoid": ["Alcohol denat.", "High-dose retinol without moisturizer"],
    },
    "combination": {
        "ingredients": ["Niacinamide", "Hyaluronic Acid", "Ceramide", "BHA (T-zone)",
                         "Glycerin", "Centella Asiatica"],
        "avoid": ["Overly rich occlusive balms on T-zone"],
    },
    "normal": {
        "ingredients": ["Niacinamide", "Peptides", "Hyaluronic Acid", "Ceramide",
                         "Vitamin C (maintenance)", "SPF50+"],
        "avoid": [],
    },
    "sensitive": {
        "ingredients": ["Centella Asiatica", "Allantoin", "Beta Glucan", "Oat Extract",
                         "Panthenol", "Azelaic Acid (low %)", "Zinc"],
        "avoid": ["Fragrance", "Essential oils", "High-dose AHA/BHA", "Alcohol denat."],
    },
    "acne": {
        "ingredients": ["Salicylic Acid (BHA)", "Benzoyl Peroxide (2.5–5%)", "Azelaic Acid",
                         "Sulfur", "Niacinamide", "Zinc PCA", "Tea Tree Extract"],
        "avoid": ["Comedogenic oils", "Lanolin", "Isopropyl myristate"],
    },
    "hyperpigmentation": {
        "ingredients": ["Vitamin C (L-Ascorbic Acid)", "Tranexamic Acid", "Alpha Arbutin",
                         "Kojic Acid", "Niacinamide", "Azelaic Acid", "Licorice Root Extract"],
        "avoid": ["Unprotected sun exposure"],
    },
    "fine_lines": {
        "ingredients": ["Retinol (0.025–0.1% for beginners)", "Peptides",
                         "Bakuchiol (retinol alternative)", "Adenosine", "Vitamin C", "SPF50+"],
        "avoid": ["Skipping SPF", "Excessive scrubbing"],
    },
    "redness": {
        "ingredients": ["Centella Asiatica", "Azelaic Acid", "Green Tea Extract",
                         "Allantoin", "Niacinamide", "Oat Extract"],
        "avoid": ["Fragrance", "High-heat treatments", "Alcohol denat."],
    },
    "dark_circles": {
        "ingredients": ["Caffeine", "Vitamin K", "Retinol (low %)", "Peptides",
                         "Niacinamide", "Arnica Extract"],
        "avoid": ["Rubbing eyes", "Salt-heavy diet (causes puffiness)"],
    },
    "dehydrated": {
        "ingredients": ["Hyaluronic Acid (multiple molecular weights)", "Glycerin",
                         "Panthenol", "Beta Glucan", "Ceramide", "Amino Acids"],
        "avoid": ["Over-cleansing", "Hot showers", "Alcohol-based toners"],
    },
}

# ──────────────────────────────────────────────
# ROUTINE STEP TEMPLATES
# ──────────────────────────────────────────────

MORNING_STEPS = [
    {
        "step": 1,
        "product_type": "Cleanser",
        "description": "Gently remove overnight sebum and impurities without stripping the skin barrier.",
    },
    {
        "step": 2,
        "product_type": "Toner / Essence",
        "description": "Rebalance skin pH and deliver first hydration layer.",
    },
    {
        "step": 3,
        "product_type": "Serum",
        "description": "Targeted treatment for primary skin concerns.",
    },
    {
        "step": 4,
        "product_type": "Moisturizer",
        "description": "Lock in hydration and reinforce skin barrier.",
    },
    {
        "step": 5,
        "product_type": "Sunscreen",
        "description": "Protect from UV-induced damage, pigmentation, and aging.",
        "base_ingredients": ["SPF50+", "PA++++"],
    },
]

NIGHT_STEPS = [
    {
        "step": 1,
        "product_type": "Oil/Balm Cleanser",
        "description": "Remove SPF, makeup, and excess sebum (first cleanse).",
    },
    {
        "step": 2,
        "product_type": "Gentle Cleanser",
        "description": "Deep clean without disrupting barrier (second cleanse).",
    },
    {
        "step": 3,
        "product_type": "Treatment Serum",
        "description": "Active ingredients for overnight skin repair and renewal.",
    },
    {
        "step": 4,
        "product_type": "Moisturizer / Night Cream",
        "description": "Nourish and repair skin during sleep.",
    },
    {
        "step": 5,
        "product_type": "Sleeping Mask (2–3×/week)",
        "description": "Intensive overnight hydration and restoration.",
    },
]


# ──────────────────────────────────────────────
# RECOMMENDATION LOGIC
# ──────────────────────────────────────────────

def _collect_concerns(analysis: Dict[str, Any]) -> List[str]:
    """Determine active skin concerns from analysis results."""
    concerns = []

    skin_type = analysis.get("skin_type", "Normal").lower()
    if skin_type in ("oily", "dry", "combination"):
        concerns.append(skin_type)

    if analysis.get("oil_level", 0) > 60:
        concerns.append("oily")
    if analysis.get("dryness", 0) > 50:
        concerns.append("dry")
    if analysis.get("dryness", 0) > 40 and analysis.get("oil_level", 0) < 40:
        concerns.append("dehydrated")

    acne_total = (
        analysis.get("acne_metrics", {}).get("acne", 0) +
        analysis.get("acne_metrics", {}).get("whitehead", 0) +
        analysis.get("acne_metrics", {}).get("blackhead", 0)
    )
    if acne_total > 3:
        concerns.append("acne")

    if analysis.get("redness", 0) > 30:
        concerns.append("redness")
    if analysis.get("pigmentation", 0) > 35:
        concerns.append("hyperpigmentation")

    dark_circle = analysis.get("dark_circle_level", "None")
    if dark_circle in ("Medium", "Heavy"):
        concerns.append("dark_circles")

    fine_lines = analysis.get("fine_lines_level", "None")
    if fine_lines in ("Moderate", "Severe"):
        concerns.append("fine_lines")

    if analysis.get("pore_visibility", 0) > 55:
        if "oily" not in concerns:
            concerns.append("oily")

    # Deduplicate
    return list(dict.fromkeys(concerns))


def _get_ingredients_for_concerns(concerns: List[str]) -> Dict[str, List[str]]:
    """Aggregate ingredient recommendations per concern."""
    result = {}
    for concern in concerns:
        if concern in INGREDIENT_KB:
            result[concern] = INGREDIENT_KB[concern]["ingredients"]
    return result


def _select_cleanser_ingredients(skin_type: str, concerns: List[str]) -> List[str]:
    base = ["Amino Acid Surfactant", "Ceramide"]
    if "acne" in concerns or skin_type == "oily":
        base += ["Salicylic Acid (0.5%)", "Tea Tree Extract"]
    elif "dry" in concerns or "dehydrated" in concerns:
        base += ["Glycerin", "Panthenol"]
    elif "sensitive" in concerns or "redness" in concerns:
        base += ["Oat Extract", "Centella Asiatica"]
    return base


def _select_toner_ingredients(concerns: List[str]) -> List[str]:
    ings = ["Panthenol", "Beta Glucan"]
    if "oily" in concerns:
        ings += ["Niacinamide", "Witch Hazel Extract"]
    if "dehydrated" in concerns or "dry" in concerns:
        ings += ["Hyaluronic Acid", "Glycerin"]
    if "redness" in concerns or "sensitive" in concerns:
        ings += ["Centella Asiatica", "Allantoin"]
    return ings


def _select_serum_ingredients(concerns: List[str], skin_type: str) -> List[str]:
    ings = []
    priority_map = {
        "hyperpigmentation": ["Vitamin C", "Tranexamic Acid", "Alpha Arbutin"],
        "acne": ["Niacinamide (10%)", "Zinc PCA", "Azelaic Acid"],
        "oily": ["Niacinamide (10%)", "BHA"],
        "redness": ["Azelaic Acid", "Centella Asiatica"],
        "fine_lines": ["Peptides", "Vitamin C"],
        "dry": ["Hyaluronic Acid", "Panthenol"],
        "dehydrated": ["Hyaluronic Acid (multi-weight)", "Glycerin"],
        "dark_circles": ["Caffeine", "Peptides"],
    }
    for concern in concerns:
        if concern in priority_map:
            for ing in priority_map[concern]:
                if ing not in ings:
                    ings.append(ing)
        if len(ings) >= 4:
            break
    if not ings:
        ings = ["Niacinamide", "Hyaluronic Acid"]
    return ings


def _select_moisturizer_ingredients(concerns: List[str], skin_type: str) -> List[str]:
    if skin_type == "oily":
        return ["Niacinamide", "Hyaluronic Acid", "Beta Glucan"]
    elif skin_type == "dry":
        return ["Ceramide", "Squalane", "Shea Butter", "Glycerin"]
    elif skin_type == "combination":
        return ["Ceramide", "Hyaluronic Acid", "Niacinamide"]
    else:
        return ["Ceramide", "Squalane", "Peptides"]


def _select_night_serum(concerns: List[str], skin_type: str) -> List[str]:
    ings = []
    if "fine_lines" in concerns:
        ings += ["Retinol (0.025–0.1%)", "Bakuchiol (retinol alternative)"]
    if "hyperpigmentation" in concerns:
        ings += ["Tranexamic Acid", "Alpha Arbutin"]
    if "acne" in concerns:
        ings += ["Azelaic Acid", "Niacinamide"]
    if "dry" in concerns or "dehydrated" in concerns:
        ings += ["Ceramide", "Peptides"]
    if not ings:
        ings = ["Niacinamide", "Hyaluronic Acid", "Peptides"]
    return ings[:5]


def generate_recommendations(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate personalized skincare routine and ingredient recommendations.
    
    Args:
        analysis: Result dict from skin analysis

    Returns:
        Dict with morning_routine, night_routine, concerns, key_ingredients, and notes
    """
    concerns = _collect_concerns(analysis)
    skin_type = analysis.get("skin_type", "Normal")
    skin_type_lower = skin_type.lower()

    concern_ingredients = _get_ingredients_for_concerns(concerns)

    # ── Morning Routine ──
    morning = []
    cleanser_ings = _select_cleanser_ingredients(skin_type_lower, concerns)
    morning.append({
        "step": 1,
        "product_type": "Gentle Cleanser",
        "ingredients": cleanser_ings,
        "why": "Removes overnight sebum and prepares skin for actives without disrupting the barrier.",
    })

    toner_ings = _select_toner_ingredients(concerns)
    morning.append({
        "step": 2,
        "product_type": "Hydrating Toner / Essence",
        "ingredients": toner_ings,
        "why": "Rebalances pH, delivers initial hydration, and preps skin to absorb actives.",
    })

    serum_ings = _select_serum_ingredients(concerns, skin_type_lower)
    morning.append({
        "step": 3,
        "product_type": "Treatment Serum",
        "ingredients": serum_ings,
        "why": "Targets primary concerns with concentrated active ingredients.",
    })

    moist_ings = _select_moisturizer_ingredients(concerns, skin_type_lower)
    morning.append({
        "step": 4,
        "product_type": "Moisturizer",
        "ingredients": moist_ings,
        "why": "Seals in actives and maintains skin barrier integrity throughout the day.",
    })

    morning.append({
        "step": 5,
        "product_type": "Sunscreen",
        "ingredients": ["SPF50+", "PA++++", "Zinc Oxide or Chemical UV filters"],
        "why": "Essential daily protection against UV-induced aging and hyperpigmentation. Never skip.",
    })

    # ── Night Routine ──
    night = []
    night.append({
        "step": 1,
        "product_type": "Oil / Balm Cleanser",
        "ingredients": ["Plant-derived oils", "Jojoba Oil", "Emulsifier"],
        "why": "Dissolves SPF, makeup, and sebum without irritation (first cleanse).",
    })

    night.append({
        "step": 2,
        "product_type": "Gentle Cleanser",
        "ingredients": cleanser_ings,
        "why": "Second cleanse ensures thorough removal without over-stripping.",
    })

    night_serum_ings = _select_night_serum(concerns, skin_type_lower)
    retinol_note = ""
    if any("Retinol" in i for i in night_serum_ings):
        retinol_note = "Start retinol 1–2×/week and gradually increase. Always follow with moisturizer."

    night.append({
        "step": 3,
        "product_type": "Treatment Serum (Night)",
        "ingredients": night_serum_ings,
        "why": "Skin undergoes repair during sleep — this is the optimal window for actives.",
        "note": retinol_note or None,
    })

    night.append({
        "step": 4,
        "product_type": "Night Moisturizer / Cream",
        "ingredients": moist_ings + (["Ceramide"] if "Ceramide" not in moist_ings else []),
        "why": "Replenishes moisture lost during the day and supports overnight barrier repair.",
    })

    night.append({
        "step": 5,
        "product_type": "Sleeping Mask (2–3×/week)",
        "ingredients": ["Hyaluronic Acid", "Ceramide", "Panthenol", "Centella Asiatica"],
        "why": "Intensive hydration boost; creates an occlusive seal for maximum absorption.",
    })

    # ── Weekly Treatments ──
    weekly = []
    if "acne" in concerns or "oily" in concerns:
        weekly.append({
            "product_type": "Clay Mask (1–2×/week)",
            "ingredients": ["Kaolin Clay", "Salicylic Acid", "Niacinamide"],
            "why": "Deep-cleans pores and controls excess sebum production.",
        })
    if "hyperpigmentation" in concerns or "fine_lines" in concerns:
        weekly.append({
            "product_type": "AHA Exfoliant (1×/week)",
            "ingredients": ["Glycolic Acid", "Lactic Acid", "Mandelic Acid"],
            "why": "Removes dead skin cells, improves tone and texture, enhances active penetration.",
        })
    if "dry" in concerns or "dehydrated" in concerns:
        weekly.append({
            "product_type": "Hydrating Sheet Mask (2–3×/week)",
            "ingredients": ["Hyaluronic Acid", "Beta Glucan", "Amino Acids"],
            "why": "Intensive hydration boost for chronically dry or dehydrated skin.",
        })

    # ── Key ingredients summary ──
    all_ings = []
    for ings_list in concern_ingredients.values():
        for ing in ings_list:
            if ing not in all_ings:
                all_ings.append(ing)

    # ── Lifestyle notes ──
    lifestyle_tips = [
        "Drink at least 2L of water daily for internal hydration.",
        "Aim for 7–9 hours of sleep to support skin repair cycles.",
        "Avoid touching your face to reduce bacterial transfer.",
        "Cleanse pillowcases at least once a week.",
    ]
    if "acne" in concerns:
        lifestyle_tips.append("Review diet: reduce high-glycemic foods and dairy if acne persists.")
    if "redness" in concerns:
        lifestyle_tips.append("Avoid extreme temperature changes and use lukewarm water when cleansing.")

    return {
        "concerns": concerns,
        "morning_routine": morning,
        "night_routine": night,
        "weekly_treatments": weekly,
        "key_ingredients": all_ings[:12],
        "ingredients_by_concern": concern_ingredients,
        "lifestyle_tips": lifestyle_tips,
        "disclaimer": (
            "Hasil analisis merupakan estimasi berbasis AI dari citra wajah dan tidak "
            "menggantikan diagnosis atau konsultasi dengan dokter kulit."
        ),
    }
