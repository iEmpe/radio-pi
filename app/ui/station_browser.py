"""Compact station browser for right panel."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.ui.fonts import font_family, stylesheet
from app.ui.theme import FONT_SIZE_SMALL, IPOD_BG, IPOD_HEADER_TOP, IPOD_LINE, IPOD_SELECT, IPOD_TEXT, IPOD_TEXT_SEL

logger = logging.getLogger(__name__)
STATIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "stations.json"
HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"
RADIO_BROWSER = "https://de1.api.radio-browser.info/json"


class StationBrowser(QWidget):
    station_selected = pyqtSignal(dict)
    back_pressed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stations: List[Dict] = []
        self._index = 0
        self.setStyleSheet(f"background: {IPOD_BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        mono = font_family()
        self._header = QLabel("Stacje")
        self._header.setAlignment(Qt.AlignCenter)
        self._header.setFixedHeight(26)
        self._header.setStyleSheet(
            f"background: {IPOD_HEADER_TOP}; color: {IPOD_TEXT};"
            f"font-family: '{mono}'; font-size: {FONT_SIZE_SMALL}px;"
            f"border-bottom: 1px solid {IPOD_LINE};"
        )
        layout.addWidget(self._header)

        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget {{ background: {IPOD_BG}; border: none; }}"
            f"QListWidget::item {{ color: {IPOD_TEXT}; padding: 6px;"
            f"font-family: '{mono}'; font-size: {FONT_SIZE_SMALL}px;"
            f"border-bottom: 1px solid {IPOD_LINE}; }}"
            f"QListWidget::item:selected {{ background: {IPOD_SELECT}; color: {IPOD_TEXT_SEL}; }}"
        )
        self._list.itemClicked.connect(self._on_click)
        layout.addWidget(self._list)

        back = QPushButton("← Menu")
        back.setStyleSheet(
            f"background: {IPOD_BG}; color: {IPOD_TEXT}; border: none; padding: 4px;"
            f"font-family: '{mono}'; font-size: {FONT_SIZE_SMALL}px;"
        )
        back.clicked.connect(self.back_pressed.emit)
        layout.addWidget(back)

        self._load_stations()

    def _load_stations(self) -> None:
        if STATIONS_PATH.exists():
            with open(STATIONS_PATH, encoding="utf-8") as f:
                self._stations = json.load(f)
        self._rebuild()

    def _rebuild(self) -> None:
        self._list.clear()
        for i, st in enumerate(self._stations):
            item = QListWidgetItem(st.get("name", "?")[:28])
            item.setData(Qt.UserRole, i)
            self._list.addItem(item)

    def show_all(self, title: str = "Ulubione stacje") -> None:
        self._header.setText(title)
        self._load_stations()
        self.show()

    def show_history(self) -> None:
        self._header.setText("Historia")
        self._stations = []
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, encoding="utf-8") as f:
                self._stations = json.load(f)
        self._rebuild()
        self.show()

    def show_by_tag(self, tag: str) -> None:
        self._header.setText(f"Gatunek: {tag}")
        try:
            resp = requests.get(
                f"{RADIO_BROWSER}/stations/bytag/{tag}",
                params={"limit": 20, "order": "clickcount", "reverse": "true"},
                timeout=12,
                headers={"User-Agent": "radio-pi/1.0"},
            )
            resp.raise_for_status()
            self._stations = [
                {
                    "name": s.get("name", "?"),
                    "url": s.get("url", ""),
                    "country": s.get("country", ""),
                    "tags": s.get("tags", ""),
                }
                for s in resp.json()
                if s.get("lastcheckok") == 1 and s.get("url")
            ]
        except requests.RequestException as exc:
            logger.error("Tag search failed: %s", exc)
            self._stations = []
        self._rebuild()
        self.show()

    def _on_click(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.UserRole)
        if idx is not None and 0 <= idx < len(self._stations):
            self._index = idx
            self.station_selected.emit(self._stations[idx])

    def current_index(self) -> int:
        return self._index

    def station_count(self) -> int:
        return len(self._stations)

    def select_next(self) -> Optional[Dict]:
        if not self._stations:
            return None
        self._index = (self._index + 1) % len(self._stations)
        self._list.setCurrentRow(self._index)
        return self._stations[self._index]

    def select_prev(self) -> Optional[Dict]:
        if not self._stations:
            return None
        self._index = (self._index - 1) % len(self._stations)
        self._list.setCurrentRow(self._index)
        return self._stations[self._index]

    def current_station(self) -> Optional[Dict]:
        if self._stations:
            return self._stations[self._index]
        return None

    @staticmethod
    def append_history(station: dict) -> None:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        hist: List[dict] = []
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, encoding="utf-8") as f:
                hist = json.load(f)
        url = station.get("url", "")
        hist = [h for h in hist if h.get("url") != url]
        hist.insert(0, station)
        hist = hist[:30]
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)
