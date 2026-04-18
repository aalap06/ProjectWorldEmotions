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
DPI      = 180
FIG_W_PX = int(FIG_W_IN * DPI)   # 720
FIG_H_PX = int(FIG_H_IN * DPI)   # 1280

BG       = "#000000"
DOT_SIZE = 1.5
SRC_CRS  = ccrs.PlateCarree()

# ── Layout ────────────────────────────────────────────────────────────────────
# Instagram Reels safe zones:
#   _NT  = 10% top    (notch + Reels header UI)
#   _M   = 6%  sides  (rounded corners + Instagram side UI)
_NT  = 0.10
_M   = 0.06
_S   = 1.0 - _NT        # content ceiling = 0.90
_CW  = 1.0 - 2 * _M    # content width   = 0.88

_TITLE_AX   = [_M,    0.957 * _S, _CW,  0.040 * _S]

_GLOBE_BOT  = 0.510 * _S
_GLOBE_H    = 0.440 * _S
_GLOBE_AX   = (0.0,  _GLOBE_BOT,  1.0,  _GLOBE_H)

_MAP_BOT    = 0.255 * _S
_MAP_H      = 0.250 * _S
_MAP_AX     = (0.0,  _MAP_BOT,    1.0,  _MAP_H)

_HBAR_AX    = [_M,    0.197 * _S, _CW,  0.053 * _S]
_LEGEND_AX  = [_M,    0.005,      0.36, 0.187 * _S]   # LEFT  — color key
_COUNTRY_AX = [0.55,  0.005,      0.39, 0.187 * _S]   # RIGHT — 4-card country grid

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

