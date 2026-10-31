"""Kaia's mood, for the music (STANDALONE-ONLY FILE).

In Kaiacord, `utils/core/kaia_art_intent.py` reads her live emotional state (the mood
engine, fed by every conversation) and also drives her fractal art; the music reads
only `mood()` and `feeling_word()` from it. Without the bot there is no conversation
to move her mood, so here it is set: `kaia.mood` in config/local.yaml, as a word
(wired, restless, tired, hollow, bright, heavy, calm, curious) or as numbers
{valence: -1..1, arousal: 0..1, energy: 0..1}; `--mood` on the command line sets
KAIA_MOOD, which wins. Unset, she is neutral — the same fallback Kaiacord's mood()
returns when its mood engine is unavailable.

`feeling_word` is Kaiacord's, copied: if it changes there, change it here
(tests/test_standalone.py pins the eight words to the values below).
"""
from __future__ import annotations

import os

NEUTRAL = {"valence": 0.0, "arousal": 0.5, "energy": 0.5}

#: A representative state for each word feeling_word() returns (each maps back to its word).
WORDS = {
    "wired": {"valence": 0.4, "arousal": 0.85, "energy": 0.8},
    "restless": {"valence": -0.3, "arousal": 0.85, "energy": 0.7},
    "tired": {"valence": 0.1, "arousal": 0.3, "energy": 0.2},
    "hollow": {"valence": -0.4, "arousal": 0.3, "energy": 0.2},
    "bright": {"valence": 0.6, "arousal": 0.55, "energy": 0.7},
    "heavy": {"valence": -0.5, "arousal": 0.5, "energy": 0.5},
    "calm": {"valence": 0.1, "arousal": 0.3, "energy": 0.5},
    "curious": {"valence": 0.1, "arousal": 0.55, "energy": 0.6},
}


def mood() -> dict:
    """Her state: KAIA_MOOD (a word), else config `kaia.mood`, else neutral."""
    word = os.environ.get("KAIA_MOOD", "").strip().lower()
    if word in WORDS:
        return dict(WORDS[word])
    try:
        from utils.infrastructure.system.yaml_config import config
        m = config.get("kaia.mood")
    except Exception:
        m = None
    if isinstance(m, str) and m.strip().lower() in WORDS:
        return dict(WORDS[m.strip().lower()])
    if isinstance(m, dict):
        out = dict(NEUTRAL)
        for k in out:
            if isinstance(m.get(k), (int, float)):
                out[k] = float(m[k])
        return out
    return dict(NEUTRAL)


def feeling_word(m: dict) -> str:
    """One plain word for a mood (Kaiacord's rule, unchanged)."""
    v, a, e = m["valence"], m["arousal"], m["energy"]
    if a > 0.7:
        return "restless" if v < 0 else "wired"
    if e < 0.3:
        return "tired" if v >= 0 else "hollow"
    if v > 0.3:
        return "bright"
    if v < -0.2:
        return "heavy"
    return "calm" if a < 0.4 else "curious"
