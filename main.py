# main.py
# Daily World Emotion Simulator — rotating globe + flat map edition

import os
import json
import shutil
import multiprocessing
import numpy as np
import imageio.v2 as imageio

from simulation import compute_happiness
from emotions import EMOTION_KEYS
from baseline import get_baseline_states, HAPPINESS_SCORES
from news_parser import parse_news
from renderer import render_frame, get_start_longitude
from countries import COUNTRIES


# ── Top-level worker (must be module-level for multiprocessing pickling) ──────
def _render_worker(args):
    states, tick, h_val, news_log, lon, save_path, news_pos, news_neg = args
    render_frame(states, tick, [h_val], news_log,
                 central_lon=lon, save_path=save_path,
                 news_positive=news_pos, news_negative=news_neg)

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

# INTRO_FRAMES     = 10     # 1s hold before reaction
# ANIMATION_FRAMES = 240    # full 360° rotation — smooth at 1.5°/frame
# OUTRO_FRAMES     = 20     # 2s hold on final frame
# FPS              = 10

INTRO_FRAMES     = 15    # 0.5s hold
ANIMATION_FRAMES = 570   # 19s rotation
OUTRO_FRAMES     = 15    # 0.5s hold
FPS              = 30

TOTAL_ROTATION   = 360.0  # full globe rotation per headline
FRAMES_DIR       = "frames"
OUTPUT_VIDEO     = "world_emotion.mp4"
STATE_FILE       = "world_state.json"


def _ease(t: float) -> float:
    """Smooth ease-in-out (cosine). t in [0, 1] → eased t in [0, 1]."""
    return (1.0 - np.cos(np.pi * t)) / 2.0


# ─────────────────────────────────────────────
#  STATE PERSISTENCE  (same file as main.py)
# ─────────────────────────────────────────────

def load_saved_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_state(day: int, states: dict, news_log: list):
    with open(STATE_FILE, "w") as f:
        json.dump({"day": day, "states": states, "news_log": news_log}, f, indent=2)
    print(f"  State saved to {STATE_FILE}  (Day {day})")


# ─────────────────────────────────────────────
#  HEADLINE INPUT
# ─────────────────────────────────────────────

