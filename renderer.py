# renderer.py — unified portrait renderer (globe + flat map, 9:16)
#
# Layout (% of screen height):
#   4%  — headline header
#  44%  — rotating globe
#  25%  — flat world map (zoomed-out overview)
#   5%  — happiness bar
#  10%  — country pins (left)  +  color legend (right)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
from matplotlib.path import Path as MplPath
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

try:
    import cartopy.crs as ccrs
except ImportError:
    raise ImportError("cartopy is required.  pip install cartopy")

from emotions import EMOTIONS, EMOTION_KEYS
import geopandas as gpd

# ── Figure ────────────────────────────────────────────────────────────────────
FIG_W_IN, FIG_H_IN = 6, 10.667
DPI      = 120
FIG_W_PX = int(FIG_W_IN * DPI)   # 720
FIG_H_PX = int(FIG_H_IN * DPI)   # 1280

BG       = "#000000"
DOT_SIZE = 1.5
SRC_CRS  = ccrs.PlateCarree()

# ── Layout ────────────────────────────────────────────────────────────────────
_TITLE_AX   = [0.03, 0.957, 0.94, 0.040]

_GLOBE_BOT  = 0.510
_GLOBE_H    = 0.440
_GLOBE_AX   = (0.0, _GLOBE_BOT, 1.0, _GLOBE_H)

_MAP_BOT    = 0.255
_MAP_H      = 0.250
_MAP_AX     = (0.0, _MAP_BOT, 1.0, _MAP_H)

_HBAR_AX    = [0.03, 0.197, 0.94, 0.053]
_LEGEND_AX  = [0.03, 0.005, 0.42, 0.187]   # LEFT  — color key
_COUNTRY_AX = [0.50, 0.005, 0.47, 0.187]   # RIGHT — 4-card country grid

# Pixel rows for PIL glow
GLOBE_TOP_PX = int((1.0 - (_GLOBE_BOT + _GLOBE_H)) * FIG_H_PX)
GLOBE_BOT_PX = int((1.0 - _GLOBE_BOT)              * FIG_H_PX)
MAP_TOP_PX   = int((1.0 - (_MAP_BOT  + _MAP_H))    * FIG_H_PX)
MAP_BOT_PX   = int((1.0 - _MAP_BOT)                * FIG_H_PX)

# ── Shapefile ─────────────────────────────────────────────────────────────────
world = gpd.read_file("ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp")
world = world[world["NAME"] != "Antarctica"].reset_index(drop=True)
_world_geoms = list(world.geometry)

NAME_MAP = {
    "UK":          "United Kingdom",
    "SaudiArabia": "Saudi Arabia",
    "SouthAfrica": "South Africa",
    "SouthKorea":  "South Korea",
    "NorthKorea":  "North Korea",
    "USA":         "United States of America",
}

EMOTION_ROW_ORDER = ["fear", "anger", "sadness", "anxiety", "hope", "joy"]

# Neon border colors — six maximally distinct hues (red/orange/yellow/green/blue/violet)
NEON = {
    "fear":    "#FF2222",   # vivid red
    "anger":   "#FF7700",   # orange  (clearly between red and yellow)
    "sadness": "#3388FF",   # sky blue
    "anxiety": "#CC33FF",   # violet
    "hope":    "#00EE77",   # green
    "joy":     "#FFEE00",   # yellow
}


# ── Color helpers ─────────────────────────────────────────────────────────────

def blend_emotion_color(emotion_state):
    weighted = {}
    for e in EMOTION_KEYS:
        v = emotion_state[e]
        if v < 0.005:
            continue
        weighted[e] = v ** 0.45
    if not weighted:
        return None
    dominant = max(weighted, key=weighted.get)
    weighted[dominant] *= 2.5
    total = sum(weighted.values())
    r = g = b = 0.0
    for e, w in weighted.items():
        c = mcolors.to_rgb(EMOTIONS[e]["color"])
        r += c[0] * w;  g += c[1] * w;  b += c[2] * w
    return (min(1.0, r / total), min(1.0, g / total), min(1.0, b / total))


def dominant_neon_color(emotion_state):
    active = {e: v for e, v in emotion_state.items() if v > 0.008}
    if not active:
        return None
    dominant = max(active, key=active.get)
    base  = np.array(mcolors.to_rgb(NEON[dominant]))
    scale = 0.35 + min(1.0, active[dominant] * 1.2) * 0.65
    return tuple(np.clip(base * scale, 0, 1))


# ── Pre-compute dots + rings ───────────────────────────────────────────────────

