"""Station list menu with search via Radio-Browser."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import ACCENT, BG, BORDER, BORDER_RADIUS, TEXT, TEXT_DIM

logger = logging.getLogger(__name__)
STATIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "stations.json"
RADIO_BROWSER = "https://de1.api.radio-browser.info/json"


class StationList(QWidget):
    station_selected = pyqtSignal(dict)
    stations_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stations: List[Dict] = []
        self._index = 0

        self.setStyleSheet(f"background: {BG}; border: 1px solid {BORDER};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        header = QLabel("Stacje")
        header.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setStyleSheet(
            f"background: #FFFFFF; color: {TEXT}; border: 1px solid {BORDER};"
            f"border-radius: {BORDER_RADIUS}px;"
        )
        self._list.itemClicked.connect(self._on_list_click)
        layout.addWidget(self._list, stretch=1)

        tools = QHBoxLayout()
        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(36, 36)
        prev_btn.clicked.connect(self._prev)
        tools.addWidget(prev_btn)
        self._counter = QLabel("1 / 1")
        self._counter.setAlignment(Qt.AlignCenter)
        self._counter.setStyleSheet(f"color: {TEXT_DIM};")
        tools.addWidget(self._counter, stretch=1)
        next_btn = QPushButton("▶")
        next_btn.setFixedSize(36, 36)
        next_btn.clicked.connect(self._next)
        tools.addWidget(next_btn)
        layout.addLayout(tools)

        search_btn = QPushButton("Szukaj stacji")
        search_btn.setStyleSheet(
            f"background: {ACCENT}; color: #FFFFFF; border-radius: {BORDER_RADIUS}px;"
            f"padding: 6px; border: none;"
        )
        search_btn.clicked.connect(self._search_dialog)
        layout.addWidget(search_btn)

        self._load_stations()

    def _load_stations(self) -> None:
        if STATIONS_PATH.exists():
            with open(STATIONS_PATH, encoding="utf-8") as f:
                self._stations = json.load(f)
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        self._list.clear()
        for i, st in enumerate(self._stations):
            country = st.get("country", "")[:2].upper()
            item = QListWidgetItem(f"{st['name']}  [{country}]")
            item.setData(Qt.UserRole, i)
            self._list.addItem(item)
        self._index = min(self._index, max(0, len(self._stations) - 1))
        self._update_counter()
        if self._stations:
            self._list.setCurrentRow(self._index)

    def _update_counter(self) -> None:
        if not self._stations:
            self._counter.setText("0 / 0")
            return
        self._counter.setText(f"{self._index + 1} / {len(self._stations)}")

    def _prev(self) -> None:
        if self._stations:
            self._index = (self._index - 1) % len(self._stations)
            self._list.setCurrentRow(self._index)
            self._update_counter()

    def _next(self) -> None:
        if self._stations:
            self._index = (self._index + 1) % len(self._stations)
            self._list.setCurrentRow(self._index)
            self._update_counter()

    def _on_list_click(self, item: QListWidgetItem) -> None:
        self._index = item.data(Qt.UserRole)
        self._update_counter()
        self.station_selected.emit(self._stations[self._index])

    def current_station(self) -> Optional[Dict]:
        if self._stations:
            return self._stations[self._index]
        return None

    def select_next(self) -> Optional[Dict]:
        self._next()
        return self.current_station()

    def select_prev(self) -> Optional[Dict]:
        self._prev()
        return self.current_station()

    def _search_dialog(self) -> None:
        from PyQt5.QtWidgets import QInputDialog
        query, ok = QInputDialog.getText(self, "Szukaj stacji", "Nazwa stacji:")
        if ok and query.strip():
            self._search_radio_browser(query.strip())

    def _search_radio_browser(self, query: str) -> None:
        try:
            resp = requests.get(
                f"{RADIO_BROWSER}/stations/search",
                params={"name": query, "limit": 10, "order": "clickcount", "reverse": "true"},
                timeout=10,
                headers={"User-Agent": "radio-pi/1.0"},
            )
            resp.raise_for_status()
            results = resp.json()
        except requests.RequestException as exc:
            logger.error("Radio-Browser search failed: %s", exc)
            return

        for st in results:
            if st.get("lastcheckok") != 1:
                continue
            entry = {
                "name": st.get("name", "Unknown"),
                "url": st.get("url", ""),
                "country": st.get("country", ""),
                "tags": st.get("tags", ""),
                "favicon_url": st.get("favicon", ""),
            }
            if entry["url"] and not any(s["url"] == entry["url"] for s in self._stations):
                self._stations.append(entry)

        self._save_stations()
        self._rebuild_list()
        self.stations_changed.emit()

    def _save_stations(self) -> None:
        STATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(self._stations, f, indent=2, ensure_ascii=False)

    def stations(self) -> List[Dict]:
        return list(self._stations)
