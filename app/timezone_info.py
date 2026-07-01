"""Warsaw timezone labels for the header clock section."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

WARSAW_TZ = ZoneInfo("Europe/Warsaw")


def _offset_hours(tzinfo) -> int:  # noqa: ANN001
    now = datetime.now(tzinfo)
    offset = now.utcoffset()
    if offset is None:
        return 0
    return int(offset.total_seconds() // 3600)


def warsaw_utc_label() -> str:
    """e.g. Warsaw: UTC+1 or Warsaw: UTC+2 (DST-aware)."""
    hours = _offset_hours(WARSAW_TZ)
    sign = "+" if hours >= 0 else ""
    return f"Warsaw: UTC{sign}{hours}"


def local_warsaw_diff_label() -> str:
    """Difference between system local zone and Warsaw, in whole hours."""
    local_h = _offset_hours(datetime.now().astimezone().tzinfo)
    warsaw_h = _offset_hours(WARSAW_TZ)
    diff = local_h - warsaw_h
    sign = "+" if diff >= 0 else ""
    return f"Local Time Zone Difference: {sign}{diff} hours"


def timezone_scroll_text() -> str:
    """Single marquee line for Warsaw UTC + local offset."""
    return f"{warsaw_utc_label()}  ·  {local_warsaw_diff_label()}"
