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


class BluetoothActionThread(QThread):
    """Scan, refresh, power-toggle, or connect without blocking the UI."""

    result = pyqtSignal(object)

    def __init__(
        self,
        nm: NetworkManagerClient,
        action: str,
        mac: str = "",
        name: str = "",
    ) -> None:
        super().__init__()
        self._nm = nm
        self._action = action
        self._mac = mac
        self._name = name

    def run(self) -> None:
        try:
            if self._action == "power":
                self._nm.set_bluetooth_enabled(not self._nm.bluetooth_enabled())
            elif self._action == "scan":
                if not self._nm.bluetooth_enabled():
                    self._nm.set_bluetooth_enabled(True)
                self._nm.scan_bluetooth()
            elif self._action == "connect":
                ok = self._nm.connect_bluetooth(self._mac)
                powered = self._nm.bluetooth_enabled()
                devices = self._nm.list_bluetooth_devices() if powered else []
                self.result.emit({
                    "action": self._action,
                    "ok": ok,
                    "powered": powered,
                    "devices": devices,
                    "name": self._name,
                    "error": "" if ok else f"Nie udało się połączyć: {self._name}",
                })
                return
            powered = self._nm.bluetooth_enabled()
            devices = self._nm.list_bluetooth_devices() if powered else []
            self.result.emit({
                "action": self._action,
                "ok": True,
                "powered": powered,
                "devices": devices,
                "name": self._name,
                "error": "",
            })
        except Exception as exc:
            self.result.emit({
                "action": self._action,
                "ok": False,
                "powered": False,
                "devices": [],
                "name": self._name,
                "error": str(exc) or "Błąd Bluetooth",
            })


class WifiConnectThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, nm: NetworkManagerClient, ssid: str, password: str) -> None:
        super().__init__()
        self._nm = nm
        self._ssid = ssid
        self._password = password

    def run(self) -> None:
        try:
            ok, message = self._nm.connect_wifi(self._ssid, self._password)
        except Exception as exc:
            ok, message = False, str(exc) or "Nie udało się połączyć"
        self.result.emit(ok, message)
