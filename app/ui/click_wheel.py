"""Virtual iPod click wheel for touch navigation."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from app.ui.theme import BORDER, CENTER_BTN, TEXT, TEXT_DIM, WHEEL_BG, WHEEL_DIAMETER, WHEEL_H


class ClickWheel(QWidget):
    menu_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()
    scroll_prev = pyqtSignal()
    scroll_next = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(WHEEL_H)
        self._playing = False
        self._dragging = False
        self._last_angle: float | None = None
        self._drag_accum = 0.0

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() // 2
        cy = self.height() // 2
        r = WHEEL_DIAMETER // 2

        p.setBrush(QColor(WHEEL_BG))
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawEllipse(QPointF(cx, cy), r, r)

        font = QFont("Sans Serif", 9, QFont.Bold)
        p.setFont(font)
        p.setPen(QColor(TEXT))
        p.drawText(cx - 18, cy - r + 16, "MENU")

        p.setPen(QColor(TEXT_DIM))
        p.drawText(cx - r + 6, cy + 4, "◀")
        p.drawText(cx + r - 14, cy + 4, "▶")

        cr = CENTER_BTN // 2
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawEllipse(QPointF(cx, cy), cr, cr)
        p.setPen(QColor(TEXT))
        if self._playing:
            p.drawText(cx - 5, cy + 5, "❚❚")
        else:
            p.drawText(cx - 4, cy + 5, "▶")

    def _center(self) -> QPointF:
        return QPointF(self.width() / 2, self.height() / 2)

    def _dist(self, pos) -> float:  # noqa: ANN001
        c = self._center()
        dx = pos.x() - c.x()
        dy = pos.y() - c.y()
        return math.hypot(dx, dy)

    def _angle(self, pos) -> float:  # noqa: ANN001
        c = self._center()
        return math.degrees(math.atan2(pos.y() - c.y(), pos.x() - c.x()))

    def _region(self, pos) -> str:  # noqa: ANN001
        d = self._dist(pos)
        cr = CENTER_BTN / 2
        if d <= cr:
            return "center"
        if d > WHEEL_DIAMETER / 2 + 4:
            return "outside"
        angle = self._angle(pos)
        if -135 <= angle <= -45:
            return "menu"
        if 135 <= angle or angle <= -135:
            return "prev"
        if 45 <= angle <= 135:
            return "next"
        return "ring"

    def mousePressEvent(self, event) -> None:  # noqa: ANN001, N802
        if event.button() != Qt.LeftButton:
            return
        region = self._region(event.pos())
        if region == "center":
            self.play_pause_clicked.emit()
        elif region == "menu":
            self.menu_clicked.emit()
        elif region == "prev":
            self.prev_clicked.emit()
        elif region == "next":
            self.next_clicked.emit()
        elif region == "ring":
            self._dragging = True
            self._last_angle = self._angle(event.pos())
            self._drag_accum = 0.0

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001, N802
        if not self._dragging or self._last_angle is None:
            return
        angle = self._angle(event.pos())
        delta = angle - self._last_angle
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        self._drag_accum += delta
        self._last_angle = angle
        if self._drag_accum >= 30:
            self.scroll_next.emit()
            self._drag_accum = 0
        elif self._drag_accum <= -30:
            self.scroll_prev.emit()
            self._drag_accum = 0

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001, N802
        del event
        self._dragging = False
        self._last_angle = None
