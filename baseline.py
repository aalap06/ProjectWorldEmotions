# baseline.py
# Real-world baseline emotion states from the World Happiness Report 2024.
# Source: https://worldhappiness.report/ed/2024/  (Cantril ladder, 0–10)
#
# All keys are canonical Natural Earth 110m shapefile "NAME" values.
#
# Mapping formula (t = score / 10):
#   joy     = 0.05 + t × 0.75
#   hope    = 0.05 + t × 0.65
#   fear    = 0.72 − t × 0.65
#   anger   = 0.50 − t × 0.45
#   sadness = 0.60 − t × 0.55
#   anxiety = 0.60 − t × 0.50

HAPPINESS_SCORES = {
    # ── Americas ──────────────────────────────────────────────────────────────
    "United States of America": 6.73,
    "Canada":                   6.90,
    "Mexico":                   6.68,
    "Brazil":                   6.27,
    "Colombia":                 5.60,
    "Argentina":                6.03,
    "Chile":                    6.41,
    "Uruguay":                  6.36,
    "Peru":                     5.49,
    "Ecuador":                  5.47,
    "Bolivia":                  5.31,
    "Venezuela":                4.73,
    "Paraguay":                 5.87,
    "Panama":                   6.62,
    "Costa Rica":               7.17,
    "Guatemala":                5.93,
    "Honduras":                 5.46,
    "Nicaragua":                5.74,
    "El Salvador":              6.09,
    "Cuba":                     5.91,
    "Dominican Rep.":           6.44,
    "Haiti":                    3.68,
    "Trinidad and Tobago":      6.23,
    "Guyana":                   5.79,
    "Suriname":                 5.99,

    # ── Europe ────────────────────────────────────────────────────────────────
    "United Kingdom":           6.74,
    "France":                   6.61,
    "Germany":                  7.01,
    "Spain":                    6.35,
    "Italy":                    6.33,
    "Poland":                   6.14,
    "Ukraine":                  4.92,
    "Russia":                   5.46,
    "Netherlands":              7.32,
    "Sweden":                   7.35,
    "Norway":                   7.31,
    "Denmark":                  7.58,
    "Finland":                  7.74,
    "Iceland":                  7.52,
    "Switzerland":              7.20,
    "Austria":                  7.10,
    "Belgium":                  6.91,
    "Ireland":                  6.83,
    "Luxembourg":               7.22,
    "Czechia":                  6.69,
    "Slovakia":                 6.19,
    "Hungary":                  5.61,
    "Romania":                  6.00,
    "Bulgaria":                 5.28,
    "Greece":                   5.93,
    "Portugal":                 6.19,
    "Serbia":                   5.74,
    "Croatia":                  5.78,
    "Slovenia":                 6.15,
    "Bosnia and Herz.":         5.30,
    "North Macedonia":          5.72,
    "Montenegro":               5.88,
    "Albania":                  5.33,
    "Kosovo":                   5.36,
    "Moldova":                  5.64,
    "Belarus":                  5.21,
    "Lithuania":                6.45,
    "Latvia":                   6.26,
    "Estonia":                  6.45,
    "Cyprus":                   6.50,
    "Malta":                    6.82,

    # ── Middle East ───────────────────────────────────────────────────────────
    "Turkey":                   4.61,
    "Iran":                     4.39,
    "Iraq":                     4.43,
    "Syria":                    3.72,
    "Saudi Arabia":             6.71,
    "United Arab Emirates":     6.73,
    "Qatar":                    6.95,
    "Kuwait":                   7.10,
    "Bahrain":                  6.67,
    "Oman":                     5.09,
    "Jordan":                   4.46,
    "Israel":                   7.34,
    "Lebanon":                  2.79,
    "Yemen":                    2.95,
    "West Bank":                4.22,

    # ── Africa ────────────────────────────────────────────────────────────────
    "Egypt":                    4.19,
    "Nigeria":                  4.55,
    "South Africa":             5.52,
    "Ethiopia":                 4.10,
    "Libya":                    4.28,
    "Sudan":                    3.98,
    "Morocco":                  5.28,
    "Algeria":                  5.19,
    "Tunisia":                  4.87,
    "Ghana":                    4.63,
    "Kenya":                    4.58,
    "Tanzania":                 4.04,
    "Uganda":                   4.45,
    "Cameroon":                 4.33,
    "Senegal":                  4.91,
    "Mali":                     4.56,
    "Niger":                    4.33,
    "Burkina Faso":             4.66,
    "Benin":                    4.89,
    "Chad":                     4.37,
    "Guinea":                   4.09,
    "Congo":                    4.07,
    "Dem. Rep. Congo":          3.17,
    "Rwanda":                   4.09,
    "Angola":                   3.92,
    "Mozambique":               2.87,
    "Zambia":                   3.57,
    "Zimbabwe":                 3.05,
    "Malawi":                   3.13,
    "Madagascar":               3.66,
    "Botswana":                 3.40,
    "Namibia":                  4.40,
    "Gabon":                    5.02,
    "Sierra Leone":             3.22,
    "Liberia":                  3.88,
    "Côte d'Ivoire":            5.26,
    "Togo":                     4.75,
    "Central African Rep.":     3.69,
    "Guinea-Bissau":            3.82,
    "Eritrea":                  3.30,
    "Somalia":                  2.95,
    "S. Sudan":                 1.86,
    "eSwatini":                 4.27,
    "Lesotho":                  3.40,
    "Djibouti":                 4.50,
    "Mauritania":               4.76,
    "Eq. Guinea":               4.57,
    "Burundi":                  2.94,
    "Mauritius":                6.07,
    "Cape Verde":               5.52,
    "Comoros":                  4.29,

    # ── Central / South Asia ──────────────────────────────────────────────────
    "Kazakhstan":               5.68,
    "Afghanistan":              1.44,
    "Pakistan":                 4.47,
    "India":                    4.05,
    "Bangladesh":               4.89,
    "Uzbekistan":               5.75,
    "Tajikistan":               5.01,
    "Kyrgyzstan":               5.07,
    "Turkmenistan":             5.31,
    "Nepal":                    5.58,
    "Bhutan":                   5.11,
    "Sri Lanka":                4.29,
    "Georgia":                  5.17,
    "Armenia":                  5.55,
    "Azerbaijan":               5.18,
    "Mongolia":                 5.47,

    # ── East / SE Asia ────────────────────────────────────────────────────────
    "China":                    5.97,
    "Japan":                    6.06,
    "South Korea":              5.95,
    "North Korea":              3.00,
    "Vietnam":                  5.68,
    "Thailand":                 6.49,
    "Indonesia":                5.70,
    "Malaysia":                 5.97,
    "Philippines":              5.89,
    "Singapore":                6.52,
    "Myanmar":                  4.21,
    "Cambodia":                 5.15,
    "Lao PDR":                  4.83,
    "Taiwan":                   6.87,
    "Timor-Leste":              4.05,
    "Papua New Guinea":         4.62,
    "Brunei":                   6.14,

    # ── Oceania ───────────────────────────────────────────────────────────────
    "Australia":                7.19,
    "New Zealand":              7.18,
    "Fiji":                     5.44,
    "Solomon Is.":              5.02,
    "Vanuatu":                  5.48,
}