def get_headlines():
    print()
    print("  Enter today's news headlines, one per line.")
    print("  Press Enter on a blank line when done.")
    print()
    headlines = []
    while True:
        try:
            line = input(f"  Headline {len(headlines) + 1}: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            if headlines:
                break
            print("  (Enter at least one headline.)")
        else:
            headlines.append(line)
    return headlines


# ─────────────────────────────────────────────
#  VIDEO EXPORT
# ─────────────────────────────────────────────

def export_video(frames_dir, output_path, fps):
    frame_files = sorted(
        os.path.join(frames_dir, f)
        for f in os.listdir(frames_dir)
        if f.endswith(".png")
    )
    if not frame_files:
        print("  No frames found — nothing to compile.")
        return
    with imageio.get_writer(output_path, fps=fps, macro_block_size=None) as writer:
        for fpath in frame_files:
            writer.append_data(imageio.imread(fpath))
    print(f"  Video saved: {output_path}")


# ─────────────────────────────────────────────
#  STARTUP — LOAD OR RESET
# ─────────────────────────────────────────────

def startup_state():
    all_ids = list(COUNTRIES.keys())
    print()
    print("=" * 52)
    print("   WORLD EMOTION SIMULATOR  —  SPHERE EDITION")
    print("=" * 52)
    print()

    saved = load_saved_state()
    if saved:
        print(f"  Saved state found:  Day {saved['day']}  "
              f"({len(saved['news_log'])} headline(s) recorded)")
        print()
        print("  (C) Continue from Day", saved["day"])
        print("  (R) Reset to real-world baseline (Day 0)")
        print()
        choice = ""
        while choice not in ("c", "r"):
            try:
                choice = input("  Choice [C/R]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "c"

        if choice == "c":
            states   = {cid: dict(emo) for cid, emo in saved["states"].items()}
            baseline = get_baseline_states(all_ids)
            for cid in all_ids:
                if cid not in states:
                    states[cid] = baseline[cid]
            news_log = saved["news_log"]
            day      = saved["day"]
            print(f"\n  Loaded Day {day} state.\n")
            return states, news_log, day

    print()
    if saved:
        print("  Resetting to Day 0 baseline (World Happiness Report 2024)...")
    else:
        print("  No saved state — starting from Day 0 baseline.")
    print()

    for region, cids in [
        ("Happiest",     sorted(HAPPINESS_SCORES, key=HAPPINESS_SCORES.get, reverse=True)[:5]),
        ("Least happy",  sorted(HAPPINESS_SCORES, key=HAPPINESS_SCORES.get)[:5]),
    ]:
        scores = ", ".join(f"{c} {HAPPINESS_SCORES[c]:.1f}" for c in cids)
        print(f"  {region}: {scores}")
    print()

    return get_baseline_states(all_ids), [], 0


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    states, news_log, current_day = startup_state()
    headlines = get_headlines()
    if not headlines:
        print("\n  No headlines entered. Exiting.")
        return

    print(f"\n  {len(headlines)} headline(s) received. Starting simulation...\n")

    os.makedirs(FRAMES_DIR, exist_ok=True)
    for f in os.listdir(FRAMES_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(FRAMES_DIR, f))

    happiness_history   = [compute_happiness(states)]
    frame_index         = 0
    frames_per_headline = INTRO_FRAMES + ANIMATION_FRAMES + OUTRO_FRAMES

    for i, headline in enumerate(headlines):
        print(f"\n  [{i + 1}/{len(headlines)}] {headline}")

        affected = parse_news(headline, states)
        if not affected:
            print("  No data — skipping this headline.")
            continue

        current_day += 1
        news_log.insert(0, {"day": current_day, "headline": headline})

        # Build target states
        target_states = {cid: dict(emo) for cid, emo in states.items()}
        for entry in affected:
            cid = entry["country"]
            if cid not in target_states:
                print(f"  [Warning] '{cid}' not found, skipping.")
                continue
            for emotion, value in entry["emotions"].items():
                if emotion in EMOTION_KEYS:
                    target_states[cid][emotion] = max(0.0, min(1.0, float(value)))

        start_states = {cid: dict(emo) for cid, emo in states.items()}

        # Ranked most positively / negatively affected countries by this headline
        _pos_scores, _neg_scores = {}, {}
        for _e in affected:
            _cid = _e["country"]
            if _cid not in states:
                continue
            for _emo, _val in _e["emotions"].items():
                _delta = float(_val) - states[_cid].get(_emo, 0.0)
                if _emo in ("hope", "joy"):
                    _pos_scores[_cid] = _pos_scores.get(_cid, 0.0) + max(0.0, _delta)
                elif _emo in ("fear", "anger", "sadness", "anxiety"):
                    _neg_scores[_cid] = _neg_scores.get(_cid, 0.0) + max(0.0, _delta)
        # Only put a country in the list where its net impact is dominant
        news_positive = [c for c in sorted(_pos_scores, key=_pos_scores.get, reverse=True)
                         if _pos_scores.get(c, 0) > _neg_scores.get(c, 0)]
        news_negative = [c for c in sorted(_neg_scores, key=_neg_scores.get, reverse=True)
                         if _neg_scores.get(c, 0) >= _pos_scores.get(c, 0)]

        # Globe rotation: start at most-affected country, ease 360° eastward
        start_lon = get_start_longitude(target_states, start_states)
        final_lon = start_lon + TOTAL_ROTATION

        print(f"  Globe starts at lon={start_lon:.1f}°  →  {final_lon:.1f}°")
        print(f"  Rendering {frames_per_headline} frames...")

        _kw = dict(news_positive=news_positive, news_negative=news_negative)

        # ── INTRO: render once, copy the rest ────────────────────────────
        intro_tick  = (current_day - 1) * 24
        intro_path  = os.path.join(FRAMES_DIR, f"frame_{frame_index:04d}.png")
        render_frame(states, intro_tick, happiness_history, news_log,
                     central_lon=start_lon, save_path=intro_path, **_kw)
        frame_index += 1
        for _ in range(INTRO_FRAMES - 1):
            dst = os.path.join(FRAMES_DIR, f"frame_{frame_index:04d}.png")
            shutil.copy2(intro_path, dst)
            frame_index += 1

        # ── ANIMATION: pre-compute all args, render in parallel ───────────
        anim_args  = []
        anim_h_vals = []
        for f in range(ANIMATION_FRAMES):
            t_lin = f / (ANIMATION_FRAMES - 1) if ANIMATION_FRAMES > 1 else 1.0
            t_rot = _ease(t_lin)
            cur_states = {
                cid: {e: start_states[cid][e]
                         + (target_states[cid][e] - start_states[cid][e]) * t_lin
                      for e in EMOTION_KEYS}
                for cid in states
            }
            h_val = compute_happiness(cur_states)
            anim_h_vals.append(h_val)
            lon  = start_lon + t_rot * TOTAL_ROTATION
            tick = (current_day - 1) * 24 + int(t_lin * 23)
            fp   = os.path.join(FRAMES_DIR, f"frame_{frame_index + f:04d}.png")
            anim_args.append((cur_states, tick, h_val, news_log, lon, fp,
                              news_positive, news_negative))

        happiness_history.extend(anim_h_vals)

        n_workers = min(multiprocessing.cpu_count(), len(anim_args))
        with multiprocessing.Pool(processes=n_workers) as pool:
            pool.map(_render_worker, anim_args)
        frame_index += ANIMATION_FRAMES

        # ── OUTRO: render once, copy the rest ────────────────────────────
        outro_tick = current_day * 24 - 1
        outro_path = os.path.join(FRAMES_DIR, f"frame_{frame_index:04d}.png")
        render_frame(target_states, outro_tick, happiness_history, news_log,
                     central_lon=final_lon, save_path=outro_path, **_kw)
        frame_index += 1
        for _ in range(OUTRO_FRAMES - 1):
            dst = os.path.join(FRAMES_DIR, f"frame_{frame_index:04d}.png")
            shutil.copy2(outro_path, dst)
            frame_index += 1

        states = target_states
        save_state(current_day, states, news_log)

    if frame_index == 0:
        print("\n  No frames rendered.")
        return

    print(f"\n  Frames rendered : {frame_index}")
    print(f"  World happiness : {happiness_history[-1]:.3f}")
    print(f"  FPS             : {FPS}  ({frame_index / FPS:.1f}s video)")
    print("\n  Compiling video...")
    export_video(FRAMES_DIR, OUTPUT_VIDEO, FPS)


if __name__ == "__main__":
    main()
