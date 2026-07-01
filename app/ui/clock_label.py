"""Clock display (HH:MM:SS) with Impact and fixed character slots."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFontMetrics, QPainter
from PyQt5.QtWidgets import QSizePolicy, QWidget

from app.ui.fonts import clock_font
from app.ui.theme import CLOCK_TRACKING, FONT_SIZE_CLOCK, TEXT

_WORST_CASE = "88:88:88"


class ClockLabel(QWidget):
    """Renders HH:MM:SS with Impact and fixed per-character slots."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self._font = clock_font(FONT_SIZE_CLOCK)
        fm = QFontMetrics(self._font)
        advances = [fm.horizontalAdvance(ch) for ch in _WORST_CASE]
        tracking = CLOCK_TRACKING
        max_w = sum(advances) + tracking * max(0, len(_WORST_CASE) - 1)
        self.setFixedSize(max_w, FONT_SIZE_CLOCK + 6)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._text = "00:00:00"
        self._color = QColor(TEXT)
        self._char_x = self._slot_positions(fm, advances, tracking, max_w)

    @staticmethod
    def _slot_positions(fm: QFontMetrics, advances: list[int], tracking: int, box_w: int) -> list[int]:
        total_w = sum(advances) + tracking * max(0, len(_WORST_CASE) - 1)
        x = max(0, (box_w - total_w) // 2)
        positions: list[int] = []
        for i, advance in enumerate(advances):
            positions.append(x)
            x += advance + tracking
        return positions

    def tick_if_needed(self) -> None:
        text = datetime.now().strftime("%H:%M:%S")
        if text == self._text:
            return
        self._text = text
        self.update()

    def _draw_tracked(self, p: QPainter, text: str) -> None:
        fm = QFontMetrics(self._font)
        chars = list(text)
        baseline = (self.height() + fm.ascent() - fm.descent()) // 2 + 1
        for i, ch in enumerate(chars):
            if i < len(self._char_x):
                p.drawText(self._char_x[i], baseline, ch)

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        if not self._text:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(self._font)
        p.setPen(self._color)
        self._draw_tracked(p, self._text)
        p.end()
