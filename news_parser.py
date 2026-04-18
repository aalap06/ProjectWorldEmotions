# news_parser.py
# No API needed.
# Prints a prompt for you to paste into Claude Pro (or any AI).
# You paste the JSON response back into the terminal.

import json
from countries import ALIASES

PROMPT_TEMPLATE = """You are an emotion analysis engine for a world simulation.

CURRENT WORLD EMOTIONAL STATE (top active countries, intensity 0.0–1.0):
{current_state}

Given a real-world news headline, determine the NEW TARGET emotional state for
each meaningfully affected country. These are absolute values after the headline's
impact — not deltas. Use the current state above as your starting context.

You can affect ANY country in the world. Use full official country names
(e.g. "United States of America", "United Kingdom", "Dem. Rep. Congo").
Available emotions: fear, anger, sadness, anxiety, hope, joy

Rules:
- Only include countries meaningfully affected by this specific headline
- Values are absolute intensities 0.0–1.0 (not changes from the current state)
- Be realistic about geographic/political reach of the news
- If a country is unaffected, omit it — it keeps its current state

Respond ONLY with a valid JSON array. No explanation. No markdown. Example:
[
  {{ "country": "Ukraine", "emotions": {{ "fear": 0.85, "sadness": 0.60, "anger": 0.50, "hope": 0.25 }} }},
  {{ "country": "Poland",  "emotions": {{ "fear": 0.45, "anxiety": 0.55, "hope": 0.35 }} }}
]

News headline: {headline}"""


def _format_state(states: dict, top_n: int = 45) -> str:
    """Show the top N most emotionally active countries (keeps prompt compact)."""
    scored = [
        (cid, sum(v for v in emo.values()))
        for cid, emo in states.items()
    ]
    scored.sort(key=lambda x: -x[1])

    lines = []
    for cid, _ in scored[:top_n]:
        emo = states[cid]
        parts = [f"{e[:3]}={v:.2f}" for e, v in sorted(emo.items()) if v > 0.05]
        if parts:
            lines.append(f"  {cid}: {', '.join(parts)}")
    return "\n".join(lines) if lines else "  (baseline neutral state)"


def _resolve_country(name: str, states: dict) -> str | None:
    """
    Resolve a country name returned by Claude to a canonical state key.
    Tries: exact match → ALIASES → case-insensitive match.
    """
    if name in states:
        return name
    canonical = ALIASES.get(name)
    if canonical and canonical in states:
        return canonical
    # Case-insensitive fallback
    name_lower = name.lower()
    for k in states:
        if k.lower() == name_lower:
            return k
    return None


def parse_news(headline: str, states: dict = None) -> list:
    """
    Prints a prompt for the user to paste into Claude Pro.
    Waits for them to paste the JSON response back.
    Returns a list of affected country emotion targets,
    with country names resolved to canonical state keys.
    """
    state_text = _format_state(states) if states else "  (no prior data — using baseline)"
    prompt = PROMPT_TEMPLATE.format(headline=headline, current_state=state_text)

    print()
    print("  ── Copy this prompt into Claude Pro ──────────────────────")
    print()
    print(prompt)
    print()
    print("  ──────────────────────────────────────────────────────────")
    print()
    print("  Paste the JSON response here, then press Enter twice:")
    print()

    lines = []
    while True:
        try:
            line = input("  ")
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip() == "" and lines:
            break
        lines.append(line)

    raw = "\n".join(lines).strip()

    # Strip markdown code fences if the AI wrapped the JSON
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        affected = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  Could not parse JSON: {e}")
        print("  Skipping this headline.")
        return []

    # Resolve country names → canonical keys
    resolved = []
    for entry in affected:
        cid = _resolve_country(entry["country"], states or {})
        if cid:
            entry["country"] = cid
            resolved.append(entry)
        else:
            print(f"  [Warning] Unknown country '{entry['country']}' — skipping.")

    print(f"  Got {len(resolved)} affected countries.")
    return resolved