# Neon border colors — six maximally distinct hues (red/yellow/blue/violet/white/green)
NEON = {
    "fear":    "#FF1111",   # vivid red
    "anger":   "#FFDD00",   # yellow  (clearly distinct from red)
    "sadness": "#3388FF",   # sky blue
    "anxiety": "#CC33FF",   # violet
    "hope":    "#F0F0FF",   # near-white
    "joy":     "#00EE55",   # green
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
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(image_path)


# ── Drawing helpers ───────────────────────────────────────────────────────────


_SCROLL_VISIBLE = 4   # entries shown at once per column
_SCROLL_SPEED   = 5   # ticks between each scroll step

def _rolling_window(items, tick):
    """Return a visible window of _SCROLL_VISIBLE items, scrolling with tick."""
    if not items:
        return []
    if len(items) <= _SCROLL_VISIBLE:
        return list(items)
    offset = (tick // _SCROLL_SPEED) % len(items)
    return [items[(offset + i) % len(items)] for i in range(_SCROLL_VISIBLE)]


def _draw_country_info(ax, states, news_positive=(), news_negative=(), tick=0):
    ax.axis("off");  ax.set_xlim(0, 1);  ax.set_ylim(0, 1)
    _cs = {c: (states[c]["joy"] * 0.55 + states[c]["hope"] * 0.45
               - states[c]["fear"] * 0.30 - states[c]["sadness"] * 0.20
               - states[c]["anger"] * 0.25 - states[c]["anxiety"] * 0.25)
           for c in states}
    best  = max(_cs, key=_cs.get)
    worst = min(_cs, key=_cs.get)
    _sn   = lambda nm: nm if len(nm) <= 13 else nm[:12] + "\u2026"
    _pct  = lambda s: f"{int((s + 1) / 2 * 100)}/100"

    # Top half — single best/worst country
    for label, country, color, xc in [
        ("HIGHEST WELLBEING", best,  "#22c55e", 0.00),
        ("MOST DISTRESSED",   worst, "#ef4444", 0.52),
    ]:
        ax.text(xc, 0.98, label, color="#94a3b8", fontsize=8.0, fontweight="bold", va="top")
        ax.text(xc, 0.83, _sn(country), color=color, fontsize=9.5, fontweight="bold", va="top")
        ax.text(xc, 0.68, _pct(_cs[country]), color=color, fontsize=8.0, va="top", alpha=0.85)

    ax.plot([0, 1], [0.64, 0.64], color="#1e293b", lw=0.6, alpha=0.7)

    # Bottom half — rolling news impact lists
    pos_list = list(news_positive)
    neg_list = list(news_negative)
    pos_view = _rolling_window(pos_list, tick)
    neg_view = _rolling_window(neg_list, tick)

    # headers with count
    pos_label = f"+ NEWS IMPACT ({len(pos_list)})" if pos_list else "+ NEWS IMPACT"
    neg_label = f"-  NEWS IMPACT ({len(neg_list)})" if neg_list else "-  NEWS IMPACT"
    ax.text(0.00, 0.62, pos_label, color="#94a3b8", fontsize=8.0, fontweight="bold", va="top")
    ax.text(0.52, 0.62, neg_label, color="#94a3b8", fontsize=8.0, fontweight="bold", va="top")

    row_step = 0.54 / _SCROLL_VISIBLE

    for i, name in enumerate(pos_view):
        ax.text(0.00, 0.54 - i * row_step, _sn(name), color="#60a5fa", fontsize=8.5, va="top")
    if not pos_view:
        ax.text(0.00, 0.52, "\u2014", color="#334155", fontsize=9, va="top")

    for i, name in enumerate(neg_view):
        ax.text(0.52, 0.54 - i * row_step, _sn(name), color="#fb923c", fontsize=8.5, va="top")
    if not neg_view:
        ax.text(0.52, 0.52, "\u2014", color="#334155", fontsize=9, va="top")


def _draw_color_legend(ax):
    ax.axis("off");  ax.set_xlim(0, 1);  ax.set_ylim(0, 1)
    ax.text(0.0, 0.97, "BORDER COLORS",
            color="#94a3b8", fontsize=10, fontweight="bold", va="top")
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
                color="#e2e8f0", fontsize=10, va="center", fontweight="bold")


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
                 news_positive=(), news_negative=(), apply_glow=True):
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

    # ── HEADER: day/time + scrolling ticker ───────────────────────────────────
    ax_title.axis("off");  ax_title.set_xlim(0, 1);  ax_title.set_ylim(0, 1)
    ax_title.patch.set_visible(True);  ax_title.patch.set_facecolor(BG)

    # Day / time — large, always visible, right-aligned
    ax_title.text(1.0, 0.88, f"Day {day_num}  \u00b7  {hour:02d}:00",
                  color="#e2e8f0", fontsize=9.5, fontweight="bold",
                  va="top", ha="right")

    # Build ticker from all headlines (newest first, separated by  ·)
    ticker_text = "  \u00b7  ".join(e["headline"] for e in news_log) if news_log else ""
    if ticker_text:
        _TICKER_SPEED = 0.045          # axes-units per tick
        _CHAR_W       = 0.0064         # approx axes-unit width per char
        _cycle = max(1, int((1.05 + len(ticker_text) * _CHAR_W) / _TICKER_SPEED) + 1)
        x_ticker = 1.05 - (day % _cycle) * _TICKER_SPEED
        txt = ax_title.text(x_ticker, 0.08, ticker_text,
                            color="#94a3b8", fontsize=9.0, va="bottom",
                            ha="left", style="italic")
        txt.set_clip_path(ax_title.patch)

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

    # Neon borders — project rings once and batch into two LineCollections
    halo_segs, halo_nc = [], []
    core_segs, core_nc = [], []
    for idx, nc in zip(tracked_idx, neon_colors):
        for ring in COUNTRY_RINGS.get(world.iloc[idx]["NAME"], []):
            try:
                pp  = proj.transform_points(SRC_CRS, ring[:, 0], ring[:, 1])
                cur = []
                for pt in pp:
                    if np.isnan(pt[0]) or np.isnan(pt[1]):
                        if len(cur) >= 2:
                            halo_segs.append(np.array(cur));  halo_nc.append(nc)
                            core_segs.append(np.array(cur));  core_nc.append(nc)
                        cur = []
                    else:
                        cur.append(pt[:2].tolist())
                if len(cur) >= 2:
                    halo_segs.append(np.array(cur));  halo_nc.append(nc)
                    core_segs.append(np.array(cur));  core_nc.append(nc)
            except Exception:
                continue
    if halo_segs:
        ax_globe.add_collection(LineCollection(
            halo_segs, colors=halo_nc, linewidths=4.5, alpha=0.18, zorder=3))
        ax_globe.add_collection(LineCollection(
            core_segs, colors=core_nc, linewidths=0.9, alpha=0.90, zorder=4))

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
                 color="#94a3b8", fontsize=9.5, fontweight="bold", va="center")
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
    _draw_country_info(ax_country, states, news_positive, news_negative, tick=day)

    # ── SAVE + GLOW ───────────────────────────────────────────────────────────
    if save_path:
        plt.savefig(save_path, dpi=DPI, facecolor=BG)
        plt.close(fig)
        if apply_glow:
            _apply_glow(save_path)
    else:
        plt.show()
        plt.close(fig)
