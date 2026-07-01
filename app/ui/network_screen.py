"""WiFi / Ethernet overlay."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.network.nm_client import BluetoothDevice, NetworkManagerClient, WifiNetwork
from app.ui.fonts import font_family, stylesheet
from app.ui.keyboard import OnScreenKeyboard
from app.ui.theme import BG, BORDER, FONT_SIZE_MED, FONT_SIZE_SMALL, IPOD_SELECT, TEXT, TEXT_DIM
from app.ui.wifi_scan_thread import WifiScanThread


class NetworkScreen(QWidget):
    closed = pyqtSignal()

    def __init__(self, nm: NetworkManagerClient, parent=None) -> None:
        super().__init__(parent)
        self._nm = nm
        self._selected_ssid = ""
        self._password = ""
        self._wifi_scan: WifiScanThread | None = None

        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(BG))
        self.setPalette(pal)
        self.setStyleSheet(f"background-color: {BG};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel("Sieć")
        self._title.setStyleSheet(
            stylesheet(FONT_SIZE_MED, TEXT)
            + f"background-color: {BG}; padding: 4px;"
        )
        header.addWidget(self._title, stretch=1)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            f"background-color: {BG}; border: 1px solid {BORDER};"
            f"border-radius: 16px; color: {TEXT_DIM};"
        )
        close_btn.clicked.connect(self.closed.emit)
        header.addWidget(close_btn)
        root.addLayout(header)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        list_page = QWidget()
        ll = QVBoxLayout(list_page)
        self._list = QListWidget()
        mono = font_family()
        self._list.setStyleSheet(
            f"QListWidget {{ border: 1px solid {BORDER}; font-family: '{mono}';"
            f"font-size: {FONT_SIZE_SMALL}px; }}"
            f"QListWidget::item:selected {{ background: {IPOD_SELECT}; color: white; }}"
        )
        self._list.itemClicked.connect(self._on_network_selected)
        ll.addWidget(self._list, stretch=1)
        self._wifi_status = QLabel("")
        self._wifi_status.setWordWrap(True)
        self._wifi_status.setStyleSheet(
            stylesheet(FONT_SIZE_SMALL, TEXT_DIM) + f"background-color: {BG};"
        )
        ll.addWidget(self._wifi_status)
        ref = QPushButton("Odśwież")
        ref.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        ref.clicked.connect(self.refresh)
        ll.addWidget(ref)
        self._stack.addWidget(list_page)

        pass_page = QWidget()
        pl = QVBoxLayout(pass_page)
        self._ssid_label = QLabel()
        self._ssid_label.setWordWrap(True)
        self._ssid_label.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        pl.addWidget(self._ssid_label)
        self._pass_display = QLabel()
        self._pass_display.setMinimumHeight(24)
        self._pass_display.setStyleSheet(
            stylesheet(FONT_SIZE_SMALL, TEXT) + f"border: 1px solid {BORDER}; padding: 4px;"
        )
        pl.addWidget(self._pass_display)
        self._keyboard = OnScreenKeyboard()
        self._keyboard.key_pressed.connect(self._on_key)
        self._keyboard.backspace_pressed.connect(self._on_backspace)
        self._keyboard.done_pressed.connect(self._connect)
        pl.addWidget(self._keyboard)
        back = QPushButton("← Lista")
        back.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        back.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        pl.addWidget(back)
        self._stack.addWidget(pass_page)

        eth_page = QWidget()
        el = QVBoxLayout(eth_page)
        el.setSpacing(12)
        self._eth_ip = QLabel()
        self._eth_gw = QLabel()
        self._eth_dev = QLabel()
        eth_style = (
            stylesheet(FONT_SIZE_SMALL, TEXT)
            + f"padding: 8px; border: 1px solid {BORDER}; border-radius: 6px;"
        )
        for lbl in (self._eth_ip, self._eth_gw, self._eth_dev):
            lbl.setWordWrap(True)
            lbl.setStyleSheet(eth_style)
            el.addWidget(lbl)
        el.addStretch()
        eb = QPushButton("Zamknij")
        eb.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        eb.clicked.connect(self.closed.emit)
        el.addWidget(eb)
        self._stack.addWidget(eth_page)

        bt_page = QWidget()
        bl = QVBoxLayout(bt_page)
        bl.setSpacing(6)
        self._bt_status = QLabel()
        self._bt_status.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        bl.addWidget(self._bt_status)
        self._bt_toggle = QPushButton()
        self._bt_toggle.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        self._bt_toggle.clicked.connect(self._toggle_bluetooth)
        bl.addWidget(self._bt_toggle)
        self._bt_list = QListWidget()
        self._bt_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid {BORDER}; font-family: '{mono}';"
            f"font-size: {FONT_SIZE_SMALL}px; }}"
            f"QListWidget::item:selected {{ background: {IPOD_SELECT}; color: white; }}"
        )
        self._bt_list.itemClicked.connect(self._on_bt_device_selected)
        bl.addWidget(self._bt_list, stretch=1)
        bt_note = QLabel("Wybierz głośnik Bluetooth z listy (skan ~10 s).")
        bt_note.setWordWrap(True)
        bt_note.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT_DIM))
        bl.addWidget(bt_note)
        bt_row = QHBoxLayout()
        bt_scan = QPushButton("Skanuj")
        bt_scan.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        bt_scan.clicked.connect(self._scan_bluetooth)
        bt_row.addWidget(bt_scan)
        bt_ref = QPushButton("Odśwież")
        bt_ref.setStyleSheet(stylesheet(FONT_SIZE_SMALL, TEXT))
        bt_ref.clicked.connect(self._refresh_bluetooth)
        bt_row.addWidget(bt_ref)
        bl.addLayout(bt_row)
        self._stack.addWidget(bt_page)

    def show_wifi(self) -> None:
        self._title.setText("Wi-Fi")
        self._stack.setCurrentIndex(0)
        self.refresh()

    def show_ethernet(self) -> None:
        self._title.setText("Ethernet")
        info = self._nm.ethernet_info()
        if info.connected:
            self._eth_ip.setText(f"IP: {info.ip or '—'}")
            self._eth_gw.setText(f"Brama: {info.gateway or '—'}")
            self._eth_dev.setText(f"IF: {info.device}")
        else:
            self._eth_ip.setText("Ethernet niepołączony")
            self._eth_gw.setText("")
            self._eth_dev.setText("")
        self._stack.setCurrentIndex(2)

    def show_bluetooth(self) -> None:
        self._title.setText("Bluetooth")
        self._stack.setCurrentIndex(3)
        self._refresh_bluetooth()

    def _refresh_bluetooth(self) -> None:
        on = self._nm.bluetooth_enabled()
        self._bt_status.setText("Bluetooth: włączony" if on else "Bluetooth: wyłączony")
        self._bt_toggle.setText("Wyłącz Bluetooth" if on else "Włącz Bluetooth")
        self._bt_list.clear()
        for dev in self._nm.list_bluetooth_devices():
            state = "połączony" if dev.connected else ("sparowany" if dev.paired else "znaleziony")
            item = QListWidgetItem(f"{dev.name}  [{state}]")
            item.setData(Qt.UserRole, dev)
            self._bt_list.addItem(item)

    def _toggle_bluetooth(self) -> None:
        on = self._nm.bluetooth_enabled()
        self._nm.set_bluetooth_enabled(not on)
        self._refresh_bluetooth()

    def _scan_bluetooth(self) -> None:
        if not self._nm.bluetooth_enabled():
            self._nm.set_bluetooth_enabled(True)
        self._bt_status.setText("Skanowanie…")
        self._nm.scan_bluetooth()
        self._refresh_bluetooth()

    def _on_bt_device_selected(self, item: QListWidgetItem) -> None:
        dev: BluetoothDevice = item.data(Qt.UserRole)
        self._bt_status.setText(f"Łączenie: {dev.name}…")
        if self._nm.connect_bluetooth(dev.mac):
            self._bt_status.setText(f"Połączono: {dev.name}")
        else:
            self._bt_status.setText(f"Nie udało się połączyć: {dev.name}")
        self._refresh_bluetooth()

    def refresh(self) -> None:
        if self._wifi_scan and self._wifi_scan.isRunning():
            return
        self._wifi_status.setText("Skanowanie sieci…")
        self._list.clear()
        self._wifi_scan = WifiScanThread(self._nm)
        self._wifi_scan.finished.connect(self._on_wifi_scan_done)
        self._wifi_scan.start()

    def _on_wifi_scan_done(self, networks: list) -> None:
        self._list.clear()
        if not networks:
            self._wifi_status.setText("Brak sieci — dotknij Odśwież")
            return
        for net in networks:
            self._list.addItem(self._wifi_list_item(net))
        n24 = sum(1 for n in networks if n.freq_mhz and n.freq_mhz < 5000)
        n5 = sum(1 for n in networks if n.freq_mhz >= 5000)
        self._wifi_status.setText(
            f"Znaleziono: {len(networks)}  ·  2,4 GHz: {n24}  ·  5 GHz: {n5}"
        )

    @staticmethod
    def _wifi_list_item(net: WifiNetwork) -> QListWidgetItem:
        lock = " *" if net.secured else ""
        active = " >" if net.in_use else ""
        band = f" [{net.band_label}]" if net.band_label else ""
        text = f"{net.ssid}  {net.signal}%{band}{lock}{active}"
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, net)
        return item

    def _on_network_selected(self, item: QListWidgetItem) -> None:
        net: WifiNetwork = item.data(Qt.UserRole)
        self._selected_ssid = net.ssid
        self._password = ""
        self._ssid_label.setText(f"Sieć: {net.ssid}")
        self._pass_display.setText("")
        if net.secured:
            self._stack.setCurrentIndex(1)
        else:
            self._nm.connect_wifi(net.ssid)
            self.closed.emit()

    def _on_key(self, key: str) -> None:
        self._password += key
        self._pass_display.setText("•" * len(self._password))

    def _on_backspace(self) -> None:
        self._password = self._password[:-1]
        self._pass_display.setText("•" * len(self._password))

    def _connect(self) -> None:
        if self._selected_ssid:
            self._nm.connect_wifi(self._selected_ssid, self._password)
            self.closed.emit()
