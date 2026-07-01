"""Load SVG icons with configurable stroke/fill color."""

from __future__ import annotations

import re
from pathlib import Path

from PyQt5.QtCore import QByteArray, QSize, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


def _tint_svg(path: Path, color: str) -> QByteArray:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', text)
    text = re.sub(r'fill="(?!none)[^"]*"', f'fill="{color}"', text)
    return QByteArray(text.encode("utf-8"))


def load_icon(name: str, color: str, size: int = 20) -> QIcon:
    path = ICONS_DIR / name
    if not path.exists():
        return QIcon()
    data = _tint_svg(path, color)
    renderer = QSvgRenderer(data)
    render_px = max(size * 3, 48)
    pixmap = QPixmap(QSize(render_px, render_px))
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return QIcon(scaled)
