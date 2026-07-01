"""Horizontal station carousel with logos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics, QIcon
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.fonts import stylesheet, ui_font
from app.ui.station_logos import load_station_pixmap
from app.ui.theme import (
    ACCENT,
    BG,
    BTN_BG,
    BORDER,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    STATION_ROW_H,
    TEXT,
    TEXT_DIM,
    TEXT_MUTED,
)

STATIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "stations.json"
VISIBLE = 5
LOGO_SIZE = 46


class _StationDot(QPushButton):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(LOGO_SIZE + 4, LOGO_SIZE + 4)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(LOGO_SIZE, LOGO_SIZE))


class StationStrip(QWidget):
    station_changed = pyqtSignal(dict)
    index_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stations: List[Dict] = []
        self._index = 0
        self.setFixedHeight(STATION_ROW_H)
        self.setStyleSheet(f"background: {BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 2, 6, 0)
        root.setSpacing(0)

        row = QHBoxLayout()
        row.setSpacing(4)

        self._prev = self._nav_btn("‹")
        self._prev.clicked.connect(self.prev_station)
        row.addWidget(self._prev)

        self._dots: List[_StationDot] = []
        dots_box = QHBoxLayout()
        dots_box.setSpacing(6)
        dots_box.setAlignment(Qt.AlignCenter)
        for _ in range(VISIBLE):
            dot = _StationDot()
            dot.clicked.connect(self._on_dot_clicked)
            self._dots.append(dot)
            dots_box.addWidget(dot)
        row.addLayout(dots_box, stretch=1)

        self._next = self._nav_btn("›")
        self._next.clicked.connect(self.next_station)
        row.addWidget(self._next)

        root.addLayout(row)

        self._raw_name = "—"
        self._name = QLabel("—")
        self._name.setAlignment(Qt.AlignCenter)
        self._name.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        root.addWidget(self._name)

        self._raw_genre = ""
        self._genre = QLabel("")
        self._genre.setAlignment(Qt.AlignCenter)
        self._genre.setStyleSheet(stylesheet(FONT_SIZE_TINY, TEXT_MUTED))
        root.addWidget(self._genre)

        self.load_stations()

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        super().resizeEvent(event)
        self._update_name_elide()
        self._update_genre_elide()

    def _update_name_elide(self) -> None:
        fm = QFontMetrics(ui_font(FONT_SIZE_SMALL))
        self._name.setText(
            fm.elidedText(self._raw_name, Qt.ElideMiddle, max(48, self.width() - 16))
        )

    def _update_genre_elide(self) -> None:
        if not self._raw_genre:
            return
        fm = QFontMetrics(ui_font(FONT_SIZE_TINY))
        self._genre.setText(
            fm.elidedText(self._raw_genre, Qt.ElideRight, max(48, self.width() - 16))
        )
        self._genre.setToolTip(self._raw_genre)

    @staticmethod
    def _nav_btn(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        btn.setStyleSheet(
            f"QPushButton {{ background: {BTN_BG}; border: 1px solid {BORDER};"
            f"border-radius: 16px; color: {TEXT_DIM}; font-size: 18px; }}"
            f"QPushButton:pressed {{ background: #D8D8E0; }}"
        )
        return btn

    def load_stations(self) -> None:
        if STATIONS_PATH.exists():
            with open(STATIONS_PATH, encoding="utf-8") as f:
                self._stations = json.load(f)
        if self._index >= len(self._stations):
            self._index = max(0, len(self._stations) - 1)
        self._refresh()

    def station_count(self) -> int:
        return len(self._stations)

    def current_index(self) -> int:
        return self._index

    def current_station(self) -> Optional[Dict]:
        if self._stations:
            return self._stations[self._index]
        return None

    def set_index(self, index: int) -> None:
        if not self._stations:
            return
        self._index = index % len(self._stations)
        self._refresh()

    def select_by_url(self, url: str) -> bool:
        if not url:
            return False
        for i, st in enumerate(self._stations):
            if st.get("url") == url:
                self._index = i
                self._refresh()
                return True
        return False

    def prev_station(self) -> None:
        if not self._stations:
            return
        self._index = (self._index - 1) % len(self._stations)
        self._refresh()
        self.index_changed.emit(self._index)
        self.station_changed.emit(self._stations[self._index])

    def next_station(self) -> None:
        if not self._stations:
            return
        self._index = (self._index + 1) % len(self._stations)
        self._refresh()
        self.index_changed.emit(self._index)
        self.station_changed.emit(self._stations[self._index])

    def _on_dot_clicked(self) -> None:
        sender = self.sender()
        if sender not in self._dots:
            return
        slot = self._dots.index(sender)
        center = VISIBLE // 2
        offset = slot - center
        if not self._stations:
            return
        new_idx = (self._index + offset) % len(self._stations)
        if new_idx != self._index:
            self._index = new_idx
            self._refresh()
            self.index_changed.emit(self._index)
            self.station_changed.emit(self._stations[self._index])

    @staticmethod
    def genre_from_config(st: Dict) -> str:
        tags = (st.get("tags") or "").strip()
        if tags:
            return tags.split(",")[0].strip().title()
        return ""

    def set_genre(self, genre: str) -> None:
        self._raw_genre = genre.strip().upper()
        if self._raw_genre:
            self._genre.show()
            self._update_genre_elide()
        else:
            self._genre.setToolTip("")
            self._genre.hide()

    def _refresh(self) -> None:
        n = len(self._stations)
        center = VISIBLE // 2
        for i, dot in enumerate(self._dots):
            offset = i - center
            if n == 0:
                dot.setIcon(Qt.NoIcon)
                dot.setEnabled(False)
                dot.setStyleSheet(self._dot_style(False))
                continue
            idx = (self._index + offset) % n
            st = self._stations[idx]
            is_center = offset == 0
            dimmed = not is_center
            pm = load_station_pixmap(st, LOGO_SIZE, dimmed=dimmed)
            dot.setIcon(QIcon(pm))
            dot.setEnabled(True)
            dot.setStyleSheet(self._dot_style(is_center))

        if n:
            st = self._stations[self._index]
            self._raw_name = st.get("name", "—").upper()
            self._update_name_elide()
            self.set_genre(self.genre_from_config(st))
        else:
            self._raw_name = "BRAK STACJI"
            self._update_name_elide()
            self.set_genre("")

        self._prev.setEnabled(n > 1)
        self._next.setEnabled(n > 1)

    @staticmethod
    def _dot_style(center: bool) -> str:
        if center:
            return (
                f"QPushButton {{ background: {BG}; border: 2px solid {ACCENT};"
                f"border-radius: {LOGO_SIZE // 2 + 4}px; padding: 0; }}"
                f"QPushButton:pressed {{ background: #EEE8FF; }}"
            )
        return (
            f"QPushButton {{ background: {BG}; border: 1px solid {BORDER};"
            f"border-radius: {LOGO_SIZE // 2 + 4}px; padding: 0; opacity: 0.85; }}"
            f"QPushButton:pressed {{ background: #F0F0F4; }}"
        )
