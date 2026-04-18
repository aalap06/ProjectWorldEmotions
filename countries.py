# countries.py
# All countries loaded directly from the Natural Earth 110m shapefile.
# COUNTRIES keys = exact shapefile "NAME" values — the canonical IDs used
# throughout the simulation, renderer, and state files.
#
# ALIASES maps short / common names (returned by Claude / news_parser)
# → canonical IDs, so Claude can return "USA" and it resolves correctly.

import geopandas as gpd

_shp_path = "ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"

try:
    _world = gpd.read_file(_shp_path)
    _world = _world[_world["NAME"] != "Antarctica"].reset_index(drop=True)
    COUNTRIES = {name: [] for name in sorted(_world["NAME"].tolist())}
except Exception as _e:
    print(f"[Warning] Could not load shapefile for countries.py: {_e}")
    COUNTRIES = {}

# ── Alias → canonical shapefile NAME ──────────────────────────────────────
# When news_parser / Claude returns a short or alternate name, resolve it here.
ALIASES = {
    # Common abbreviations
    "USA":                    "United States of America",
    "US":                     "United States of America",
    "America":                "United States of America",
    "United States":          "United States of America",
    "UK":                     "United Kingdom",
    "Britain":                "United Kingdom",
    "Great Britain":          "United Kingdom",
    "England":                "United Kingdom",
    "UAE":                    "United Arab Emirates",
    "DRC":                    "Dem. Rep. Congo",
    "DR Congo":               "Dem. Rep. Congo",
    "Congo-Kinshasa":         "Dem. Rep. Congo",
    "Congo-Brazzaville":      "Congo",
    "Republic of Congo":      "Congo",
    "CAR":                    "Central African Rep.",
    "Czech Republic":         "Czechia",
    "Ivory Coast":            "Côte d'Ivoire",
    "Cote d'Ivoire":          "Côte d'Ivoire",
    "Burma":                  "Myanmar",
    "South Sudan":            "S. Sudan",
    "Macedonia":              "North Macedonia",
    "Bosnia":                 "Bosnia and Herz.",
    "Bosnia Herzegovina":     "Bosnia and Herz.",
    "Swaziland":              "eSwatini",
    "East Timor":             "Timor-Leste",
    "Laos":                   "Lao PDR",
    "Palestine":              "West Bank",
    "Palestinian Territories": "West Bank",
    "Lao PDR":                "Lao PDR",
    "Korea":                  "South Korea",
    # Legacy short IDs from old world_state.json (backward compat)
    "SaudiArabia":            "Saudi Arabia",
    "SouthAfrica":            "South Africa",
    "SouthKorea":             "South Korea",
    "NorthKorea":             "North Korea",
}
