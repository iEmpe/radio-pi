"""Audio settings panel."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.fonts import font_family, stylesheet
from app.ui.theme import FONT_SIZE_SMALL, IPOD_BG, IPOD_HEADER_TOP, IPOD_LINE, IPOD_TEXT


class AudioSettings(QWidget):
    back_pressed = pyqtSignal()
    mute_toggled = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {IPOD_BG};")
        layout = QVBoxLayout(self)

        hdr = QLabel("Ustawienia audio")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setFixedHeight(26)
        mono = font_family()
        hdr.setStyleSheet(
            f"background: {IPOD_HEADER_TOP}; font-family: '{mono}';"
            f"font-size: {FONT_SIZE_SMALL}px; border-bottom: 1px solid {IPOD_LINE};"
        )
        layout.addWidget(hdr)

        self._mute_btn = QPushButton("Wycisz / Odcisz")
        self._mute_btn.clicked.connect(self.mute_toggled.emit)
        layout.addWidget(self._mute_btn)

        note = QLabel("Głośność: suwak na dole ekranu.\nSieć: Wi-Fi / ETH u góry.")
        note.setStyleSheet(stylesheet(FONT_SIZE_SMALL, IPOD_TEXT))
        layout.addWidget(note)
        layout.addStretch()

        back = QPushButton("← Menu")
        back.clicked.connect(self.back_pressed.emit)
        layout.addWidget(back)

    def set_muted(self, muted: bool) -> None:
        self._mute_btn.setText("Odcisz" if muted else "Wycisz")
