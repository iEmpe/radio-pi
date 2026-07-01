"""Bottom bar — volume slider and track counter."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from app.ui.theme import BAR_BOT, BAR_TEXT, BAR_TOP, BOTTOM_H, FONT_MONO, NET_ACTIVE


class BottomBar(QWidget):
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(BOTTOM_H)
        self.setStyleSheet(
            f"background: qlineargradient(y1:0,y2:1,stop:0 {BAR_TOP},stop:1 {BAR_BOT});"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)

        vol_lbl = QLabel("VOL:")
        vol_lbl.setStyleSheet(f"color: {BAR_TEXT}; font-family: {FONT_MONO}; font-size: 9px;")
        layout.addWidget(vol_lbl)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(80)
        self._slider.setFixedWidth(140)
        self._slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ height: 8px; background: #1A1A1A; border: 1px solid #555; }}"
            f"QSlider::sub-page:horizontal {{ background: {NET_ACTIVE}; }}"
            f"QSlider::handle:horizontal {{ width: 10px; background: #CCC; margin: -3px 0; }}"
        )
        self._slider.valueChanged.connect(self.volume_changed.emit)
        layout.addWidget(self._slider)

        layout.addStretch()

        self._track = QLabel("TRACK: 0 / 0")
        self._track.setStyleSheet(f"color: {NET_ACTIVE}; font-family: {FONT_MONO}; font-size: 9px;")
        layout.addWidget(self._track)

    def set_volume(self, level: int) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(level)
        self._slider.blockSignals(False)

    def set_track(self, index: int, total: int) -> None:
        self._track.setText(f"TRACK: {index} / {total}")

    def volume(self) -> int:
        return self._slider.value()