def _sample_dots(geom, n, rng):
    if geom is None or geom.is_empty:
        return np.zeros((0, 3))
    minx, miny, maxx, maxy = geom.bounds
    batch  = max(n * 25, 500)
    xs     = rng.uniform(minx, maxx, batch)
    ys     = rng.uniform(miny, maxy, batch)
    pts_2d = np.column_stack([xs, ys])
    if geom.geom_type == "Polygon":
        mask = MplPath(np.array(geom.exterior.coords)).contains_points(pts_2d)
    elif geom.geom_type == "MultiPolygon":
        mask = np.zeros(len(pts_2d), dtype=bool)
        for poly in geom.geoms:
            if not poly.is_empty:
                mask |= MplPath(np.array(poly.exterior.coords)).contains_points(pts_2d)
    else:
        return np.zeros((0, 3))
    inside = pts_2d[mask][:n]
    if len(inside) == 0:
        return np.zeros((0, 3))
    return np.column_stack([inside, rng.random(len(inside))])


def _geom_to_rings(geom):
    rings = []
    if geom is None or geom.is_empty:
        return rings
    if geom.geom_type == "Polygon":
        rings.append(np.array(geom.exterior.coords))
    elif geom.geom_type == "MultiPolygon":
        for poly in geom.geoms:
            if not poly.is_empty:
                rings.append(np.array(poly.exterior.coords))
    return rings


print("Pre-computing country data...", end="", flush=True)
_rng = np.random.default_rng(42)
COUNTRY_DOTS  = {}
COUNTRY_RINGS = {}
for _, _row in world.iterrows():
    _geom = _row.geometry
    if _geom is None or _geom.is_empty:
        continue
    _n    = max(80, min(1200, int(_geom.area * 1.4)))
    _pts  = _sample_dots(_geom, _n, _rng)
    if len(_pts) > 0:
        COUNTRY_DOTS[_row["NAME"]] = _pts
    _rings = _geom_to_rings(_geom)
    if _rings:
        COUNTRY_RINGS[_row["NAME"]] = _rings
print(f" done ({len(COUNTRY_DOTS)} countries).")


# ── Longitude helper ──────────────────────────────────────────────────────────

def get_start_longitude(target_states: dict, current_states: dict) -> float:
    """Return the centroid longitude of the country with the largest total emotion change."""
    best_lon  = -20.0
    max_delta = -1.0
    for cid, emo_target in target_states.items():
        if cid not in current_states:
            continue
        delta = sum(abs(emo_target[e] - current_states[cid].get(e, 0.0))
                    for e in EMOTION_KEYS)
        if delta > max_delta:
            name = NAME_MAP.get(cid, cid)
            rows = world[world["NAME"] == name]
            if not rows.empty:
                best_lon  = float(rows.geometry.centroid.x.values[0])
                max_delta = delta
    return best_lon


# ── PIL glow ──────────────────────────────────────────────────────────────────

def _glow_region(arr, top_px, bot_px, blur_radius, bloom):
    crop  = arr[top_px:bot_px]
    img_c = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8))
    g     = ImageEnhance.Color(img_c).enhance(2.0)
    g     = ImageEnhance.Brightness(g).enhance(1.2)
    g     = g.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    bm    = np.array(g, dtype=np.float32) / 255.0
    out   = 1.0 - (1.0 - crop) * (1.0 - bm * bloom)
    return np.clip(out, 0, 1)


def _apply_glow(image_path):
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0
    arr[GLOBE_TOP_PX:GLOBE_BOT_PX] = _glow_region(arr, GLOBE_TOP_PX, GLOBE_BOT_PX,
                                                    blur_radius=14, bloom=0.50)
    arr[MAP_TOP_PX:MAP_BOT_PX]     = _glow_region(arr, MAP_TOP_PX,   MAP_BOT_PX,
                                                    blur_radius=8,  bloom=0.40)
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(image_path)


# ── Drawing helpers ───────────────────────────────────────────────────────────


