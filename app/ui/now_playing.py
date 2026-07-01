"""Now Playing screen — iPod 6G light style."""

from __future__ import annotations

import random
from datetime import timedelta

from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import (
    BORDER,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    LIVE_RED,
    PANEL_BLUE,
    TEXT,
    TEXT_DIM,
)


class ActivityBars(QWidget):
    """Animated bar visualization for live stream."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(14)
        self._levels = [3, 5, 4, 6, 3, 5, 4]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(180)

    def _tick(self) -> None:
        self._levels = [max(2, min(10, v + random.randint(-2, 2))) for v in self._levels]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        p = QPainter(self)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(TEXT_DIM))
        w = 3
        gap = 2
        x = 0
        h_max = self.height() - 2
        for level in self._levels:
            bar_h = max(2, int(h_max * level / 10))
            p.drawRect(x, h_max - bar_h, w, bar_h)
            x += w + gap


class NowPlayingScreen(QWidget):
    volume_changed = pyqtSignal(int)
    mute_toggled = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._playing = False
        self._muted = False
        self._listen_seconds = 0

        self.setStyleSheet(f"background: {PANEL_BLUE}; border: 1px solid {BORDER};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(3)

        top = QHBoxLayout()
        self._logo = QLabel()
        self._logo.setFixedSize(44, 44)
        self._logo.setAlignment(Qt.AlignCenter)
        self._logo.setStyleSheet(
            f"background: #FFFFFF; border: 1px solid {BORDER}; font-size: 18px;"
        )
        self._logo.setText("♪")
        top.addWidget(self._logo)

        info = QVBoxLayout()
        info.setSpacing(0)
        self._name = QLabel("Wybierz stację")
        self._name.setStyleSheet(
            f"color: {TEXT}; font-size: {FONT_SIZE_MEDIUM}px; font-weight: bold;"
        )
        info.addWidget(self._name)
        self._tags = QLabel("")
        self._tags.setStyleSheet(f"color: {TEXT_DIM}; font-size: {FONT_SIZE_SMALL}px;")
        info.addWidget(self._tags)
        self._subtitle = QLabel("Radio internetowe")
        self._subtitle.setStyleSheet(f"color: {TEXT_DIM}; font-size: {FONT_SIZE_SMALL}px;")
        info.addWidget(self._subtitle)
        top.addLayout(info, stretch=1)
        layout.addLayout(top)

        live_row = QHBoxLayout()
        live_left = QHBoxLayout()
        live_left.setSpacing(4)
        self._live_dot = QLabel("●")
        self._live_dot.setStyleSheet(f"color: {LIVE_RED}; font-size: 10px;")
        live_left.addWidget(self._live_dot)
        live_lbl = QLabel("LIVE")
        live_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: {FONT_SIZE_SMALL}px; font-weight: bold;"
        )
        live_left.addWidget(live_lbl)
        live_row.addLayout(live_left)

        self._activity = ActivityBars()
        live_row.addWidget(self._activity, stretch=1)

        self._timer_label = QLabel("00:00:00")
        self._timer_label.setStyleSheet(f"color: {TEXT}; font-size: {FONT_SIZE_SMALL}px;")
        live_row.addWidget(self._timer_label)
        layout.addLayout(live_row)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(6)
        self._vol_icon = QLabel("🔊")
        self._vol_icon.setFixedWidth(18)
        vol_row.addWidget(self._vol_icon)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(80)
        self._slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ height: 6px; background: #FFFFFF;"
            f"border: 1px solid {BORDER}; }}"
            f"QSlider::handle:horizontal {{ width: 14px; margin: -5px 0;"
            f"background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 7px; }}"
        )
        self._slider.valueChanged.connect(self._on_volume)
        vol_row.addWidget(self._slider, stretch=1)

        self._mute_btn = QPushButton()
        self._mute_btn.setFixedSize(28, 28)
        self._mute_btn.setStyleSheet(
            f"background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 14px;"
        )
        self._mute_btn.clicked.connect(self.mute_toggled.emit)
        vol_row.addWidget(self._mute_btn)
        layout.addLayout(vol_row)

        self._listen_timer = QTimer(self)
        self._listen_timer.timeout.connect(self._tick_listen)
        self._update_mute_icon()

    def _on_volume(self, value: int) -> None:
        self._update_vol_icon(value)
        self.volume_changed.emit(value)

    def _update_vol_icon(self, volume: int) -> None:
        if self._muted:
            self._vol_icon.setText("🔇")
        elif volume < 30:
            self._vol_icon.setText("🔈")
        else:
            self._vol_icon.setText("🔊")

    def _update_mute_icon(self) -> None:
        self._mute_btn.setText("🔇" if self._muted else "🔊")

    def set_station(self, name: str, tags: str = "", favicon: str = "") -> None:
        display = name if len(name) <= 24 else name[:22] + "…"
        self._name.setText(display)
        tag_display = tags if len(tags) <= 28 else tags[:26] + "…"
        self._tags.setText(tag_display)
        if favicon:
            self._logo.setText("")
            self._logo.setStyleSheet(
                f"background: #FFFFFF; border: 1px solid {BORDER};"
                f"background-image: url({favicon}); background-size: contain;"
            )
        else:
            self._logo.setText("♪")

    def set_metadata(self, meta: str) -> None:
        if meta:
            display = meta if len(meta) <= 28 else meta[:26] + "…"
            self._tags.setText(display)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        if playing:
            self._listen_timer.start(1000)
        else:
            self._listen_timer.stop()

    def reset_listen_timer(self) -> None:
        self._listen_seconds = 0
        self._timer_label.setText("00:00:00")

    def _tick_listen(self) -> None:
        if not self._playing:
            return
        self._listen_seconds += 1
        td = timedelta(seconds=self._listen_seconds)
        h, rem = divmod(int(td.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        self._timer_label.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def set_volume(self, level: int) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(level)
        self._slider.blockSignals(False)
        self._update_vol_icon(level)

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        self._update_mute_icon()
        self._update_vol_icon(self._slider.value())

    def volume(self) -> int:
        return self._slider.value()
