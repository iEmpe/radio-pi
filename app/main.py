#!/usr/bin/env python3
"""Radio Pi — light player UI on desktop X11 (480×320)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.audio.eq_presets import DEFAULT_PRESET  # noqa: E402
from app.audio.player import AudioPlayer  # noqa: E402
from app.audio.spectrum import SpectrumAnalyzer  # noqa: E402
from app.network.nm_client import NetworkManagerClient  # noqa: E402
from app.ui.controls_bar import ControlsBar  # noqa: E402
from app.ui.equalizer_panel import EqualizerPanel  # noqa: E402
from app.ui.network_screen import NetworkScreen  # noqa: E402
from app.ui.station_browser import StationBrowser  # noqa: E402
from app.stations.last_station import load as load_last_station  # noqa: E402
from app.stations.last_station import save as save_last_station  # noqa: E402
from app.stations.logo_loader import LogoStartupThread, STATIONS_PATH  # noqa: E402
from app.ui.splash_screen import SplashScreen  # noqa: E402
from app.ui.station_strip import StationStrip  # noqa: E402
from app.ui.fonts import ensure_clock_font_loaded, ensure_fonts_loaded, ui_font
from app.ui.theme import BG, FONT_SIZE_SMALL, SCREEN_H, SCREEN_W  # noqa: E402
from app.ui.top_bar import TopBar  # noqa: E402
from app.ui.volume_bar import VolumeBar  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class RadioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Radio Pi")
        self.setFixedSize(SCREEN_W, SCREEN_H)

        self._nm = NetworkManagerClient()
        self._player = AudioPlayer()
        self._current_station: dict | None = None
        self._spectrum = SpectrumAnalyzer()

        central = QWidget()
        central.setStyleSheet(f"background: {BG};")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._top = TopBar(self._nm)
        self._top.wifi_tapped.connect(self._show_wifi)
        self._top.ethernet_tapped.connect(self._show_ethernet)
        self._top.bluetooth_tapped.connect(self._show_bluetooth)
        root.addWidget(self._top)

        self._stations = StationStrip()
        self._stations.station_changed.connect(self._on_station_selected)
        root.addWidget(self._stations)

        self._equalizer = EqualizerPanel()
        self._equalizer.preset_changed.connect(self._on_eq_preset)
        self._spectrum.levels_ready.connect(self._equalizer.set_levels)
        root.addWidget(self._equalizer, stretch=1)

        self._volume = VolumeBar()
        self._volume.volume_changed.connect(self._on_volume)
        self._volume.mute_changed.connect(self._on_mute)
        root.addWidget(self._volume)

        self._controls = ControlsBar()
        self._controls.play_pause_clicked.connect(self._toggle_play_pause)
        self._controls.close_clicked.connect(self._close_overlay)
        root.addWidget(self._controls)

        self._network = NetworkScreen(self._nm)
        self._network.closed.connect(self._hide_network)
        self._network.setParent(central)
        self._network.hide()

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._poll_stream_info)

        self._volume.set_volume(self._player.volume)
        self._player.set_eq_preset(DEFAULT_PRESET)
        self._equalizer.set_active_preset(DEFAULT_PRESET)
        self._autoplay_first()

        QTimer.singleShot(700, self._start_metadata_poll)

    def _autoplay_first(self) -> None:
        last = load_last_station()
        station: dict | None = None
        if last:
            if self._stations.select_by_url(last.get("url", "")):
                station = self._stations.current_station()
            else:
                station = last
        if station is None:
            station = self._stations.current_station()
        if station:
            self._play_station(station, auto=True)

    def _show_wifi(self) -> None:
        self._set_main_chrome_visible(False)
        self._network.show_wifi()
        self._network.setGeometry(0, 0, SCREEN_W, SCREEN_H)
        self._network.raise_()
        self._network.show()

    def _show_ethernet(self) -> None:
        self._set_main_chrome_visible(False)
        self._network.show_ethernet()
        self._network.setGeometry(0, 0, SCREEN_W, SCREEN_H)
        self._network.raise_()
        self._network.show()

    def _show_bluetooth(self) -> None:
        self._set_main_chrome_visible(False)
        self._network.show_bluetooth()
        self._network.setGeometry(0, 0, SCREEN_W, SCREEN_H)
        self._network.raise_()
        self._network.show()

    def _hide_network(self) -> None:
        self._network.hide()
        self._set_main_chrome_visible(True)

    def _set_main_chrome_visible(self, visible: bool) -> None:
        for widget in (
            self._top,
            self._stations,
            self._equalizer,
            self._volume,
            self._controls,
        ):
            widget.setVisible(visible)

    def _on_station_selected(self, station: dict) -> None:
        self._play_station(station)

    def _play_station(self, station: dict, auto: bool = False) -> None:
        url = station.get("url", "")
        if not url:
            return
        self._current_station = station
        cfg_name = station.get("name", "—")
        self._stations.set_genre(StationStrip.genre_from_config(station))
        self._controls.set_now_playing("")
        self._player.play(url)
        self._controls.set_playing(True)
        self._equalizer.set_active(True)
        self._start_spectrum()
        save_last_station(station)
        StationBrowser.append_history(station)
        if not auto:
            logger.info("Playing: %s", cfg_name)
        for delay in (800, 2000, 5000):
            QTimer.singleShot(delay, self._poll_stream_info)

    def _toggle_play_pause(self) -> None:
        if self._player.playing:
            self._player.pause()
            self._controls.set_playing(False)
            self._equalizer.set_active(False)
            self._stop_spectrum()
        elif self._current_station:
            self._player.resume()
            self._controls.set_playing(True)
            self._equalizer.set_active(True)
            self._start_spectrum()
        else:
            station = self._stations.current_station()
            if station:
                self._play_station(station)

    def _on_volume(self, level: int) -> None:
        self._player.set_volume(level)
        if level > 0:
            self._player.set_mute(False)

    def _on_mute(self, muted: bool) -> None:
        self._player.set_mute(muted)
        if muted:
            self._equalizer.set_active(False)
        elif self._player.playing:
            self._equalizer.set_active(True)

    def _on_eq_preset(self, preset_id: str) -> None:
        self._player.set_eq_preset(preset_id)
        self._equalizer.set_active_preset(preset_id)
        logger.info("EQ preset selected: %s", preset_id)

    def _start_metadata_poll(self) -> None:
        self._poll_stream_info()
        self._poll.start(2500)

    def _poll_stream_info(self) -> None:
        if not self._player.playing:
            return
        info = self._player.get_stream_info(self._current_station)
        cfg_name = (self._current_station or {}).get("name", "")
        self._controls.set_now_playing(info.track_scroll_text(cfg_name))
        if info.genre:
            self._stations.set_genre(info.genre)
        elif self._current_station:
            self._stations.set_genre(StationStrip.genre_from_config(self._current_station))
        if info.bitrate_kbps:
            self._top.set_bitrate(str(info.bitrate_kbps))
        elif self._current_station:
            tags = self._current_station.get("tags", "")
            if "128" in tags:
                self._top.set_bitrate("128")
            else:
                self._top.set_bitrate("---")

    def _start_spectrum(self) -> None:
        if self._spectrum.isRunning():
            return
        if self._spectrum.isFinished():
            self._spectrum = SpectrumAnalyzer()
            self._spectrum.levels_ready.connect(self._equalizer.set_levels)
        self._spectrum.start()

    def _stop_spectrum(self) -> None:
        if self._spectrum.isRunning():
            self._spectrum.stop()
            self._spectrum.wait(2000)

    def _close_overlay(self) -> None:
        self._stop_spectrum()
        self._player.shutdown()
        self.close()

    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        self._stop_spectrum()
        self._player.shutdown()
        super().closeEvent(event)


def main() -> int:
    import fcntl

    lock_path = "/tmp/radio-pi-ui.lock"
    lock_file = open(lock_path, "w", encoding="utf-8")  # noqa: SIM115
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.warning("Radio Pi already running — exiting duplicate instance")
        return 0

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ensure_fonts_loaded()
    ensure_clock_font_loaded()
    app.setFont(ui_font(FONT_SIZE_SMALL))

    splash = SplashScreen()
    splash.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    splash.showFullScreen()
    app.processEvents()

    window_holder: list[RadioWindow | None] = [None]

    def open_main_window(_ok: int, _total: int) -> None:
        window_holder[0] = RadioWindow()
        window_holder[0].setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        window_holder[0].showFullScreen()
        splash.close()

    loader = LogoStartupThread(STATIONS_PATH)
    loader.status_changed.connect(splash.set_status)
    loader.finished_loading.connect(open_main_window)
    loader.start()

    def _force_open_if_stuck() -> None:
        if window_holder[0] is None:
            logger.warning("Logo startup timeout — opening UI")
            open_main_window(0, 0)

    QTimer.singleShot(16_000, _force_open_if_stuck)

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
