"""Persist last played station across app restarts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

LAST_PATH = Path(__file__).resolve().parent.parent / "data" / "last_station.json"


def save(station: dict) -> None:
    url = station.get("url", "")
    if not url:
        return
    LAST_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(LAST_PATH, "w", encoding="utf-8") as f:
            json.dump(station, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.warning("Could not save last station: %s", exc)


def load() -> Optional[dict]:
    if not LAST_PATH.exists():
        return None
    try:
        with open(LAST_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load last station: %s", exc)
        return None
    if isinstance(data, dict) and data.get("url"):
        return data
    return None


def find_index(stations: List[Dict], station: dict) -> Optional[int]:
    url = station.get("url", "")
    if not url:
        return None
    for i, st in enumerate(stations):
        if st.get("url") == url:
            return i
    return None
