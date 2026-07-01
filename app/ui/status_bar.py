"""Top status bar — play icon, station name, clock, WiFi, Ethernet."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.network.nm_client import NetworkManagerClient
from app.ui.icons import load_icon
from app.ui.theme import BORDER, FONT_SIZE_SMALL, NET_ACTIVE, NET_INACTIVE, STATUS_H, TEXT


class StatusBar(QWidget):
    wifi_tapped = pyqtSignal()
    ethernet_tapped = pyqtSignal()

    def __init__(self, nm: NetworkManagerClient, parent=None) -> None:
        super().__init__(parent)
        self._nm = nm
        self._playing = False
        self.setFixedHeight(STATUS_H)
        self.setStyleSheet(f"background: #FFFFFF; border-bottom: 1px solid {BORDER};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)

        self._play_icon = QLabel("▶")
        self._play_icon.setFixedWidth(14)
        self._play_icon.setStyleSheet(f"color: {TEXT}; font-size: 9px;")
        layout.addWidget(self._play_icon)

        self._station = QLabel("")
        self._station.setStyleSheet(
            f"color: {TEXT}; font-size: {FONT_SIZE_SMALL}px; font-weight: bold;"
        )
        layout.addWidget(self._station, stretch=1)

        self._clock = QLabel("00:00")
        self._clock.setStyleSheet(f"color: {TEXT}; font-size: {FONT_SIZE_SMALL}px;")
        layout.addWidget(self._clock)

        self._wifi_btn = QPushButton()
        self._wifi_btn.setFixedSize(22, 22)
        self._wifi_btn.setFlat(True)
        self._wifi_btn.setStyleSheet("border: none; background: transparent;")
        self._wifi_btn.clicked.connect(self.wifi_tapped.emit)
        layout.addWidget(self._wifi_btn)

        self._eth_btn = QPushButton()
        self._eth_btn.setFixedSize(22, 22)
        self._eth_btn.setFlat(True)
        self._eth_btn.setStyleSheet("border: none; background: transparent;")
        self._eth_btn.clicked.connect(self.ethernet_tapped.emit)
        layout.addWidget(self._eth_btn)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_network)
        self._timer.start(4000)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()
        self._update_network()

    def set_station_name(self, name: str) -> None:
        display = name if len(name) <= 16 else name[:14] + "…"
        self._station.setText(display)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._play_icon.setText("▶" if playing else " ")

    def _update_clock(self) -> None:
        self._clock.setText(datetime.now().strftime("%H:%M"))

    def _wifi_level_icon(self, signal: int) -> str:
        if signal < 0:
            return "wifi_0.svg"
        if signal < 25:
            return "wifi_1.svg"
        if signal < 50:
            return "wifi_2.svg"
        if signal < 75:
            return "wifi_3.svg"
        return "wifi_4.svg"

    def _update_network(self) -> None:
        wifi_on = self._nm.wifi_connected()
        color = NET_ACTIVE if wifi_on else NET_INACTIVE
        signal = self._nm.wifi_signal_strength() if wifi_on else -1
        icon_name = self._wifi_level_icon(signal)
        self._wifi_btn.setIcon(load_icon(icon_name, color, 18))
        self._wifi_btn.setIconSize(self._wifi_btn.size())

        eth_on = self._nm.ethernet_connected()
        eth_color = NET_ACTIVE if eth_on else NET_INACTIVE
        eth_icon = "ethernet_on.svg" if eth_on else "ethernet_off.svg"
        self._eth_btn.setIcon(load_icon(eth_icon, eth_color, 18))
        self._eth_btn.setIconSize(self._eth_btn.size())
