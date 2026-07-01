"""EQ preset selector — pills above the spectrum visualizer."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt5.QtWidgets import QHBoxLayout, QWidget

from app.audio.eq_presets import DEFAULT_PRESET, PRESET_IDS, PRESET_LABELS
from app.ui.fonts import ui_font
from app.ui.theme import FONT_SIZE_TINY

_DNB_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("plain", "DRUM & BASS"),
    ("underline", "D&B"),
    ("plain", "D'n'B"),
    ("plain", "DRUMS"),
)

_HIPHOP_CANDIDATES = ("HIP-HOP", "HIPHOP")


class _PresetPill(QWidget):
    clicked = pyqtSignal()

    _PAD_X = 4

    def __init__(self, preset_id: str, parent=None) -> None:
        super().__init__(parent)
        self._preset_id = preset_id
        self._active = False
        self._label = PRESET_LABELS.get(preset_id, preset_id.upper())
        self._dnb_mode = "plain"
        self.setFixedHeight(22)
        self.setCursor(Qt.PointingHandCursor)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001, N802
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        super().resizeEvent(event)
        self._fit_label()

    def _fit_label(self) -> None:
        fm = QFontMetrics(self._pill_font())
        avail = max(1, self.width() - self._PAD_X * 2)

        if self._preset_id == "dnb":
            for mode, label in _DNB_CANDIDATES:
                if fm.horizontalAdvance(label) <= avail:
                    self._dnb_mode = mode
                    self._label = label
                    break
            else:
                self._dnb_mode = "plain"
                self._label = "DRUMS"
        elif self._preset_id == "hiphop":
            for label in _HIPHOP_CANDIDATES:
                if fm.horizontalAdvance(label) <= avail:
                    self._label = label
                    break
            else:
                self._label = "HIPHOP"
            self._dnb_mode = "plain"
        else:
            self._dnb_mode = "plain"
            self._label = PRESET_LABELS.get(self._preset_id, self._preset_id.upper())
        self.update()

    def _pill_font(self) -> QFont:
        return ui_font(FONT_SIZE_TINY)

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1)
        if self._active:
            p.setBrush(Qt.white)
            p.setPen(Qt.NoPen)
            text_color = QColor("#9B6DFF")
        else:
            p.setBrush(Qt.transparent)
            p.setPen(QPen(Qt.white, 1))
            text_color = QColor("#FFFFFF")

        p.drawRoundedRect(rect, 11, 11)

        font = self._pill_font()
        p.setFont(font)
        p.setPen(text_color)

        if self._preset_id == "dnb" and self._dnb_mode == "underline":
            self._paint_dnb_underline(p, font, text_color)
        else:
            p.drawText(self.rect(), Qt.AlignCenter, self._label)
        p.end()

    def _paint_dnb_underline(
        self, p: QPainter, font: QFont, color: QColor
    ) -> None:
        fm = QFontMetrics(font)
        d_w = fm.horizontalAdvance("D")
        amp_w = fm.horizontalAdvance("&")
        b_w = fm.horizontalAdvance("B")
        total = d_w + amp_w + b_w
        x = (self.width() - total) // 2
        baseline = (self.height() + fm.ascent() - fm.descent()) // 2

        p.setPen(color)
        p.drawText(x, baseline, "D")
        x += d_w
        p.drawText(x, baseline, "&")
        x += amp_w
        p.drawText(x, baseline, "B")

        underline_y = baseline + 1
        p.drawLine(x, underline_y, x + b_w, underline_y)


class EqPresetBar(QWidget):
    preset_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet("background: transparent;")

        self._active = DEFAULT_PRESET
        self._pills: dict[str, _PresetPill] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for pid in PRESET_IDS:
            pill = _PresetPill(pid)
            pill.clicked.connect(lambda p=pid: self._select(p))
            self._pills[pid] = pill
            layout.addWidget(pill, stretch=1)

        self._apply_styles()

    def set_active(self, preset_id: str) -> None:
        if preset_id in self._pills:
            self._active = preset_id
            self._apply_styles()

    def _select(self, preset_id: str) -> None:
        if preset_id == self._active:
            return
        self._active = preset_id
        self._apply_styles()
        self.preset_changed.emit(preset_id)

    def _apply_styles(self) -> None:
        for pid, pill in self._pills.items():
            pill.set_active(pid == self._active)
