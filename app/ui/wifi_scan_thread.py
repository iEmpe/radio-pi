"""Background WiFi scan for network overlay."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from app.network.nm_client import NetworkManagerClient, WifiNetwork


class WifiScanThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, nm: NetworkManagerClient) -> None:
        super().__init__()
        self._nm = nm

    def run(self) -> None:
        try:
            networks = self._nm.scan_wifi()
        except Exception:
            networks = []
        self.finished.emit(networks)
