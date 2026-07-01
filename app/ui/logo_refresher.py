"""Background worker — refresh cached logos for all stations."""

from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import QThread, pyqtSignal

from app.stations.logos import download_station_logo


class LogoRefresher(QThread):
    logo_ready = pyqtSignal(str)
    finished_all = pyqtSignal(int, int)

    def __init__(self, stations: List[Dict], *, force: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._stations = list(stations)
        self._force = force

    def run(self) -> None:
        ok = 0
        for st in self._stations:
            name = st.get("name", "")
            if download_station_logo(st, force=self._force):
                ok += 1
                self.logo_ready.emit(name)
        self.finished_all.emit(ok, len(self._stations))