def _draw_country_info(ax, states, news_positive=None, news_negative=None):
    ax.axis("off");  ax.set_xlim(0, 1);  ax.set_ylim(0, 1)
    _cs = {c: (states[c]["joy"] * 0.55 + states[c]["hope"] * 0.45
               - states[c]["fear"] * 0.30 - states[c]["sadness"] * 0.20
               - states[c]["anger"] * 0.25 - states[c]["anxiety"] * 0.25)
           for c in states}
    best  = max(_cs, key=_cs.get)
    worst = min(_cs, key=_cs.get)
    _sn   = lambda nm: nm if len(nm) <= 13 else nm[:12] + "\u2026"
    _pct  = lambda s: f"{int((s + 1) / 2 * 100)}/100"

    # 2×2 card grid — no bars, just label / name / score
    cards = [
        ("HIGHEST WELLBEING", best,           "#22c55e", _pct(_cs[best]),  0.00, 0.52),
        ("MOST DISTRESSED",   worst,          "#ef4444", _pct(_cs[worst]), 0.52, 0.52),
        ("+ NEWS IMPACT",     news_positive,  "#60a5fa", None,             0.00, 0.02),
        ("-  NEWS IMPACT",    news_negative,  "#fb923c", None,             0.52, 0.02),
    ]
    for label, country, color, score, xc, yb in cards:
        ax.text(xc, yb + 0.46, label,
                color="#475569", fontsize=6.0, fontweight="bold", va="bottom")
        name_str = _sn(country) if country else "\u2014"
        name_col = color if country else "#334155"
        ax.text(xc, yb + 0.26, name_str,
                color=name_col, fontsize=8.5, fontweight="bold", va="bottom")
        if score is not None and country:
            ax.text(xc, yb + 0.06, score,
                    color=color, fontsize=6.5, va="bottom", alpha=0.75)


def _draw_color_legend(ax):
    ax.axis("off");  ax.set_xlim(0, 1);  ax.set_ylim(0, 1)
    ax.text(0.0, 0.97, "BORDER COLORS",
            color="#475569", fontsize=8, fontweight="bold", va="top")
    n       = len(EMOTION_ROW_ORDER)
    row_top = 0.86
    row_h   = row_top / n
    for i, emo_key in enumerate(EMOTION_ROW_ORDER):
        yc    = row_top - (i + 0.5) * row_h
        color = NEON[emo_key]
        ax.add_patch(mpatches.Rectangle(
            (0.0, yc - 0.040), 0.09, 0.080,
            facecolor=color, edgecolor="none", alpha=0.85
        ))
        ax.text(0.14, yc, EMOTIONS[emo_key]["label"],
                color="#94a3b8", fontsize=10, va="center", fontweight="bold")


def _draw_flat_map(ax_map, states):
    ax_map.set_facecolor(BG)
    ax_map.set_xlim(-180, 180)
    ax_map.set_ylim(-60, 85)

    for _lat in range(-60, 86, 30):
        ax_map.plot([-180, 180], [_lat, _lat], color="#111111", lw=0.4, alpha=0.9, zorder=1)
    for _lon in range(-180, 181, 30):
        ax_map.plot([_lon, _lon], [-60, 85], color="#111111", lw=0.4, alpha=0.9, zorder=1)

    world.plot(ax=ax_map, color="none", edgecolor="#1a3a5c",
               linewidth=0.35, alpha=0.55, aspect="auto", zorder=2)
    ax_map.set_xlim(-180, 180);  ax_map.set_ylim(-60, 85)

    tracked_idx, blend_colors, neon_colors = [], [], []
    for idx, row in world.iterrows():
        cid = next((c for c in states if NAME_MAP.get(c, c) == row["NAME"]), None)
        if cid is None:
            continue
        bc = blend_emotion_color(states[cid])
        nc = dominant_neon_color(states[cid])
        if bc is not None or nc is not None:
            tracked_idx.append(idx)
            blend_colors.append(bc if bc is not None else (0.05, 0.10, 0.18))
            neon_colors.append(nc if nc is not None else (0.05, 0.15, 0.25))

    if tracked_idx:
        world.iloc[tracked_idx].plot(
            ax=ax_map, color=blend_colors, edgecolor="none",
            linewidth=0, aspect="auto", alpha=0.10, zorder=3)
        ax_map.set_xlim(-180, 180);  ax_map.set_ylim(-60, 85)

    halo_rings, halo_colors = [], []
    core_rings, core_colors = [], []
    for idx, nc in zip(tracked_idx, neon_colors):
        for ring in COUNTRY_RINGS.get(world.iloc[idx]["NAME"], []):
            halo_rings.append(ring);  halo_colors.append(nc)
            core_rings.append(ring);  core_colors.append(nc)

    if halo_rings:
        ax_map.add_collection(LineCollection(
            halo_rings, colors=halo_colors,
            linewidths=4.5, alpha=0.18, zorder=4, capstyle="round", joinstyle="round"))
        ax_map.add_collection(LineCollection(
            core_rings, colors=core_colors,
            linewidths=0.9, alpha=0.92, zorder=5, capstyle="round", joinstyle="round"))

    xs_list, ys_list, colors_list = [], [], []
    for _, row in world.iterrows():
        cid = next((c for c in states if NAME_MAP.get(c, c) == row["NAME"]), None)
        if cid is None:
            continue
        pts = COUNTRY_DOTS.get(row["NAME"])
        if pts is None or len(pts) == 0:
            continue
        emo_state   = states[cid]
        sorted_emos = sorted(
            [(e, emo_state[e]) for e in EMOTION_KEYS if emo_state[e] > 0.003],
            key=lambda x: -x[1])
        if not sorted_emos:
            continue
        total_intensity = min(1.0, sum(v for _, v in sorted_emos))
        ros        = pts[:, 2]
        rgb_colors = np.zeros((len(pts), 3))
        assigned   = np.zeros(len(pts), dtype=bool)
        cumulative = 0.0
        for e, v in sorted_emos:
            band = (~assigned) & (ros >= cumulative) & (ros < cumulative + v)
            if band.any():
                rgb_colors[band] = mcolors.to_rgb(EMOTIONS[e]["color"])
                assigned[band]   = True
            cumulative += v
        visible = assigned & (ros < total_intensity)
        if visible.any():
            xs_list.append(pts[visible, 0])
            ys_list.append(pts[visible, 1])
            colors_list.append(rgb_colors[visible])

    if xs_list:
        ax_map.scatter(
            np.concatenate(xs_list), np.concatenate(ys_list),
            c=np.concatenate(colors_list),
            s=DOT_SIZE * 0.65, alpha=0.75, zorder=6, linewidths=0)

    ax_map.axis("off")


