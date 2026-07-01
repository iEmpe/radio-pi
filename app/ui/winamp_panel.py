"""Left panel — Winamp-style station info, spectrum, metadata."""

from __future__ import annotations

import random
from datetime import timedelta

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.theme import (
    FONT_MONO,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    WINAMP_BG,
    WINAMP_BORDER,
    WINAMP_GREEN,
    WINAMP_ORANGE,
    WINAMP_YELLOW,
)


class SpectrumWidget(QWidget):
    """14-bar spectrum analyzer (decorative for live stream)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(72)
        self._levels = [4] * 14
        self._active = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self._timer.start(120)
        else:
            self._timer.stop()
            self._levels = [2] * 14
            self.update()

    def _tick(self) -> None:
        self._levels = [
            max(1, min(16, v + random.randint(-3, 3))) for v in self._levels
        ]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(WINAMP_BG))
        bar_w = max(4, (self.width() - 15) // 14)
        gap = 2
        x = 4
        h_max = self.height() - 8
        for i, level in enumerate(self._levels):
            bar_h = int(h_max * level / 16)
            y = self.height() - 4 - bar_h
            ratio = level / 16.0
            if ratio > 0.75:
                color = QColor(WINAMP_ORANGE)
            elif ratio > 0.45:
                color = QColor(WINAMP_YELLOW)
            else:
                color = QColor(WINAMP_GREEN)
            p.fillRect(x, y, bar_w, bar_h, color)
            x += bar_w + gap


class WinampPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {WINAMP_BG};")
        self._listen_sec = 0
        self._playing = False

        mono = f"font-family: {FONT_MONO}; color: {WINAMP_GREEN};"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 4, 4)
        layout.setSpacing(2)

        self._station = QLabel("STATION: ---")
        self._station.setStyleSheet(f"{mono} font-size: {FONT_SIZE_SMALL}px; font-weight: bold;")
        layout.addWidget(self._station)

        self._time = QLabel("TIME:  00:00")
        self._time.setStyleSheet(f"{mono} font-size: {FONT_SIZE_TINY}px;")
        layout.addWidget(self._time)

        qual = QLabel("[ 128 kbps ] [ 44.1 kHz ]")
        qual.setStyleSheet(
            f"{mono} font-size: 8px; color: {WINAMP_GREEN};"
            f"border: 1px solid {WINAMP_BORDER}; padding: 1px;"
        )
        self._qual = qual
        layout.addWidget(qual)

        self._spectrum = SpectrumWidget()
        layout.addWidget(self._spectrum, stretch=1)

        self._track = QLabel("—")
        self._track.setAlignment(Qt.AlignCenter)
        self._track.setWordWrap(True)
        self._track.setStyleSheet(
            f"font-family: {FONT_MONO}; color: {WINAMP_ORANGE}; font-size: 9px;"
            f"border: 1px solid {WINAMP_BORDER}; padding: 3px; background: #0A0A0A;"
        )
        self._track.setMinimumHeight(28)
        layout.addWidget(self._track)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_time)

    def set_station(self, name: str) -> None:
        display = name.upper()[:22]
        self._station.setText(f"STATION: {display}")

    def set_metadata(self, title: str) -> None:
        text = title if title else "—"
        if len(text) > 32:
            text = text[:30] + "…"
        self._track.setText(text)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._spectrum.set_active(playing)
        if playing:
            self._timer.start(1000)
        else:
            self._timer.stop()

    def reset_timer(self) -> None:
        self._listen_sec = 0
        self._time.setText("TIME:  00:00")

    def _tick_time(self) -> None:
        if not self._playing:
            return
        self._listen_sec += 1
        td = timedelta(seconds=self._listen_sec)
        m, s = divmod(int(td.total_seconds()), 60)
        self._time.setText(f"TIME:  {m:02d}:{s:02d}")
