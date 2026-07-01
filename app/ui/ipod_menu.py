"""Right panel — iPod Classic menu."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.ui.fonts import font_family, stylesheet
from app.ui.theme import (
    FONT_SIZE_SMALL,
    IPOD_BG,
    IPOD_HEADER_BOT,
    IPOD_HEADER_TOP,
    IPOD_LINE,
    IPOD_SELECT,
    IPOD_TEXT,
    IPOD_TEXT_SEL,
)

MENU_ITEMS = [
    "Teraz odtwarzane",
    "Ulubione stacje",
    "Gatunki (Pls/M3u)",
    "Historia (History)",
    "Ustawienia audio",
]


class IPodMenu(QWidget):
    item_activated = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {IPOD_BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("[ INTERNET RADIO ]")
        header.setAlignment(Qt.AlignCenter)
        header.setFixedHeight(26)
        mono = font_family()
        header.setStyleSheet(
            f"background: qlineargradient(y1:0,y2:1,stop:0 {IPOD_HEADER_TOP},stop:1 {IPOD_HEADER_BOT});"
            f"color: {IPOD_TEXT}; font-family: '{mono}'; font-size: {FONT_SIZE_SMALL}px;"
            f"border-bottom: 1px solid {IPOD_LINE};"
        )
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget {{ background: {IPOD_BG}; border: none; outline: none; }}"
            f"QListWidget::item {{ color: {IPOD_TEXT}; padding: 8px 6px;"
            f"border-bottom: 1px solid {IPOD_LINE}; font-family: '{mono}';"
            f"font-size: {FONT_SIZE_SMALL}px; }}"
            f"QListWidget::item:selected {{ background: {IPOD_SELECT}; color: {IPOD_TEXT_SEL}; }}"
        )
        self._list.setSpacing(0)
        for label in MENU_ITEMS:
            item = QListWidgetItem(label)
            self._list.addItem(item)
        self._list.setCurrentRow(0)
        self._list.itemClicked.connect(self._on_click)
        layout.addWidget(self._list)

    def _on_click(self, item: QListWidgetItem) -> None:
        self.item_activated.emit(item.text())

    def select_now_playing(self) -> None:
        self._list.setCurrentRow(0)
