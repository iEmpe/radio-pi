"""NetworkManager wrapper via nmcli with D-Bus fallback."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

FORCE_WIFI_BAND = "bg"  # used only when explicitly limiting to 2.4 GHz
HOTSPOT_NAME = "RadioPi-Setup"
HOTSPOT_SSID = "RadioPi-Setup"
HOTSPOT_CHANNEL = 6


@dataclass
class WifiNetwork:
    ssid: str
    signal: int
    secured: bool
    channel: int = 0
    freq_mhz: int = 0
    in_use: bool = False

    @property
    def band_label(self) -> str:
        if self.freq_mhz >= 5000:
            return "5 GHz"
        if self.freq_mhz > 0:
            return "2,4 GHz"
        return ""


@dataclass
class ConnectionInfo:
    connected: bool
    ip: str = ""
    gateway: str = ""
    device: str = ""


@dataclass
class BluetoothDevice:
    mac: str
    name: str
    connected: bool = False
    paired: bool = False


class NetworkManagerClient:
    """Thin wrapper around nmcli for WiFi/Ethernet management."""

    def __init__(self) -> None:
        self._use_nmcli = self._check_nmcli()

    @staticmethod
    def _check_nmcli() -> bool:
        try:
            subprocess.run(
                ["nmcli", "--version"],
                check=True,
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.warning("nmcli not available")
            return False

    def _run(self, args: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["nmcli"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def scan_wifi(self) -> List[WifiNetwork]:
        if not self._use_nmcli:
            return []
        self._run(["dev", "wifi", "rescan"], timeout=15)
        result = self._run([
            "--escape", "no", "-t",
            "-f", "IN-USE,SSID,SIGNAL,SECURITY,CHAN,FREQ",
            "dev", "wifi", "list",
        ])
        networks: List[WifiNetwork] = []
        seen: set[tuple[str, int]] = set()
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) < 6:
                continue
            in_use = parts[0].strip() in ("*", "yes", "tak")
            ssid = parts[1].strip()
            if not ssid:
                continue
            try:
                signal = int(parts[2]) if parts[2] else 0
            except ValueError:
                signal = 0
            secured = parts[3] not in ("", "--")
            try:
                channel = int(parts[4]) if parts[4] else 0
            except ValueError:
                channel = 0
            freq_mhz = self._parse_freq_mhz(parts[5])
            key = (ssid, freq_mhz)
            if key in seen:
                continue
            seen.add(key)
            networks.append(
                WifiNetwork(
                    ssid=ssid,
                    signal=signal,
                    secured=secured,
                    channel=channel,
                    freq_mhz=freq_mhz,
                    in_use=in_use,
                )
            )
        networks.sort(key=lambda n: (not n.in_use, -n.signal, n.ssid.lower()))
        return networks

    @staticmethod
    def _parse_freq_mhz(raw: str) -> int:
        digits = "".join(ch for ch in raw if ch.isdigit())
        try:
            return int(digits) if digits else 0
        except ValueError:
            return 0

    def connect_wifi(self, ssid: str, password: str = "") -> bool:
        if not self._use_nmcli:
            return False
        args = ["dev", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        result = self._run(args, timeout=30)
        if result.returncode != 0:
            logger.error("WiFi connect failed: %s", result.stderr)
            return False
        return True

    def _force_band_on_profile(self, ssid: str) -> None:
        """Optional: limit profile to 2.4 GHz (legacy Pi 3). Not used by default."""
        self._run([
            "con", "modify", ssid,
            "802-11-wireless.band", FORCE_WIFI_BAND,
        ])

    def wifi_connected(self) -> bool:
        if not self._use_nmcli:
            return False
        result = self._run(["-t", "-f", "DEVICE,TYPE,STATE", "dev"])
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "wifi" and parts[2] == "connected":
                return True
        return False

    def wifi_signal_strength(self) -> int:
        """Return signal 0-100, or -1 if disconnected."""
        if not self.wifi_connected():
            return -1
        result = self._run(["-t", "-f", "ACTIVE,SIGNAL", "dev", "wifi"])
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[0] == "yes":
                try:
                    return int(parts[1])
                except ValueError:
                    return 0
        return 0

    def ethernet_connected(self) -> bool:
        if not self._use_nmcli:
            return False
        result = self._run(["-t", "-f", "DEVICE,TYPE,STATE", "dev"])
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "ethernet" and parts[2] == "connected":
                return True
        return False

    def any_connected(self) -> bool:
        return self.wifi_connected() or self.ethernet_connected()

    def bluetooth_enabled(self) -> bool:
        return self._bluetooth_powered()

    def set_bluetooth_enabled(self, on: bool) -> bool:
        state = "on" if on else "off"
        result = self._run_bluetoothctl(["power", state])
        if result.returncode != 0:
            logger.error("BT power %s failed: %s", state, result.stderr or result.stdout)
            return False
        return True

    @staticmethod
    def _bluetooth_powered() -> bool:
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return "Powered: yes" in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _run_bluetoothctl(args: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bluetoothctl"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def list_bluetooth_devices(self) -> List[BluetoothDevice]:
        paired: dict[str, BluetoothDevice] = {}
        for line in self._run_bluetoothctl(["paired-devices"]).stdout.splitlines():
            parts = line.strip().split(" ", 2)
            if len(parts) < 3 or parts[0] != "Device":
                continue
            mac, name = parts[1], parts[2]
            paired[mac] = BluetoothDevice(mac=mac, name=name, paired=True)

        for line in self._run_bluetoothctl(["devices"]).stdout.splitlines():
            parts = line.strip().split(" ", 2)
            if len(parts) < 3 or parts[0] != "Device":
                continue
            mac, name = parts[1], parts[2]
            if mac not in paired:
                paired[mac] = BluetoothDevice(mac=mac, name=name)

        for dev in paired.values():
            info = self._run_bluetoothctl(["info", dev.mac], timeout=8).stdout
            dev.connected = "Connected: yes" in info
            dev.paired = dev.paired or "Paired: yes" in info

        devices = list(paired.values())
        devices.sort(key=lambda d: (not d.connected, not d.paired, d.name.lower()))
        return devices

    def scan_bluetooth(self) -> None:
        self._run_bluetoothctl(["scan", "on"], timeout=12)

    def connect_bluetooth(self, mac: str) -> bool:
        if not self.bluetooth_enabled():
            self.set_bluetooth_enabled(True)
        trust = self._run_bluetoothctl(["trust", mac], timeout=10)
        pair = self._run_bluetoothctl(["pair", mac], timeout=20)
        if pair.returncode != 0 and "AlreadyExists" not in pair.stderr + pair.stdout:
            logger.warning("BT pair %s: %s", mac, pair.stderr or pair.stdout)
        result = self._run_bluetoothctl(["connect", mac], timeout=25)
        if result.returncode != 0:
            logger.error("BT connect failed: %s", result.stderr or result.stdout)
            return False
        return True

    def _ethernet_device(self) -> str:
        if not self._use_nmcli:
            return "eth0"
        result = self._run(["-t", "-f", "DEVICE,TYPE,STATE", "dev"])
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "ethernet" and parts[2] == "connected":
                return parts[0]
        return "eth0"

    def ethernet_info(self) -> ConnectionInfo:
        if not self.ethernet_connected():
            return ConnectionInfo(connected=False)
        dev = self._ethernet_device()
        ip, gw = "", ""
        if self._use_nmcli:
            result = self._run(["-g", "IP4.ADDRESS,IP4.GATEWAY", "dev", "show", dev])
            lines = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
            if lines:
                ip = lines[0].split("/")[0] if lines[0] else ""
            if len(lines) > 1:
                gw = lines[1]
        if not ip:
            ip, gw = self._ip_from_system(dev)
        return ConnectionInfo(connected=True, ip=ip, gateway=gw, device=dev)

    @staticmethod
    def _ip_from_system(device: str) -> tuple[str, str]:
        """Fallback when nmcli fields are empty."""
        import re as _re

        ip, gw = "", ""
        try:
            addr = subprocess.run(
                ["ip", "-4", "-o", "addr", "show", device],
                capture_output=True, text=True, timeout=5, check=False,
            )
            m = _re.search(r"inet (\d+\.\d+\.\d+\.\d+)", addr.stdout)
            if m:
                ip = m.group(1)
            route = subprocess.run(
                ["ip", "route", "show", "default", "dev", device],
                capture_output=True, text=True, timeout=5, check=False,
            )
            m = _re.search(r"default via (\d+\.\d+\.\d+\.\d+)", route.stdout)
            if m:
                gw = m.group(1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return ip, gw

    def create_hotspot(self) -> bool:
        """Create emergency AP hotspot on 2.4 GHz."""
        if not self._use_nmcli:
            return False
        self._run(["con", "delete", HOTSPOT_NAME], timeout=10)
        result = self._run([
            "con", "add",
            "type", "wifi",
            "ifname", "wlan0",
            "con-name", HOTSPOT_NAME,
            "autoconnect", "no",
            "ssid", HOTSPOT_SSID,
            "mode", "ap",
        ])
        if result.returncode != 0:
            logger.error("Hotspot create failed: %s", result.stderr)
            return False
        self._run([
            "con", "modify", HOTSPOT_NAME,
            "802-11-wireless.band", FORCE_WIFI_BAND,
            "802-11-wireless.channel", str(HOTSPOT_CHANNEL),
            "ipv4.method", "shared",
        ])
        up = self._run(["con", "up", HOTSPOT_NAME], timeout=20)
        return up.returncode == 0

    def stop_hotspot(self) -> None:
        if self._use_nmcli:
            self._run(["con", "down", HOTSPOT_NAME], timeout=10)
