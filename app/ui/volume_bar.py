"""Purple volume slider bar with speaker icons."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from app.ui.icons import load_icon
from app.ui.theme import GRAD_BOT, GRAD_TOP, VOLUME_H


class _ClickableIcon(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001, N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class VolumeBar(QWidget):
    volume_changed = pyqtSignal(int)
    mute_changed = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(VOLUME_H)
        self.setStyleSheet("background: transparent;")

        self._muted = False
        self._saved_volume = 80

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(8)

        self._vol_low = QLabel()
        self._vol_low.setFixedSize(18, 18)
        layout.addWidget(self._vol_low)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(80)
        self._slider.setStyleSheet(
            "QSlider::groove:horizontal {"
            "  height: 14px; border-radius: 7px;"
            "  background: #1A1030;"
            "  border: 1px solid #3A2860;"
            "}"
            "QSlider::sub-page:horizontal {"
            "  height: 14px; border-radius: 7px;"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #5CC8FF, stop:1 #9BE8FF);"
            "}"
            "QSlider::add-page:horizontal {"
            "  height: 14px; border-radius: 7px;"
            "  background: #1A1030;"
            "}"
            "QSlider::handle:horizontal {"
            "  width: 14px; height: 18px; margin: -3px 0;"
            "  border-radius: 4px;"
            "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "    stop:0 #F0F0F0, stop:1 #B8B8C0);"
            "  border: 1px solid #888;"
            "}"
        )
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider, stretch=1)

        self._vol_high = _ClickableIcon()
        self._vol_high.setFixedSize(22, 22)
        self._vol_high.setCursor(Qt.PointingHandCursor)
        self._vol_high.setToolTip("Wycisz / odcisz")
        self._vol_high.clicked.connect(self._toggle_mute)
        layout.addWidget(self._vol_high)

        self._update_icons()

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(GRAD_TOP))
        grad.setColorAt(1, QColor(GRAD_BOT))
        p.fillRect(self.rect(), grad)
        super().paintEvent(event)

    def _on_slider_changed(self, value: int) -> None:
        if self._muted:
            if value == 0:
                return
            self._muted = False
            self.mute_changed.emit(False)

        if value > 0:
            self._saved_volume = value
        self._update_icons()
        self.volume_changed.emit(value)

    def _toggle_mute(self) -> None:
        if self._muted:
            self._muted = False
            self._set_slider_display(self._saved_volume)
            self._update_icons()
            self.mute_changed.emit(False)
            self.volume_changed.emit(self._saved_volume)
            return

        current = self._slider.value()
        if current > 0:
            self._saved_volume = current
        elif self._saved_volume <= 0:
            self._saved_volume = 80

        self._muted = True
        self._set_slider_display(0)
        self._update_icons()
        self.mute_changed.emit(True)

    def _set_slider_display(self, level: int) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(level)
        self._slider.blockSignals(False)

    def set_volume(self, level: int) -> None:
        if self._muted:
            self._saved_volume = max(0, min(100, level))
            return
        self._set_slider_display(level)
        if level > 0:
            self._saved_volume = level

    def set_muted(self, muted: bool) -> None:
        if muted == self._muted:
            return
        if muted:
            self._toggle_mute()
        elif self._muted:
            self._toggle_mute()

    def is_muted(self) -> bool:
        return self._muted

    def volume(self) -> int:
        return self._saved_volume if self._muted else self._slider.value()

    def _update_icons(self) -> None:
        low = load_icon("vol_low.svg", "#FFFFFF", 16)
        self._vol_low.setPixmap(low.pixmap(16, 16))

        if self._muted:
            icon_name = "vol_mute.svg"
            color = "#FF8A8A"
        else:
            icon_name = "vol_high.svg"
            color = "#FFFFFF"
        high = load_icon(icon_name, color, 18)
        self._vol_high.setPixmap(high.pixmap(18, 18))
