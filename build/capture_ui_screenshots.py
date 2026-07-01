#!/usr/bin/env python3
"""Render UI screenshots for documentation (480×320, offscreen)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "screenshots"


def _save(widget, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    img = QImage(widget.size(), QImage.Format_ARGB32)
    widget.render(img)
    path = OUT / f"{name}.png"
    img.save(str(path))
    print(f"  saved {path}")


def main() -> int:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)

    from app.ui.fonts import ensure_clock_font_loaded, ensure_fonts_loaded
    from app.ui.splash_screen import SplashScreen
    from app.ui.theme import FONT_SIZE_SMALL
    from app.ui.fonts import ui_font

    ensure_fonts_loaded()
    ensure_clock_font_loaded()
    app.setFont(ui_font(FONT_SIZE_SMALL))

    splash = SplashScreen()
    splash.set_status("Ładowanie logo stacji…", "12 / 27")
    _save(splash, "01-splash")

    from app.network.nm_client import WifiNetwork

    mock_nm = MagicMock()
    mock_nm.wifi_status.return_value = (3, True)
    mock_nm.ethernet_connected.return_value = True
    mock_nm.bluetooth_powered.return_value = True
    mock_nm.bluetooth_connected.return_value = False
    mock_nm.scan_wifi.return_value = [
        WifiNetwork("wifirifi_2G", 82, True, 6, 2437, True),
        WifiNetwork("Sasiad_5G", 45, True, 36, 5180, False),
    ]
    eth = MagicMock()
    eth.connected = True
    eth.ip = "192.168.0.81"
    eth.gateway = "192.168.0.1"
    eth.device = "eth0"
    mock_nm.ethernet_info.return_value = eth

    with patch("app.main.NetworkManagerClient", return_value=mock_nm), patch(
        "app.ui.network_screen.NetworkManagerClient", return_value=mock_nm
    ), patch("app.main.AudioPlayer") as mock_player_cls, patch(
        "app.main.SpectrumAnalyzer"
    ), patch.object(
        QTimer, "singleShot", staticmethod(lambda *_a, **_k: None)
    ):
        mock_player = MagicMock()
        mock_player.volume = 80
        mock_player.playing = True
        mock_player.muted = False
        mock_player_cls.return_value = mock_player

        from app.main import RadioWindow

        win = RadioWindow()
        win._controls.set_now_playing("Bassdrive — liquid dnb session")
        win._top.set_bitrate("206")
        win._stations.set_genre("DRUM AND BASS")
        win._equalizer.set_active(True)
        win._equalizer.set_levels([0.3, 0.5, 0.7, 0.85, 0.6, 0.45] * 4)
        win.show()
        app.processEvents()
        _save(win, "02-main-playing")

        win._volume._toggle_mute()
        app.processEvents()
        _save(win, "03-main-muted")

        win._set_main_chrome_visible(False)
        win._network.show_wifi()
        app.processEvents()
        # Poczekaj na wątek skanu WiFi (mock)
        if win._network._wifi_scan:
            win._network._wifi_scan.wait(3000)
        app.processEvents()
        _save(win._network, "04-wifi-menu")

    print(f"Done — {len(list(OUT.glob('*.png')))} screenshots in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
