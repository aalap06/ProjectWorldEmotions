# test_sphere.py
# Quick globe rendering test — no user input, no persistence.
# Produces 20 frames + a short video so you can verify visuals fast.
#
# Usage:  python test_sphere.py

import os
import numpy as np
import imageio.v2 as imageio

from simulation import compute_happiness
from emotions import EMOTION_KEYS
from baseline import get_baseline_states
from renderer import render_frame, get_start_longitude
from countries import COUNTRIES

FRAMES_DIR   = "test_frames"
OUTPUT_VIDEO = "test.mp4"
TOTAL_FRAMES = 20
FPS          = 5       # 4-second video
TOTAL_ROT    = 60.0    # degrees of rotation over the 20 frames

# ── Same test scenario as test_render.py ─────────────────────────────────────
TEST_AFFECTED = [
    {"country": "United States of America", "emotions": {"fear": 0.75, "anger": 0.60, "anxiety": 0.70}},
    {"country": "United Kingdom",          "emotions": {"fear": 0.55, "sadness": 0.50, "anxiety": 0.60}},
    {"country": "Russia",      "emotions": {"anger": 0.80, "fear": 0.65}},
    {"country": "Ukraine",     "emotions": {"fear": 0.90, "sadness": 0.80, "anxiety": 0.85}},
    {"country": "Germany",     "emotions": {"anxiety": 0.55, "sadness": 0.40}},
    {"country": "China",       "emotions": {"anxiety": 0.50, "anger": 0.45}},
    {"country": "India",       "emotions": {"hope": 0.60, "joy": 0.40}},
    {"country": "Australia",   "emotions": {"joy": 0.80, "hope": 0.75}},
    {"country": "Afghanistan", "emotions": {"fear": 0.95, "sadness": 0.90, "anger": 0.70}},
    {"country": "Brazil",      "emotions": {"hope": 0.65, "joy": 0.55}},
]

FAKE_HEADLINE = "Global tensions rise as major powers clash over trade and security"


def _ease(t: float) -> float:
    return (1.0 - np.cos(np.pi * t)) / 2.0


def main():
    all_ids = list(COUNTRIES.keys())

    start_states  = get_baseline_states(all_ids)
    target_states = {cid: dict(emo) for cid, emo in start_states.items()}

    for entry in TEST_AFFECTED:
        cid = entry["country"]
        if cid not in target_states:
            print(f"  [Warning] '{cid}' not found — skipping.")
            continue
        for emotion, value in entry["emotions"].items():
            if emotion in EMOTION_KEYS:
                target_states[cid][emotion] = max(0.0, min(1.0, float(value)))

    news_log  = [{"day": 0, "headline": FAKE_HEADLINE}]
    start_lon = get_start_longitude(target_states, start_states)
    print(f"Globe starts at lon={start_lon:.1f}°  (most-affected country centroid)")

    os.makedirs(FRAMES_DIR, exist_ok=True)
    for f in os.listdir(FRAMES_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(FRAMES_DIR, f))

    print(f"Rendering {TOTAL_FRAMES} test frames...")
    happiness_history = [compute_happiness(start_states)]

    for i in range(TOTAL_FRAMES):
        t = i / (TOTAL_FRAMES - 1)

        current_states = {
            cid: {
                e: start_states[cid][e] + (target_states[cid][e] - start_states[cid][e]) * t
                for e in EMOTION_KEYS
            }
            for cid in start_states
        }

        lon = start_lon + _ease(t) * TOTAL_ROT
        happiness_history.append(compute_happiness(current_states))

        frame_path = os.path.join(FRAMES_DIR, f"frame_{i:04d}.png")
        render_frame(current_states, i, happiness_history, news_log,
                     central_lon=lon, save_path=frame_path,
                     news_positive="Australia", news_negative="Ukraine")
        print(f"  [{i + 1:2d}/{TOTAL_FRAMES}]  lon={lon:6.1f}°  "
              f"happiness={happiness_history[-1]:.3f}", end="\r")

    print(f"\nDone. Frames saved to {FRAMES_DIR}/")

    frame_files = sorted(
        os.path.join(FRAMES_DIR, f)
        for f in os.listdir(FRAMES_DIR)
        if f.endswith(".png")
    )
    with imageio.get_writer(OUTPUT_VIDEO, fps=FPS, macro_block_size=None) as writer:
        for fpath in frame_files:
            writer.append_data(imageio.imread(fpath))

    print(f"Video saved: {OUTPUT_VIDEO}  ({TOTAL_FRAMES / FPS:.1f}s)")


if __name__ == "__main__":
    main()