# ── Main render function ───────────────────────────────────────────────────────

def render_frame(states, day, happiness_history, news_log,
                 central_lon=0.0, central_lat=20.0, save_path=None,
                 news_positive=None, news_negative=None):
    day_num = day // 24
    hour    = day % 24

    proj = ccrs.Orthographic(central_longitude=central_lon, central_latitude=central_lat)
    fig  = plt.figure(figsize=(FIG_W_IN, FIG_H_IN), facecolor=BG)

    ax_title   = fig.add_axes(_TITLE_AX)
    ax_globe   = fig.add_axes(_GLOBE_AX, projection=proj)
    ax_map     = fig.add_axes(_MAP_AX)
    ax_hbar    = fig.add_axes(_HBAR_AX)
    ax_country = fig.add_axes(_COUNTRY_AX)
    ax_legend  = fig.add_axes(_LEGEND_AX)

    for ax in [ax_title, ax_map, ax_hbar, ax_country, ax_legend]:
        ax.set_facecolor(BG)
        for sp in ax.spines.values():
            sp.set_edgecolor("#1e293b")

    # ── HEADLINE HEADER ───────────────────────────────────────────────────────
    ax_title.axis("off");  ax_title.set_xlim(0, 1);  ax_title.set_ylim(0, 1)
    headline = ""
    for entry in news_log:                  # prepended → newest first
        if entry["day"] <= day:
            headline = entry["headline"]
            break
    if not headline and news_log:
        headline = news_log[0]["headline"]
    display = (headline[:65] + "\u2026") if len(headline) > 65 else headline
    ax_title.text(0.0, 0.55, display,
                  color="#94a3b8", fontsize=7.5, va="center", style="italic",
                  clip_on=True)
    ax_title.text(1.0, 0.55, f"Day {day_num}  \u00b7  {hour:02d}:00",
                  color="#475569", fontsize=6.5, va="center", ha="right")

    # ── GLOBE ─────────────────────────────────────────────────────────────────
    ax_globe.set_facecolor(BG)
    ax_globe.set_global()
    ax_globe.gridlines(color="#111111", linewidth=0.4, alpha=0.9, draw_labels=False)
    ax_globe.add_geometries(_world_geoms, crs=SRC_CRS,
                            facecolor="#080808", edgecolor="#1a3a5c",
                            linewidth=0.3, alpha=1.0, zorder=1)

    tracked_idx, blend_colors, neon_colors = [], [], []
    for idx, row in world.iterrows():
        cid = next((c for c in states if NAME_MAP.get(c, c) == row["NAME"]), None)
        if cid is None:
            continue
        bc = blend_emotion_color(states[cid])
        nc = dominant_neon_color(states[cid])
        if bc is not None or nc is not None:
            tracked_idx.append(idx)
            blend_colors.append(bc if bc is not None else (0.05, 0.10, 0.18))
            neon_colors.append(nc if nc is not None else (0.05, 0.15, 0.28))

    for idx, color in zip(tracked_idx, blend_colors):
        ax_globe.add_geometries([world.iloc[idx].geometry], crs=SRC_CRS,
                                facecolor=color, edgecolor="none",
                                alpha=0.13, zorder=2)
    for idx, color in zip(tracked_idx, neon_colors):
        ax_globe.add_geometries([world.iloc[idx].geometry], crs=SRC_CRS,
                                facecolor="none", edgecolor=color,
                                linewidth=4.5, alpha=0.18, zorder=3)
    for idx, color in zip(tracked_idx, neon_colors):
        ax_globe.add_geometries([world.iloc[idx].geometry], crs=SRC_CRS,
                                facecolor="none", edgecolor=color,
                                linewidth=0.9, alpha=0.90, zorder=4)

    try:
        ax_globe.spines["geo"].set_edgecolor("#2a5a8c")
        ax_globe.spines["geo"].set_linewidth(0.9)
        ax_globe.spines["geo"].set_alpha(0.8)
    except (KeyError, AttributeError):
        pass

    xs_list, ys_list, colors_list = [], [], []
    for _, row in world.iterrows():
        cid = next((c for c in states if NAME_MAP.get(c, c) == row["NAME"]), None)
        if cid is None:
            continue
        pts = COUNTRY_DOTS.get(row["NAME"])
        if pts is None or len(pts) == 0:
            continue
        emo_state   = states[cid]
        sorted_emos = sorted(
            [(e, emo_state[e]) for e in EMOTION_KEYS if emo_state[e] > 0.003],
            key=lambda x: -x[1])
        if not sorted_emos:
            continue
        total_intensity = min(1.0, sum(v for _, v in sorted_emos))
        ros        = pts[:, 2]
        rgb_colors = np.zeros((len(pts), 3))
        assigned   = np.zeros(len(pts), dtype=bool)
        cumulative = 0.0
        for e, v in sorted_emos:
            band = (~assigned) & (ros >= cumulative) & (ros < cumulative + v)
            if band.any():
                rgb_colors[band] = mcolors.to_rgb(EMOTIONS[e]["color"])
                assigned[band]   = True
            cumulative += v
        visible = assigned & (ros < total_intensity)
        if visible.any():
            xs_list.append(pts[visible, 0])
            ys_list.append(pts[visible, 1])
            colors_list.append(rgb_colors[visible])

    if xs_list:
        ax_globe.scatter(
            np.concatenate(xs_list), np.concatenate(ys_list),
            c=np.concatenate(colors_list),
            s=DOT_SIZE, alpha=0.80, zorder=5, linewidths=0,
            transform=SRC_CRS)

    # ── FLAT MAP ──────────────────────────────────────────────────────────────
    _draw_flat_map(ax_map, states)

    # ── HAPPINESS BAR ─────────────────────────────────────────────────────────
    ax_hbar.axis("off");  ax_hbar.set_xlim(0, 1);  ax_hbar.set_ylim(0, 1)
    h_val   = happiness_history[-1] if happiness_history else 0.0
    fill    = (h_val + 1) / 2
    score   = int(fill * 100)
    h_color = "#22c55e" if h_val >= 0 else "#ef4444"
    ax_hbar.text(0.00, 0.88, "WORLD HAPPINESS INDEX",
                 color="#475569", fontsize=7.5, fontweight="bold", va="center")
    ax_hbar.text(1.00, 0.88, f"{score} / 100",
                 color=h_color, fontsize=8.0, fontweight="bold", va="center", ha="right")
    ax_hbar.add_patch(mpatches.Rectangle(
        (0.0, 0.10), 1.0, 0.38, facecolor="#0f1a2e", edgecolor="#1e3a5c", linewidth=0.6))
    if fill > 0.01:
        ax_hbar.add_patch(mpatches.Rectangle(
            (0.0, 0.12), fill, 0.34, facecolor=h_color, edgecolor="none", alpha=0.22))
        ax_hbar.add_patch(mpatches.Rectangle(
            (0.0, 0.15), fill, 0.28, facecolor=h_color, edgecolor="none", alpha=0.85))

    # ── COLOR LEGEND (left) + COUNTRY CARDS (right) ───────────────────────────
    _draw_color_legend(ax_legend)
    _draw_country_info(ax_country, states, news_positive, news_negative)

    # ── SAVE + GLOW ───────────────────────────────────────────────────────────
    if save_path:
        plt.savefig(save_path, dpi=DPI, facecolor=BG)
        plt.close(fig)
        _apply_glow(save_path)
    else:
        plt.show()
        plt.close(fig)
