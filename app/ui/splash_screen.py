"""Black startup screen shown while station logos are loading."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.fonts import stylesheet
from app.ui.theme import FONT_SIZE_MED, FONT_SIZE_SMALL, SCREEN_H, SCREEN_W

_SPLASH_BG = "#000000"
_SPLASH_TITLE = "#FFFFFF"
_SPLASH_STATUS = "#CCCCCC"
_SPLASH_DETAIL = "#888888"


class SplashScreen(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(SCREEN_W, SCREEN_H)
        self.setStyleSheet(f"background: {_SPLASH_BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 0)
        root.addStretch(2)

        self._title = QLabel("Radio Pi")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(
            stylesheet(FONT_SIZE_MED + 4, _SPLASH_TITLE, bold=True)
        )
        root.addWidget(self._title)

        root.addSpacing(12)

        self._status = QLabel("Uruchamianie…")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(stylesheet(FONT_SIZE_MED, _SPLASH_STATUS))
        root.addWidget(self._status)

        root.addSpacing(8)

        self._detail = QLabel("")
        self._detail.setAlignment(Qt.AlignCenter)
        self._detail.setWordWrap(True)
        self._detail.setStyleSheet(stylesheet(FONT_SIZE_SMALL, _SPLASH_DETAIL))
        root.addWidget(self._detail)

        root.addStretch(3)

    def set_status(self, main: str, detail: str = "") -> None:
        self._title.setText("Radio Pi")
        self._status.setText(main or "Uruchamianie…")
        self._detail.setText(detail or "")
