"""Top header — network labels, clock, full-width timezone marquee, bitrate."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.network.nm_client import NetworkManagerClient
from app.timezone_info import timezone_scroll_text
from app.ui.clock_label import ClockLabel
from app.ui.fonts import stylesheet
from app.ui.marquee_label import MarqueeLabel
from app.ui.theme import (
    BG,
    BG_SOFT,
    BORDER,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    HEADER_H,
    NET_ACTIVE,
    NET_INACTIVE,
    TEXT,
    TEXT_LIGHT,
    TEXT_MUTED,
)

NET_LABEL_SIZE = FONT_SIZE_SMALL + 2
NET_LABEL_GAP = 12
NET_LABEL_LEFT_PAD = 8
SIDE_SLOT_W = 130
UI_FRAME_MS = 16
TZ_MARQUEE_H = 13
_NET_LABEL_BASE = "border: none; background: transparent; padding: 0; margin: 0; outline: none;"


class TopBar(QWidget):
    wifi_tapped = pyqtSignal()
    ethernet_tapped = pyqtSignal()
    bluetooth_tapped = pyqtSignal()

    def __init__(self, nm: NetworkManagerClient, parent=None) -> None:
        super().__init__(parent)
        self._nm = nm
        self._wifi_key = ""
        self._eth_key = ""
        self._bt_key = ""
        self.setFixedHeight(HEADER_H)
        self.setStyleSheet(f"background: {BG}; border-bottom: 1px solid {BORDER};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header_row = QWidget()
        header_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        header_lay = QHBoxLayout(header_row)
        header_lay.setContentsMargins(8, 0, 8, 0)
        header_lay.setSpacing(0)

        left = QWidget()
        left.setFixedWidth(SIDE_SLOT_W)
        left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left_outer = QVBoxLayout(left)
        left_outer.setContentsMargins(0, 0, 0, 0)
        left_outer.setSpacing(0)
        left_outer.addStretch(1)

        left_row = QHBoxLayout()
        left_row.setContentsMargins(NET_LABEL_LEFT_PAD, 0, 0, 0)
        left_row.setSpacing(NET_LABEL_GAP)

        self._wifi_btn = QPushButton("WiFi")
        self._wifi_btn.setFlat(True)
        self._wifi_btn.setFocusPolicy(Qt.NoFocus)
        self._wifi_btn.setCursor(Qt.PointingHandCursor)
        self._wifi_btn.clicked.connect(self.wifi_tapped.emit)
        left_row.addWidget(self._wifi_btn)

        self._eth_btn = QPushButton("ETH")
        self._eth_btn.setFlat(True)
        self._eth_btn.setFocusPolicy(Qt.NoFocus)
        self._eth_btn.setCursor(Qt.PointingHandCursor)
        self._eth_btn.clicked.connect(self.ethernet_tapped.emit)
        left_row.addWidget(self._eth_btn)

        self._bt_btn = QPushButton("BT")
        self._bt_btn.setFlat(True)
        self._bt_btn.setFocusPolicy(Qt.NoFocus)
        self._bt_btn.setCursor(Qt.PointingHandCursor)
        self._bt_btn.clicked.connect(self.bluetooth_tapped.emit)
        left_row.addWidget(self._bt_btn)
        left_row.addStretch()
        left_outer.addLayout(left_row)
        left_outer.addStretch(1)
        header_lay.addWidget(left)

        clock_wrap = QWidget()
        clock_wrap.setAttribute(Qt.WA_TranslucentBackground, True)
        clock_wrap.setAutoFillBackground(False)
        clock_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        clock_lay = QVBoxLayout(clock_wrap)
        clock_lay.setContentsMargins(0, 2, 0, 0)
        clock_lay.setSpacing(0)
        clock_lay.addStretch(1)
        self._clock = ClockLabel(clock_wrap)
        clock_lay.addWidget(self._clock, alignment=Qt.AlignHCenter)
        clock_lay.addStretch(1)
        header_lay.addWidget(clock_wrap, stretch=1)

        right = QWidget()
        right.setFixedWidth(SIDE_SLOT_W)
        right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_outer = QVBoxLayout(right)
        right_outer.setContentsMargins(0, 0, 0, 0)
        right_outer.setSpacing(0)
        right_outer.addStretch(1)

        right_row = QHBoxLayout()
        right_row.setContentsMargins(0, 0, 0, 0)
        right_row.setAlignment(Qt.AlignVCenter)
        self._bitrate_lbl = QLabel("--- kbps")
        self._bitrate_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._bitrate_lbl.setStyleSheet(
            stylesheet(FONT_SIZE_SMALL, TEXT)
            + f"background: {BG_SOFT}; border: 1px solid {TEXT_LIGHT};"
            f"border-radius: 10px; padding: 2px 6px;"
        )
        right_row.addStretch()
        right_row.addWidget(self._bitrate_lbl)
        right_outer.addLayout(right_row)
        right_outer.addStretch(1)
        header_lay.addWidget(right)

        self._tz_marquee = MarqueeLabel(
            self,
            ticker=True,
            external_drive=True,
            speed_px_s=18.0,
            loop_sep="   ·   ",
            background=BG,
        )
        self._tz_marquee.setFixedHeight(TZ_MARQUEE_H)
        self._tz_marquee.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._tz_marquee.set_font("", FONT_SIZE_TINY, TEXT_MUTED)

        root.addWidget(header_row, stretch=1)
        root.addWidget(self._tz_marquee)

        self._ui_timer = QTimer(self)
        self._ui_timer.setTimerType(Qt.PreciseTimer)
        self._ui_timer.timeout.connect(self._on_ui_frame)
        self._ui_timer.start(UI_FRAME_MS)

        self._net_timer = QTimer(self)
        self._net_timer.timeout.connect(self._tick_network)
        self._net_timer.start(5000)

        self._tz_timer = QTimer(self)
        self._tz_timer.timeout.connect(self._refresh_tz)
        self._tz_timer.start(60_000)

        self._refresh_tz()
        self._clock.tick_if_needed()
        self._tick_network()

    def _on_ui_frame(self) -> None:
        self._tz_marquee.tick()
        self._clock.tick_if_needed()

    def _refresh_tz(self) -> None:
        self._tz_marquee.set_text(timezone_scroll_text())

    def set_bitrate(self, kbps: str) -> None:
        text = kbps if kbps else "---"
        if not text.endswith("kbps"):
            text = f"{text} kbps"
        if text != self._bitrate_lbl.text():
            self._bitrate_lbl.setText(text)

    def _set_net_label(self, btn: QPushButton, active: bool) -> None:
        color = NET_ACTIVE if active else NET_INACTIVE
        btn.setStyleSheet(
            stylesheet(NET_LABEL_SIZE, color, bold=True) + _NET_LABEL_BASE
        )

    def _tick_network(self) -> None:
        wifi_on = self._nm.wifi_connected()
        if self._wifi_key != str(wifi_on):
            self._wifi_key = str(wifi_on)
            self._set_net_label(self._wifi_btn, wifi_on)

        eth_on = self._nm.ethernet_connected()
        if self._eth_key != str(eth_on):
            self._eth_key = str(eth_on)
            self._set_net_label(self._eth_btn, eth_on)

        bt_on = self._nm.bluetooth_enabled()
        if self._bt_key != str(bt_on):
            self._bt_key = str(bt_on)
            self._set_net_label(self._bt_btn, bt_on)
