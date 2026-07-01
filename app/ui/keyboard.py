"""On-screen keyboard for WiFi password entry."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from app.ui.fonts import font_family, stylesheet
from app.ui.theme import FONT_SIZE_SMALL, IPOD_BG, IPOD_LINE, IPOD_SELECT, IPOD_TEXT

ROWS = [
    list("1234567890"),
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]


class OnScreenKeyboard(QWidget):
    key_pressed = pyqtSignal(str)
    backspace_pressed = pyqtSignal()
    done_pressed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {IPOD_BG};")
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        for row_keys in ROWS:
            row = QHBoxLayout()
            for key in row_keys:
                row.addWidget(self._key(key))
            layout.addLayout(row)
        bottom = QHBoxLayout()
        bottom.addWidget(self._key(" ", wide=True))
        bs = self._key("⌫")
        bs.clicked.connect(self.backspace_pressed.emit)
        bottom.addWidget(bs)
        ok = self._key("OK", accent=True)
        ok.clicked.connect(self.done_pressed.emit)
        bottom.addWidget(ok)
        layout.addLayout(bottom)

    def _key(self, label: str, wide: bool = False, accent: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(28)
        if wide:
            btn.setMinimumWidth(80)
        else:
            btn.setFixedWidth(26)
        bg = IPOD_SELECT if accent else IPOD_BG
        fg = "white" if accent else IPOD_TEXT
        mono = font_family()
        btn.setStyleSheet(
            f"background: {bg}; color: {fg}; border: 1px solid {IPOD_LINE};"
            f"font-family: '{mono}'; font-size: {FONT_SIZE_SMALL}px;"
        )
        if not accent and label not in ("⌫", "OK"):
            btn.clicked.connect(lambda _=False, k=label: self.key_pressed.emit(k))
        return btn
