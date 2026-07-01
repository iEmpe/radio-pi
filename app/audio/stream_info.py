"""Parse ICY/mpv stream metadata into display-friendly fields."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.text_utils import strip_polish_diacritics


@dataclass
class StreamInfo:
    artist: str = ""
    title: str = ""
    genre: str = ""
    station_label: str = ""
    bitrate_kbps: Optional[int] = None

    @property
    def has_track(self) -> bool:
        if self.artist and self.title:
            return True
        if self.title and self.artist:
            return True
        return bool(self.title) and not _looks_like_station_name(self.title)

    def track_scroll_text(self, station_name: str = "") -> str:
        """Single line for bottom bar — only now-playing, never station/genre."""
        name = (station_name or "").strip().lower()

        if self.artist and self.title:
            return f"{self.artist} — {self.title}"

        if not self.title or _is_junk(self.title):
            return ""

        t_lower = self.title.lower()
        if name and t_lower == name:
            return ""
        if self.station_label and t_lower == self.station_label.lower():
            return ""
        if self.genre and t_lower == self.genre.lower():
            return ""

        artist, track = _split_artist_title(self.title)
        if artist and track:
            return f"{artist} — {track}"

        if _looks_like_station_name(self.title) and not artist:
            return ""

        return self.title


def _display(text: str) -> str:
    return strip_polish_diacritics(text.strip()) if text else ""


def _is_junk(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return True
    if t.startswith(("http://", "https://")):
        return True
    if re.search(r"\.(mp3|aac|m3u8?|pls)(\?|$)", t):
        return True
    if len(t) > 120:
        return True
    return False


def _looks_like_station_name(text: str) -> bool:
    t = text.lower()
    return "radio" in t or "fm" in t or "antyradio" in t


def _parse_iheart(raw: str) -> tuple[str, str]:
    artist = ""
    title = ""
    m = re.search(r'artist="([^"]*)"', raw)
    if m:
        artist = m.group(1).strip()
    m = re.search(r'title="([^"]*)"', raw)
    if m:
        title = m.group(1).strip()
    return artist, title


def _split_artist_title(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if " / " in raw and " - " not in raw[:20]:
        parts = raw.split(" / ", 1)
        return parts[0].strip(), parts[1].strip()
    if " - " in raw:
        parts = raw.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    if ": " in raw:
        parts = raw.split(": ", 1)
        return parts[0].strip(), parts[1].strip()
    if "," in raw and raw.count(",") == 1:
        parts = raw.split(",", 1)
        return parts[0].strip(), parts[1].strip()
    return "", raw


def _pick_raw_title(meta: Dict[str, Any], media_title: str = "") -> str:
    del media_title
    for key in ("icy-title", "title", "Title", "StreamTitle"):
        val = meta.get(key)
        if val is not None and str(val).strip() and not _is_junk(str(val)):
            return str(val).strip()
    return ""


def _pick_station_label(meta: Dict[str, Any]) -> str:
    for key in ("icy-description", "icy-name"):
        val = meta.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return ""


def _pick_genre(meta: Dict[str, Any], config_tags: str = "") -> str:
    g = str(meta.get("icy-genre", "") or "").strip()
    if g and g.lower() not in ("", "various", "unspecified"):
        return g.title()
    tags = (config_tags or "").strip()
    if tags:
        first = tags.split(",")[0].strip()
        if first:
            return first.title()
    return ""


def parse_stream_info(
    meta: Optional[Dict[str, Any]],
    media_title: str = "",
    config_station: Optional[Dict[str, Any]] = None,
    bitrate_kbps: Optional[int] = None,
) -> StreamInfo:
    meta = meta or {}
    config = config_station or {}
    info = StreamInfo(bitrate_kbps=bitrate_kbps)

    raw = _pick_raw_title(meta, media_title)
    if raw and 'artist="' in raw:
        info.artist, info.title = _parse_iheart(raw)
    elif raw:
        info.artist, info.title = _split_artist_title(raw)

    info.station_label = _display(_pick_station_label(meta) or config.get("name", ""))
    info.genre = _display(_pick_genre(meta, config.get("tags", "")))
    info.artist = _display(info.artist)
    info.title = _display(info.title)

    return info