def _score_to_emotions(score: float) -> dict:
    t = max(0.0, min(1.0, score / 10.0))
    return {
        "joy":     round(max(0.0, min(1.0, 0.05 + t * 0.75)), 2),
        "hope":    round(max(0.0, min(1.0, 0.05 + t * 0.65)), 2),
        "fear":    round(max(0.0, min(1.0, 0.72 - t * 0.65)), 2),
        "anger":   round(max(0.0, min(1.0, 0.50 - t * 0.45)), 2),
        "sadness": round(max(0.0, min(1.0, 0.60 - t * 0.55)), 2),
        "anxiety": round(max(0.0, min(1.0, 0.60 - t * 0.50)), 2),
    }


# Default for any country not in HAPPINESS_SCORES (global average ≈ 5.5)
_DEFAULT_SCORE = 5.0

# Pre-computed baseline states
BASELINE_STATES = {
    cid: _score_to_emotions(score)
    for cid, score in HAPPINESS_SCORES.items()
}


def get_baseline_states(all_country_ids: list) -> dict:
    """
    Return a starting state dict for all countries in the simulation.
    Countries with WHR data get real baseline values;
    any others fall back to the global-average neutral state.
    """
    _default_emo = _score_to_emotions(_DEFAULT_SCORE)
    states = {}
    for cid in all_country_ids:
        states[cid] = dict(BASELINE_STATES.get(cid, _default_emo))
    return states
