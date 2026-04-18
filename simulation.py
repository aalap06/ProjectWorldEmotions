# simulation.py
# Core logic: initializing country states, spreading emotions, computing happiness

from countries import COUNTRIES
from emotions import EMOTIONS, EMOTION_KEYS


def init_states():
    """
    Initialize all countries with near-zero emotion values.
    Returns a dict: { country_id: { emotion: value } }
    """
    states = {}
    for country_id in COUNTRIES:
        states[country_id] = {e: 0.0 for e in EMOTION_KEYS}
    return states


def get_dominant_emotion(emotion_state):
    """
    Returns the emotion with the highest value for a country.
    """
    return max(emotion_state, key=emotion_state.get)


def compute_happiness(all_states):
    """
    World happiness index — average across all countries.
    Each emotion contributes its happiness_weight * intensity.
    Returns a value between -1.0 and +1.0
    """
    total = 0.0
    count = len(all_states)

    for country_id, emo_state in all_states.items():
        country_score = 0.0
        for e in EMOTION_KEYS:
            country_score += emo_state[e] * EMOTIONS[e]["happiness_weight"]
        total += country_score

    raw = total / count if count > 0 else 0
    return max(-1.0, min(1.0, raw))


def simulate_tick(states):
    """
    One day simulation tick:
    1. Decay all emotions slightly
    2. Spread emotions to neighbors
    3. Clamp values between 0 and 1
    Returns a new states dict (does not modify original)
    """
    next_states = {}

    for country_id in states:
        # Start with a copy
        next_states[country_id] = dict(states[country_id])

        # Step 1 — Decay
        for e in EMOTION_KEYS:
            decay = EMOTIONS[e]["decay_rate"]
            next_states[country_id][e] = max(0.0, next_states[country_id][e] - decay * states[country_id][e])

        # Step 2 — Spread from neighbors
        neighbors = COUNTRIES[country_id]["neighbors"]
        for neighbor_id in neighbors:
            if neighbor_id not in states:
                continue
            for e in EMOTION_KEYS:
                spread = states[neighbor_id][e] * EMOTIONS[e]["spread_rate"] * 0.3
                next_states[country_id][e] = min(1.0, next_states[country_id][e] + spread)

        # Step 3 — Clamp
        for e in EMOTION_KEYS:
            next_states[country_id][e] = max(0.0, min(1.0, next_states[country_id][e]))

    return next_states


def apply_news_event(states, affected):
    """
    Apply emotion deltas to specific countries based on a news event.

    affected: list of dicts like:
        [
            { "country": "USA", "emotions": { "fear": 0.5, "anger": 0.3 } },
            { "country": "UK",  "emotions": { "sadness": 0.4 } },
        ]

    Returns new states dict.
    """
    next_states = {cid: dict(emo) for cid, emo in states.items()}

    for entry in affected:
        country_id = entry["country"]
        if country_id not in next_states:
            print(f"  [Warning] Country '{country_id}' not found, skipping.")
            continue
        for emotion, delta in entry["emotions"].items():
            if emotion not in EMOTION_KEYS:
                continue
            current = next_states[country_id][emotion]
            next_states[country_id][emotion] = max(0.0, min(1.0, current + delta))

    return next_states
