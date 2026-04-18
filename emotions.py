# emotions.py
# Each emotion has:
#   color           - for visualization
#   spread_rate     - how fast it spreads to neighbors (0 to 1)
#   decay_rate      - how fast it fades on its own (0 to 1)
#   happiness_weight - contribution to happiness index (-1 to +1)

EMOTIONS = {
    "fear":    {
        "label":             "Fear",
        "color":             "#CC0000",   # red
        "spread_rate":       0.35/6,     # spreads fast — panic is contagious
        "decay_rate":        0.04/6,     # lingers long
        "happiness_weight":  -0.8,
    },
    "anger":   {
        "label":             "Anger",
        "color":             "#CCAA00",   # golden yellow
        "spread_rate":       0.30/6,     # spreads fast
        "decay_rate":        0.08/6,     # fades quicker than fear
        "happiness_weight":  -0.7,
    },
    "sadness": {
        "label":             "Sadness",
        "color":             "#1E3A8A",   # deep blue
        "spread_rate":       0.15/6,     # spreads slowly
        "decay_rate":        0.02/6,     # very slow to go away
        "happiness_weight":  -0.6,
    },
    "anxiety": {
        "label":             "Anxiety",
        "color":             "#7C3AED",   # purple
        "spread_rate":       0.20/6,     # moderate spread
        "decay_rate":        0.03/6,     # persistent
        "happiness_weight":  -0.5,
    },
    "hope":    {
        "label":             "Hope",
        "color":             "#C8C8E8",   # near-white lavender
        "spread_rate":       0.10/6,     # hard to spread
        "decay_rate":        0.05/6,     # fades at medium rate
        "happiness_weight":  +0.9,
    },
    "joy":     {
        "label":             "Joy",
        "color":             "#00AA44",   # green
        "spread_rate":       0.08/6,     # hardest to spread
        "decay_rate":        0.10/6,     # fades fastest — joy is fragile
        "happiness_weight":  +1.0,
    },
}

EMOTION_KEYS = list(EMOTIONS.keys())
