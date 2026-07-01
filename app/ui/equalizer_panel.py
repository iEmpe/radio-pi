"""Gradient equalizer with EQ preset bar and spectrum visualizer."""

from __future__ import annotations

import math

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter
from PyQt5.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.audio.spectrum import BANDS as BAR_COUNT
from app.audio.spectrum import FREQ_LABELS_HZ, FREQ_MAX_HZ, FREQ_MIN_HZ
from app.ui.eq_preset_bar import EqPresetBar
from app.ui.fonts import ui_font
from app.ui.theme import FONT_SIZE_TINY, GRAD_BOT, GRAD_TOP

MARGIN_X = 10
GAP = 3
LABEL_H = 12
TICK_H = 3


def _format_hz(hz: int) -> str:
    if hz >= 1000:
        k = hz / 1000
        return f"{int(k)}k" if k == int(k) else f"{k:g}k"
    return str(hz)


def _hz_to_x(hz: float, usable: int) -> float:
    log_min = math.log10(FREQ_MIN_HZ)
    log_max = math.log10(FREQ_MAX_HZ)
    t = (math.log10(hz) - log_min) / (log_max - log_min)
    return MARGIN_X + t * usable


class _SpectrumCanvas(QWidget):
    """Spectrum bars with logarithmic frequency axis."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._levels = [0.08] * BAR_COUNT
        self._active = False
        self._label_font = ui_font(FONT_SIZE_TINY)

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = [0.06] * BAR_COUNT
        self.update()

    def set_levels(self, levels: list[float]) -> None:
        if not self._active:
            return
        n = min(len(levels), BAR_COUNT)
        for i in range(n):
            self._levels[i] = max(0.05, min(0.92, levels[i]))
        self.update()

    def _draw_bars(self, p: QPainter, usable: int, bars_bottom: int) -> None:
        total_gaps = GAP * (BAR_COUNT - 1)
        base_w = max(1, (usable - total_gaps) // BAR_COUNT)
        extra = (usable - total_gaps) - base_w * BAR_COUNT
        h_max = bars_bottom - 2

        x = MARGIN_X
        for i, level in enumerate(self._levels):
            bar_w = base_w + (1 if i < extra else 0)
            bar_h = max(2, int(h_max * level))
            y = bars_bottom - bar_h
            alpha = int(65 + 60 * level)
            p.fillRect(int(x), y, bar_w, bar_h, QColor(255, 255, 255, alpha))
            x += bar_w + GAP

    def _draw_freq_axis(self, p: QPainter, usable: int, bars_bottom: int, h: int) -> None:
        p.setFont(self._label_font)
        p.setPen(QColor(255, 255, 255, 140))
        fm = QFontMetrics(self._label_font)
        baseline = h - 2

        for hz in FREQ_LABELS_HZ:
            x_center = _hz_to_x(hz, usable)
            tick_x = int(x_center)
            p.drawLine(tick_x, bars_bottom + 1, tick_x, bars_bottom + TICK_H + 1)

            label = _format_hz(hz)
            text_x = int(x_center - fm.horizontalAdvance(label) / 2)
            text_x = max(MARGIN_X, min(text_x, self.width() - MARGIN_X - fm.horizontalAdvance(label)))
            p.drawText(text_x, baseline, label)

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w, h = self.width(), self.height()
        usable = w - MARGIN_X * 2
        bars_bottom = h - LABEL_H - 1

        self._draw_bars(p, usable, bars_bottom)
        self._draw_freq_axis(p, usable, bars_bottom, h)
        p.end()


class EqualizerPanel(QWidget):
    preset_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 4)
        root.setSpacing(4)

        self._presets = EqPresetBar()
        self._presets.preset_changed.connect(self.preset_changed.emit)
        root.addWidget(self._presets)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.25);")
        root.addWidget(sep)

        self._canvas = _SpectrumCanvas()
        root.addWidget(self._canvas, stretch=1)

    def set_active_preset(self, preset_id: str) -> None:
        self._presets.set_active(preset_id)

    def set_active(self, active: bool) -> None:
        self._canvas.set_active(active)

    def set_levels(self, levels: list[float]) -> None:
        self._canvas.set_levels(levels)

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(GRAD_TOP))
        grad.setColorAt(1, QColor(GRAD_BOT))
        p.fillRect(self.rect(), grad)
        p.end()
        super().paintEvent(event)
