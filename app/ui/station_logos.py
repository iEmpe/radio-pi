"""Load cached station logos (local PNG) with text fallback."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap

from app.ui.fonts import ui_font

LOGO_DIR = Path(__file__).resolve().parent.parent / "assets" / "stations"

_PALETTE = (
    "#E53935", "#8E24AA", "#3949AB", "#00897B",
    "#F9A825", "#EF6C00", "#546E7A", "#1E88E5",
)


from app.stations.logos import station_slug


def _fallback_color(name: str) -> str:
    h = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    return _PALETTE[h % len(_PALETTE)]


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper() if name else "?"


def _find_logo_path(station: Dict) -> Optional[Path]:
    slug = station_slug(station.get("name", ""))
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico"):
        path = LOGO_DIR / f"{slug}{ext}"
        if path.exists():
            return path
    # legacy hash by url
    url = station.get("url", "")
    if url:
        h = hashlib.md5(url.encode()).hexdigest()[:12]
        for ext in (".png", ".jpg", ".jpeg"):
            path = LOGO_DIR / f"{h}{ext}"
            if path.exists():
                return path
    return None


def load_station_pixmap(station: Dict, size: int = 48, dimmed: bool = False) -> QPixmap:
    path = _find_logo_path(station)
    if path:
        pm = QPixmap(str(path))
        if not pm.isNull():
            scaled = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            canvas = QPixmap(size, size)
            canvas.fill(Qt.transparent)
            p = QPainter(canvas)
            x = (size - scaled.width()) // 2
            y = (size - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            p.end()
            if dimmed:
                faded = QPixmap(canvas)
                p2 = QPainter(faded)
                p2.fillRect(faded.rect(), QColor(255, 255, 255, 140))
                p2.end()
                return faded
            return canvas

    return _make_fallback(station.get("name", "?"), size, dimmed)


def _make_fallback(name: str, size: int, dimmed: bool) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    color = QColor(_fallback_color(name))
    if dimmed:
        color.setAlpha(160)
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.setPen(QColor("#FFFFFF"))
    font = ui_font(max(8, size // 4))
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, _initials(name))
    p.end()
    return pm
