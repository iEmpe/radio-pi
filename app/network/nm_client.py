"""NetworkManager wrapper via nmcli with D-Bus fallback."""

from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _wifi_error_message(raw: str) -> str:
    low = raw.lower()
    if "not authorized" in low or "insufficient privileges" in low:
        return "Brak uprawnień do Wi-Fi"
    if "secret" in low or "password" in low or "hasło" in low:
        return "Hasło odrzucone"
    if "no network" in low or "not found" in low or "nie znaleziono" in low:
        return "Nie znaleziono tej sieci"
    if "timeout" in low or "time-out" in low or "czas" in low:
        return "Przekroczono czas łączenia"
    return "Nie udało się połączyć"

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
    rssi: int | None = None


class NetworkManagerClient:
    """Thin wrapper around nmcli for WiFi/Ethernet management."""

    def __init__(self) -> None:
        self._use_nmcli = self._check_nmcli()
        self._bt_rssi: dict[str, int] = {}
        self._bt_names: dict[str, str] = {}

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

    def connect_wifi(self, ssid: str, password: str = "") -> tuple[bool, str]:
        if not self._use_nmcli:
            return False, "nmcli niedostępne"
        args = ["dev", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        try:
            result = self._run(args, timeout=45)
        except subprocess.TimeoutExpired:
            logger.error("WiFi connect timed out for %s", ssid)
            return False, "Przekroczono czas łączenia"
        if result.returncode != 0:
            raw = (result.stderr or result.stdout or "").strip()
            logger.error("WiFi connect failed: %s", raw)
            return False, _wifi_error_message(raw)
        return True, ""

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

    def _bluetooth_powered(self) -> bool:
        result = self._run_bluetoothctl(["show"], timeout=5)
        return "Powered: yes" in (result.stdout or "")

    @staticmethod
    def _run_bluetoothctl(args: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
        cmd = ["bluetoothctl", *args]
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("bluetoothctl timeout: %s", " ".join(cmd))
            out = exc.stdout or ""
            err = exc.stderr or ""
            if isinstance(out, bytes):
                out = out.decode("utf-8", "replace")
            if isinstance(err, bytes):
                err = err.decode("utf-8", "replace")
            return subprocess.CompletedProcess(cmd, 124, stdout=out, stderr=err or "timeout")
        except FileNotFoundError:
            logger.error("bluetoothctl not installed")
            return subprocess.CompletedProcess(cmd, 127, stdout="", stderr="brak bluetoothctl")

    @staticmethod
    def _parse_bt_devices(text: str) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for line in (text or "").splitlines():
            clean = _ANSI.sub("", line).strip()
            parts = clean.split(" ", 2)
            if len(parts) < 2 or parts[0] != "Device":
                continue
            mac = parts[1].upper()
            name = parts[2].strip() if len(parts) > 2 and parts[2].strip() else mac
            found.append((mac, name))
        return found

    def _remember_rssi(self, mac: str, rssi: int) -> None:
        key = mac.upper()
        prev = self._bt_rssi.get(key)
        if prev is None or rssi > prev:
            self._bt_rssi[key] = rssi

    @staticmethod
    def _is_mac_label(name: str, mac: str) -> bool:
        def hex_only(value: str) -> str:
            return re.sub(r"[^0-9A-Fa-f]", "", value).upper()

        label = hex_only(name)
        addr = hex_only(mac)
        return not label or label == addr

    def list_bluetooth_devices(self) -> List[BluetoothDevice]:
        devices: dict[str, BluetoothDevice] = {}
        for mac, name in self._parse_bt_devices(
            self._run_bluetoothctl(["paired-devices"], timeout=8).stdout
        ):
            devices[mac] = BluetoothDevice(mac=mac, name=name, paired=True)
        for mac, name in self._parse_bt_devices(
            self._run_bluetoothctl(["devices"], timeout=8).stdout
        ):
            if mac not in devices:
                devices[mac] = BluetoothDevice(mac=mac, name=name)
        for dev in devices.values():
            if not dev.paired:
                continue
            info = self._run_bluetoothctl(["info", dev.mac], timeout=4).stdout or ""
            dev.connected = "Connected: yes" in info
            dev.paired = True
            rssi_match = re.search(r"RSSI:\s*(-?\d+)", info)
            if rssi_match:
                self._remember_rssi(dev.mac, int(rssi_match.group(1)))
        for dev in devices.values():
            mac = dev.mac.upper()
            cached_name = self._bt_names.get(mac)
            if cached_name and not self._is_mac_label(cached_name, mac):
                dev.name = cached_name
            dev.rssi = self._bt_rssi.get(mac)
        ordered = list(devices.values())
        ordered.sort(key=self._bt_sort_key)
        return ordered

    @classmethod
    def _bt_sort_key(cls, dev: BluetoothDevice) -> tuple:
        mac_only = cls._is_mac_label(dev.name, dev.mac)
        if dev.rssi is None:
            distance = 10_000
        else:
            distance = -dev.rssi
        return (mac_only, distance, dev.name.lower())

    def scan_bluetooth(self) -> None:
        # RSSI exists only while discovery is running, and bluetoothctl's
        # pipe output drops most of those lines. Read them from BlueZ instead.
        proc = subprocess.Popen(
            ["bluetoothctl", "--timeout", "10", "scan", "on"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(6)
            self._read_live_bluetooth()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        finally:
            if proc.poll() is None:
                proc.kill()
        self._run_bluetoothctl(["scan", "off"], timeout=5)

    def _read_live_bluetooth(self) -> None:
        tree = self._busctl(["tree", "org.bluez"])
        paths = re.findall(r"/org/bluez/hci\d+/dev_[0-9A-Fa-f_]+", tree.stdout or "")
        for path in dict.fromkeys(paths):
            mac = self._mac_from_bluez_path(path)
            if not mac:
                continue
            alias = self._busctl_string(path, "Alias")
            name = self._busctl_string(path, "Name")
            label = alias or name
            if label and not self._is_mac_label(label, mac):
                self._bt_names[mac] = label
            rssi_text = self._busctl(["get-property", "org.bluez", path, "org.bluez.Device1", "RSSI"]).stdout or ""
            if rssi_text.startswith("n "):
                try:
                    self._remember_rssi(mac, int(rssi_text.split()[1]))
                except ValueError:
                    pass

    @staticmethod
    def _busctl(args: list[str], timeout: int = 4) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                ["busctl", *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("busctl failed: %s", exc)
            return subprocess.CompletedProcess(["busctl", *args], 1, "", "")

    def _busctl_string(self, path: str, prop: str) -> str:
        text = self._busctl(["get-property", "org.bluez", path, "org.bluez.Device1", prop]).stdout or ""
        match = re.match(r'^s "(.*)"\s*$', text.strip())
        if not match:
            return ""
        return match.group(1).replace('\\"', '"')

    @staticmethod
    def _mac_from_bluez_path(path: str) -> str:
        tail = path.rsplit("/", 1)[-1]
        if not tail.startswith("dev_"):
            return ""
        parts = tail[4:].split("_")
        if len(parts) != 6:
            return ""
        return ":".join(parts).upper()

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
