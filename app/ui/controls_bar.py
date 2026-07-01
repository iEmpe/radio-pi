"""Bottom controls — play/pause, scrolling now-playing, close."""

from __future__ import annotations

from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QWidget

from app.ui.icons import load_icon
from app.ui.marquee_label import MarqueeLabel
from app.ui.theme import (
    BG,
    BORDER,
    BTN_BG,
    CONTROLS_H,
    FONT_SIZE_SMALL,
    TEXT,
)


class ControlsBar(QWidget):
    play_pause_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._playing = False
        self.setFixedHeight(CONTROLS_H)
        self.setStyleSheet(f"background: {BG}; border-top: 1px solid {BORDER};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)

        self._play_btn = QPushButton()
        self._play_btn.setFixedSize(36, 36)
        self._play_btn.setFlat(True)
        self._play_btn.setStyleSheet(
            f"QPushButton {{ background: {BTN_BG}; border: 1px solid {BORDER};"
            f"border-radius: 6px; }}"
            f"QPushButton:pressed {{ background: #D8D8E0; }}"
        )
        self._play_btn.clicked.connect(self.play_pause_clicked.emit)
        layout.addWidget(self._play_btn)

        self._marquee = MarqueeLabel()
        self._marquee.set_font("", FONT_SIZE_SMALL, TEXT)
        layout.addWidget(self._marquee, stretch=1)

        self._close_btn = QPushButton()
        self._close_btn.setFixedSize(36, 36)
        self._close_btn.setFlat(True)
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: {BTN_BG}; border: 1px solid {BORDER};"
            f"border-radius: 18px; }}"
            f"QPushButton:pressed {{ background: #FFD8D8; }}"
        )
        close_icon = load_icon("close.svg", TEXT, 16)
        self._close_btn.setIcon(close_icon)
        self._close_btn.setIconSize(QSize(16, 16))
        self._close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self._close_btn)

        self._update_play_icon()

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._update_play_icon()

    def set_now_playing(self, text: str) -> None:
        self._marquee.set_text(text)

    def set_track_info(self, primary: str, secondary: str = "") -> None:
        del secondary
        self.set_now_playing(primary if primary and primary != "—" else "")

    def set_metadata(self, text: str) -> None:
        self.set_now_playing(text)

    def _update_play_icon(self) -> None:
        name = "pause.svg" if self._playing else "play.svg"
        icon = load_icon(name, TEXT, 18)
        self._play_btn.setIcon(icon)
        self._play_btn.setIconSize(QSize(18, 18))
