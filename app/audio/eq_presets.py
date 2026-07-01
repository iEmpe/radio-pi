"""EQ preset definitions and mpv audio-filter chains."""

from __future__ import annotations

from typing import Dict, List, Tuple

# (frequency Hz, gain dB)
Band = Tuple[int, float]

PRESETS: Dict[str, List[Band]] = {
    "dnb": [
        (60, 6.0),
        (120, 4.0),
        (250, -3.0),
        (500, -2.0),
        (1000, 1.0),
        (3000, 2.0),
        (8000, 4.0),
    ],
    "pop": [
        (60, -1.0),
        (120, 0.0),
        (250, 2.0),
        (500, 2.0),
        (1000, 3.0),
        (3000, 4.0),
        (8000, 2.0),
    ],
    "rock": [
        (60, 2.0),
        (120, 4.0),
        (250, 2.0),
        (500, 1.0),
        (1000, 2.0),
        (3000, 5.0),
        (8000, 2.0),
    ],
    "hiphop": [
        (60, 6.0),
        (120, 5.0),
        (250, 1.0),
        (500, -2.0),
        (1000, 2.0),
        (3000, 3.0),
        (8000, 2.0),
    ],
}

PRESET_LABELS: Dict[str, str] = {
    "dnb": "D&B",
    "pop": "POP",
    "rock": "ROCK",
    "hiphop": "HIP-HOP",
}

PRESET_IDS = list(PRESETS.keys())
DEFAULT_PRESET = "pop"


def _band_width(freq: int) -> int:
    if freq <= 120:
        return 80
    if freq <= 500:
        return 150
    if freq <= 3000:
        return 400
    return 900


def mpv_af_string(preset_id: str) -> str:
    """Build mpv --af chain: parametric equalizer bands + soft limiter."""
    bands = PRESETS.get(preset_id, PRESETS[DEFAULT_PRESET])
    parts: List[str] = []
    for freq, gain in bands:
        if abs(gain) < 0.05:
            continue
        w = _band_width(freq)
        parts.append(
            f"equalizer=f={freq}:width_type=h:width={w}:g={gain:.1f}"
        )
    parts.append("alimiter=limit=0.95")
    return ",".join(parts)
